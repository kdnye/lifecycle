from __future__ import annotations

from functools import wraps

from flask import abort, g, session

from app.models import User, db

SESSION_USER_ID_KEY = "fsi_user_id"


def get_current_user() -> User | None:
    user_id = session.get(SESSION_USER_ID_KEY)
    if not user_id:
        return None
    return db.session.get(User, user_id)


def attach_current_user() -> None:
    g.current_user = get_current_user()


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if get_current_user() is None:
            abort(401)
        return view_func(*args, **kwargs)

    return wrapped_view


def set_authenticated_user(user: User) -> None:
    session[SESSION_USER_ID_KEY] = user.id


def clear_authenticated_user() -> None:
    session.pop(SESSION_USER_ID_KEY, None)
