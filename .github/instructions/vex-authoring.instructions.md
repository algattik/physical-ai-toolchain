---
description: 'OpenVEX authoring rules for base-image CVE suppression documents under security/vex/ - Brought to you by microsoft/hve-core'
applyTo: 'security/vex/**/*.openvex.json'
---

# VEX Authoring

Authoritative rules for writing and triaging the OpenVEX documents under `security/vex/`. These documents record the exploitability of base-image CVEs, and both the CI enforcement gate and the remediation tracker consume them, so a single triaged set of documents must be correct for both.

<!-- Vendored and adapted from microsoft/hve-core .github/instructions/security/vex-standards.instructions.md, pinned at commit e6f414dabf65d67d59763ce776fa2212bd70b028. Re-sync from that path when updating. -->

## Scope

Applies to every OpenVEX document under `security/vex/`, one per base image (for example `security/vex/inference-base.openvex.json`). `scripts/security/generate-vex.sh` scans an image and emits a stub document with one `under_investigation` statement per discovered CVE. The rules below govern how each statement is triaged before the document is committed.

## Status labels and safe default

Every statement asserts one `status` for a vulnerability against a product. OpenVEX v0.2.0 defines exactly four status labels:

| Status                | Meaning                                                            |
|-----------------------|--------------------------------------------------------------------|
| `under_investigation` | Exploitability is not yet determined.                              |
| `not_affected`        | The product is not affected; requires a justification (see below). |
| `affected`            | The product is affected; requires an action statement (see below). |
| `fixed`               | The vulnerability is remediated in the product.                    |

> [!IMPORTANT]
> When reachability or exploitability cannot be established from evidence, `under_investigation` is the only valid status. `generate-vex.sh` emits every statement as `under_investigation` by design. A status is never promoted to `not_affected`, `affected`, or `fixed` without supporting analysis.

## Justifications and action statements

A `not_affected` statement must carry a machine-readable `justification` label. Reserve the free-form `impact_statement` for optional enrichment; it breaks automated policy evaluation and is not a substitute for the label. The valid justification labels:

| Justification label                                 | Applies when                                                        |
|-----------------------------------------------------|---------------------------------------------------------------------|
| `component_not_present`                             | The vulnerable component is not in the image.                       |
| `vulnerable_code_not_present`                       | The component is present but the vulnerable code is not built in.   |
| `vulnerable_code_not_in_execute_path`               | The vulnerable code is present but never called.                    |
| `vulnerable_code_cannot_be_controlled_by_adversary` | An attacker cannot reach or control the vulnerable code.            |
| `inline_mitigations_already_exist`                  | Built-in protections that cannot be subverted prevent exploitation. |

An `affected` statement must carry an `action_statement` describing the remediation or mitigation. Record the reasoning behind any status in `status_notes`.

```json
{
  "vulnerability": { "name": "CVE-2024-12345" },
  "products": [{ "@id": "pkg:oci/minimal-py312-inference@sha256:..." }],
  "status": "not_affected",
  "justification": "vulnerable_code_not_in_execute_path",
  "status_notes": "The package ships in the base layer but the affected entrypoint is never invoked by the inference runtime."
}
```

## Status transitions

Promote a statement out of `under_investigation` only once the evidence for the target status exists. A vendor-disputed finding is no exception: record the dispute in `status_notes` and keep the status at `under_investigation` until reachability evidence is gathered. Reverting a triaged statement to `under_investigation` requires a documented reason in `status_notes`.

## Document mutation contract

Each document is a single rolling artifact for one base image. Every pull request that adds or changes a statement must update the document metadata so consumers detect the new revision:

- Set `timestamp` to the current UTC time of issuance.
- Increment the integer `version` by one.
- Regenerate `@id` so it is unique per revision, embedding the issuance date to match the `.../security/vex/<product>/<date>` form that `generate-vex.sh` produces.
- Keep the `_source` provenance block accurate (base image, digest, generator command). Rerun `generate-vex.sh` rather than hand-editing a digest.

Reject any statement-changing pull request that leaves `version`, `timestamp`, or `@id` stale.

## Data source licensing

Triage prose in `impact_statement` and `status_notes` draws on vulnerability databases with distinct licensing obligations:

| Source             | License                     | Usage                                                                                                  |
|--------------------|-----------------------------|--------------------------------------------------------------------------------------------------------|
| NVD                | US Government public domain | Use freely for CVSS vectors and CWE classifications.                                                   |
| OSV.dev            | Mixed (varies per record)   | Check the record prefix; paraphrase only CC0 or public-domain records, write original prose otherwise. |
| GitHub Advisory DB | CC-BY-4.0                   | Reference the advisory URL and identifiers only; do not quote GHSA prose.                              |

Write original remediation and impact prose. Do not copy text from any external source.

## Author of record

VEX documents follow a draft-and-merge accountability model. `generate-vex.sh` and the triaging author draft the statements; the reviewer who merges the pull request is the accountable author of record for every statement in it. Attest published documents with cosign, as `generate-vex.sh` directs.

## Validation

Before merging a statement-changing pull request, confirm:

- Every `not_affected` statement carries a valid `justification` label.
- Every `affected` statement carries an `action_statement`.
- No status was promoted out of `under_investigation` without supporting evidence.
- `version`, `timestamp`, and `@id` were updated.
- No GHSA prose was quoted verbatim.
