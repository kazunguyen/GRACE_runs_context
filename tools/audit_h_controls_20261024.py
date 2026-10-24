"""Offline audit of H1/H2/H3-A/H3-B evidence; never train, infer or alter sources.
All comparisons use one evaluator, canonical labels, paired IDs and saved predictions.
Run: python tools/audit_h_controls_20261024.py
"""
from pathlib import Path
from collections import Counter
from functools import lru_cache
import hashlib,json,math
import numpy as np
from scipy.stats import binomtest

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT.parent
OUT=ROOT/'audits/h_controls_20261024'
QWEN='publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas'
REGISTRY={}

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def register(p):
    p=Path(p).resolve();REGISTRY[str(p)]={'sha256':digest(p),'bytes':p.stat().st_size};return p
def read(p): return json.loads(register(p).read_text(encoding='utf-8-sig'))
def lines(p):
    p=register(p)
    with p.open(encoding='utf-8-sig') as f:return [json.loads(s) for s in f if s.strip()]
def indexed(rows):
    result={r['record_id']:r for r in rows}
    if len(result)!=len(rows):raise ValueError('Duplicate record IDs')
    return result
@lru_cache(maxsize=None)
def canonical(ds,split='test'):
    return indexed(lines(PARENT/f'GRACE-H1-SecurityProjection/data/{ds}/{split}.jsonl'))
def metrics(y,p):
    y=np.asarray(y,dtype=int);p=np.asarray([-1 if v is None else v for v in p],dtype=int)
    if not len(y) or len(y)!=len(p) or not np.isin(y,[0,1]).all():raise ValueError('Bad cohort')
    valid=np.isin(p,[0,1]);a=y[valid];b=p[valid]
    tn=int(((a==0)&(b==0)).sum());fp=int(((a==0)&(b==1)).sum())
    fn=int(((a==1)&(b==0)).sum());tp=int(((a==1)&(b==1)).sum())
    div=lambda n,d:n/d if d else None
    den=math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    rec=div(tp,tp+fn);specificity=div(tn,tn+fp)
    return {'n':len(y),'valid':int(valid.sum()),'invalid':int((~valid).sum()),
        'coverage':float(valid.mean()),'n0':int((y==0).sum()),'n1':int((y==1).sum()),
        'cm':{'tn':tn,'fp':fp,'fn':fn,'tp':tp},'accuracy':div(tp+tn,len(a)),
        'precision':div(tp,tp+fp),'recall':rec,'f1':div(2*tp,2*tp+fp+fn),
        'mcc':div(tp*tn-fp*fn,den),'balanced_accuracy':None if rec is None or specificity is None else (rec+specificity)/2,
        'predicted_positive_rate_all':float((p==1).mean())}

