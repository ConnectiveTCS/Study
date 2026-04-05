from flask import Blueprint

gamification_bp = Blueprint(
    "gamification",
    __name__,
    url_prefix="/gamification",
    template_folder="templates",
)

from . import routes  # noqa: F401, E402
