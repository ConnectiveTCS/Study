from flask import Blueprint

mindmaps_bp = Blueprint('mindmaps', __name__, url_prefix='/mindmaps')

from . import routes  # noqa: F401, E402
