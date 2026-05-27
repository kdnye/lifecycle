import enum
from datetime import datetime
import uuid

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()

USERS_TABLE = "users"
ROLE_MATRIX_TABLE = "role_matrix"
QUESTION_MATRIX_TABLE = "question_matrix"
ACTION_MATRIX_TABLE = "action_matrix"
INTAKE_REQUEST_TABLE = "intake_request"
INVENTORY_TABLE = "inventory"
ASSET_CATEGORIES_TABLE = "asset_categories"
COMMUNICATION_OPTIONS_TABLE = "communication_options"
INTAKE_ANSWERS_TABLE = "intake_answers"
DISTRIBUTION_LISTS_TABLE = "distribution_lists"
FILE_SHARE_PERMISSIONS_TABLE = "file_share_permissions"
ROLE_DISTRIBUTION_LISTS_TABLE = "role_distribution_lists"
ROLE_FILE_SHARE_PERMISSIONS_TABLE = "role_file_share_permissions"


role_distribution_lists = db.Table(
    ROLE_DISTRIBUTION_LISTS_TABLE,
    db.Column(
        "role_matrix_id",
        db.Integer,
        db.ForeignKey(f"{ROLE_MATRIX_TABLE}.id"),
        primary_key=True,
    ),
    db.Column(
        "distribution_list_id",
        db.Integer,
        db.ForeignKey(f"{DISTRIBUTION_LISTS_TABLE}.id"),
        primary_key=True,
    ),
)

role_file_share_permissions = db.Table(
    ROLE_FILE_SHARE_PERMISSIONS_TABLE,
    db.Column(
        "role_matrix_id",
        db.Integer,
        db.ForeignKey(f"{ROLE_MATRIX_TABLE}.id"),
        primary_key=True,
    ),
    db.Column(
        "file_share_permission_id",
        db.Integer,
        db.ForeignKey(f"{FILE_SHARE_PERMISSIONS_TABLE}.id"),
        primary_key=True,
    ),
)


class AssetStatus(str, enum.Enum):
    AVAILABLE = "Available"
    ASSIGNED  = "Assigned"
    IN_REPAIR = "In_Repair"
    RETIRED   = "Retired"
    LOST      = "Lost"


class AssetTrackingMode(str, enum.Enum):
    SERIALIZED = "Serialized"
    QUANTITY = "Quantity"


class User(db.Model):
    """Mapped representation of the central FSI users table."""

    __tablename__ = USERS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    name = db.Column(db.String(120))
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone = db.Column(db.String(50))
    password_hash = db.Column(db.String(255), nullable=True)
    auth_provider = db.Column(db.String(32), nullable=False, default="local")
    role = db.Column(db.String(50), nullable=False, default="EMPLOYEE")
    employee_approved = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, default=True)
    can_manage_lifecycle = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return check_password_hash(self.password_hash, raw_password)
        except (ValueError, TypeError):
            return False


class RoleMatrix(db.Model):
    __tablename__ = ROLE_MATRIX_TABLE

    id = db.Column(db.Integer, primary_key=True)
    role_profile = db.Column(db.String(64), unique=True, nullable=False)
    m365_plan = db.Column(db.String(64), nullable=False)
    hardware_default = db.Column(db.String(128), nullable=False)
    vpn_policy = db.Column(db.String(64), nullable=False)
    distribution_lists = db.relationship(
        "DistributionList",
        secondary=role_distribution_lists,
        back_populates="role_profiles",
        lazy="select",
    )
    file_share_permissions = db.relationship(
        "FileSharePermission",
        secondary=role_file_share_permissions,
        back_populates="role_profiles",
        lazy="select",
    )


class QuestionMatrix(db.Model):
    __tablename__ = QUESTION_MATRIX_TABLE

    id = db.Column(db.Integer, primary_key=True)
    role_profile = db.Column(db.String(64), nullable=False)
    question_key = db.Column(db.String(128), nullable=False)
    prompt = db.Column(db.String(512), nullable=False)
    is_required = db.Column(db.Boolean, default=False, nullable=False)
    intake_step = db.Column(db.Integer, nullable=False, default=1)
    field_type = db.Column(db.String(32), nullable=True)
    options_json = db.Column(db.Text, nullable=True)
    depends_on_question_key = db.Column(db.String(128), nullable=True, index=True)
    depends_on_answer_value = db.Column(db.String(512), nullable=True)
    visibility_rule = db.Column(db.String(16), nullable=False, default="equals")
    is_dynamic = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class IntakeAnswer(db.Model):
    __tablename__ = INTAKE_ANSWERS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    intake_request_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{INTAKE_REQUEST_TABLE}.id"),
        nullable=False,
        index=True,
    )
    question_matrix_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{QUESTION_MATRIX_TABLE}.id"),
        nullable=False,
        index=True,
    )
    answer_value = db.Column(db.Text, nullable=True)
    answered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    intake_request = db.relationship("IntakeRequest")
    question = db.relationship("QuestionMatrix")


