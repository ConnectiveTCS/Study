from flask import Blueprint

flashcards_bp = Blueprint("flashcards", __name__, url_prefix="/flashcards")

from . import routes  # noqa: F401, E402
