from flask import Blueprint

pdfs_bp = Blueprint('pdfs', __name__, url_prefix='/pdfs')

from . import routes  # noqa: F401, E402