class DistributionList(db.Model):
    __tablename__ = DISTRIBUTION_LISTS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    role_profiles = db.relationship(
        "RoleMatrix",
        secondary=role_distribution_lists,
        back_populates="distribution_lists",
        lazy="select",
    )


class FileSharePermission(db.Model):
    __tablename__ = FILE_SHARE_PERMISSIONS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    resource_path = db.Column(db.String(512), nullable=False, unique=True)
    access_level = db.Column(db.String(64), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    role_profiles = db.relationship(
        "RoleMatrix",
        secondary=role_file_share_permissions,
        back_populates="file_share_permissions",
        lazy="select",
    )


class ActionMatrix(db.Model):
    __tablename__ = ACTION_MATRIX_TABLE

    id = db.Column(db.Integer, primary_key=True)
    intake_condition = db.Column(db.String(128), nullable=False)
    action_name = db.Column(db.String(128), nullable=False)
    target_system = db.Column(db.String(128), nullable=False)


class IntakeRequest(db.Model):
    __tablename__ = INTAKE_REQUEST_TABLE

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    role_profile = db.Column(db.String(64), nullable=False)
    event_type = db.Column(db.String(32), nullable=False)
    manager_email = db.Column(db.String(255), nullable=True)
    generated_email = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    needs_equipment = db.Column(db.Boolean, nullable=False, default=False)
    equip_status = db.Column(db.String(32), nullable=True)
    equip_type = db.Column(db.String(32), nullable=True)
    equip_peripherals = db.Column(db.String(64), nullable=True)
    needs_did = db.Column(db.Boolean, nullable=False, default=False)
    area_code = db.Column(db.String(8), nullable=True)
    needs_physical_phone = db.Column(db.Boolean, nullable=False, default=False)
    driver_needs_laptop = db.Column(db.Boolean, nullable=False, default=False)
    driver_needs_printer = db.Column(db.Boolean, nullable=False, default=False)
    driver_needs_fuel_card = db.Column(db.Boolean, nullable=False, default=False)
    driver_needs_vehicle = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(32), nullable=False, default="draft")
    approval_token = db.Column(
        db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex
    )
    termination_date = db.Column(db.Date, nullable=True)
    is_immediate = db.Column(db.Boolean, nullable=False, default=False)
    forwarding_email = db.Column(db.String(255), nullable=True)


class CommunicationOptions(db.Model):
    __tablename__ = COMMUNICATION_OPTIONS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    it_support_email = db.Column(db.String(255), nullable=False)
    it_sales_email = db.Column(db.String(255), nullable=False)
    telecon_sales_email = db.Column(db.String(255), nullable=False)
    internal_notification_list = db.Column(db.String(1024), nullable=True)


class AssetCategory(db.Model):
    __tablename__ = ASSET_CATEGORIES_TABLE

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_category_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{ASSET_CATEGORIES_TABLE}.id"),
        nullable=True,
        index=True,
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    parent = db.relationship(
        "AssetCategory",
        remote_side="AssetCategory.id",
        foreign_keys="[AssetCategory.parent_category_id]",
        backref=db.backref("subcategories", lazy="select"),
    )
    assets = db.relationship("Inventory", back_populates="category", lazy="dynamic")


class Inventory(db.Model):
    __tablename__ = INVENTORY_TABLE

    id = db.Column(db.Integer, primary_key=True)
    # Identification
    serial_number = db.Column(db.String(128), nullable=True, unique=True, index=True)
    asset_tag = db.Column(db.String(100), nullable=True, unique=True, index=True)
    asset_number = db.Column(db.String(100), nullable=True)
    it_asset_tag = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    ble_tag_id = db.Column(db.String(100), nullable=True, unique=True, index=True)
    # Classification
    category_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{ASSET_CATEGORIES_TABLE}.id"),
        nullable=True,
        index=True,
    )
    make = db.Column(db.String(100), nullable=True)
    model_name = db.Column(db.String(100), nullable=True)
    tracking_mode = db.Column(
        db.Enum(
            AssetTrackingMode,
            name="asset_tracking_mode",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
        default=AssetTrackingMode.SERIALIZED,
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    # State
    status = db.Column(
        db.Enum(
            AssetStatus,
            name="asset_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
        default=AssetStatus.AVAILABLE,
    )
    assigned_to_user_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{USERS_TABLE}.id"),
        nullable=True,
        index=True,
    )
    # Media & notes
    photo_url = db.Column(db.String(1024), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    # Financials
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_price = db.Column(db.Numeric(10, 2), nullable=True)
    warranty_expiry = db.Column(db.Date, nullable=True)
    # Lifecycle linkage
    intake_request_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{INTAKE_REQUEST_TABLE}.id"),
        nullable=True,
    )
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    # Relationships
    category = db.relationship("AssetCategory", back_populates="assets")
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_user_id])
    intake_request = db.relationship("IntakeRequest")
