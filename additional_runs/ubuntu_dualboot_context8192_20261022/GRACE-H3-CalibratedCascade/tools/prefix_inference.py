"""Call a stable prefix of frozen prompts, reusing the shared exact-request cache."""
from pathlib import Path
import math
import shutil
from grace_h1.io import read_json, write_json, write_jsonl, iter_jsonl, file_hash
from grace_h1.pipeline import verify_frozen
from grace_h1.inference import run_inference, request_spec, request_key, read_cached
from grace_h3.workflow import selected_jobs, merge_predictions


def _prefix_view(root, source, percent):
    if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not math.isfinite(percent) or not 0 <= percent <= 100:
        raise ValueError('LLM_PROMPT_PERCENT must be a finite number from 0 to 100')
    manifest = verify_frozen(root, source)
    prompts = list(iter_jsonl(source / 'prompts.jsonl'))
    count = math.ceil(len(prompts) * percent / 100)
    view = source / 'inference_prefix' / f'first_{count:06d}'
    view.mkdir(parents=True, exist_ok=True)
    write_jsonl(view / 'prompts.jsonl', prompts[:count])
    selected_manifest = dict(manifest, target_count=count,
                             prefix_selection={'source_run':source.relative_to(root).as_posix(),
                                               'total_prompts':len(prompts), 'selected_prompts':count,
                                               'order':'original prompts.jsonl order'})
    write_json(view / 'run_manifest.json', selected_manifest)
    files = [view/'prompts.jsonl', view/'run_manifest.json', source/'freeze.json']
    write_json(view/'freeze.json', {'files':{p.relative_to(root).as_posix():file_hash(p) for p in files}})
    return view, prompts, count


def run_prefix_all(root, config, *, percent=50, allow_api=False):
    root = Path(root).resolve()
    reports = []
    for folder, job in selected_jobs(root, config):
        source_reports = {}
        for relative in dict.fromkeys(job[k] for k in ('inspect_path','reference_path') if job.get(k)):
            source = root / relative
            view, all_prompts, count = _prefix_view(root, source, percent)
            spec = request_spec(root)
            cached_all = sum(read_cached(root, request_key(p['prompt_sha256'],spec),p['prompt_sha256'],spec) is not None
                             for p in all_prompts)
            print(f'{job["dataset"]}: first {count}/{len(all_prompts)} prompts ({percent}%); '
                  f'already successful across full set: {cached_all}/{len(all_prompts)}', flush=True)
            report = run_inference(root, view, allow_api=allow_api, workers=config['inference_workers'])
            cached_after = sum(read_cached(root, request_key(p['prompt_sha256'],spec),p['prompt_sha256'],spec) is not None
                               for p in all_prompts)
            report.update(prompt_percent=percent, selected_prompts=count, total_prompts=len(all_prompts),
                          successful_prompts_total=cached_after, source_run=relative,
                          prefix_output=view.relative_to(root).as_posix())
            write_json(view/'prefix_summary.json', report)
            source_reports[relative] = report
            # Only promote full-cohort results; partial runs never overwrite complete predictions.
            if count == len(all_prompts) and (view/'predictions.jsonl').is_file() and report['status'] != 'prepared_cache_only':
                for name in ('predictions.jsonl','raw_responses.jsonl','inference_summary.json'):
                    shutil.copy2(view/name, source/name)
        cascade = source_reports.get(job.get('inspect_path'), {'status':'complete','queries':0})
        reference = source_reports.get(job.get('reference_path'))
        full = percent == 100 and all(r['status'] == 'complete' for r in source_reports.values())
        result = {'dataset':job['dataset'], 'status':'complete' if full else 'partial_or_planned',
                  'prompt_percent':percent, 'cascade':cascade, 'reference_incremental':reference,
                  'algorithmic_llm_query_ratio':job['branch_counts'].get('inspect',0)/job['n'],
                  'branch_counts':job['branch_counts'], 'n':job['n']}
        if full:
            merge_predictions(root, folder, job)
            write_json(folder/'inference_summary.json',result)
        write_json(folder/'prefix_inference_summary.json',result)
        reports.append(result)
    return reports


def evaluate_cached_all(root, config):
    """Evaluate successful current-model responses, including unparseable answers in invalid rate."""
    from grace_h1.data import load_rows
    from grace_h1.metrics import binary_metrics
    from grace_h1.parser import parse_prediction
    root = Path(root).resolve()
    spec = request_spec(root)
    datasets = []
    for folder, job in selected_jobs(root, config):
        labeled = {r['record_id']:r for r in load_rows(root,job['dataset'],config['split'],labels=True)}
        routes = {r['record_id']:r for r in iter_jsonl(folder/'routing.jsonl')}
        report = {'dataset':job['dataset'], 'cohort_n':len(labeled), 'branches':job['branch_counts'],
                  'status':'complete', 'coverage':{},
                  'note':'Metrics use only successful cached API responses for the current prompt/model settings. '
                         'Uncalled/failed requests are excluded; successful but unparseable answers remain in invalid_rate. '
                         'A prefix is not necessarily representative of the full test set.'}
        for arm, key in [('cascade','inspect_path'),('full_reference','reference_path')]:
            relative = job.get(key)
            if not relative:
                continue
            source = root/relative
            verify_frozen(root,source)
            prompts = list(iter_jsonl(source/'prompts.jsonl'))
            predictions = []
            for p in prompts:
                cached = read_cached(root,request_key(p['prompt_sha256'],spec),p['prompt_sha256'],spec)
                if cached is None:
                    continue
                target = labeled[p['record_id']]
                if target['code_sha256'] != p['code_sha256']:
                    raise ValueError('Evaluation code identity mismatch')
                parsed = parse_prediction(cached['raw_response'])
                predictions.append({'record_id':p['record_id'],'label':target['label'],
                                    'prediction':parsed.prediction,'parse_status':parsed.parse_status,
                                    'prompt_sha256':p['prompt_sha256']})
            n = len(predictions)
            report['coverage'][arm] = {'inferred_n':n,'total_prompts':len(prompts),
                                      'pending_n':len(prompts)-n,
                                      'inferred_percent':100*n/len(prompts) if prompts else 100,
                                      'inference_complete':n==len(prompts)}
            if n < len(prompts):
                report['status']='partial'
            if predictions:
                labels = [p['label'] for p in predictions]
                report[arm] = binary_metrics(labels,[p['prediction'] for p in predictions])
                report[arm]['evaluation_scope']='successful_inference_subset'
                if arm == 'cascade':
                    report['gate_only'] = binary_metrics(labels,[routes[p['record_id']]['gate_prediction'] for p in predictions])
                    report['gate_only']['evaluation_scope']='same_inferred_subset_as_cascade'
            write_jsonl(folder/f'partial_{arm}_evaluated_predictions.jsonl',predictions)
        write_json(folder/'partial_evaluation.json',report)
        datasets.append(report)
    summary = {'config':config,'status':'complete' if all(r['status']=='complete' for r in datasets) else 'partial',
               'request_spec':spec,'datasets':datasets,
               'note':'Chưa inference xong nếu status=partial. Metrics chỉ tính trên các phản hồi API thành công đã có.'}
    write_json(root/'runs/partial_experiment_summary.json',summary)
    return summary
