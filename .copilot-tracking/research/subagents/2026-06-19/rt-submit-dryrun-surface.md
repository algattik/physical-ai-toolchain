<!-- markdownlint-disable-file -->
# rt-submit-dryrun: AML/OSMO submission dry-run / offline-validatable surface

Captured by parent (research subagent read-only).

## Verdict: ~70% of the submission flow is validatable OFFLINE (no Azure/GPU/OSMO).

## Key findings
* `--config-preview` ALREADY EXISTS and exits before any cloud call:
  * training/rl/scripts/submit-osmo-training.sh (flag ~:55, handling ~:174-194)
  * training/il/scripts/submit-osmo-lerobot-training.sh (~:73, :241-263)
  * training/il/scripts/submit-azureml-lerobot-training.sh (~:115,:449) and submit-azureml-lerobot-pipeline.sh
  * BUT it prints CLI-parsed values, NOT the rendered workflow/job YAML.
* AzureML submit scripts have `-a/--save-as PATH` to write the rendered job YAML (submit-azureml-lerobot-training.sh ~:107-108) — a hook to dump+validate offline.
* OSMO workflow YAML uses `{{ }}` Jinja templates with a `default-values:` block (training/rl/workflows/osmo/train.yaml); base64-archive payload packing is done fully locally (submit-osmo-training.sh:200-227). AzureML job YAML references commandJob.schema.json (lerobot-train.yaml:20) — locally schema-validatable.
* Offline-validatable: script arg-parse; base64 payload packing; YAML template render (python, local FS); generated-YAML syntax + JSON-schema validation; shellcheck; yaml-lint/actionlint (already in CI).
* Strictly-online: osmo login / az login / OIDC; `osmo workflow create`; `az ml job create` against a workspace; model-registry asset resolution (azureml:NAME:VERSION); dataset URI checks.

## Recommended offline smoke
Extend `--config-preview` (or use `--save-as`) to EMIT the rendered YAML, then a CI job: render → yaml-lint → JSON-schema validate (AzureML commandJob schema; for OSMO assert required keys: tasks, env, file blocks) → shellcheck. Catches template/script breakage from dep or refactor changes with zero cloud.

## Open questions
1. Does OSMO publish a workflow JSON schema? If not, define minimal required-keys validator.
2. Wire `--save-as` into a CI smoke job?
3. Offline validator: check all `{{ }}`/`${{ }}` refs resolve, or syntax only?
