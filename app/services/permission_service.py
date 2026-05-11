from __future__ import annotations

from typing import Optional

from app.models import DistributionList, FileSharePermission, RoleMatrix, db


def list_distribution_lists(active_only: bool = True) -> list[DistributionList]:
    q = DistributionList.query
    if active_only:
        q = q.filter_by(is_active=True)
    return q.order_by(DistributionList.name).all()


def list_file_shares(active_only: bool = True) -> list[FileSharePermission]:
    q = FileSharePermission.query
    if active_only:
        q = q.filter_by(is_active=True)
    return q.order_by(FileSharePermission.name).all()


def create_distribution_list(data: dict) -> DistributionList:
    dl = DistributionList(
        name=data["name"],
        email_address=data.get("email_address") or None,
        description=data.get("description") or None,
        is_active=True,
    )
    db.session.add(dl)
    db.session.commit()
    return dl


def update_distribution_list(dl: DistributionList, data: dict) -> DistributionList:
    dl.name = data.get("name", dl.name)
    dl.email_address = data.get("email_address") or dl.email_address
    dl.description = data.get("description", dl.description)
    db.session.commit()
    return dl


def deactivate_distribution_list(dl: DistributionList) -> None:
    dl.is_active = False
    db.session.commit()


def create_file_share(data: dict) -> FileSharePermission:
    share = FileSharePermission(
        name=data["name"],
        share_path=data.get("share_path") or None,
        access_level=data.get("access_level", "Read"),
        description=data.get("description") or None,
        is_active=True,
    )
    db.session.add(share)
    db.session.commit()
    return share


def update_file_share(share: FileSharePermission, data: dict) -> FileSharePermission:
    share.name = data.get("name", share.name)
    share.share_path = data.get("share_path", share.share_path)
    share.access_level = data.get("access_level", share.access_level)
    share.description = data.get("description", share.description)
    db.session.commit()
    return share


def deactivate_file_share(share: FileSharePermission) -> None:
    share.is_active = False
    db.session.commit()


def get_role_assignments() -> dict[int, dict]:
    """Returns {role_matrix_id: {dl_ids: set, share_ids: set}} for the matrix UI."""
    roles = RoleMatrix.query.all()
    result: dict[int, dict] = {}
    for role in roles:
        result[role.id] = {
            "dl_ids": {dl.id for dl in role.distribution_lists},
            "share_ids": {s.id for s in role.file_share_permissions},
        }
    return result


def set_role_dl_assignment(
    role_matrix_id: int, dl_id: int, assigned: bool
) -> None:
    role = db.session.get(RoleMatrix, role_matrix_id)
    dl = db.session.get(DistributionList, dl_id)
    if not role or not dl:
        return
    if assigned:
        if dl not in role.distribution_lists:
            role.distribution_lists.append(dl)
    else:
        if dl in role.distribution_lists:
            role.distribution_lists.remove(dl)
    db.session.commit()


def set_role_share_assignment(
    role_matrix_id: int, share_id: int, assigned: bool
) -> None:
    role = db.session.get(RoleMatrix, role_matrix_id)
    share = db.session.get(FileSharePermission, share_id)
    if not role or not share:
        return
    if assigned:
        if share not in role.file_share_permissions:
            role.file_share_permissions.append(share)
    else:
        if share in role.file_share_permissions:
            role.file_share_permissions.remove(share)
    db.session.commit()


def get_permissions_for_role(role_profile: str) -> dict:
    """Returns assigned active DLs and file shares for a role profile."""
    role = RoleMatrix.query.filter_by(role_profile=role_profile).first()
    if not role:
        return {"distribution_lists": [], "file_shares": []}
    dls = [dl for dl in role.distribution_lists if dl.is_active]
    shares = [s for s in role.file_share_permissions if s.is_active]
    return {"distribution_lists": dls, "file_shares": shares}
