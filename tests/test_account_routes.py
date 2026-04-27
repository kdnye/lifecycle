import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.models import CommunicationOptions, db


def test_communication_options_page_renders_with_defaults():
    app = create_app()

    with app.app_context():
        db.create_all()

    client = app.test_client()
    response = client.get('/account/communication-options')

    assert response.status_code == 200
    assert b'Communication Options' in response.data


def test_communication_options_save_persists_values():
    app = create_app()

    with app.app_context():
        db.create_all()

    client = app.test_client()
    response = client.post(
        '/account/communication-options',
        data={
            'it_support_email': 'support@example.com',
            'it_sales_email': 'sales@example.com',
            'telecon_sales_email': 'telecon@example.com',
            'internal_notification_list': 'ops@example.com,hr@example.com',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Communication options saved.' in response.data

    with app.app_context():
        options = CommunicationOptions.query.first()
        assert options is not None
        assert options.it_support_email == 'support@example.com'
        assert options.it_sales_email == 'sales@example.com'
        assert options.telecon_sales_email == 'telecon@example.com'
        assert options.internal_notification_list == 'ops@example.com,hr@example.com'
