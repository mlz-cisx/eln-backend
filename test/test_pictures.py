import gzip
import os
import shutil
import tempfile
import uuid

from joeseln_backend.conf.base_conf import ELEM_MAXIMUM_SIZE
from joeseln_backend.conf.content_types import picture_content_type, \
    picture_content_type_model
from joeseln_backend.main import app
from joeseln_backend.models import models
from test.conftest import (
    TestSession,
    mock_get_current_user_admin,
    mock_get_current_user_nonadmin,
    mock_get_current_user_groupuser,
    mock_get_current_user_groupadmin,
    mock_get_current_user_groupguest,
    _assign_users_to_labbook_group,
    get_current_user,
)


# -------------------------------------------------------------------
# Labbook creation helper (always admin)
# -------------------------------------------------------------------
def _create_labbook(client):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    title = f"Pic Test Labbook {uuid.uuid4().hex[:8]}"
    resp = client.post("/api/labbooks/",
                       json={"title": title, "description": "temp"})
    assert resp.status_code == 200
    return resp.json()["pk"]


# -------------------------------------------------------------------
# Temporary storage helper — patches PICTURES_BASE_PATH for tests
# -------------------------------------------------------------------
def _temp_picture_storage(monkeypatch):
    temp_dir = tempfile.mkdtemp(prefix="mlzeln_pictures_")
    monkeypatch.setattr("joeseln_backend.conf.base_conf.PICTURES_BASE_PATH",
                        temp_dir + "/")
    return temp_dir


# -------------------------------------------------------------------
# Upload helper — background image upload
# -------------------------------------------------------------------
def _upload_picture_background(client, title="testpic",
                               img_name="bg.png", img_content=b"PNGDATA",
                               labbook_pk=None):
    data = {"title": title}
    if labbook_pk:
        data["labbook_pk"] = labbook_pk

    return client.post(
        "/api/pictures/",
        data=data,
        files={"background_image": (img_name, img_content, "image/png")},
    )


# -------------------------------------------------------------------
# Picture helper — update canvas content
# -------------------------------------------------------------------
def _update_picture_canvas_content(
        client,
        picture_pk,
        canvas_content='{"objects":[]}',
        origin=None,
):
    return client.patch(
        f"/api/pictures/{picture_pk}/canvas_content/",
        json={
            "canvas_content": canvas_content,
            "origin": str(origin or picture_pk),
        },
    )


# -------------------------------------------------------------------
# Upload helper — sketch upload
# -------------------------------------------------------------------
def _upload_picture_sketch(client, title="sketchpic",
                           canvas_json='{"a":1}', labbook_pk=None):
    compressed = gzip.compress(canvas_json.encode("utf-8"))
    data = {"title": title}
    if labbook_pk:
        data["labbook_pk"] = labbook_pk

    return client.post(
        "/api/pictures/",
        data=data,
        files={"canvas_content": (
        "canvas.json.gz", compressed, "application/gzip")},
    )


# -------------------------------------------------------------------
# DB fetch helper
# -------------------------------------------------------------------
def _get_db_picture(pk):
    db = TestSession()
    try:
        return db.get(models.Picture, uuid.UUID(pk))
    finally:
        db.close()


# -------------------------------------------------------------------
# Mock guest-role check
# -------------------------------------------------------------------
def mock_check_for_guest_role(db, labbook_pk, user):
    return ["guest-role-found"]


# ===================================================================
#  WRITE-ACCESS TESTS (admin, groupadmin, groupuser, nonadmin assigned)
# ===================================================================

def test_upload_picture_background_as_admin(client, as_admin, monkeypatch):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    app.dependency_overrides[get_current_user] = mock_get_current_user_admin

    resp = _upload_picture_background(client, labbook_pk=labbook_pk)
    assert resp.status_code == 200

    pic_pk = resp.json()["pk"]
    assert _get_db_picture(pic_pk) is not None

    shutil.rmtree(temp_dir)


def test_upload_picture_background_as_groupadmin(client, as_groupadmin,
                                                 monkeypatch):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    app.dependency_overrides[
        get_current_user] = mock_get_current_user_groupadmin

    resp = _upload_picture_background(client, img_name="ga.png",
                                      labbook_pk=labbook_pk)
    assert resp.status_code == 200

    pic_pk = resp.json()["pk"]
    db_pic = _get_db_picture(pic_pk)
    assert db_pic is not None

    assert os.path.exists(os.path.join(temp_dir, db_pic.background_image))
    shutil.rmtree(temp_dir)


def test_upload_picture_background_as_groupuser(client, as_groupuser,
                                                monkeypatch):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupuser

    resp = _upload_picture_background(client, img_name="gu.png",
                                      labbook_pk=labbook_pk)
    assert resp.status_code == 200

    pic_pk = resp.json()["pk"]
    db_pic = _get_db_picture(pic_pk)
    assert db_pic is not None

    assert os.path.exists(os.path.join(temp_dir, db_pic.background_image))
    shutil.rmtree(temp_dir)


def test_upload_picture_sketch_as_admin(client, as_admin, monkeypatch):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    app.dependency_overrides[get_current_user] = mock_get_current_user_admin

    resp = _upload_picture_sketch(client, labbook_pk=labbook_pk)
    assert resp.status_code == 200

    pic_pk = resp.json()["pk"]
    assert _get_db_picture(pic_pk) is not None

    shutil.rmtree(temp_dir)


