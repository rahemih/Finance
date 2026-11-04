"""P24-WY offline evidence reconciliation boundary checks, no broker/runtime access."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_p24_wy_checkpoint_does_not_claim_postmerge_pass():
    state = (ROOT / "docs/02-current-state/CURRENT-STATE.md").read_text(encoding="utf-8")
    note = (ROOT / "docs/19-production/P24-WY-SECURITY-POSTMERGE-EVIDENCE-CHECKPOINT.md").read_text(encoding="utf-8")
    assert "FIN-P24-WY-001" in state
    assert "POSTMERGE_UNVERIFIED" in state
    assert "**POSTMERGE_UNVERIFIED**" in note
    assert "5ac2a04dad1ce2d5603154bfc5b769da82c0beaa" in state
    assert "P24-B BLOCKED" in state
    assert "G13 NOT_STARTED" in state
    assert "LIVE_TRADING DISABLED" in state
    assert "AUTO_TRADING DISABLED" in state


def test_p24_wy_dossier_keeps_all_pre_first_live_fail_closed():
    dossier = json.loads((ROOT / "config/production/production-readiness-dossier.json").read_text(encoding="utf-8"))
    pre = [item for item in dossier["production_prerequisites"] if item["stage"] == "PRE_FIRST_LIVE"]
    assert len(pre) == 9
    assert all(item["satisfied"] is False for item in pre)
    assert dossier["next"]["p24_b"] == "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES"
    assert dossier["next"]["g13"] == "NOT_STARTED"
    assert dossier["safety"]["live_trading"] == "DISABLED"
    assert dossier["safety"]["auto_trading"] == "DISABLED"


def test_p24_wy_catalog_reconciled_without_phase_promotion():
    cat = (ROOT / "docs/13-tasks/TASK-CATALOG.md").read_text(encoding="utf-8")
    assert "| FIN-P24-WY-001 |" in cat
    assert "POSTMERGE_UNVERIFIED" in cat
    assert "PR #521 MERGED" in cat
