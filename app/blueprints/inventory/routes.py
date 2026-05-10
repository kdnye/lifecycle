from flask import Blueprint, abort

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.get("/")
def list_assets():
    # Stub: full implementation in inventory service phase
    abort(501)
