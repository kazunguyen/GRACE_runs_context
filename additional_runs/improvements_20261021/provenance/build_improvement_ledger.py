from pathlib import Path
import collections
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).parent))
import publish_improvements as pub

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def rows(p):
    if not p.is_file():
        return []
    return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]

def metric(y, pred):
    pairs = [(a,b) for a,b in zip(y,pred) if b in (0,1)]
    tn=sum(a==b==0 for a,b in pairs);tp=sum(a==b==1 for a,b in pairs)
    fp=sum(a==0 and b==1 for a,b in pairs);fn=sum(a==1 and b==0 for a,b in pairs)
    div=lambda a,b:a/b if b else 0.0
    return {'n':len(y),'valid_n':len(pairs),'invalid_n':len(y)-len(pairs),
            'precision':div(tp,tp+fp),'recall':div(tp,tp+fn),'f1':div(2*tp,2*tp+fp+fn),
            'accuracy_all':div(tp+tn,len(y)),
            'balanced_accuracy':(div(tp,tp+fn)+div(tn,tn+fp))/2,
            'mcc':div(tp*tn-fp*fn,math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))),
            'confusion_matrix_valid_only':{'tn':tn,'fp':fp,'fn':fn,'tp':tp}}

def link(p, label):
    if p is None or not p.exists():
        return '—'
    return f'[{label}](<{p.relative_to(pub.SHARE).as_posix()}>)'

def notebook(root):
    return root/'notebooks/full-pipeline.ipynb'

