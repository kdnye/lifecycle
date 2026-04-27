import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.models import ActionMatrix, QuestionMatrix, RoleMatrix, db
from scripts.seeds import seed_baseline_policy_rows


def test_baseline_seed_is_idempotent_and_complete():
    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()

        first_changes = seed_baseline_policy_rows()
        assert first_changes > 0

        second_changes = seed_baseline_policy_rows()
        assert second_changes == 0

        assert RoleMatrix.query.count() == 5
        assert QuestionMatrix.query.count() == 9
        assert ActionMatrix.query.count() == 7

        contractor_row = QuestionMatrix.query.filter_by(
            role_profile="contractor",
            question_key="contract_end_date_required",
        ).first()
        assert contractor_row is not None
        assert contractor_row.is_required is True
        assert "hard-stop" in contractor_row.prompt.lower()
