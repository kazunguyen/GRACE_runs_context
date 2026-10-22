"""Re-fit oversized prompts with the historical UTF-8 byte cap; preserve frozen source runs."""
from pathlib import Path
import math
import yaml
from grace_h1.io import read_json,write_json,write_jsonl,iter_jsonl,file_hash,fingerprint,sha256
from grace_h1.pipeline import verify_frozen, INSTRUCTION
from grace_h1.graphs import GraphStore
from grace_h1.reference import raw_graph_context,fit_contracted_prompt
from grace_h1.data import load_rows
from grace_h1.inference import run_inference,request_spec,request_key,read_cached
from grace_h1.parser import parse_prediction
from grace_h1.metrics import binary_metrics
from grace_h3.workflow import selected_jobs
from prefix_inference import _prefix_view


def prepare_context_view(root, source, dataset, split, limit):
    if isinstance(limit,bool) or not isinstance(limit,int) or limit<=0:
        raise ValueError('OLD_CONTEXT_LIMIT_BYTES must be a positive integer')
    manifest=verify_frozen(root,source)
    original=list(iter_jsonl(source/'prompts.jsonl'))
    identity={'source_freeze_sha256':file_hash(source/'freeze.json'),
              'limit_bytes':limit,'fitter_sha256':file_hash(Path(__file__).parents[1]/'grace_h1/reference.py'),
              'builder_sha256':file_hash(Path(__file__)), 'policy':'refit_only_oversized_keep_demo_graph_target_prefix_order'}
    view=root/'runs/context_limit_rerun'/dataset/split/fingerprint(identity)[:16]
    if (view/'freeze.json').exists():
        verify_frozen(root,view)
        return view,original,list(iter_jsonl(view/'prompts.jsonl')),read_json(view/'context_profile.json')
    contract=yaml.safe_load((root/'configs/reference_contract.yaml').read_text())
    policy=dict(contract['prompt_context_policy']['truncation_policy'])
    policy['context_limit']=limit
    old_policy=dict(policy,context_limit=contract['prompt_context_policy']['context_limit'])
    template=(root/'configs/prompt_template.txt').read_text()
    targets={r['record_id']:r for r in load_rows(root,dataset,split)}
    train=None
    graphs=GraphStore(root)
    updated=[];changes=[]
    for prompt in original:
        size=len(prompt['prompt'].encode('utf-8'))
        row=dict(prompt)
        if size>limit:
            if train is None:
                train={r['record_id']:r for r in load_rows(root,dataset,'train',labels=True)}
            target=targets[prompt['record_id']]
            graph=graphs.get(prompt['code_sha256'])
            if graph['feature_sha256']!=prompt['graph_feature_sha256']:
                raise ValueError('Frozen prompt graph differs from current cache')
            demos=[train[rid] for rid in prompt['selected_demo_ids']]
            graph_text,counts=raw_graph_context(graph,policy)
            # Check that reconstruction uses the exact original source/template/demos.
            rebuilt,_=fit_contracted_prompt(template,target['code'],graph_text,demos,INSTRUCTION,old_policy)
            if rebuilt!=prompt['prompt']:
                raise ValueError(f'Cannot exactly reconstruct original prompt: {prompt["record_id"]}')
            text,metadata=fit_contracted_prompt(template,target['code'],graph_text,demos,INSTRUCTION,policy)
            row.update(prompt=text,prompt_sha256=sha256(text),prompt_truncation=metadata,graph_counts=counts)
            changes.append({'record_id':prompt['record_id'],'old_prompt_sha256':prompt['prompt_sha256'],
                            'new_prompt_sha256':row['prompt_sha256'],'old_bytes':size,
                            'new_bytes':len(text.encode('utf-8'))})
        else:
            # Unchanged bytes => same exact request cache, even though the profile is now 8192.
            row['prompt_truncation']=dict(prompt['prompt_truncation'],context_limit=limit,
                                         prompt_utf8_bytes=size,context_refit_unchanged=True)
        row['source_prompt_sha256']=prompt['prompt_sha256']
        assert len(row['prompt'].encode('utf-8'))<=limit
        updated.append(row)
    assert [(p['record_id'],p['code_sha256']) for p in original]==[(p['record_id'],p['code_sha256']) for p in updated]
    view.mkdir(parents=True,exist_ok=True)
    profile={'identity':identity,'dataset':dataset,'split':split,'limit_bytes':limit,
             'total_prompts':len(updated),'oversized_prompts':len(changes),'changes':changes,
             'source_run':source.relative_to(root).as_posix(),
             'unit':'UTF-8 bytes, not measured model tokens'}
    write_jsonl(view/'prompts.jsonl',updated)
    write_json(view/'context_profile.json',profile)
    write_json(view/'run_manifest.json',dict(manifest,target_count=len(updated),context_profile=profile['identity']))
    paths=[view/'prompts.jsonl',view/'run_manifest.json',view/'context_profile.json',source/'freeze.json']
    write_json(view/'freeze.json',{'files':{p.relative_to(root).as_posix():file_hash(p) for p in paths}})
    return view,original,updated,profile


