# n8n DevOps Automation Hub

Five importable [n8n](https://n8n.io) workflows for common DevOps toil — CI failure
alerting, PR triage, Terraform drift detection, a security-scan digest, and on-call
incident bootstrapping — plus `n8nhublint`, a small structural linter that keeps every
workflow in this repo actually valid before you import it.

## Why

n8n workflow JSON exports are easy to hand-edit and easy to break: two nodes with the
same name silently breaks routing (n8n connects nodes by *name*, not id), and a
connection pointing at a renamed or deleted node fails quietly at import or, worse, at
runtime. Rather than a folder of unverified JSON blobs, this repo ships each workflow
alongside a linter that checks the things that actually cause that kind of failure —
so every workflow here is verified importable, not just plausible-looking.

## Workflows

| File | Trigger | What it does |
|---|---|---|
| `ci-pipeline-failure-alert.json` | Webhook (CI failure) | Parses a pipeline-failure payload and posts a formatted alert to Slack only when the build actually failed. |
| `pr-auto-triage.json` | Webhook (PR opened) | Fetches changed files, sizes the PR, flags anything touching Terraform/pipeline/Dockerfiles, applies labels, and pings an infra-review channel. |
| `terraform-drift-check.json` | Schedule (daily) | Runs `terraform plan -detailed-exitcode`, files a Jira ticket and Slack alert only when drift (exit code 2) is detected. |
| `tfscan-security-digest.json` | Schedule (weekly) | Runs [tfscan](https://github.com/i-ankitkumar/terraform-security-scanner) against your infra and posts a severity-counted digest to `#security`. |
| `oncall-incident-bootstrap.json` | Webhook (Alertmanager) | Normalizes a Prometheus Alertmanager alert, opens an incident for critical severity, and pages `#oncall` with the runbook link. |

Every workflow ships `active: false` and placeholder channel names/URLs — review the
node parameters and wire in your own credentials before activating.

### Importing one

In n8n: **Workflows → Import from File**, pick a file from `workflows/`, then fill in
your own credentials (Slack, GitHub, Jira/incident API) on the nodes that need them —
each workflow's `meta.notes` field (visible in the n8n editor) says which.

## The linter

```bash
pip install -e .
n8nhublint workflows
```

```
Checked 5 workflow file(s).

All workflows are structurally valid.
```

Point it at a broken workflow and it tells you exactly what n8n wouldn't:

```bash
$ n8nhublint tests/fixtures --strict
Checked 1 workflow file(s).

┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ File                 ┃ Rule  ┃ Severity ┃ Message                            ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ broken_workflow.json │ WF003 │ ERROR    │ Duplicate node name 'Start'        │
│                      │       │          │ (connections route by name)        │
├──────────────────────┼───────┼──────────┼────────────────────────────────────┤
│ broken_workflow.json │ WF002 │ ERROR    │ Node 'Missing Position' missing    │
│                      │       │          │ required field 'position'          │
├──────────────────────┼───────┼──────────┼────────────────────────────────────┤
│ broken_workflow.json │ WF004 │ ERROR    │ Connection target 'Nonexistent     │
│                      │       │          │ Node' (from 'Start') is not a      │
│                      │       │          │ defined node                       │
├──────────────────────┼───────┼──────────┼────────────────────────────────────┤
│ broken_workflow.json │ WF004 │ ERROR    │ Connection source 'Ghost Source'   │
│                      │       │          │ is not a defined node              │
├──────────────────────┼───────┼──────────┼────────────────────────────────────┤
│ broken_workflow.json │ WF007 │ WARNING  │ Workflow is marked active:true —   │
│                      │       │          │ template exports should ship       │
│                      │       │          │ inactive                           │
└──────────────────────┴───────┴──────────┴────────────────────────────────────┘

4 error(s)  1 warning(s)
```

## Rules

| ID | Check | Severity |
|---|---|---|
| WF000 | File isn't valid JSON | error |
| WF001 | Missing a required top-level key (`name`, `nodes`, `connections`) | error |
| WF002 | A node is missing a required field (`id`, `name`, `type`, `position`) | error |
| WF003 | Two nodes share a name (breaks n8n's name-based connection routing) | error |
| WF004 | A connection references a node that doesn't exist | error |
| WF005 | No trigger/webhook node found — the workflow can never run on its own | warning |
| WF006 | A node's `position` isn't a valid `[x, y]` pair | warning |
| WF007 | Workflow exported with `active: true` (templates should ship inactive) | warning |

## Development

```bash
pip install -e ".[dev]"
pytest
```

`tests/test_validator.py` runs the linter against every shipped workflow (must be
error-free) and against `tests/fixtures/broken_workflow.json`, a deliberately broken
example that trips every error rule at once.

## Roadmap

- [ ] GitHub Action that lints changed workflow files on every PR
- [ ] A `--fix` mode for the mechanical issues (duplicate renames, position gaps)
- [ ] More workflows: automated changelog generation from merged PRs, cost-anomaly alerts
- [ ] Docker Compose file to spin up a local n8n instance pre-loaded with these workflows

## About

Built by [Ankit Kumar](https://iankitkumar.in) — DevOps/Cloud engineer working with
Azure, Terraform, and automation tooling day to day. Part of a series of small, real
infra tools; see [pinned repos](https://github.com/i-ankitkumar) for the others,
including [tfscan](https://github.com/i-ankitkumar/terraform-security-scanner), which
this hub's security-digest workflow runs directly.

## License

MIT
