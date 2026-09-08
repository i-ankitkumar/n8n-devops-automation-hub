import json
from pathlib import Path

from n8nhublint.validator import validate, validate_directory

REPO_ROOT = Path(__file__).parent.parent
WORKFLOWS_DIR = REPO_ROOT / "workflows"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_all_shipped_workflows_are_clean():
    results = validate_directory(WORKFLOWS_DIR)
    assert len(results) == 5, "expected 5 workflow files in workflows/"
    for file_name, findings in results.items():
        errors = [f for f in findings if f.severity == "error"]
        assert not errors, f"{file_name} has validation errors: {errors}"


def test_broken_fixture_flags_duplicate_node_name():
    findings = validate(FIXTURES_DIR / "broken_workflow.json")
    rule_ids = {f.rule_id for f in findings}
    assert "WF003" in rule_ids


def test_broken_fixture_flags_missing_node_field():
    findings = validate(FIXTURES_DIR / "broken_workflow.json")
    assert any(f.rule_id == "WF002" for f in findings)


def test_broken_fixture_flags_dangling_connections():
    findings = validate(FIXTURES_DIR / "broken_workflow.json")
    messages = " ".join(f.message for f in findings if f.rule_id == "WF004")
    assert "Nonexistent Node" in messages
    assert "Ghost Source" in messages


def test_broken_fixture_flags_active_true():
    findings = validate(FIXTURES_DIR / "broken_workflow.json")
    assert any(f.rule_id == "WF007" for f in findings)


def test_missing_required_top_level_key(tmp_path):
    bad = tmp_path / "no_connections.json"
    bad.write_text(json.dumps({"name": "x", "nodes": []}))
    findings = validate(bad)
    assert any(f.rule_id == "WF001" and "connections" in f.message for f in findings)


def test_no_trigger_node_warns(tmp_path):
    wf = {
        "name": "No Trigger",
        "nodes": [
            {"id": "a", "name": "Set", "type": "n8n-nodes-base.set", "position": [0, 0]},
        ],
        "connections": {},
    }
    path = tmp_path / "no_trigger.json"
    path.write_text(json.dumps(wf))
    findings = validate(path)
    assert any(f.rule_id == "WF005" for f in findings)


def test_invalid_json_reports_wf000(tmp_path):
    path = tmp_path / "not_json.json"
    path.write_text("{not valid json")
    findings = validate(path)
    assert len(findings) == 1
    assert findings[0].rule_id == "WF000"
