from flask import Blueprint

pomodoro_bp = Blueprint('pomodoro', __name__, url_prefix='/pomodoro')

from . import routes  # noqa: F401, E402
