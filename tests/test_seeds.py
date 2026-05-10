import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.models import ActionMatrix, AssetCategory, QuestionMatrix, RoleMatrix, db
from scripts.seeds import seed_baseline_policy_rows


def _fresh_app_with_db():
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app


def test_baseline_seed_is_idempotent_and_complete():
    app = _fresh_app_with_db()

    with app.app_context():
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


def test_category_seeds_create_hierarchy():
    app = _fresh_app_with_db()

    with app.app_context():
        seed_baseline_policy_rows()

        # Verify top-level categories exist
        computers = AssetCategory.query.filter_by(name="Computers", parent_category_id=None).first()
        assert computers is not None
        assert computers.is_active is True

        vehicles = AssetCategory.query.filter_by(name="Vehicles", parent_category_id=None).first()
        assert vehicles is not None

        # Verify children are correctly linked
        laptops = AssetCategory.query.filter_by(name="Laptops").first()
        assert laptops is not None
        assert laptops.parent_category_id == computers.id

        trucks = AssetCategory.query.filter_by(name="Trucks").first()
        assert trucks is not None
        assert trucks.parent_category_id == vehicles.id

        pallet_jacks = AssetCategory.query.filter_by(name="Pallet Jacks").first()
        assert pallet_jacks is not None
        assert pallet_jacks.parent_category_id == vehicles.id

        # Verify total count: 6 top-level + 8 children = 14
        assert AssetCategory.query.count() == 14

        # Seeding again is idempotent
        seed_baseline_policy_rows()
        assert AssetCategory.query.count() == 14
