from app.models import User, db


def test_login_with_malformed_password_hash_returns_401(client):
    user = User(
        email="manager@example.com",
        role="ADMIN",
        can_manage_lifecycle=True,
        password_hash="legacy-hash-format",
    )
    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/auth/login",
        data={"email": user.email, "password": "password123"},
        follow_redirects=False,
    )

    assert response.status_code == 401
