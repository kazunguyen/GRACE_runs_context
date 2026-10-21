# H3 snapshot: validation 8192 / test 24000 bytes

This is an additional H3 snapshot, not part of the original 36 context8192 runs.
Source commit: `ab32b16196a26a61ad37b667c2f0f014d1625b18`. Files were copied unchanged and verified by SHA-256.

| Dataset | Split | Queries | Prompt limit (UTF-8 bytes) |
|---|---|---:|---:|
| devign | validation | 2724 | 8192 |
| devign | test | 2732 | 24000 |
| reveal | validation | 2196 | 8192 |
| reveal | test | 2274 | 24000 |

Validation combines Qwen/Vertex successes and DeepSeek/FPT recovery; test uses DeepSeek/FPT.
This snapshot is exploratory and not a uniform-backbone/context benchmark.
See [benchmark_summary.json](runs/h3v2/5fc21bd7cafff9846aff/benchmark_summary.json) and [copy_manifest.json](copy_manifest.json).
Both locked development winners are gate_tuned. No winner was reselected on test.

Included: rendered prompts, raw responses, predictions, retrievals, graph feature indices,
run manifests/freezes, inference plans/summaries, all evaluated H3 arms, model manifests,
configuration, notebooks with results, and source code. Original failed validation outputs
are retained under each validation run's recovery/original/.
Weights, embeddings, graph caches, credentials and duplicate per-request journals are omitted.
Freeze files retain source paths and may reference omitted caches/weights; this is an inspection
and provenance snapshot, not a standalone runtime.
