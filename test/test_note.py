import uuid

from joeseln_backend.main import app
from joeseln_backend.conf.base_conf import ELEM_MAXIMUM_SIZE
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
    title = f"Note Test Labbook {uuid.uuid4().hex[:8]}"
    resp = client.post("/api/labbooks/", json={"title": title, "description": "temp"})
    assert resp.status_code == 200
    return resp.json()["pk"]


# -------------------------------------------------------------------
# DB fetch helper
# -------------------------------------------------------------------
def _get_db_note(pk):
    db = TestSession()
    try:
        return db.get(models.Note, uuid.UUID(pk))
    finally:
        db.close()


# -------------------------------------------------------------------
# Upload helper — create note
# -------------------------------------------------------------------
def _create_note(client, subject="Test Note", content="Hello", labbook_pk=None):
    payload = {
        "subject": subject,
        "content": content,
    }
    if labbook_pk:
        payload["labbook_pk"] = labbook_pk

    return client.post("/api/notes/", json=payload)


# ===================================================================
#  WRITE-ACCESS TESTS
# ===================================================================

def test_create_note_as_admin(client, as_admin):
    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    app.dependency_overrides[get_current_user] = mock_get_current_user_admin

    resp = _create_note(client, labbook_pk=labbook_pk)
    assert resp.status_code == 200

    note_pk = resp.json()["pk"]
    db_note = _get_db_note(note_pk)
    assert db_note is not None
    assert db_note.subject == "Test Note"
    assert db_note.content == "Hello"


def test_create_note_as_groupadmin(client, as_groupadmin):
    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupadmin

    resp = _create_note(client, labbook_pk=labbook_pk)
    assert resp.status_code == 200


def test_create_note_as_groupuser(client, as_groupuser):
    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupuser

    resp = _create_note(client, labbook_pk=labbook_pk)
    assert resp.status_code == 200


# ===================================================================
#  NO-ACCESS TESTS
# ===================================================================

def test_create_note_as_nonadmin_no_access(client, as_nonadmin):
    labbook_pk = _create_labbook(client)

    app.dependency_overrides[get_current_user] = mock_get_current_user_nonadmin

    resp = _create_note(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403


def test_create_note_as_groupuser_no_access(client, as_groupuser):
    labbook_pk = _create_labbook(client)

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupuser

    resp = _create_note(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403


def test_create_note_as_groupadmin_no_access(client, as_groupadmin):
    labbook_pk = _create_labbook(client)

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupadmin

    resp = _create_note(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403


def test_create_note_as_groupguest(client, as_groupguest):
    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupguest

    resp = _create_note(client, labbook_pk=labbook_pk)
    assert resp.status_code == 403


# ===================================================================
#  MISSING LABBOOK_PK TEST
# ===================================================================

def test_create_note_missing_labbook_pk(client, as_admin):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin

    resp = _create_note(client, labbook_pk=None)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Missing labbook_pk"


# ===================================================================
#  SIZE LIMIT TEST
# ===================================================================

def test_create_note_rejected_for_size_limit(client, as_admin):
    labbook_pk = _create_labbook(client)
    _assign_users_to_labbook_group(labbook_pk)

    app.dependency_overrides[get_current_user] = mock_get_current_user_admin

    too_big = (ELEM_MAXIMUM_SIZE << 10) + 1
    content = "x" * too_big

    resp = _create_note(client, content=content, labbook_pk=labbook_pk)
    assert resp.status_code != 200
