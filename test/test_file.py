import os
import shutil
import tempfile
import uuid

from joeseln_backend.conf.base_conf import ELEM_MAXIMUM_SIZE
from joeseln_backend.models import models
from joeseln_backend.models.models import File
from test.conftest import TestSession, app, get_current_user, \
    mock_get_current_user_admin, _assign_users_to_labbook_group, \
    mock_get_current_user_groupguest, mock_get_current_user_groupadmin, \
    mock_get_current_user_groupuser, mock_get_current_user_nonadmin


def mock_check_for_guest_role(db, labbook_pk, user):
    # Always treat the user as having a guest role
    return ["guest-role-found"]


def _create_labbook_and_assign_roles(client):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin

    unique_title = f"Upload Test Labbook {uuid.uuid4()}"

    resp = client.post(
        "/api/labbooks/",
        json={"title": unique_title, "description": "temp"},
    )
    assert resp.status_code == 200

    labbook_pk = resp.json()["pk"]
    _assign_users_to_labbook_group(labbook_pk)
    return labbook_pk


# -------------------------------------------------------------------
# Temporary storage helper — patches FILES_BASE_PATH for tests
# -------------------------------------------------------------------
def _temp_storage(monkeypatch):
    temp_dir = tempfile.mkdtemp(prefix="mlzeln_files_")
    monkeypatch.setattr("joeseln_backend.conf.base_conf.FILES_BASE_PATH",
                        temp_dir)
    return temp_dir


# -------------------------------------------------------------------
# Upload helper — ensures filename is preserved
# -------------------------------------------------------------------
def _upload_file(
        client,
        name="file.txt",
        content=b"DATA",
        description="",
        labbook_pk=None,
):
    if labbook_pk is None:
        labbook_pk = uuid.uuid4()

    data = {
        "title": name,
        "name": name,
        "description": description,
        "labbook_pk": str(labbook_pk),
    }

    return client.post(
        "/api/files/",
        data=data,
        files={"path": (name, content, "application/octet-stream")},
        headers={"Authorization": "Bearer dummy"},
    )


# -------------------------------------------------------------------
# DB fetch helper
# -------------------------------------------------------------------
def _get_db_file(file_pk):
    db = TestSession()
    try:
        return db.get(File, uuid.UUID(file_pk))
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════
# GROUP MEMBERSHIP — verify assigned roles for labbook group
# ═══════════════════════════════════════════════════════════════════

def _get_roles_for_user(db, user_id, group_id):
    return db.query(
        models.UserToGroupRole.user_group_role
    ).filter(
        models.UserToGroupRole.user_id == user_id,
        models.UserToGroupRole.group_id == group_id
    ).all()


def test_group_roles_assigned_correctly(client, as_admin, monkeypatch):
    """
    After creating a labbook and calling _assign_users_to_labbook_group,
    verify that groupadmin, groupuser, nonadmin, and groupguest users
    are correctly assigned to the labbook's owner group.
    """

    # create labbook as admin
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    labbook_resp = client.post(
        "/api/labbooks/",
        json={"title": "Role Test Labbook", "description": "temp"},
    )
    assert labbook_resp.status_code == 200
    labbook_pk = labbook_resp.json()["pk"]

    # fetch labbook owner group
    db = TestSession()
    labbook = db.get(models.Labbook, labbook_pk)
    owner_groupname = labbook.owner_group
    owner_group = db.query(models.Group).filter(
        models.Group.groupname == owner_groupname
    ).first()
    assert owner_group is not None

    # assign roles
    _assign_users_to_labbook_group(labbook_pk)

    # role map from your backend
    role_map = {
        "admin": 1,
        "groupadmin": 2,
        "user": 3,
        "guest": 4,
    }

    # fetch real role IDs from DB
    roles_db = db.query(models.Role).all()
    role_map = {r.rolename: r.id for r in roles_db}

    # expected assignments from your helper:
    expected = {
        3: role_map["groupadmin"],  # groupadmin user
        4: role_map["user"],  # groupuser
        5: role_map["guest"],  # groupguest
    }

    # verify each user has correct role in group
    for user_id, expected_role in expected.items():
        roles = _get_roles_for_user(db, user_id, owner_group.id)
        role_ids = [r[0] for r in roles]
        assert expected_role in role_ids

    db.close()
    app.dependency_overrides.pop(get_current_user, None)


