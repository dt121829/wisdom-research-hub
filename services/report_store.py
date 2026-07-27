"""Archive of generated reports.

Reports are written as JSON files under data/reports/. This is durable when the app
runs locally or on your own server. On Streamlit Community Cloud the container's
disk is reset whenever the app restarts or redeploys, so the archive is effectively
session-length there — the Reports Library page says so plainly rather than implying
permanence. To make it durable in the cloud, swap the three functions below for a
database or object-store implementation; nothing else needs to change.
"""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent.parent / "data" / "reports"


def _ensure_dir() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def save_report(body: str, *, topic: str, report_type: str, audience: str,
                length: str, style: str, language: str, purpose: str,
                provider: str) -> str:
    """Persist a report and return its id."""
    _ensure_dir()
    report_id = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
    record = {
        "id": report_id,
        "created": datetime.now().isoformat(timespec="seconds"),
        "topic": topic,
        "report_type": report_type,
        "audience": audience,
        "length": length,
        "style": style,
        "language": language,
        "purpose": purpose,
        "provider": provider,
        "body": body,
    }
    (REPORTS_DIR / f"{report_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_id


def list_reports() -> list[dict]:
    """All stored reports, newest first, without their bodies."""
    _ensure_dir()
    out = []
    for path in REPORTS_DIR.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            record.pop("body", None)
            out.append(record)
        except Exception:
            continue  # skip anything corrupted rather than breaking the page
    return sorted(out, key=lambda r: r.get("created", ""), reverse=True)


def get_report(report_id: str) -> dict | None:
    path = REPORTS_DIR / f"{_safe_id(report_id)}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def delete_report(report_id: str) -> bool:
    path = REPORTS_DIR / f"{_safe_id(report_id)}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def _safe_id(report_id: str) -> str:
    """Defend against path traversal in an id coming from the UI."""
    return re.sub(r"[^A-Za-z0-9_-]", "", report_id)
