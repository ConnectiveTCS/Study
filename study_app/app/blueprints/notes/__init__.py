from flask import Blueprint

notes_bp = Blueprint("notes", __name__, url_prefix="/notes")

from . import routes  # noqa: F401, E402