# ═══════════════════════════════════════════════════════════════════
# ADMIN — upload file
# ═══════════════════════════════════════════════════════════════════

def test_upload_file_as_admin(client, as_admin, monkeypatch):
    temp_dir = _temp_storage(monkeypatch)

    labbook_pk = _create_labbook_and_assign_roles(client)

    resp = _upload_file(client, labbook_pk=labbook_pk)
    assert resp.status_code == 200

    file_pk = resp.json()["pk"]
    db_file = _get_db_file(file_pk)
    assert db_file is not None

    normalized = os.path.basename(db_file.path.lstrip("/"))
    stored_path = os.path.join(temp_dir, normalized)
    assert os.path.exists(stored_path)

    shutil.rmtree(temp_dir)



# ═══════════════════════════════════════════════════════════════════
# NONADMIN — allowed
# ═══════════════════════════════════════════════════════════════════

def test_upload_file_as_nonadmin(client, as_nonadmin, monkeypatch):
    temp_dir = _temp_storage(monkeypatch)

    labbook_pk = _create_labbook_and_assign_roles(client)

    resp = _upload_file(client, labbook_pk=labbook_pk)
    assert resp.status_code == 200

    file_pk = resp.json()["pk"]
    assert _get_db_file(file_pk) is not None

    shutil.rmtree(temp_dir)



# ═══════════════════════════════════════════════════════════════════
# GROUPADMIN — allowed
# ═══════════════════════════════════════════════════════════════════

def test_upload_file_as_groupadmin(client, as_groupadmin, monkeypatch):
    temp_dir = _temp_storage(monkeypatch)

    labbook_pk = _create_labbook_and_assign_roles(client)

    resp = _upload_file(client, name="ga.txt", labbook_pk=labbook_pk)
    assert resp.status_code == 200

    file_pk = resp.json()["pk"]
    db_file = _get_db_file(file_pk)
    assert db_file is not None

    stored_path = os.path.join(temp_dir, db_file.path)
    assert os.path.exists(stored_path)

    shutil.rmtree(temp_dir)



# ═══════════════════════════════════════════════════════════════════
# GROUPUSER — allowed
# ═══════════════════════════════════════════════════════════════════
def test_upload_file_as_groupuser(client, as_groupuser, monkeypatch):
    temp_dir = _temp_storage(monkeypatch)

    labbook_pk = _create_labbook_and_assign_roles(client)

    resp = _upload_file(client, name="gu.txt", labbook_pk=labbook_pk)
    assert resp.status_code == 200

    file_pk = resp.json()["pk"]
    db_file = _get_db_file(file_pk)
    assert db_file is not None

    stored_path = os.path.join(temp_dir, db_file.path)
    assert os.path.exists(stored_path)

    shutil.rmtree(temp_dir)


# ═══════════════════════════════════════════════════════════════════
# GROUPGUEST — not allowed
# ═══════════════════════════════════════════════════════════════════

