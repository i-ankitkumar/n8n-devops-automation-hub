"""Structural validation for exported n8n workflow JSON files.

n8n will happily import a workflow file that's missing a node a connection
points at, or that has two nodes sharing a name (connections in n8n route by
node *name*, not id, so a duplicate silently breaks routing) — it just fails
oddly at runtime instead of at import time. This checks the things that are
cheap to check statically and that turn into confusing runtime failures
otherwise, so a broken workflow in this repo gets caught by CI rather than
by whoever imports it next.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

WORKFLOW_REQUIRED_KEYS = ("name", "nodes", "connections")
NODE_REQUIRED_KEYS = ("id", "name", "type", "position")
TRIGGER_TYPE_HINTS = ("trigger", "webhook")


@dataclass
class Finding:
    file: str
    rule_id: str
    severity: str  # "error" or "warning"
    message: str


def load_workflow(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _check_top_level(file_name: str, workflow: dict) -> list[Finding]:
    findings = []
    for key in WORKFLOW_REQUIRED_KEYS:
        if key not in workflow:
            findings.append(Finding(file_name, "WF001", "error", f"Missing required top-level key '{key}'"))
    return findings


def _check_nodes(file_name: str, nodes: list) -> tuple[list[Finding], set[str]]:
    findings = []
    seen_names: set[str] = set()
    has_trigger = False

    if not isinstance(nodes, list) or not nodes:
        findings.append(Finding(file_name, "WF002", "error", "'nodes' must be a non-empty list"))
        return findings, seen_names

    for i, n in enumerate(nodes):
        label = n.get("name", f"<node #{i}>") if isinstance(n, dict) else f"<node #{i}>"
        if not isinstance(n, dict):
            findings.append(Finding(file_name, "WF002", "error", f"Node #{i} is not an object"))
            continue

        for key in NODE_REQUIRED_KEYS:
            if key not in n:
                findings.append(Finding(file_name, "WF002", "error", f"Node '{label}' missing required field '{key}'"))

        name = n.get("name")
        if name:
            if name in seen_names:
                findings.append(Finding(file_name, "WF003", "error", f"Duplicate node name '{name}' (connections route by name)"))
            seen_names.add(name)

        position = n.get("position")
        if position is not None and (not isinstance(position, list) or len(position) != 2):
            findings.append(Finding(file_name, "WF006", "warning", f"Node '{label}' has a malformed 'position' (expected [x, y])"))

        node_type = n.get("type", "")
        if any(hint in node_type.lower() for hint in TRIGGER_TYPE_HINTS):
            has_trigger = True

    if not has_trigger:
        findings.append(Finding(file_name, "WF005", "warning", "No trigger/webhook node found — workflow may never run"))

    return findings, seen_names


def _check_connections(file_name: str, connections: dict, node_names: set[str]) -> list[Finding]:
    findings = []
    if not isinstance(connections, dict):
        findings.append(Finding(file_name, "WF004", "error", "'connections' must be an object"))
        return findings

    for source, outputs in connections.items():
        if source not in node_names:
            findings.append(Finding(file_name, "WF004", "error", f"Connection source '{source}' is not a defined node"))
        main = outputs.get("main", []) if isinstance(outputs, dict) else []
        for branch in main:
            for target in branch or []:
                target_name = target.get("node") if isinstance(target, dict) else None
                if target_name and target_name not in node_names:
                    findings.append(
                        Finding(file_name, "WF004", "error", f"Connection target '{target_name}' (from '{source}') is not a defined node")
                    )
    return findings


def validate(path: str | Path) -> list[Finding]:
    """Validate one workflow JSON file. Returns a list of Findings (empty = clean)."""
    file_name = Path(path).name

    try:
        workflow = load_workflow(path)
    except json.JSONDecodeError as exc:
        return [Finding(file_name, "WF000", "error", f"Invalid JSON: {exc}")]

    if not isinstance(workflow, dict):
        return [Finding(file_name, "WF000", "error", "Top level of file must be a JSON object")]

    findings = _check_top_level(file_name, workflow)

    nodes = workflow.get("nodes", [])
    node_findings, node_names = _check_nodes(file_name, nodes)
    findings.extend(node_findings)

    connections = workflow.get("connections", {})
    findings.extend(_check_connections(file_name, connections, node_names))

    if workflow.get("active") is True:
        findings.append(
            Finding(file_name, "WF007", "warning", "Workflow is marked active:true — template exports should ship inactive")
        )

    return findings


def validate_directory(directory: str | Path) -> dict[str, list[Finding]]:
    """Validate every *.json file directly under `directory`. Returns {filename: findings}."""
    directory = Path(directory)
    results = {}
    for path in sorted(directory.glob("*.json")):
        results[path.name] = validate(path)
    return results
