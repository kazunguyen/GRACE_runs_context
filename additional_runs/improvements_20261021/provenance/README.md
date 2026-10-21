# Archive tooling

Scripts used on 2026-10-21 to collect the three completed/inactive improvement workspaces and generate the separate run ledger. H2 was excluded.

Paths in the scripts refer to the original Windows workspace under D:/JUNIOR/LabThayTho. The ledger builder requires the canonical local data labels and archived snapshot files; it performs no LLM calls. It reconstructs raw rows only when request key, prompt hash, status and parsed label agree, recording missing historical raw explicitly. Re-running it writes supplemental raw/metric files into the three source projects and the SHARE snapshot.

Snapshot manifests describe original copied files. The publication manifest records supplemental generated files and final Git references. API keys entered in notebooks were removed only from committed/archive bytes, leaving working notebooks intact.