# ===================================================================
#  NO-ACCESS TESTS (nonadmin, groupuser, groupadmin without assignment)
# ===================================================================

def test_upload_picture_background_as_nonadmin_no_access(client, as_nonadmin,
                                                         monkeypatch):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)

    app.dependency_overrides[get_current_user] = mock_get_current_user_nonadmin

    resp = _upload_picture_background(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403

    shutil.rmtree(temp_dir)


def test_upload_picture_background_as_groupuser_no_access(client, as_groupuser,
                                                          monkeypatch):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupuser

    resp = _upload_picture_background(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403

    shutil.rmtree(temp_dir)


def test_upload_picture_background_as_groupadmin_no_access(client,
                                                           as_groupadmin,
                                                           monkeypatch):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)

    app.dependency_overrides[
        get_current_user] = mock_get_current_user_groupadmin

    resp = _upload_picture_background(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403

    shutil.rmtree(temp_dir)


def test_upload_picture_sketch_as_groupguest(client, as_groupguest,
                                             monkeypatch):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    app.dependency_overrides[
        get_current_user] = mock_get_current_user_groupguest

    monkeypatch.setattr(
        "joeseln_backend.services.labbook.labbook_service.check_for_guest_role",
        mock_check_for_guest_role,
    )

    resp = _upload_picture_sketch(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403

    shutil.rmtree(temp_dir)


# ===================================================================
#  SIZE LIMIT TEST
# ===================================================================

def test_upload_picture_rejected_for_size_limit(client, as_admin, monkeypatch):
    _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    too_big = (ELEM_MAXIMUM_SIZE << 10) + 1
    content = b"x" * too_big

    app.dependency_overrides[get_current_user] = mock_get_current_user_admin

    resp = _upload_picture_background(client, img_content=content,
                                      labbook_pk=labbook_pk)
    assert resp.status_code != 200


def test_update_picture_canvas_content(
        client,
        as_admin,
        monkeypatch,
):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    picture_resp = _upload_picture_background(
        client,
        labbook_pk=labbook_pk,
    )
    assert picture_resp.status_code == 200

    picture_pk = picture_resp.json()["pk"]

    lb_data = {
        "position_x": 0,
        "position_y": 0,
        "width": 15,
        "height": 15,
        "child_object_id": picture_pk,
        "child_object_content_type": picture_content_type,
        "child_object_content_type_model": picture_content_type_model,
    }

    r = client.post(
        f"/api/labbooks/{labbook_pk}/elements/",
        json=lb_data,
    )
    assert r.status_code == 200

    resp = _update_picture_canvas_content(
        client,
        picture_pk,
        canvas_content='{"objects":[{"text":"hello world"}]}',
    )

    assert resp.status_code == 200

    shutil.rmtree(temp_dir)


def test_update_picture_canvas_content_rejected_for_size_limit(
        client,
        as_admin,
        monkeypatch,
):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    picture_resp = _upload_picture_background(
        client,
        labbook_pk=labbook_pk,
    )
    assert picture_resp.status_code == 200

    picture_pk = picture_resp.json()["pk"]

    lb_data = {
        "position_x": 0,
        "position_y": 0,
        "width": 15,
        "height": 15,
        "child_object_id": picture_pk,
        "child_object_content_type": picture_content_type,
        "child_object_content_type_model": picture_content_type_model,
    }

    r = client.post(
        f"/api/labbooks/{labbook_pk}/elements/",
        json=lb_data,
    )
    assert r.status_code == 200

    too_big = (ELEM_MAXIMUM_SIZE << 10) + 1
    canvas_content = "x" * too_big

    resp = _update_picture_canvas_content(
        client,
        picture_pk,
        canvas_content=canvas_content,
    )

    assert resp.status_code == 204
    assert resp.content == b""

    shutil.rmtree(temp_dir)


def test_update_picture_canvas_content_denied_in_strict_mode(
        client,
        as_admin,
        monkeypatch,
):
    temp_dir = _temp_picture_storage(monkeypatch)

    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    # Enable strict mode
    resp = client.patch(
        f"/api/labbooks/{labbook_pk}/",
        json={
            "title": "Some other title for test strict mode",
            "strict_mode": True,
        },
    )
    assert resp.status_code == 200

    picture_resp = _upload_picture_background(
        client,
        labbook_pk=labbook_pk,
    )
    assert picture_resp.status_code == 200

    picture_pk = picture_resp.json()["pk"]

    lb_data = {
        "position_x": 0,
        "position_y": 0,
        "width": 15,
        "height": 15,
        "child_object_id": picture_pk,
        "child_object_content_type": picture_content_type,
        "child_object_content_type_model": picture_content_type_model,
    }

    r = client.post(
        f"/api/labbooks/{labbook_pk}/elements/",
        json=lb_data,
    )
    assert r.status_code == 200

    app.dependency_overrides[
        get_current_user
    ] = mock_get_current_user_groupuser

    resp = _update_picture_canvas_content(
        client,
        picture_pk,
        canvas_content='{"objects":[{"text":"forbidden"}]}',
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Picture not found"}

    shutil.rmtree(temp_dir)