def main():
    entries=[];prepared=[];missing=[]
    for name in pub.NAMES:
        source=pub.BASE/name
        archive=pub.SHARE/pub.DEST/name
        labels={}
        for ds in ['devign','reveal']:
            for split in ['validation','test']:
                labels[(ds,split)]={r['record_id']:r['label'] for r in rows(source/f'data/{ds}/{split}.jsonl')}
        # Includes original historical Devign runs and preserved before-recovery versions.
        for mp in sorted(archive.rglob('run_manifest.json')):
            if mp.relative_to(archive).parts[0] not in {'runs','archives'}:
                continue
            m=read(mp);cfg=m.get('config',{});ds=cfg.get('dataset');split=cfg.get('split')
            if ds not in ['devign','reveal'] or split not in ['validation','test']:
                continue
            folder=mp.parent;pp=folder/'predictions.jsonl';sp=folder/'inference_summary.json'
            if not pp.is_file() or not sp.is_file():
                prepared.append({'project':name,'path':folder.relative_to(archive).as_posix(),'status':'prepared_only'})
                continue
            summary=read(sp);pred=rows(pp);prompt=rows(folder/'prompts.jsonl')
            if not isinstance(summary,dict) or 'request_spec' not in summary:
                continue
            y=[labels[(ds,split)][r['record_id']] for r in pred]
            met=metric(y,[p.get('prediction') for p in pred])
            spec=summary['request_spec'];counts=collections.Counter(y)
            caps=collections.Counter(p.get('effective_context_limit_utf8_bytes',p.get('prompt_truncation',{}).get('context_limit')) for p in prompt)
            # Materialize the response rows supporting this exact prediction file.
            raw=[];unavailable=0
            for p in pred:
                key=p.get('request_key');candidates=[folder/'requests'/f'{key}.json',archive/'cache/responses'/f'{key}.json']
                candidates += [pub.SHARE/pub.DEST/other/'cache/responses'/f'{key}.json' for other in pub.NAMES if other != name]
                if 'archives' in folder.parts:
                    idx=folder.parts.index('archives');historical=Path(*folder.parts[:idx+3])
                    candidates.insert(1,historical/'cache/responses'/f'{key}.json')
                found=None
                for cp in candidates:
                    if cp.is_file():
                        q=read(cp)
                        if q.get('request_key')==key and q.get('prompt_sha256')==p.get('prompt_sha256') and q.get('request_status')==p.get('request_status'):
                            last=next((s.strip() for s in reversed(q.get('raw_response','').splitlines()) if s.strip()),'')
                            if p.get('prediction') in (0,1) and last != str(p['prediction']):
                                continue
                            found={**q,'archive_raw_source':cp.relative_to(pub.SHARE).as_posix()};break
                if found is None:
                    unavailable+=1
                    found={'request_key':key,'prompt_sha256':p.get('prompt_sha256'),
                           'raw_response_unavailable':True,'request_status':p.get('request_status')}
                raw.append({'record_id':p['record_id'],**found})
            rp=folder/'raw_responses_archive.jsonl'
            rp.write_bytes((''.join(json.dumps(q,ensure_ascii=False)+'\n' for q in raw)).encode())
            # Keep a complete, per-run raw file in its source project too, including reused requests.
            source_folder=source/folder.relative_to(archive)
            if pub.sha((source_folder/'predictions.jsonl').read_bytes()) != pub.sha(pp.read_bytes()):
                raise RuntimeError(f'Prediction source changed while building ledger: {source_folder}')
            (source_folder/rp.name).write_bytes(rp.read_bytes())
            if unavailable:missing.append({'project':name,'run':str(folder.relative_to(archive)),'missing_raw_rows':unavailable})
            ep=folder/'ledger_metrics.json';pub.dump(ep,{'metrics':met,'source':'Recomputed offline from archived predictions and canonical source labels; invalid retained, excluded from binary confusion matrix.',
                                                    'n0':counts[0],'n1':counts[1], 'raw_unavailable_n':unavailable})
            (source_folder/ep.name).write_bytes(ep.read_bytes())
            entry={'project':name,'run':folder.relative_to(archive).as_posix(),'dataset':ds,'split':split,'arm':cfg.get('arm'),
                   'status':summary.get('status'),'n0':counts[0],'n1':counts[1],'metrics':met,'request_spec':spec,
                   'context_limits':{str(k):v for k,v in caps.items()},'mixed_model_recovery':bool(summary.get('mixed_model_recovery')),
                   'artifact_paths':{'notebook':str(notebook(archive).relative_to(pub.SHARE)),
                                     'prompts':str((folder/'prompts.jsonl').relative_to(pub.SHARE)),
                                     'predictions':str(pp.relative_to(pub.SHARE)),'raw_responses':str(rp.relative_to(pub.SHARE)),
                                     'manifest':str(mp.relative_to(pub.SHARE)),'metrics':str(ep.relative_to(pub.SHARE))},
                   'raw_unavailable_n':unavailable}
            entries.append(entry)
            print('RUN',name,ds,split,folder.name,'raw_missing',unavailable,flush=True)
    # Derived H3 arms share expert requests; do not count these as fresh LLM runs.
    derived=[]
    name='GRACE-H3-BenchmarkEnsemble';archive=pub.SHARE/pub.DEST/name
    for p in sorted((archive/'runs/h3v2').rglob('benchmark_summary.json')):
        s=read(p)
        for d in s['datasets']:
            for arm,a in d['arms'].items():
                derived.append({'project':name,'dataset':d['dataset'],'split':'test','arm':arm,
                                'selected_before_test':arm==d['locked_development_winner'],
                                'historical': 'archive' in p.parts,'context_limits':s.get('effective_context_limits'),
                                'metrics':a['metrics'],'algorithmic_expert_query_ratio':a.get('algorithmic_expert_query_ratio'),
                                'report':str(p.relative_to(pub.SHARE)),'benchmark_comparable':s.get('benchmark_comparable')})
    name='GRACE-H3-CalibratedCascade';archive=pub.SHARE/pub.DEST/name
    for p in (archive/'runs/h3').rglob('evaluation.json'):
        s=read(p)
        for arm in ['full_reference','cascade','gate_only']:
            if arm in s:
                derived.append({'project':name,'dataset':s['dataset'],'split':'test','arm':arm,'metrics':s[arm],
                                'report':str(p.relative_to(pub.SHARE)), 'algorithmic_call_saving':s.get('algorithmic_call_saving')})
    obj={'schema':'grace_improvement_run_ledger_v1','updated':'2026-10-21','llm_runs':entries,'derived_arms':derived,
         'prepared_only':prepared,'missing_raw':missing,'h2':read(pub.SHARE/pub.DEST/'publication_manifest.json')['h2']['publication_update_20261021'],
         'scope':'Separate from original 36-run ledger. Includes historical/partial runs with explicit status; metrics are descriptive, not proof of improvement.'}
    pub.dump(pub.SHARE/'bang_quan_ly_run_cai_tien.json',obj)
    md=['# Bảng quản lý run cải tiến H1, H2, H3','',
        'Cập nhật: **21/10/2026**. Bảng riêng cho các cải tiến; không cộng vào 36 run trong `bang_quan_ly_run.md`.', '',
        "H2 đã công bố mã nguồn và bốn notebook trên nhánh `main`, commit [`4a23088`](https://github.com/kazunguyen/GRACE-H2-GuardedEvidence/commit/4a230882b265b8d86c306f0aacdaa00f497ca6e7). Xem [full pipeline](https://github.com/kazunguyen/GRACE-H2-GuardedEvidence/blob/4a230882b265b8d86c306f0aacdaa00f497ca6e7/notebooks/full-pipeline.ipynb), [bản Ubuntu](https://github.com/kazunguyen/GRACE-H2-GuardedEvidence/blob/4a230882b265b8d86c306f0aacdaa00f497ca6e7/notebooks/full-pipeline-ubuntu.ipynb), [Kaggle accelerator](https://github.com/kazunguyen/GRACE-H2-GuardedEvidence/blob/4a230882b265b8d86c306f0aacdaa00f497ca6e7/notebooks/kaggle_accelerator.ipynb) và [Kaggle CPU](https://github.com/kazunguyen/GRACE-H2-GuardedEvidence/blob/4a230882b265b8d86c306f0aacdaa00f497ca6e7/notebooks/kaggle_cpu_pipeline.ipynb). Việc công bố code không đồng nghĩa đã hoàn tất benchmark H2; dữ liệu và runtime đang chạy được giữ nguyên trên máy.", '',
        '## Repository và nhánh','',
        '| Project | Origin | Nhánh lưu kết quả |',
        '|---|---|---|',
        '| H1 | [GRACE-H1-SecurityProjection](https://github.com/kazunguyen/GRACE-H1-SecurityProjection) | `projection-v2-local-metric`; cả `main`, `devign`, `reveal` cũng đã push |',
        '| H2 | [GRACE-H2-GuardedEvidence](https://github.com/kazunguyen/GRACE-H2-GuardedEvidence) | `main`; code và notebook đã push (`4a23088`) |',
        '| H3 Cascade | [GRACE-H3-CalibratedCascade](https://github.com/kazunguyen/GRACE-H3-CalibratedCascade) | `main` |',
        '| H3 Ensemble | [GRACE-H3-BenchmarkEnsembled](https://github.com/kazunguyen/GRACE-H3-BenchmarkEnsembled) | `feat/h3-v2-benchmark` |', '',
        '## Quy ước','',
        '- `complete` là inference hoàn tất; `partial_request_errors` chưa đủ request, không dùng làm kết luận benchmark hoàn chỉnh.',
        '- Context là UTF-8 bytes của prompt đã lưu; 8.192 và 24.000 bytes là hai profile khác nhau.',
        '- Run validation ghép Qwen/Vertex và DeepSeek/FPT được ghi `mixed`; không coi là benchmark một backbone.',
        '- P/R/F1/Accuracy/BA dưới đây là phần trăm; MCC từ -1 đến 1. Invalid không vào confusion matrix. JSON lưu đủ metric không làm tròn.',
        '- Raw được tổng hợp theo request key + prompt hash của prediction; thiếu raw sẽ ghi rõ, không thay bằng response của model khác.',
        '- Notebook commit/archive đã che API key điền trực tiếp. Bản gốc vẫn nằm ở project để resume; snapshot không chứa weights, embeddings, graph cache hoặc runtime.', '',
        '## Các run có inference','',
        '| Project / run | Dataset / split | Arm | N0 / N1 | Valid / invalid | Trạng thái | Model / context bytes | P / R / F1 (%) | MCC | Notebook | Prediction | Raw | Prompt | Manifest |',
        '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for e in entries:
        m=e['metrics'];spec=e['request_spec'];model=spec.get('model','mixed')
        if 'qwen3-coder' in model:model='Qwen3-Coder-480B / Vertex'
        if e['mixed_model_recovery']:model='mixed Qwen/DeepSeek'
        cap=','.join(e['context_limits']) or 'không ghi'
        p=e['artifact_paths'];short=e['project'].replace('GRACE-','')+' / `'+Path(e['run']).name+'`'
        if '/recovery/original' in e['run']:short+=' (before recovery)'
        if e['run'].startswith('archives/'):short+=' (historical)'
        md.append('| '+' | '.join([short,e['dataset']+' / '+e['split'],e['arm'],f"{e['n0']} / {e['n1']}",f"{m['valid_n']} / {m['invalid_n']}",e['status'],model+' / '+cap,
                                  f"{m['precision']*100:.2f} / {m['recall']*100:.2f} / {m['f1']*100:.2f}",f"{m['mcc']:.4f}",
                                  *[link(pub.SHARE/p[k],lab)+(f" (thiếu {e['raw_unavailable_n']})" if k=='raw_responses' and e['raw_unavailable_n'] else '') for k,lab in [('notebook','notebook'),('predictions','prediction'),('raw_responses','raw'),('prompts','prompt'),('manifest','manifest')]]])+' |')
    md += ['', '## Kết quả các nhánh H3 trên test','',
           'Các nhánh dưới dùng chung raw của expert: không phải mỗi dòng là một lượt gọi LLM mới. Winner được khóa trên development, không chọn lại theo test. Tỷ lệ gọi của router là yêu cầu thuật toán giả định khi triển khai riêng, không phải tiết kiệm API thực tế của combined benchmark.', '',
           '| Project / dataset | Profile | Arm | Chọn trước test | Accuracy (%) | P / R / F1 (%) | MCC | Báo cáo |',
           '|---|---|---|---|---|---|---|---|']
    for e in derived:
        m=e['metrics'];profile='historical test24k' if e.get('historical') else ('test8192' if 'Benchmark' in e['project'] else 'cascade8192')
        md.append('| '+' | '.join([e['project'].replace('GRACE-','')+' / '+e['dataset'],profile,e['arm'],'Có' if e.get('selected_before_test') else '—',f"{m['accuracy_all']*100:.2f}",
                                  f"{m['precision']*100:.2f} / {m['recall']*100:.2f} / {m['f1']*100:.2f}",f"{m['mcc']:.4f}",link(pub.SHARE/e['report'],'evaluation')])+' |')
    md += ['', '## Diễn giải và phạm vi so sánh','',
           '- H1 có cả Devign lịch sử trong `archives/devign/2026-10-16` và ReVeal. Các run V2 còn request errors được giữ riêng.',
           '- H3 cascade Devign có full reference, cascade và gate-only. Cascade chỉ tiết kiệm thuật toán 6/2.732 query; mức tăng metric rất nhỏ.',
           '- H3 ensemble chọn `gate_tuned` cho cả hai tập. Test DeepSeek gần như dự đoán toàn 0; chưa thể dùng baseline này để khẳng định ensemble cải thiện một GRACE hoạt động bình thường.',
           '- Baseline các project là adaptation với masked-mean và syntax atomic-token cost 2; không gọi là baseline Code-Based chuẩn hóa theo tài liệu so sánh.',
           '- Historical 24k được bảo tồn; kết quả chính hiện tại là test8192. Validation meta dùng cohort độc lập đủ điều kiện, không bằng toàn official validation.', '',
           '## Kiểm kê artifact','',f'- Có **{len(entries)}** bộ run có prediction + inference summary, **{len(derived)}** dòng nhánh H3 và **{len(prepared)}** preparation chưa có inference trong snapshot H1/H3; số này không bao gồm H2.',
           f"- Số bộ run còn thiếu raw gốc khớp prediction khi tổng hợp: **{len(missing)}**, tổng **{sum(e['missing_raw_rows'] for e in missing)}** response lịch sử. Cache hiện có vẫn được lưu nguyên; không dùng câu trả lời khác để điền vào. Chi tiết trong JSON.",
           '- Snapshot manifest của từng project ghi đường dẫn nguồn, SHA-256, byte size và commit nguồn.',
           '- [JSON quản lý run](bang_quan_ly_run_cai_tien.json).', '']
    (pub.SHARE/'bang_quan_ly_run_cai_tien.md').write_bytes('\n'.join(md).encode())
    print('LEDGER',len(entries),'llm run sets',len(derived),'derived arms','missing',missing,flush=True)

if __name__=='__main__':main()