def test_upload_file_as_groupguest(client, as_groupguest, monkeypatch):
    temp_dir = _temp_storage(monkeypatch)

    # create labbook as admin
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    labbook_resp = client.post(
        "/api/labbooks/",
        json={"title": "Upload Test Labbook", "description": "temp"},
    )
    assert labbook_resp.status_code == 200
    labbook_pk = labbook_resp.json()["pk"]

    # assign roles
    _assign_users_to_labbook_group(labbook_pk)

    # NOW switch override to groupguest
    app.dependency_overrides[
        get_current_user] = mock_get_current_user_groupguest

    # mock guest-role check
    monkeypatch.setattr(
        "joeseln_backend.services.labbook.labbook_service.check_for_guest_role",
        mock_check_for_guest_role,
    )

    # upload with token
    resp = _upload_file(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403

    shutil.rmtree(temp_dir)


# ═══════════════════════════════════════════════════════════════════
# SIZE LIMIT — rejected
# ═══════════════════════════════════════════════════════════════════

def test_upload_file_rejected_for_size_limit(client, as_admin, monkeypatch):
    _temp_storage(monkeypatch)

    too_big = (ELEM_MAXIMUM_SIZE << 10) + 1
    content = b"x" * too_big

    resp = _upload_file(client, content=content)
    assert resp.status_code != 200


# ═══════════════════════════════════════════════════════════════════
# DESCRIPTION sanitization
# ═══════════════════════════════════════════════════════════════════

def test_upload_file_sanitizes_description(client, as_admin, monkeypatch):
    temp_dir = _temp_storage(monkeypatch)

    labbook_pk = _create_labbook_and_assign_roles(client)

    dirty = "<script>alert('x')</script>Clean"
    resp = _upload_file(client, description=dirty, labbook_pk=labbook_pk)
    assert resp.status_code == 200

    returned = resp.json()["description"].lower()
    assert "<script>" not in returned
    assert "</script>" not in returned
    assert "&lt;script" in returned

    shutil.rmtree(temp_dir)


# ═══════════════════════════════════════════════════════════════════
# DESY_INTEGRATION — .spc file triggers plot generation
# ═══════════════════════════════════════════════════════════════════

def test_upload_spc_file_triggers_desy_integration(client, as_admin,
                                                   monkeypatch):
    temp_dir = _temp_storage(monkeypatch)

    monkeypatch.setattr("joeseln_backend.conf.base_conf.DESY_INTEGRATION", True)

    def fake_plot(*args, **kwargs):
        return "Generated Plot Content"

    import joeseln_backend.services.file.file_service as file_service
    monkeypatch.setattr(file_service, "create_plot_content_from_spec_file",
                        fake_plot)

    valid_spec = b"""
                    #F test.spc
                    #D Mon Sep 7 11:00:00 2026
                    #C Test SPEC file
                    #S 1 scan_cmd
                    #L X Y
                    1 2
                    """

    resp = _upload_file(
        client,
        name="test.spc",
        content=valid_spec,
        description="Initial",
    )

    assert resp.status_code == 200
    assert "Generated Plot Content" in resp.json()["description"]

    shutil.rmtree(temp_dir)


# ═══════════════════════════════════════════════════════════════════
# Upload Permission Tests — Users Without Write Access Must Receive 403
# ═══════════════════════════════════════════════════════════════════

def test_upload_file_as_nonadmin_no_access(client, as_nonadmin, monkeypatch):
    temp_dir = _temp_storage(monkeypatch)

    # create labbook as admin
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    unique_title = f"NoAccess Labbook {uuid.uuid4()}"
    labbook_resp = client.post(
        "/api/labbooks/",
        json={"title": unique_title, "description": "temp"},
    )
    assert labbook_resp.status_code == 200
    labbook_pk = labbook_resp.json()["pk"]

    # switch to nonadmin (no role assignment!)
    app.dependency_overrides[get_current_user] = mock_get_current_user_nonadmin

    resp = _upload_file(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403

    shutil.rmtree(temp_dir)


def test_upload_file_as_groupuser_no_access(client, as_groupuser, monkeypatch):
    temp_dir = _temp_storage(monkeypatch)

    # create labbook as admin
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    unique_title = f"NoAccess Labbook {uuid.uuid4()}"
    labbook_resp = client.post(
        "/api/labbooks/",
        json={"title": unique_title, "description": "temp"},
    )
    assert labbook_resp.status_code == 200
    labbook_pk = labbook_resp.json()["pk"]

    # switch to groupuser (no role assignment!)
    app.dependency_overrides[get_current_user] = mock_get_current_user_groupuser

    resp = _upload_file(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403

    shutil.rmtree(temp_dir)


def test_upload_file_as_groupadmin_no_access(client, as_groupadmin,
                                             monkeypatch):
    temp_dir = _temp_storage(monkeypatch)

    # create labbook as admin
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    unique_title = f"NoAccess Labbook {uuid.uuid4()}"
    labbook_resp = client.post(
        "/api/labbooks/",
        json={"title": unique_title, "description": "temp"},
    )
    assert labbook_resp.status_code == 200
    labbook_pk = labbook_resp.json()["pk"]

    # switch to groupadmin (no role assignment!)
    app.dependency_overrides[
        get_current_user] = mock_get_current_user_groupadmin

    resp = _upload_file(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403

    shutil.rmtree(temp_dir)
