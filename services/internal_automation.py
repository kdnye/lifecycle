from __future__ import annotations

from datetime import date

from app.models import IntakeRequest, db
from services.workflow import execute_lifecycle_event

_FINAL_STATUSES = {"processed", "rejected"}
_EXECUTABLE_STATUSES = {"approved"}
_CONTRACTOR_AUTO_APPROVAL_STATUSES = {"draft", "submitted", "pending_approval"}


def _normalize_status(status: str | None) -> str:
    return (status or "").strip().lower()


def _is_contractor_hard_stop_candidate(intake_request: IntakeRequest, normalized_status: str) -> bool:
    return (
        intake_request.event_type == "offboarding"
        and intake_request.role_profile == "contractor"
        and intake_request.termination_date is not None
        and normalized_status in _CONTRACTOR_AUTO_APPROVAL_STATUSES
    )


def process_due_terminations(target_date: date | None = None) -> dict[str, object]:
    """Process termination requests due on a date with idempotent lifecycle execution."""
    due_date = target_date or date.today()
    candidates = (
        IntakeRequest.query.filter_by(event_type="offboarding", termination_date=due_date)
        .order_by(IntakeRequest.id.asc())
        .all()
    )

    summary: dict[str, object] = {
        "status": "ok",
        "date": due_date.isoformat(),
        "total_candidates": len(candidates),
        "processed": 0,
        "auto_approved": 0,
        "skipped_final": 0,
        "skipped_not_ready": 0,
        "errors": [],
    }

    for intake_request in candidates:
        normalized_status = _normalize_status(intake_request.status)

        if normalized_status in _FINAL_STATUSES:
            summary["skipped_final"] += 1
            continue

        if normalized_status in _EXECUTABLE_STATUSES:
            result = execute_lifecycle_event(intake_request.id)
            if result.get("status") == "processed":
                summary["processed"] += 1
            else:
                summary["errors"].append(
                    {
                        "intake_id": intake_request.id,
                        "reason": result.get("message", "Execution failed."),
                    }
                )
            continue

        if _is_contractor_hard_stop_candidate(intake_request, normalized_status):
            intake_request.status = "approved"
            try:
                db.session.commit()
            except Exception as exc:  # pragma: no cover - defensive DB handling
                db.session.rollback()
                summary["errors"].append({"intake_id": intake_request.id, "reason": str(exc)})
                continue

            summary["auto_approved"] += 1
            result = execute_lifecycle_event(intake_request.id)
            if result.get("status") == "processed":
                summary["processed"] += 1
            else:
                summary["errors"].append(
                    {
                        "intake_id": intake_request.id,
                        "reason": result.get("message", "Execution failed after auto-approval."),
                    }
                )
            continue

        summary["skipped_not_ready"] += 1

    if summary["errors"]:
        summary["status"] = "partial"

    return summary
