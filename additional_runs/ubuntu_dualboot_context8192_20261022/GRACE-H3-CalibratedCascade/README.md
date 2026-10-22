# Ubuntu dualboot — historical 8192-byte context rerun

ReVeal/test, DeepSeek-V4-Flash on FPT. First 50% of the original ordered dataset: 1137 of 2274 samples.
Selected prefix completed, full dataset remains **partial**. 446 oversized prompts were re-fit using the historical
fitter and re-called; 691 exact cached responses reused. No request errors or invalid answers.
Accuracy 90.8531%, F1=0, MCC=0. All 1137 predictions are non-vulnerable (1033 negatives, 104 positives).

The 24000-byte comparator uses the same 1137 record IDs. This context-normalized prefix result is descriptive;
other historical graph/retrieval/model differences are not normalized by clipping context alone.
Prompts are <=8192 UTF-8 bytes, not measured model token counts. Exact response/prompt hashes are validated.

Original frozen run: `runs/reveal/test/baseline_whitening/5a64cba3ab7edefb`. New selected profile: `runs/context_limit_rerun/reveal/test/f65b0c326b9337c4/inference_prefix/first_001137`.
The exact saved notebook is included; context_benchmark.json is the authoritative execution result.
No credentials are included. Runtime/cache increment is published in:
https://github.com/kazunguyen/GRACE-H3-CalibratedCascade/tree/main/exports/ubuntu-dualboot-context8192-20261022

Source publication commit: https://github.com/kazunguyen/GRACE-H3-CalibratedCascade/commit/7d3516d627118b9eb52c157d5f6d20dd53994ccb
