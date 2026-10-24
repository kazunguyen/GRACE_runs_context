from __future__ import annotations
import gzip, hashlib, json, math, os, sys, time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from strict_parser import parse_prediction

ROOT = Path(__file__).resolve().parent
INFERENCE = {'temperature': 0.0, 'seed': 42, 'max_tokens': 256, 'stream': False, 'max_attempts': 5}
TERMINAL = {'valid', 'invalid'}
DEFAULT_VERTEX_MODEL = 'deepseek-ai/deepseek-v4.1-flash-maas'

def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def canonical_hash(value) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))

def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def read_jsonl_gz(path: Path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]

def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)

def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8', newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)

def find_dotenv(root: Path) -> Path | None:
    candidates = [root / '.env']
    cwd = Path.cwd().resolve()
    candidates.extend(parent / '.env' for parent in (cwd, *cwd.parents) if parent != root)
    seen = set()
    for path in candidates:
        try: path = path.resolve()
        except OSError: continue
        if path in seen: continue
        seen.add(path)
        if not path.is_file(): continue
        return path
    return None

def dotenv_values(path: Path | None):
    values = {}
    if path is None: return values
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        text = line.strip()
        if not text or text.startswith('#') or '=' not in text: continue
        key, value = text.split('=', 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key: values[key] = value
    return values

def load_dotenv(root: Path) -> Path | None:
    path = find_dotenv(root)
    for key, value in dotenv_values(path).items():
        if not os.environ.get(key): os.environ[key] = value
    return path

def safe_url(value: str) -> str:
    parsed = urlsplit(value)
    host = parsed.hostname or ''
    if parsed.port: host += ':' + str(parsed.port)
    return urlunsplit((parsed.scheme, host, parsed.path, '', ''))

def vertex_project() -> str | None:
    project = (os.environ.get('VERTEX_PROJECT') or os.environ.get('GOOGLE_CLOUD_PROJECT') or '').strip()
    if project: return project
    try:
        import google.auth
        _, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        return project
    except Exception:
        return None

def provider_config(root: Path = ROOT):
    env_path = find_dotenv(root)
    values_from_file = dotenv_values(env_path)
    names = ('LLM_API', 'LLM_MODEL', 'LLM_BASE_URL')
    values = {name: values_from_file.get(name, '').strip() for name in names}
    present = [name for name, value in values.items() if value]
    if present and len(present) != len(names):
        missing = [name for name, value in values.items() if not value]
        raise RuntimeError('Incomplete .env API configuration; missing: ' + ', '.join(missing))
    if len(present) == len(names):
        base = values['LLM_BASE_URL'].rstrip('/')
        endpoint = base if base.endswith('/chat/completions') else base + '/chat/completions'
        if not endpoint.startswith(('http://', 'https://')):
            raise RuntimeError('LLM_BASE_URL must start with http:// or https://')
        return {'provider': 'OpenAI-compatible API', 'model': values['LLM_MODEL'], 'api_key': values['LLM_API'],
                'endpoint': endpoint, 'safe_endpoint': safe_url(endpoint), 'project': None, 'location': None}
    cfg = read_json(root / 'request_config.json')
    location = (os.environ.get('VERTEX_LOCATION') or os.environ.get('GOOGLE_CLOUD_LOCATION') or cfg.get('vertex_location') or 'global').strip()
    project = vertex_project()
    base_host = 'https://aiplatform.googleapis.com' if location == 'global' else f'https://{location}-aiplatform.googleapis.com'
    endpoint = f'{base_host}/v1/projects/{project or "<PROJECT_REQUIRED>"}/locations/{location}/endpoints/openapi/chat/completions'
    return {'provider': 'Vertex AI', 'model': cfg.get('vertex_model', DEFAULT_VERTEX_MODEL), 'api_key': None,
            'endpoint': endpoint, 'safe_endpoint': endpoint, 'project': project, 'location': location}

def public_provider(config):
    return {key: config.get(key) for key in ('provider', 'model', 'safe_endpoint', 'project', 'location')}

def inference_parameters(config):
    params = dict(INFERENCE)
    if config['provider'] == 'OpenAI-compatible API' and 'deepseek-v4' in config['model'].casefold():
        params['chat_template_kwargs'] = {'thinking': False}
    return params

def percent_prefix_count(total: int, percent: float) -> int:
    value = float(percent)
    if not math.isfinite(value) or value < 0 or value > 100:
        raise ValueError('PERCENT must be between 0 and 100')
    return int(total * value / 100)

def preflight(root: Path, dataset: str):
    if dataset not in ('devign', 'reveal'): raise ValueError('dataset must be devign or reveal')
    manifest = read_json(root / 'bundle_manifest.json')
    for name, expected in manifest['files'].items():
        if sha_bytes((root / name).read_bytes()) != expected:
            raise ValueError('Bundle checksum mismatch: ' + name)
    prompts = read_jsonl_gz(root / 'inputs' / dataset / 'prompts.jsonl.gz')
    if not prompts: raise ValueError('No prompts found for ' + dataset)
    ids = [row.get('record_id') for row in prompts]
    if len(set(ids)) != len(ids) or any(not value for value in ids): raise ValueError('Duplicate or empty record_id')
    max_bytes = 0
    for row in prompts:
        if row.get('dataset') != dataset or row.get('split') != 'test': raise ValueError('Unexpected dataset/split in prompts')
        content = row.get('prompt', '').encode('utf-8'); size = len(content); max_bytes = max(max_bytes, size)
        if not content or size > 8192 or sha_bytes(content) != row.get('prompt_sha256'):
            raise ValueError('Prompt is empty, over context limit, or hash mismatch: ' + str(row.get('record_id')))
        truncation = row.get('prompt_truncation', {})
        if truncation.get('context_limit') != 8192 or truncation.get('prompt_utf8_bytes') != size:
            raise ValueError('Prompt context metadata mismatch: ' + str(row.get('record_id')))
    expected = manifest['cohorts'][dataset]['n']
    if len(prompts) != expected: raise ValueError('Unexpected test cohort size')
    return {'dataset': dataset, 'split': 'test', 'arm': 'baseline_whitening', 'n': len(prompts),
            'max_prompt_utf8_bytes': max_bytes, 'source_run_id': manifest['cohorts'][dataset]['source_run_id']}

def identity_for(root: Path, config):
    bundle_sha = sha_bytes((root / 'bundle_manifest.json').read_bytes())
    return {'provider': config['provider'], 'model': config['model'], 'endpoint': config['safe_endpoint'],
            'project': config.get('project'), 'location': config.get('location'), 'inference': inference_parameters(config),
            'context_limit_utf8_bytes': 8192, 'parser': 'exact_last_line_binary_v1',
            'bundle_manifest_sha256': bundle_sha, 'split': 'test', 'arm': 'baseline_whitening'}

def request_key(identity, prompt):
    return canonical_hash({'identity': identity, 'dataset': prompt['dataset'], 'record_id': prompt['record_id'],
                           'prompt_sha256': prompt['prompt_sha256']})

def request_path(out: Path, key: str): return out / 'requests' / (key + '.json')
def load_state(path: Path): return read_json(path) if path.is_file() else None

class ProviderFailure(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message); self.status_code = status_code

def create_client(config):
    import requests
    session = requests.Session()
    if config['provider'] == 'Vertex AI':
        import google.auth
        from google.auth.transport.requests import Request
        credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        if not config.get('project') and project:
            config['project'] = project
            config['endpoint'] = config['endpoint'].replace('<PROJECT_REQUIRED>', project)
            config['safe_endpoint'] = config['endpoint']
        if not config.get('project'): raise RuntimeError('No Vertex project found; set VERTEX_PROJECT or configure ADC')
        return ('vertex', session, credentials, Request())
    return ('api', session, None, None)

def send_once(client, config, prompt):
    import requests
    if client[0] == 'vertex':
        credentials, auth_request = client[2], client[3]
        if not credentials.valid or credentials.expired: credentials.refresh(auth_request)
        headers = {'Authorization': 'Bearer ' + credentials.token, 'Content-Type': 'application/json'}
    else:
        headers = {'Authorization': 'Bearer ' + config['api_key'], 'Content-Type': 'application/json'}
    body = {'model': config['model'], 'messages': [{'role': 'user', 'content': prompt}],
            'temperature': INFERENCE['temperature'], 'seed': INFERENCE['seed'],
            'max_tokens': INFERENCE['max_tokens'], 'stream': False}
    if 'chat_template_kwargs' in inference_parameters(config):
        body['chat_template_kwargs'] = {'thinking': False}
    try:
        response = client[1].post(config['endpoint'], headers=headers, json=body, timeout=(20, 600))
    except requests.RequestException as exc:
        raise ProviderFailure(type(exc).__name__ + ': request failed') from None
    if not response.ok:
        detail = response.text[:1000]
        if config.get('api_key'): detail = detail.replace(config['api_key'], '<redacted>')
        raise ProviderFailure(f'HTTP {response.status_code}: {detail}', response.status_code)
    try:
        envelope = response.json(); choice = envelope['choices'][0]
        text = choice['message'].get('content') or ''
    except Exception:
        raise ProviderFailure('OpenAI-compatible response envelope invalid') from None
    if not isinstance(text, str): raise ProviderFailure('Response content was not text')
    return text, envelope.get('usage'), choice.get('finish_reason')

def call_prompt(out, identity, config, row, client):
    key = request_key(identity, row); path = request_path(out, key)
    state = load_state(path) or {'request_key': key, 'record_id': row['record_id'], 'prompt_sha256': row['prompt_sha256'],
                                'status': 'pending', 'attempts': [], 'prediction': None, 'raw_response': None}
    if state.get('status') in TERMINAL: return state
    import requests
    for attempt in range(len(state['attempts']) + 1, INFERENCE['max_attempts'] + 1):
        if attempt > 1: time.sleep(min(120, 5 * 2 ** (attempt - 2)))
        event = {'attempt': attempt, 'started_unix': time.time()}; state['attempts'].append(event); write_json(path, state)
        try:
            raw, usage, finish = send_once(client, config, row['prompt']); parsed = parse_prediction(raw)
            state.update(status=parsed.parse_status, prediction=parsed.prediction, parse_method=parsed.parse_method,
                         raw_response=raw, usage=usage, finish_reason=finish)
            event['finished_unix'] = time.time(); write_json(path, state); return state
        except ProviderFailure as exc:
            detail = str(exc)
            if config.get('api_key'): detail = detail.replace(config['api_key'], '<redacted>')
            event.update(finished_unix=time.time(), error=detail, http_status=exc.status_code)
            if exc.status_code in (400, 401, 403, 404) or attempt == INFERENCE['max_attempts']:
                state.update(status='exhausted', error=detail); write_json(path, state); return state
            write_json(path, state)
    state['status'] = 'exhausted'; write_json(path, state); return state

def run_dataset(root: Path, dataset: str, percent: float, allow_api: bool = False):
    root = Path(root).resolve(); plan = preflight(root, dataset); config = provider_config(root)
    if not allow_api: raise RuntimeError('Set RUN_API=True before allowing inference calls')
    prompts = read_jsonl_gz(root / 'inputs' / dataset / 'prompts.jsonl.gz')
    target_n = percent_prefix_count(len(prompts), percent); selected = prompts[:target_n]
    identity = identity_for(root, config); run_id = canonical_hash(identity)[:16]
    out = root / 'outputs' / dataset / run_id; out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / 'run_manifest.json'; old = read_json(manifest_path) if manifest_path.exists() else {}
    if old and old.get('identity') != identity: raise RuntimeError('Output run identity mismatch')
    done_before = sum(1 for row in selected if (load_state(request_path(out, request_key(identity, row))) or {}).get('status') in TERMINAL)
    invocation = {'percent': float(percent), 'prefix_target_count': target_n, 'started_unix': time.time(),
                  'terminal_requests_before': done_before}
    manifest = {'identity': identity, 'run_id': run_id, 'cohort': plan, 'provider': public_provider(config),
                'ground_truth_included': False, 'invocations': old.get('invocations', []) + [invocation]}
    write_json(manifest_path, manifest)
    todo = [row for row in selected if (load_state(request_path(out, request_key(identity, row))) or {}).get('status') not in TERMINAL]
    lock = out / 'RUNNING.lock'
    if todo:
        try: fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError: raise RuntimeError(f'Run lock exists: {lock}') from None
        os.close(fd)
    client = None; completed = 0
    try:
        if todo: client = create_client(config)
        for row in todo:
            state = call_prompt(out, identity, config, row, client); completed += 1
            pct = 100.0 * completed / len(todo)
            print(f'{dataset}: {completed}/{len(todo)} new requests ({pct:.1f}%); {row["record_id"]} -> {state["status"]}', flush=True)
            if state['status'] == 'exhausted': raise RuntimeError('Request exhausted; inspect checkpoint before resuming')
    finally:
        if client is not None: client[1].close()
        if todo: lock.unlink(missing_ok=True)
        after = sum(1 for row in selected if (load_state(request_path(out, request_key(identity, row))) or {}).get('status') in TERMINAL)
        invocation.update(finished_unix=time.time(), new_requests=completed, terminal_requests_after=after)
        write_json(manifest_path, manifest)
    return {'dataset': dataset, 'run_id': run_id, 'requested_percent': float(percent), 'selected_n': target_n,
            'new_requests': completed, 'terminal_requests_after': after, 'output': str(out), 'provider': public_provider(config)}

def export_dataset(root: Path, dataset: str, percent: float):
    root = Path(root).resolve(); plan = preflight(root, dataset); config = provider_config(root)
    prompts = read_jsonl_gz(root / 'inputs' / dataset / 'prompts.jsonl.gz')
    target_n = percent_prefix_count(len(prompts), percent); identity = identity_for(root, config)
    run_id = canonical_hash(identity)[:16]; out = root / 'outputs' / dataset / run_id
    predictions, raw_rows = [], []
    for row in prompts:
        key = request_key(identity, row); state = load_state(request_path(out, key))
        status = state.get('status') if state else 'not_run'
        predictions.append({'record_id': row['record_id'], 'code_sha256': row['code_sha256'],
            'prompt_sha256': row['prompt_sha256'], 'prediction': state.get('prediction') if state else None,
            'parse_status': status, 'parse_method': state.get('parse_method') if state else None,
            'request_key': key, 'provider': config['provider'], 'model': config['model'],
            'arm': 'baseline_whitening', 'split': 'test'})
        raw_rows.append({'record_id': row['record_id'], 'prompt_sha256': row['prompt_sha256'],
                         'request_key': key, 'request': state})
    write_jsonl(out / 'predictions.jsonl', predictions)
    write_jsonl(out / 'raw_responses.jsonl', raw_rows)
    counts = {}
    for row in predictions[:target_n]: counts[row['parse_status']] = counts.get(row['parse_status'], 0) + 1
    export = {'dataset': dataset, 'split': 'test', 'arm': 'baseline_whitening', 'run_id': run_id,
              'provider': public_provider(config), 'requested_percent': float(percent),
              'cohort_n': len(prompts), 'selected_prefix_n': target_n, 'status_counts_in_selected_prefix': counts,
              'ground_truth_included': False, 'predictions_file': 'predictions.jsonl',
              'raw_responses_file': 'raw_responses.jsonl'}
    write_json(out / 'export_manifest.json', export)
    return {'dataset': dataset, 'output': str(out), 'selected_prefix_n': target_n, 'status_counts': counts}