def paired(y,a,b,seed=42,draws=5000):
    y=np.asarray(y);a=np.asarray(a);b=np.asarray(b);n=len(y)
    left=metrics(y,a);right=metrics(y,b);keys=('mcc','f1','balanced_accuracy')
    rng=np.random.default_rng(seed);values={k:[] for k in keys}
    # Multinomial resampling of the eight (gold,left,right) categories is exactly
    # equivalent to paired IID query bootstrap, while retaining paired labels.
    codes=y*4+a*2+b;freq=np.bincount(codes,minlength=8)
    yy=np.array([i//4 for i in range(8)]);aa=np.array([(i//2)%2 for i in range(8)]);bb=np.array([i%2 for i in range(8)])
    def weighted(counts,p):
        tn=counts[(yy==0)&(p==0)].sum(axis=0);fp=counts[(yy==0)&(p==1)].sum(axis=0)
        fn=counts[(yy==1)&(p==0)].sum(axis=0);tp=counts[(yy==1)&(p==1)].sum(axis=0)
        den=np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
        with np.errstate(divide='ignore',invalid='ignore'):
            return {'mcc':(tp*tn-fp*fn)/den,'f1':2*tp/(2*tp+fp+fn),
                    'balanced_accuracy':(tp/(tp+fn)+tn/(tn+fp))/2}
    counts=rng.multinomial(n,freq/n,size=draws).astype(float).T
    ml=weighted(counts,aa);mr=weighted(counts,bb)
    for gold_result,point in ((left,weighted(freq.astype(float)[:,None],aa)),(right,weighted(freq.astype(float)[:,None],bb))):
        for metric in keys:
            if gold_result[metric] is not None and not math.isclose(float(point[metric][0]),gold_result[metric],abs_tol=1e-12):raise ValueError('Bootstrap category metric differs from per-ID metric')
    ci={};undefined={}
    for k in keys:
        v=mr[k]-ml[k];finite=np.isfinite(v);undefined[k]=int((~finite).sum())
        ci[k]=np.quantile(v[finite],[.025,.975]).tolist() if finite.any() else None
    improved=int(((a!=y)&(b==y)).sum());harmed=int(((a==y)&(b!=y)).sum())
    return {'common_valid_n':n,'left':left,'right':right,'delta_right_minus_left':{k:right[k]-left[k] for k in keys},
        'ci95_query_bootstrap':ci,'bootstrap':draws,'seed':seed,'undefined_bootstrap_draws':undefined,
        'improved':improved,'harmed':harmed,'same_prediction':int((a==b).sum()),
        'mcnemar_exact_two_sided_p':float(binomtest(improved,improved+harmed,.5).pvalue) if improved+harmed else 1.0,
        'trivial':{'always_vulnerable':metrics(y,np.ones(n,dtype=int)),'always_safe':metrics(y,np.zeros(n,dtype=int))},
        'inference_scope':'Exploratory post-hoc; no multiplicity adjustment; IID query CI, not cluster-adjusted; previously exposed test'}

def load_h1(ds,run):
    base=ROOT/'additional_runs/improvements_20261021/GRACE-H1-SecurityProjection'
    folder=next(base.rglob(run+'/predictions.jsonl')).parent
    pred=indexed(lines(folder/'predictions.jsonl'));prompts=indexed(lines(folder/'prompts.jsonl'))
    raw=indexed(lines(folder/'raw_responses_archive.jsonl'));gold=canonical(ds)
    kept={};specs=[];parse_mismatch=[]
    for rid,r in raw.items():
        spec=r.get('request_spec',{});p=prompts[rid]
        if spec.get('provider')!='Vertex AI' or spec.get('model')!=QWEN:continue
        if p['prompt_truncation']['context_limit']!=8192:continue
        q=pred[rid]
        if q['code_sha256']!=gold[rid]['code_sha256'] or r['prompt_sha256']!=p['prompt_sha256'] or q['prompt_sha256']!=p['prompt_sha256']:
            raise ValueError('H1 input identity mismatch: '+rid)
        if hashlib.sha256(p['prompt'].encode()).hexdigest()!=p['prompt_sha256']:raise ValueError('Prompt corrupt')
        text=r.get('raw_response') or '';last=next((s.strip() for s in reversed(text.splitlines()) if s.strip()),'')
        parsed=int(last) if last in ('0','1') else None
        if parsed!=q.get('prediction'):parse_mismatch.append(rid)
        kept[rid]=q;specs.append(spec)
    if parse_mismatch:raise ValueError('Stored H1 predictions disagree with raw parser')
    manifest=read(folder/'run_manifest.json')
    audit={'run_id':run,'records':len(pred),'eligible':len(kept),'excluded_unknown_or_other_request':len(pred)-len(kept),
        'valid':sum(q.get('prediction') in (0,1) for q in kept.values()),'raw_parse_disagreements':parse_mismatch,
        'inference_specs':list({json.dumps(x,sort_keys=True) for x in specs}),'common_pool_sha256':manifest.get('common_pool_sha256')}
    return kept,prompts,audit

def compare_rows(ds,left,right,lp=None,rp=None):
    gold=canonical(ds);ids=sorted(set(left)&set(right));valid=[rid for rid in ids if left[rid].get('prediction') in (0,1) and right[rid].get('prediction') in (0,1)]
    y=[gold[rid]['label'] for rid in valid];a=[left[rid]['prediction'] for rid in valid];b=[right[rid]['prediction'] for rid in valid]
    result=paired(y,a,b)
    result['cohort']={'left_ids':len(left),'right_ids':len(right),'shared_ids':len(ids),'excluded_invalid_on_shared':len(ids)-len(valid),
        'ordered_valid_id_sha256':hashlib.sha256('\n'.join(valid).encode()).hexdigest()}
    if lp and rp:
        result['same_rendered_prompt_n']=sum(lp[rid]['prompt_sha256']==rp[rid]['prompt_sha256'] for rid in valid)
        result['same_query_graph_n']=sum(lp[rid].get('graph_feature_sha256')==rp[rid].get('graph_feature_sha256') for rid in valid)
        result['same_selected_demo_n']=sum(lp[rid].get('selected_demo_ids')==rp[rid].get('selected_demo_ids') for rid in valid)
        same=[rid for rid in valid if lp[rid]['prompt_sha256']==rp[rid]['prompt_sha256']]
        result['same_prompt_prediction_disagreement_n']=sum(left[rid]['prediction']!=right[rid]['prediction'] for rid in same)
        result['changed_demo_but_identical_prompt_n']=sum(lp[rid].get('selected_demo_ids')!=rp[rid].get('selected_demo_ids') for rid in same)
        result['empty_demo_render_n']={'left':sum(not any(lp[rid]['prompt_truncation'].get('demo_chars_used',[])) for rid in valid),'right':sum(not any(rp[rid]['prompt_truncation'].get('demo_chars_used',[])) for rid in valid)}
        result['scope_note']='Same-prompt predictions may still vary across independent LLM calls; raw paired differences do not isolate retrieval without a repeat control.'
    result['changed_examples']=[{'record_id':rid,'gold':gold[rid]['label'],'left':left[rid]['prediction'],'right':right[rid]['prediction']} for rid in valid if left[rid]['prediction']!=right[rid]['prediction']][:12]
    return result

def expert_spec(m):
    identity=m.get('identity',m);params=identity.get('inference',m.get('parameters',{}))
    return {'model':identity.get('model',params.get('model')),'provider':identity.get('provider'),
        'endpoint':identity.get('endpoint',identity.get('url')),'temperature':params.get('temperature'),'seed':params.get('seed'),
        'max_tokens':params.get('max_tokens'),'thinking':params.get('chat_template_kwargs',{}).get('thinking'),
        'context':identity.get('context_limit_utf8_bytes')}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={'schema':'h_controls_evidence_audit_v1','date':'2026-10-24','new_api_calls':0,'training_runs':0,
        'evaluator_policy':'Canonical gold, positive=1; invalid retained in coverage, paired inference on common valid IDs; undefined metrics=null',
        'H1':{},'H3A':{},'H3B':{},'H2':{}}
    baselines={}
    for ds,baseline,v1 in [('devign','9afe3268729648c6','7c4a52705268af6f'),('reveal','0779c879b6d11431','d318d1344264b913')]:
        left,lp,la=load_h1(ds,baseline);baselines[ds]=left
        for version,run in [('V1',v1)]+([('V2','98d7f32cd098d4c0')] if ds=='reveal' else []):
            right,rp,ra=load_h1(ds,run);result=compare_rows(ds,left,right,lp,rp);result['left_audit']=la;result['right_audit']=ra
            result['same_common_pool_manifest']=la['common_pool_sha256']==ra['common_pool_sha256']
            report['H1'][ds+'_'+version]=result
        folder=ROOT/'audits/h3a_h1_baseline_reuse_20261022'
        cascade=indexed(lines(folder/f'{ds}_h1_expert_cascade_predictions.jsonl'))
        for rid,row in cascade.items():
            if row['code_sha256']!=canonical(ds)[rid]['code_sha256']:raise ValueError('Cascade code differs')
        report['H3A'][ds]={'cascade_vs_full':compare_rows(ds,left,cascade),
            'gate_vs_full':compare_rows(ds,left,{rid:dict(row,prediction=row['gate_prediction']) for rid,row in cascade.items()}),
            'branches':dict(Counter(row['branch'] for row in cascade.values())),'source':read(folder/f'{ds}_h1_expert_evaluation.json')}
    session=PARENT/'GRACE-H3-BenchmarkEnsemble/runs/h3v2/notebook_sessions/deepseek_v41_hieu_8192_seed42'
    lock=read(session/'winner_lock.json');checksum=read(session/'winner_lock_checksum.json')
    if digest(session/'winner_lock.json')!=checksum['sha256']:raise ValueError('Winner lock checksum')
    for job in lock['jobs']:
        ds=job['dataset'];folder=session/f'test/{ds}/42';manifest=read(folder/'manifest.json');evaluation=read(folder/'evaluation.json')
        for stage in ('base','meta'):
            model_manifest=PARENT/'GRACE-H3-BenchmarkEnsemble'/job[stage+'_folder']/'manifest.json'
            if digest(register(model_manifest))!=job[stage+'_manifest_sha256']:raise ValueError('Changed locked model manifest')
        if evaluation['winner_lock_sha256']!=digest(session/'winner_lock.json'):raise ValueError('Wrong test lock')
        arms={}
        for arm,expected in manifest['files'].items():
            path=folder/(arm+'.jsonl')
            if digest(register(path))!=expected:raise ValueError('Changed H3B prediction')
            records=indexed(lines(path));gold=canonical(ds)
            if any(q['code_sha256']!=gold[rid]['code_sha256'] for rid,q in records.items()):raise ValueError('H3B code differs')
            ids=sorted(records);m=metrics([gold[rid]['label'] for rid in ids],[records[rid]['prediction'] for rid in ids])
            stored=evaluation['arms'][arm]['metrics']
            for key in ('mcc','f1','precision','recall'):
                if m[key] is None:
                    if stored[key] not in (None,0):raise ValueError('H3B undefined metric differs')
                elif not math.isclose(m[key],stored[key],abs_tol=1e-12):raise ValueError('H3B stored metric differs')
            arms[arm]={'metrics':m,'query_ratio':evaluation['arms'][arm]['algorithmic_expert_query_ratio'],'rows':records}
        winner=job['winner']['name'];comparisons={}
        for control in ('full_grace','gate_0_5', 'base_'+job['base_winner']['name']):
            comparisons[control]=compare_rows(ds,arms[control]['rows'],arms[winner]['rows'])
        report['H3B'][ds]={'winner':winner,'threshold':job['winner']['threshold'],
            'lock_sha256':digest(session/'winner_lock.json'),'test_labels_used_in_selection_declared':lock['test_labels_used'],
            'expert_shift':manifest.get('expert_shift'),'benchmark_comparable':manifest['benchmark_comparable'],
            'arms':{k:{'metrics':v['metrics'],'query_ratio':v['query_ratio']} for k,v in arms.items()},'paired':comparisons}
        hp=ROOT/f'additional_runs/kaggle_deepseek_v41_20261023/{ds}'
        predictions=indexed(lines(hp/'predictions.jsonl'));gold=canonical(ds)
        if set(predictions)!=set(gold):raise ValueError('H2 target cohort differs')
        if any(p['code_sha256']!=gold[rid]['code_sha256'] for rid,p in predictions.items()):raise ValueError('H2 code differs')
        spec=expert_spec(read(hp/'run_manifest.json'));testspec=manifest['expert_identity']['expert_spec']
        report['H2'][ds]={'metrics':metrics([gold[rid]['label'] for rid in sorted(predictions)],[predictions[rid]['prediction'] for rid in sorted(predictions)]),
            'expert_spec':spec,'same_test_target_code_n':len(predictions),'controls_complete':False,
            'comparison_to_fpt_baseline':'Not an isolated H2 effect: different provider/thinking declaration and graph/demo packaging policies',
            'new_test_baseline_expert_spec':testspec}
    report['source_files']=REGISTRY
    report['audit_script_sha256']=digest(Path(__file__))
    (OUT/'audit_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for section in ('H1','H3A','H3B'):
        for key,r in report[section].items():
            pair=r if section=='H1' else r['cascade_vs_full'] if section=='H3A' else r['paired']['full_grace']
            print(section,key,'n=',pair['common_valid_n'],'delta_MCC=',pair['delta_right_minus_left']['mcc'],'CI=',pair['ci95_query_bootstrap']['mcc'])
    print('Sources:',len(REGISTRY),'output:',OUT/'audit_results.json')
if __name__=='__main__':main()