def _metrics_from_cache(root,prompts,spec,labels):
    evaluated=[]
    for p in prompts:
        response=read_cached(root,request_key(p['prompt_sha256'],spec),p['prompt_sha256'],spec)
        if response is None:continue
        target=labels[p['record_id']]
        if target['code_sha256']!=p['code_sha256']:raise ValueError('Evaluation identity mismatch')
        parsed=parse_prediction(response['raw_response'])
        evaluated.append({'record_id':p['record_id'],'code_sha256':p['code_sha256'],
                          'sealed_label':target['label'],'prediction':parsed.prediction,
                          'parse_status':parsed.parse_status,'prompt_sha256':p['prompt_sha256'],
                          'request_key':response['request_key']})
    metrics=binary_metrics([p['sealed_label'] for p in evaluated],[p['prediction'] for p in evaluated]) if evaluated else None
    return metrics,evaluated


def run_context_limit(root,config,*,percent=50,limit=8192,allow_api=False):
    if isinstance(percent,bool) or not isinstance(percent,(int,float)) or not math.isfinite(percent) or not 0<=percent<=100:
        raise ValueError('LLM_PROMPT_PERCENT must be from 0 to 100')
    root=Path(root).resolve();spec=request_spec(root);reports=[]
    for folder,job in selected_jobs(root,config):
        labels={r['record_id']:r for r in load_rows(root,job['dataset'],config['split'],labels=True)}
        for relative in dict.fromkeys(job[k] for k in ('inspect_path','reference_path') if job.get(k)):
            source=root/relative
            view,original,updated,profile=prepare_context_view(root,source,job['dataset'],config['split'],limit)
            selected,_,count=_prefix_view(root,view,percent)
            changed=sum(p['prompt_sha256']!=old['prompt_sha256'] for p,old in zip(updated[:count],original[:count]))
            uncached_changed=sum(p['prompt_sha256']!=old['prompt_sha256'] and
                                 read_cached(root,request_key(p['prompt_sha256'],spec),p['prompt_sha256'],spec) is None
                                 for p,old in zip(updated[:count],original[:count]))
            print(f'{job["dataset"]}/{config["split"]}: first {count}/{len(updated)} ({percent}%); '
                  f'cap={limit} UTF-8 bytes; oversized in selected cohort={changed}; '
                  f'changed prompts needing new calls={uncached_changed}',flush=True)
            inference=run_inference(root,selected,allow_api=allow_api,workers=config['inference_workers'])
            metrics,evaluated=_metrics_from_cache(root,updated[:count],spec,labels)
            old_metrics,old_evaluated=_metrics_from_cache(root,original[:count],spec,labels)
            # Paired descriptive comparison uses the SAME record IDs available under both profiles.
            common={p['record_id'] for p in evaluated}&{p['record_id'] for p in old_evaluated}
            paired={}
            for name,records in [('old_context',old_evaluated),('limited_context',evaluated)]:
                records=[p for p in records if p['record_id'] in common]
                paired[name]=binary_metrics([p['sealed_label'] for p in records],[p['prediction'] for p in records]) if records else None
            report={'dataset':job['dataset'],'split':config['split'],'limit_bytes':limit,
                    'prompt_percent':percent,'selected_prompts':count,'total_prompts':len(updated),
                    'oversized_selected':changed,'oversized_full_dataset':profile['oversized_prompts'],
                    'inferred_selected':len(evaluated),'pending_selected':count-len(evaluated),
                    'pending_full_dataset':len(updated)-len(evaluated),
                    'status':'complete' if len(evaluated)==len(updated) else 'partial',
                    'selected_prefix_complete':len(evaluated)==count,
                    'request_spec':spec,'inference':inference,'metrics':metrics,
                    'old_context_same_selected_prefix_metrics':old_metrics,
                    'paired_common_record_n':len(common),'paired_common_record_metrics':paired,
                    'output':selected.relative_to(root).as_posix(),
                    'note':'Metrics on successful responses within the selected dataset prefix only; '
                           'unparseable successful responses retained in invalid_rate. '
                           'Old oversized prompt responses are never used for changed prompt hashes. '
                           'This normalizes context size, not other historical model/graph/retrieval differences.'}
            write_jsonl(selected/'evaluated_predictions.jsonl',evaluated)
            write_json(selected/'context_benchmark.json',report)
            print('Context benchmark saved:',selected/'context_benchmark.json',flush=True)
            reports.append(report)
    write_json(root/'runs/context_limit_benchmark_latest.json',{'percent':percent,'limit_bytes':limit,'reports':reports})
    return reports
