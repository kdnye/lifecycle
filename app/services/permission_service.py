from __future__ import annotations

from app.models import DistributionList, FileSharePermission, RoleMatrix, db


def list_active_distribution_lists() -> list[DistributionList]:
    return (
        db.session.query(DistributionList)
        .filter(DistributionList.is_active.is_(True))
        .order_by(DistributionList.name.asc())
        .all()
    )


def list_active_file_shares() -> list[FileSharePermission]:
    return (
        db.session.query(FileSharePermission)
        .filter(FileSharePermission.is_active.is_(True))
        .order_by(FileSharePermission.name.asc())
        .all()
    )


def list_role_assignments() -> list[RoleMatrix]:
    return db.session.query(RoleMatrix).order_by(RoleMatrix.role_profile.asc()).all()


def set_distribution_list_assignment(role: RoleMatrix, distribution_list: DistributionList) -> bool:
    if distribution_list in role.distribution_lists:
        return False
    role.distribution_lists.append(distribution_list)
    db.session.commit()
    return True


def unset_distribution_list_assignment(role: RoleMatrix, distribution_list: DistributionList) -> bool:
    if distribution_list not in role.distribution_lists:
        return False
    role.distribution_lists.remove(distribution_list)
    db.session.commit()
    return True


def set_file_share_assignment(role: RoleMatrix, file_share: FileSharePermission) -> bool:
    if file_share in role.file_share_permissions:
        return False
    role.file_share_permissions.append(file_share)
    db.session.commit()
    return True


def unset_file_share_assignment(role: RoleMatrix, file_share: FileSharePermission) -> bool:
    if file_share not in role.file_share_permissions:
        return False
    role.file_share_permissions.remove(file_share)
    db.session.commit()
    return True


def create_distribution_list(payload: dict) -> DistributionList:
    record = DistributionList(
        name=(payload.get("name") or "").strip(),
        email=(payload.get("email") or "").strip(),
        description=(payload.get("description") or "").strip() or None,
        is_active=bool(payload.get("is_active", True)),
    )
    db.session.add(record)
    db.session.commit()
    return record


def create_file_share(payload: dict) -> FileSharePermission:
    record = FileSharePermission(
        name=(payload.get("name") or "").strip(),
        resource_path=(payload.get("resource_path") or "").strip(),
        access_level=(payload.get("access_level") or "").strip() or None,
        description=(payload.get("description") or "").strip() or None,
        is_active=bool(payload.get("is_active", True)),
    )
    db.session.add(record)
    db.session.commit()
    return record


def get_role_permissions(role_profile: str) -> dict[str, list[str]]:
    role = db.session.query(RoleMatrix).filter(RoleMatrix.role_profile == role_profile).first()
    if role is None:
        return {"distribution_lists": [], "file_share_permissions": []}

    distribution_lists = [f"{item.name} <{item.email}>" for item in role.distribution_lists if item.is_active]
    file_share_permissions = [
        f"{item.name} ({item.resource_path}){f' - {item.access_level}' if item.access_level else ''}"
        for item in role.file_share_permissions
        if item.is_active
    ]
    return {
        "distribution_lists": sorted(distribution_lists),
        "file_share_permissions": sorted(file_share_permissions),
    }
