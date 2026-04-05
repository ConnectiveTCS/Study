"""Anonymous session middleware — ensures every visitor has a session token cookie."""
import uuid
from flask import request, g, current_app
from flask_login import current_user
from .extensions import db
from .models.user import AnonymousSession


def init_anon_session() -> None:
    """Before every request: ensure an anonymous session token exists in g and cookie."""
    cookie_name = current_app.config["ANON_COOKIE_NAME"]
    token = request.cookies.get(cookie_name)

    if not token:
        token = str(uuid.uuid4())
        g.new_anon_token = token  # signal after_request to set cookie
        # Create DB record
        session_row = AnonymousSession(session_token=token)
        db.session.add(session_row)
        db.session.commit()
    else:
        g.new_anon_token = None

    g.anon_token = token


def set_anon_cookie(response):
    """After request: set the cookie if a new token was generated."""
    if g.get("new_anon_token"):
        cookie_name = current_app.config["ANON_COOKIE_NAME"]
        max_age = current_app.config["ANON_COOKIE_MAX_AGE"]
        response.set_cookie(
            cookie_name,
            g.new_anon_token,
            max_age=max_age,
            httponly=True,
            samesite="Lax",
            secure=not current_app.debug,
        )
    return response
