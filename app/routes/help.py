from flask import Blueprint, render_template

help_bp = Blueprint("help", __name__, url_prefix="/help")


@help_bp.route("/")
def index():
    """Main help dashboard."""
    return render_template("help/index.html", title="Lifecycle Help Center")


@help_bp.route("/how-to-use")
def how_to_use():
    """Step-by-step guide for intake forms."""
    return render_template(
        "help/how_to_use.html",
        title="How to Process a Lifecycle Event",
    )


@help_bp.route("/role-entitlements")
def role_entitlements():
    """Explanation of the Role Matrix and baseline access."""
    return render_template(
        "help/role_entitlements.html",
        title="Role Entitlements Matrix",
    )


@help_bp.route("/vendor-routing")
def vendor_routing():
    """Explanation of the automated Action Matrix (MSPs)."""
    return render_template(
        "help/vendor_routing.html",
        title="Automated Vendor Routing",
    )
