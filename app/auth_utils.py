from __future__ import annotations

from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from sqlalchemy.exc import SQLAlchemyError

from app.models import User, db

SESSION_USER_ID_KEY = "fsi_user_id"


def get_current_user() -> User | None:
    user_id = session.get(SESSION_USER_ID_KEY)
    if not user_id:
        return None
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        clear_authenticated_user()
        return None
    if user is None:
        clear_authenticated_user()
    return user


def attach_current_user() -> None:
    g.current_user = get_current_user()


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if get_current_user() is None:
            if request.path.startswith("/api/"):
                abort(401)
            next_path = request.path
            if request.query_string:
                next_path = f"{request.path}?{request.query_string.decode('utf-8', errors='ignore')}"
            return redirect(url_for("auth.login", next=next_path))
        return view_func(*args, **kwargs)

    return wrapped_view


def set_authenticated_user(user_id: int) -> None:
    session[SESSION_USER_ID_KEY] = int(user_id)


def clear_authenticated_user() -> None:
    session.pop(SESSION_USER_ID_KEY, None)
