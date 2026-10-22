# GRACE H2 GuardedEvidence: stopped 50% inference snapshot

The user stopped the notebook run on 2026-10-22. Source code was committed locally as `ab3e17a` (not pushed). These files preserve the prompts and responses already recorded. No test labels or evaluation metrics are included.

- Notebook: `notebooks/infer_guarded_prompts.ipynb`
- One prompt per query; prompt budget: 8,192 UTF-8 bytes.
- Provider/model recorded by the run: FPT AI Factory / DeepSeek-V4-Flash.
- The FPT adapter sends `thinking: false` for DeepSeek-V4. See the run manifests and the project source.
- Both dataset jobs selected the first 50% of the frozen test order.
- Devign: 1,366/1,366 selected prompts have completed responses; all raw responses are `0`.
- ReVeal: 63/1,137 completed responses, all `0`; one more request is `dispatched` with no saved response. The remaining selected samples were not sent.
- The dispatched ReVeal request is uncertain. Do not count it as a response or automatically resend it.
- Inference was not completed, and evaluation was not run. These partial outputs are not a benchmark result.

Each dataset folder contains the complete prompt export (`prompts.jsonl.gz`) and the available `raw_responses.jsonl`, `predictions.jsonl`, `inference_summary.json`, and `run_manifest.json`.
