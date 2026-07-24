from joeseln_backend.conf.content_types import (
    note_content_type,
    note_content_type_model,
)
from joeseln_backend.main import (
    app,
    get_current_user,
)
from test.conftest import (
    mock_get_current_user_admin,
    mock_get_current_user_groupadmin,
    mock_get_current_user_groupuser,
)


def _create_fresh_element(client, labbook_pk, position_y):
    """create a brand-new note element at a distinct y position.
    for note beside/below testing
    """
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "Fresh Element", "content": "For aside/below tests"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    elem_data = {
        "position_x": 0,
        "position_y": position_y,
        "width": 15,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
        "child_object_content_type_model": note_content_type_model,
    }
    response = client.post(f"/api/labbooks/{labbook_pk}/elements/", json=elem_data)
    assert response.status_code == 200
    return response.json()["pk"]


# ═══════════════════════════════════════════════════════════════════
# GET /api/labbooks/ — list labbooks
# ═══════════════════════════════════════════════════════════════════


# scenario: basic listing — returns a list of labbooks with title, pk, length
def test_get_labbooks(a_labbook, client, as_admin):
    response = client.get("/api/labbooks/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    titles = [lb["title"] for lb in data]
    assert "Test Labbook" in titles


# scenario: non-admin without group membership sees empty list
def test_get_labbooks_as_nonadmin(a_labbook, client, as_nonadmin):
    response = client.get("/api/labbooks/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


# scenario: search by title — filters results
def test_get_labbooks_with_search(a_labbook, client, as_admin):
    response = client.get("/api/labbooks/", params={"search": "Test"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    titles = [lb["title"] for lb in data]
    assert "Test Labbook" in titles


# scenario: search with no match — returns empty list
def test_get_labbooks_with_search_no_match(a_labbook, client, as_admin):
    response = client.get("/api/labbooks/", params={"search": "zzz_nonexistent_zzz"})
    assert response.status_code == 200
    assert len(response.json()) == 0


# scenario: show deleted (deleted=True) — soft-deleted labbooks appear
def test_get_labbooks_show_deleted(a_second_labbook, client, as_admin):
    client.patch(f"/api/labbooks/{a_second_labbook}/soft_delete")
    response = client.get("/api/labbooks/", params={"deleted": True})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    client.patch(f"/api/labbooks/{a_second_labbook}/restore")


# scenario: exclude deleted (deleted=False) — no soft-deleted labbooks in result
def test_get_labbooks_deleted_false(a_labbook, client, as_admin):
    response = client.get("/api/labbooks/", params={"deleted": False})
    assert response.status_code == 200
    for lb in response.json():
        assert lb.get("deleted") is not True


# scenario: ordering by field — results respect the ordering param
def test_get_labbooks_with_ordering(a_labbook, client, as_admin):
    response = client.get("/api/labbooks/", params={"ordering": "title"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: pagination (limit / offset) — slices the result set
def test_get_labbooks_with_pagination(a_labbook, client, as_admin):
    response = client.get("/api/labbooks/", params={"limit": 1})
    assert response.status_code == 200
    assert len(response.json()) <= 1

    response = client.get("/api/labbooks/", params={"offset": 0, "limit": 1})
    assert response.status_code == 200
    assert len(response.json()) <= 1


# scenario: groupadmin sees labbooks in their groups
def test_get_labbooks_as_groupadmin(a_labbook, client, as_groupadmin):
    response = client.get("/api/labbooks/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    titles = [lb["title"] for lb in data]
    assert "Test Labbook" in titles


# scenario: groupuser sees labbooks in their groups
def test_get_labbooks_as_groupuser(a_labbook, client, as_groupuser):
    response = client.get("/api/labbooks/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    titles = [lb["title"] for lb in data]
    assert "Test Labbook" in titles


# scenario: groupguest sees labbooks in their groups
def test_get_labbooks_as_groupguest(a_labbook, client, as_groupguest):
    response = client.get("/api/labbooks/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    titles = [lb["title"] for lb in data]
    assert "Test Labbook" in titles


# ═══════════════════════════════════════════════════════════════════
# POST /api/labbooks/ — create labbook
# ═══════════════════════════════════════════════════════════════════


# scenario: successful creation — admin creates a labbook, all fields returned
def test_create_labbook(client, as_admin):
    data = {"title": "Unique Labbook", "description": "A fresh labbook for testing."}
    response = client.post("/api/labbooks/", json=data)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Unique Labbook"
    assert body["description"] == "A fresh labbook for testing."
    assert body["deleted"] is False
    assert "pk" in body
    assert "created_by" in body
    assert "last_modified_by" in body


# scenario: rejected for non-admin — non-admin cannot create a labbook
def test_create_labbook_rejected_for_nonadmin(client, as_nonadmin):
    data = {"title": "ShouldFail", "description": "Not allowed."}
    response = client.post("/api/labbooks/", json=data)
    assert response.status_code != 200


# scenario: rejected for groupadmin — only admin can create labbooks
def test_create_labbook_rejected_for_groupadmin(client, as_groupadmin):
    data = {"title": "GroupadminCreate", "description": "Not allowed."}
    response = client.post("/api/labbooks/", json=data)
    assert response.status_code != 200


# scenario: rejected for groupuser — only admin can create labbooks
def test_create_labbook_rejected_for_groupuser(client, as_groupuser):
    data = {"title": "GroupuserCreate", "description": "Not allowed."}
    response = client.post("/api/labbooks/", json=data)
    assert response.status_code != 200


# scenario: rejected for groupguest — only admin can create labbooks
def test_create_labbook_rejected_for_groupguest(client, as_groupguest):
    data = {"title": "GroupguestCreate", "description": "Not allowed."}
    response = client.post("/api/labbooks/", json=data)
    assert response.status_code != 200


# scenario: duplicate title → 204 — unique constraint violation
def test_create_labbook_duplicate_title(a_labbook, client, as_admin):
    data = {"title": "Test Labbook", "description": "Duplicate."}
    response = client.post("/api/labbooks/", json=data)
    assert response.status_code == 204


# scenario: empty / whitespace title → 204 — is_clean_title rejects it
def test_create_labbook_empty_title(client, as_admin):
    response = client.post(
        "/api/labbooks/", json={"title": "   ", "description": "desc"}
    )
    assert response.status_code == 204


# scenario: missing required fields → 422
def test_create_labbook_missing_fields(client, as_admin):
    response = client.post("/api/labbooks/", json={"description": "No title here."})
    assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════
# GET /api/labbooks/{labbook_pk} — get single labbook
# ═══════════════════════════════════════════════════════════════════


# scenario: admin fetches a labbook — returns labbook data and admin privileges
def test_get_labbook(a_labbook, client, as_admin):
    response = client.get(f"/api/labbooks/{a_labbook}")
    assert response.status_code == 200
    body = response.json()
    assert "labbook" in body
    assert "privileges" in body
    assert body["labbook"]["title"] == "Test Labbook"
    assert body["privileges"]["fullAccess"] is True
    assert body["privileges"]["edit"] is True
    assert body["privileges"]["delete"] is True
    assert body["privileges"]["trash"] is True


# scenario: rejected for non-admin — non-admin without group membership gets 404
def test_get_labbook_rejected_for_nonadmin(a_labbook, client, as_nonadmin):
    response = client.get(f"/api/labbooks/{a_labbook}")
    assert response.status_code == 404


# scenario: groupadmin fetches a labbook — returns labbook with groupadmin privileges
def test_get_labbook_as_groupadmin(a_labbook, client, as_groupadmin):
    response = client.get(f"/api/labbooks/{a_labbook}")
    assert response.status_code == 200
    body = response.json()
    assert body["labbook"]["title"] == "Test Labbook"
    assert body["privileges"]["fullAccess"] is False
    assert body["privileges"]["view"] is True
    assert body["privileges"]["edit"] is False
    assert body["privileges"]["delete"] is False
    assert body["privileges"]["trash"] is False
    assert body["privileges"]["restore"] is True


# scenario: groupuser fetches a labbook — returns labbook with user privileges
def test_get_labbook_as_groupuser(a_labbook, client, as_groupuser):
    response = client.get(f"/api/labbooks/{a_labbook}")
    assert response.status_code == 200
    body = response.json()
    assert body["labbook"]["title"] == "Test Labbook"
    assert body["privileges"]["fullAccess"] is False
    assert body["privileges"]["view"] is True
    assert body["privileges"]["edit"] is False
    assert body["privileges"]["delete"] is False
    assert body["privileges"]["trash"] is False
    assert body["privileges"]["restore"] is False


# scenario: groupguest fetches a labbook — returns labbook with all privileges False
def test_get_labbook_as_groupguest(a_labbook, client, as_groupguest):
    response = client.get(f"/api/labbooks/{a_labbook}")
    assert response.status_code == 200
    body = response.json()
    assert body["labbook"]["title"] == "Test Labbook"
    assert body["privileges"]["fullAccess"] is False
    assert body["privileges"]["view"] is False
    assert body["privileges"]["edit"] is False
    assert body["privileges"]["delete"] is False
    assert body["privileges"]["trash"] is False
    assert body["privileges"]["restore"] is False


# scenario: nonexistent labbook → 404
def test_get_nonexistent_labbook(client, as_admin):
    response = client.get("/api/labbooks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# PATCH /api/labbooks/{labbook_pk} — patch labbook
# ═══════════════════════════════════════════════════════════════════


# scenario: patch title — admin changes the labbook title
def test_patch_labbook_title(a_second_labbook, client, as_admin):
    response = client.patch(
        f"/api/labbooks/{a_second_labbook}",
        json={"title": "Patched Labbook Title", "strict_mode": False},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Patched Labbook Title"


# scenario: patch description — admin updates only the description
def test_patch_labbook_description(a_labbook, client, as_admin):
    response = client.patch(
        f"/api/labbooks/{a_labbook}",
        json={"description": "Updated description."},
    )
    assert response.status_code == 200
    assert "Updated description." in response.json()["description"]


# scenario: patch strict mode — admin toggles strict_mode on
def test_patch_labbook_strict_mode(a_second_labbook, client, as_admin):
    response = client.patch(
        f"/api/labbooks/{a_second_labbook}",
        json={"title": "Patched Labbook Title", "strict_mode": True},
    )
    assert response.status_code == 200
    assert response.json()["strict_mode"] is True


# scenario: non-admin patch returns 200 but title is unchanged —
# lb_privileges['edit'] is False so the edit block is skipped
def test_patch_labbook_noop_for_nonadmin(a_labbook, client, as_nonadmin):
    original_title = "Test Labbook"
    response = client.patch(
        f"/api/labbooks/{a_labbook}",
        json={"title": "Hacked Title", "strict_mode": False},
    )
    assert response.status_code == 200
    assert response.json()["title"] == original_title


# scenario: groupadmin patch returns 200 but title is unchanged (edit=False)
def test_patch_labbook_noop_for_groupadmin(a_labbook, client, as_groupadmin):
    original_title = "Test Labbook"
    response = client.patch(
        f"/api/labbooks/{a_labbook}",
        json={"title": "Hacked Title", "strict_mode": False},
    )
    assert response.status_code == 200
    assert response.json()["title"] == original_title


# scenario: groupuser patch returns 200 but title is unchanged (edit=False)
def test_patch_labbook_noop_for_groupuser(a_labbook, client, as_groupuser):
    original_title = "Test Labbook"
    response = client.patch(
        f"/api/labbooks/{a_labbook}",
        json={"title": "Hacked Title", "strict_mode": False},
    )
    assert response.status_code == 200
    assert response.json()["title"] == original_title


# scenario: groupguest patch returns 200 but title is unchanged (edit=False)
def test_patch_labbook_noop_for_groupguest(a_labbook, client, as_groupguest):
    original_title = "Test Labbook"
    response = client.patch(
        f"/api/labbooks/{a_labbook}",
        json={"title": "Hacked Title", "strict_mode": False},
    )
    assert response.status_code == 200
    assert response.json()["title"] == original_title


# scenario: nonexistent labbook
def test_patch_nonexistent_labbook(client, as_admin):
    response = client.patch(
        "/api/labbooks/00000000-0000-0000-0000-000000000000",
        json={"title": "Ghost", "strict_mode": False},
    )
    assert response.status_code != 200


# ═══════════════════════════════════════════════════════════════════
# PATCH — soft-delete & restore labbook
# ═══════════════════════════════════════════════════════════════════


# scenario: soft-delete then restore lifecycle — admin can delete and restore
def test_soft_delete_and_restore_labbook(a_second_labbook, client, as_admin):
    # soft delete
    response = client.patch(f"/api/labbooks/{a_second_labbook}/soft_delete")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    # double-delete should fail — already deleted
    response = client.patch(f"/api/labbooks/{a_second_labbook}/soft_delete")
    assert response.status_code == 404

    # deleted labbook hidden from default listing
    response = client.get("/api/labbooks/")
    titles = [lb["title"] for lb in response.json()]
    assert "Patched Labbook Title" not in titles

    # restore
    response = client.patch(f"/api/labbooks/{a_second_labbook}/restore")
    assert response.status_code == 200
    assert response.json()["deleted"] is False

    # restored labbook visible again
    response = client.get("/api/labbooks/")
    titles = [lb["title"] for lb in response.json()]
    assert "Patched Labbook Title" in titles


# scenario: rejected for non-admin — non-admin cannot soft-delete
def test_soft_delete_rejected_for_nonadmin(a_labbook, client, as_nonadmin):
    response = client.patch(f"/api/labbooks/{a_labbook}/soft_delete")
    assert response.status_code == 404


# scenario: rejected for non-admin — non-admin cannot restore
def test_restore_rejected_for_nonadmin(a_labbook, client, as_nonadmin):
    response = client.patch(f"/api/labbooks/{a_labbook}/restore")
    assert response.status_code == 404


# scenario: rejected for groupadmin — soft-delete requires admin flag
def test_soft_delete_rejected_for_groupadmin(a_labbook, client, as_groupadmin):
    response = client.patch(f"/api/labbooks/{a_labbook}/soft_delete")
    assert response.status_code == 404


# scenario: rejected for groupadmin — restore requires admin flag
def test_restore_rejected_for_groupadmin(a_labbook, client, as_groupadmin):
    response = client.patch(f"/api/labbooks/{a_labbook}/restore")
    assert response.status_code == 404


# scenario: rejected for groupuser — soft-delete requires admin flag
def test_soft_delete_rejected_for_groupuser(a_labbook, client, as_groupuser):
    response = client.patch(f"/api/labbooks/{a_labbook}/soft_delete")
    assert response.status_code == 404


# scenario: rejected for groupuser — restore requires admin flag
def test_restore_rejected_for_groupuser(a_labbook, client, as_groupuser):
    response = client.patch(f"/api/labbooks/{a_labbook}/restore")
    assert response.status_code == 404


# scenario: rejected for groupguest — soft-delete requires admin flag
def test_soft_delete_rejected_for_groupguest(a_labbook, client, as_groupguest):
    response = client.patch(f"/api/labbooks/{a_labbook}/soft_delete")
    assert response.status_code == 404


# scenario: rejected for groupguest — restore requires admin flag
def test_restore_rejected_for_groupguest(a_labbook, client, as_groupguest):
    response = client.patch(f"/api/labbooks/{a_labbook}/restore")
    assert response.status_code == 404


# scenario: restore non-deleted labbook → 404
def test_restore_non_deleted_labbook(a_labbook, client, as_admin):
    response = client.patch(f"/api/labbooks/{a_labbook}/restore")
    assert response.status_code == 404


# scenario: nonexistent labbook → 404 — soft-delete
def test_soft_delete_nonexistent_labbook(client, as_admin):
    response = client.patch(
        "/api/labbooks/00000000-0000-0000-0000-000000000000/soft_delete"
    )
    assert response.status_code == 404


# scenario: nonexistent labbook → 404 — restore
def test_restore_nonexistent_labbook(client, as_admin):
    response = client.patch(
        "/api/labbooks/00000000-0000-0000-0000-000000000000/restore"
    )
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# GET /api/labbooks/{labbook_pk}/elements/ — list elements
# ═══════════════════════════════════════════════════════════════════


# scenario: admin lists elements — returns list of child elements
def test_get_labbook_elements(a_labbook, a_note, client, as_admin):
    response = client.get(f"/api/labbooks/{a_labbook}/elements/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


# scenario: empty elements for labbook with no children — returns empty list
def test_get_labbook_elements_empty(a_second_labbook, client, as_admin):
    response = client.get(f"/api/labbooks/{a_second_labbook}/elements/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: rejected for non-admin — non-admin without group membership gets 404
def test_get_labbook_elements_rejected_for_nonadmin(a_labbook, client, as_nonadmin):
    response = client.get(f"/api/labbooks/{a_labbook}/elements/")
    assert response.status_code == 404


# scenario: groupadmin lists elements — has Write access, can list elements
def test_get_labbook_elements_as_groupadmin(a_labbook, client, as_groupadmin):
    response = client.get(f"/api/labbooks/{a_labbook}/elements/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: groupuser lists elements — has Write access, can list elements
def test_get_labbook_elements_as_groupuser(a_labbook, client, as_groupuser):
    response = client.get(f"/api/labbooks/{a_labbook}/elements/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: groupguest lists elements — has Read access, sufficient for listing
def test_get_labbook_elements_as_groupguest(a_labbook, client, as_groupguest):
    response = client.get(f"/api/labbooks/{a_labbook}/elements/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: nonexistent labbook
def test_get_elements_nonexistent_labbook(client, as_admin):
    response = client.get(
        "/api/labbooks/00000000-0000-0000-0000-000000000000/elements/"
    )
    assert response.status_code != 200


# ═══════════════════════════════════════════════════════════════════
# POST /api/labbooks/{labbook_pk}/elements/ — create element
# ═══════════════════════════════════════════════════════════════════


# scenario: admin creates an element — adds a note to the labbook
def test_create_elem(a_labbook, client, as_admin):
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "Element Note", "content": "For element creation test"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    elem_data = {
        "position_x": 0,
        "position_y": 500,
        "width": 20,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
        "child_object_content_type_model": note_content_type_model,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/", json=elem_data)
    assert response.status_code == 200
    body = response.json()
    assert "pk" in body


# scenario: rejected for non-admin — non-admin cannot create elements
def test_create_elem_rejected_for_nonadmin(a_labbook, a_note, client, as_nonadmin):
    elem_data = {
        "position_x": 0,
        "position_y": 600,
        "width": 20,
        "height": 10,
        "child_object_id": a_note,
        "child_object_content_type": note_content_type,
        "child_object_content_type_model": note_content_type_model,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/", json=elem_data)
    assert response.status_code != 200


# scenario: groupadmin creates an element — has Write access
def test_create_elem_as_groupadmin(a_labbook, client, as_groupadmin):
    # create a fresh note as admin first, then add element as groupadmin
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "Groupadmin Elem Note", "content": "For groupadmin"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupadmin
    elem_data = {
        "position_x": 0,
        "position_y": 700,
        "width": 20,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
        "child_object_content_type_model": note_content_type_model,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/", json=elem_data)
    assert response.status_code == 200
    assert "pk" in response.json()


# scenario: groupuser creates an element — has Write access
def test_create_elem_as_groupuser(a_labbook, client, as_groupuser):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "Groupuser Elem Note", "content": "For groupuser"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupuser
    elem_data = {
        "position_x": 0,
        "position_y": 800,
        "width": 20,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
        "child_object_content_type_model": note_content_type_model,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/", json=elem_data)
    assert response.status_code == 200
    assert "pk" in response.json()


# scenario: rejected for groupguest — Read access is not sufficient to create elements
def test_create_elem_rejected_for_groupguest(a_labbook, a_note, client, as_groupguest):
    elem_data = {
        "position_x": 0,
        "position_y": 900,
        "width": 20,
        "height": 10,
        "child_object_id": a_note,
        "child_object_content_type": note_content_type,
        "child_object_content_type_model": note_content_type_model,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/", json=elem_data)
    assert response.status_code != 200


# scenario: nonexistent labbook → 404
def test_create_elem_nonexistent_labbook(a_note, client, as_admin):
    elem_data = {
        "position_x": 0,
        "position_y": 0,
        "width": 15,
        "height": 15,
        "child_object_id": a_note,
        "child_object_content_type": note_content_type,
        "child_object_content_type_model": note_content_type_model,
    }
    response = client.post(
        "/api/labbooks/00000000-0000-0000-0000-000000000000/elements/",
        json=elem_data,
    )
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# PATCH /api/labbooks/{labbook_pk}/elements/{element_pk}/ — patch element height
# ═══════════════════════════════════════════════════════════════════


# scenario: admin patches element height
def test_patch_elem_height(a_labbook, a_labbook_element_pk, client, as_admin):
    response = client.patch(
        f"/api/labbooks/{a_labbook}/elements/{a_labbook_element_pk}/",
        json={"height": 25},
    )
    assert response.status_code == 200
    assert response.json() == "ok"


# scenario: rejected for non-admin — non-admin cannot patch element height
def test_patch_elem_rejected_for_nonadmin(
    a_labbook, a_labbook_element_pk, client, as_nonadmin
):
    response = client.patch(
        f"/api/labbooks/{a_labbook}/elements/{a_labbook_element_pk}/",
        json={"height": 30},
    )
    assert response.status_code != 200


# scenario: groupadmin patches element height — has Write access
def test_patch_elem_as_groupadmin(
    a_labbook, a_labbook_element_pk, client, as_groupadmin
):
    response = client.patch(
        f"/api/labbooks/{a_labbook}/elements/{a_labbook_element_pk}/",
        json={"height": 35},
    )
    assert response.status_code == 200
    assert response.json() == "ok"


# scenario: groupuser patches element height — has Write access
def test_patch_elem_as_groupuser(a_labbook, a_labbook_element_pk, client, as_groupuser):
    response = client.patch(
        f"/api/labbooks/{a_labbook}/elements/{a_labbook_element_pk}/",
        json={"height": 40},
    )
    assert response.status_code == 200
    assert response.json() == "ok"


# scenario: rejected for groupguest — Read access insufficient to patch elements
def test_patch_elem_rejected_for_groupguest(
    a_labbook, a_labbook_element_pk, client, as_groupguest
):
    response = client.patch(
        f"/api/labbooks/{a_labbook}/elements/{a_labbook_element_pk}/",
        json={"height": 45},
    )
    assert response.status_code != 200


# scenario: nonexistent element
def test_patch_elem_height_nonexistent(a_labbook, client, as_admin):
    response = client.patch(
        f"/api/labbooks/{a_labbook}/elements/00000000-0000-0000-0000-000000000000/",
        json={"height": 20},
    )
    assert response.status_code != 200


# ═══════════════════════════════════════════════════════════════════
# POST /api/labbooks/{labbook_pk}/elements/bottom — create element at bottom
# ═══════════════════════════════════════════════════════════════════


# scenario: admin adds a fresh element at the bottom of the labbook
def test_create_elem_bottom(a_labbook, client, as_admin):
    # create a fresh note
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "Bottom Note", "content": "For bottom test"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    elem_data = {
        "width": 20,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/bottom", json=elem_data)
    assert response.status_code == 200
    assert "pk" in response.json()


# scenario: rejected for non-admin — non-admin cannot add to bottom
def test_create_elem_bottom_rejected(a_labbook, a_note, client, as_nonadmin):
    elem_data = {
        "width": 20,
        "height": 10,
        "child_object_id": a_note,
        "child_object_content_type": note_content_type,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/bottom", json=elem_data)
    assert response.status_code != 200


# scenario: groupadmin adds element at bottom — has Write access
def test_create_elem_bottom_as_groupadmin(a_labbook, client, as_groupadmin):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "GA Bottom Note", "content": "For groupadmin bottom"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupadmin
    elem_data = {
        "width": 20,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/bottom", json=elem_data)
    assert response.status_code == 200
    assert "pk" in response.json()


# scenario: groupuser adds element at bottom — has Write access
def test_create_elem_bottom_as_groupuser(a_labbook, client, as_groupuser):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "GU Bottom Note", "content": "For groupuser bottom"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupuser
    elem_data = {
        "width": 20,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/bottom", json=elem_data)
    assert response.status_code == 200
    assert "pk" in response.json()


# scenario: rejected for groupguest — Read access insufficient for bottom
def test_create_elem_bottom_rejected_for_groupguest(
    a_labbook, a_note, client, as_groupguest
):
    elem_data = {
        "width": 20,
        "height": 10,
        "child_object_id": a_note,
        "child_object_content_type": note_content_type,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/bottom", json=elem_data)
    assert response.status_code != 200


# ═══════════════════════════════════════════════════════════════════
# POST /api/labbooks/{labbook_pk}/elements/row — create element at row
# ═══════════════════════════════════════════════════════════════════


# scenario: admin adds a fresh element at "top" row
def test_create_elem_row(a_labbook, client, as_admin):
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "Row Note", "content": "For row test"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    elem_data = {
        "position": "top",
        "width": 20,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/row", json=elem_data)
    assert response.status_code == 200
    assert "pk" in response.json()


# scenario: rejected for non-admin
def test_create_elem_row_rejected(a_labbook, a_note, client, as_nonadmin):
    elem_data = {
        "position": "top",
        "width": 20,
        "height": 10,
        "child_object_id": a_note,
        "child_object_content_type": note_content_type,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/row", json=elem_data)
    assert response.status_code != 200


# scenario: groupadmin adds element at row — has Write access
def test_create_elem_row_as_groupadmin(a_labbook, client, as_groupadmin):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "GA Row Note", "content": "For groupadmin row"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupadmin
    elem_data = {
        "position": "top",
        "width": 20,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/row", json=elem_data)
    assert response.status_code == 200
    assert "pk" in response.json()


# scenario: groupuser adds element at row — has Write access
def test_create_elem_row_as_groupuser(a_labbook, client, as_groupuser):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "GU Row Note", "content": "For groupuser row"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    app.dependency_overrides[get_current_user] = mock_get_current_user_groupuser
    elem_data = {
        "position": "top",
        "width": 20,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/row", json=elem_data)
    assert response.status_code == 200
    assert "pk" in response.json()


# scenario: rejected for groupguest — Read access insufficient for row
def test_create_elem_row_rejected_for_groupguest(
    a_labbook, a_note, client, as_groupguest
):
    elem_data = {
        "position": "top",
        "width": 20,
        "height": 10,
        "child_object_id": a_note,
        "child_object_content_type": note_content_type,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/row", json=elem_data)
    assert response.status_code != 200


# ═══════════════════════════════════════════════════════════════════
# PUT /api/labbooks/{labbook_pk}/elements/update_all/ — batch update
# ═══════════════════════════════════════════════════════════════════


# scenario: admin updates all element positions in bulk
def test_update_all_elems(a_labbook, client, as_admin):
    res = client.get(f"/api/labbooks/{a_labbook}/elements/")
    assert res.status_code == 200
    elems = res.json()

    if not elems:
        response = client.put(
            f"/api/labbooks/{a_labbook}/elements/update_all/", json=[]
        )
        assert response.status_code in (200, 404)
        return

    update_data = [
        {
            "id": e["pk"],
            "position_y": e["position_y"],
            "position_x": e["position_x"] + 1,
            "width": e["width"],
            "height": e["height"],
        }
        for e in elems
    ]
    response = client.put(
        f"/api/labbooks/{a_labbook}/elements/update_all/", json=update_data
    )
    assert response.status_code == 200
    assert response.json() == "ok"


# scenario: rejected for non-admin
def test_update_all_elems_rejected(a_labbook, client, as_nonadmin):
    response = client.put(f"/api/labbooks/{a_labbook}/elements/update_all/", json=[])
    assert response.status_code != 200


# scenario: groupadmin updates all element positions — all in-group allowed
def test_update_all_elems_as_groupadmin(a_labbook, client, as_groupadmin):
    res = client.get(f"/api/labbooks/{a_labbook}/elements/")
    assert res.status_code == 200
    elems = res.json()
    if not elems:
        return
    update_data = [
        {
            "id": e["pk"],
            "position_y": e["position_y"],
            "position_x": e["position_x"] + 1,
            "width": e["width"],
            "height": e["height"],
        }
        for e in elems
    ]
    response = client.put(
        f"/api/labbooks/{a_labbook}/elements/update_all/", json=update_data
    )
    assert response.status_code == 200
    assert response.json() == "ok"


# scenario: groupuser updates all element positions — all in-group allowed
def test_update_all_elems_as_groupuser(a_labbook, client, as_groupuser):
    res = client.get(f"/api/labbooks/{a_labbook}/elements/")
    assert res.status_code == 200
    elems = res.json()
    if not elems:
        return
    update_data = [
        {
            "id": e["pk"],
            "position_y": e["position_y"],
            "position_x": e["position_x"] + 1,
            "width": e["width"],
            "height": e["height"],
        }
        for e in elems
    ]
    response = client.put(
        f"/api/labbooks/{a_labbook}/elements/update_all/", json=update_data
    )
    assert response.status_code == 200
    assert response.json() == "ok"


# scenario: groupguest updates all element positions — all in-group allowed
def test_update_all_elems_as_groupguest(a_labbook, client, as_groupguest):
    res = client.get(f"/api/labbooks/{a_labbook}/elements/")
    assert res.status_code == 200
    elems = res.json()
    if not elems:
        return
    update_data = [
        {
            "id": e["pk"],
            "position_y": e["position_y"],
            "position_x": e["position_x"] + 1,
            "width": e["width"],
            "height": e["height"],
        }
        for e in elems
    ]
    response = client.put(
        f"/api/labbooks/{a_labbook}/elements/update_all/", json=update_data
    )
    assert response.status_code == 200
    assert response.json() == "ok"


# ═══════════════════════════════════════════════════════════════════
# GET /api/labbooks/{labbook_pk}/history/ — history
# ═══════════════════════════════════════════════════════════════════


# scenario: admin sees history — create generates history entries
def test_get_labbook_history(a_labbook, client, as_admin):
    response = client.get(f"/api/labbooks/{a_labbook}/history/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


# scenario: non-admin also gets history — get_history has no permission check
def test_get_labbook_history_as_nonadmin(a_labbook, client, as_nonadmin):
    response = client.get(f"/api/labbooks/{a_labbook}/history/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: groupadmin sees history — no permission check on get_history
def test_get_labbook_history_as_groupadmin(a_labbook, client, as_groupadmin):
    response = client.get(f"/api/labbooks/{a_labbook}/history/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: groupuser sees history — no permission check on get_history
def test_get_labbook_history_as_groupuser(a_labbook, client, as_groupuser):
    response = client.get(f"/api/labbooks/{a_labbook}/history/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: groupguest sees history — no permission check on get_history
def test_get_labbook_history_as_groupguest(a_labbook, client, as_groupguest):
    response = client.get(f"/api/labbooks/{a_labbook}/history/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: nonexistent labbook returns
def test_get_history_nonexistent_labbook(client, as_admin):
    response = client.get("/api/labbooks/00000000-0000-0000-0000-000000000000/history/")
    assert response.status_code != 200


# ═══════════════════════════════════════════════════════════════════
# GET /api/labbooks/{labbook_pk}/versions/ — list versions
# ═══════════════════════════════════════════════════════════════════


# scenario: admin lists versions — returns list
def test_get_versions(a_labbook, client, as_admin):
    response = client.get(f"/api/labbooks/{a_labbook}/versions/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: rejected for non-admin — non-admin without group membership gets 404
def test_get_versions_rejected_for_nonadmin(a_labbook, client, as_nonadmin):
    response = client.get(f"/api/labbooks/{a_labbook}/versions/")
    assert response.status_code == 404


# scenario: groupadmin lists versions — in-group member, can access
def test_get_versions_as_groupadmin(a_labbook, client, as_groupadmin):
    response = client.get(f"/api/labbooks/{a_labbook}/versions/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: groupuser lists versions — in-group member, can access
def test_get_versions_as_groupuser(a_labbook, client, as_groupuser):
    response = client.get(f"/api/labbooks/{a_labbook}/versions/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: groupguest lists versions — in-group member (Read access), can access
def test_get_versions_as_groupguest(a_labbook, client, as_groupguest):
    response = client.get(f"/api/labbooks/{a_labbook}/versions/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: nonexistent labbook
def test_get_versions_nonexistent_labbook(client, as_admin):
    response = client.get(
        "/api/labbooks/00000000-0000-0000-0000-000000000000/versions/"
    )
    assert response.status_code != 200


# ═══════════════════════════════════════════════════════════════════
# POST /api/labbooks/{labbook_pk}/versions/ — create version
# ═══════════════════════════════════════════════════════════════════


# scenario: admin creates a version snapshot — returns the updated labbook
def test_create_version(a_labbook, client, as_admin):
    response = client.post(
        f"/api/labbooks/{a_labbook}/versions/",
        json={"summary": "Test version snapshot"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "pk" in body
    assert body["title"] == "Test Labbook"


# scenario: rejected for non-admin — non-admin cannot create versions
def test_create_version_rejected_for_nonadmin(a_labbook, client, as_nonadmin):
    response = client.post(
        f"/api/labbooks/{a_labbook}/versions/",
        json={"summary": "Should fail"},
    )
    assert response.status_code != 200


# scenario: groupadmin creates a version — has admin access (check_for_labbook_admin_access)
def test_create_version_as_groupadmin(a_labbook, client, as_groupadmin):
    response = client.post(
        f"/api/labbooks/{a_labbook}/versions/",
        json={"summary": "Groupadmin version snapshot"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "pk" in body


# scenario: rejected for groupuser — only admin + groupadmin can create versions
def test_create_version_rejected_for_groupuser(a_labbook, client, as_groupuser):
    response = client.post(
        f"/api/labbooks/{a_labbook}/versions/",
        json={"summary": "Should fail"},
    )
    assert response.status_code != 200


# scenario: rejected for groupguest — only admin + groupadmin can create versions
def test_create_version_rejected_for_groupguest(a_labbook, client, as_groupguest):
    response = client.post(
        f"/api/labbooks/{a_labbook}/versions/",
        json={"summary": "Should fail"},
    )
    assert response.status_code != 200


# scenario: nonexistent labbook
def test_create_version_nonexistent_labbook(client, as_admin):
    response = client.post(
        "/api/labbooks/00000000-0000-0000-0000-000000000000/versions/",
        json={"summary": "Ghost version"},
    )
    assert response.status_code != 200


# ═══════════════════════════════════════════════════════════════════
# POST …/versions/{version_pk}/restore/ — restore version
# GET  …/versions/{version_pk}/preview/ — preview version
# ═══════════════════════════════════════════════════════════════════

# NOTE: POST …/versions/ returns a Labbook model (not Version), so the
# response does not include the version pk.  To get the version pk we
# must list versions first.


def _create_and_get_version_pk(client, labbook_pk, summary):
    """Create a version and return its pk (fetched from versions list)."""
    client.post(
        f"/api/labbooks/{labbook_pk}/versions/",
        json={"summary": summary},
    )
    ver_list = client.get(f"/api/labbooks/{labbook_pk}/versions/")
    assert ver_list.status_code == 200
    versions = ver_list.json()
    assert len(versions) >= 1, f"No versions found after creating '{summary}'"
    return versions[0]["pk"]


# scenario: admin creates a version and then restores it
def test_restore_version(a_labbook, client, as_admin):
    version_pk = _create_and_get_version_pk(client, a_labbook, "Version to restore")
    response = client.post(f"/api/labbooks/{a_labbook}/versions/{version_pk}/restore/")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Labbook"


# scenario: admin previews a version — returns version metadata
def test_preview_version(a_labbook, client, as_admin):
    version_pk = _create_and_get_version_pk(client, a_labbook, "Version to preview")
    response = client.get(f"/api/labbooks/{a_labbook}/versions/{version_pk}/preview/")
    assert response.status_code == 200
    body = response.json()
    assert "title" in body


# scenario: rejected for non-admin — cannot restore versions
def test_restore_version_rejected_for_nonadmin(a_labbook, client, as_nonadmin):
    response = client.post(
        f"/api/labbooks/{a_labbook}/versions/00000000-0000-0000-0000-000000000000/restore/"
    )
    assert response.status_code != 200


# scenario: rejected for non-admin — cannot preview versions
def test_preview_version_rejected_for_nonadmin(a_labbook, client, as_nonadmin):
    response = client.get(
        f"/api/labbooks/{a_labbook}/versions/00000000-0000-0000-0000-000000000000/preview/"
    )
    assert response.status_code != 200


# scenario: groupadmin restores a version — has admin access
def test_restore_version_as_groupadmin(a_labbook, client, as_groupadmin):
    # create version as admin first
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    version_pk = _create_and_get_version_pk(client, a_labbook, "GA restore version")
    # restore as groupadmin
    app.dependency_overrides[get_current_user] = mock_get_current_user_groupadmin
    response = client.post(f"/api/labbooks/{a_labbook}/versions/{version_pk}/restore/")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Labbook"


# scenario: groupadmin previews a version — has admin access
def test_preview_version_as_groupadmin(a_labbook, client, as_groupadmin):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    version_pk = _create_and_get_version_pk(client, a_labbook, "GA preview version")
    app.dependency_overrides[get_current_user] = mock_get_current_user_groupadmin
    response = client.get(f"/api/labbooks/{a_labbook}/versions/{version_pk}/preview/")
    assert response.status_code == 200
    assert "title" in response.json()


# scenario: rejected for groupuser — cannot restore versions
def test_restore_version_rejected_for_groupuser(a_labbook, client, as_groupuser):
    response = client.post(
        f"/api/labbooks/{a_labbook}/versions/00000000-0000-0000-0000-000000000000/restore/"
    )
    assert response.status_code != 200


# scenario: rejected for groupuser — cannot preview versions
def test_preview_version_rejected_for_groupuser(a_labbook, client, as_groupuser):
    response = client.get(
        f"/api/labbooks/{a_labbook}/versions/00000000-0000-0000-0000-000000000000/preview/"
    )
    assert response.status_code != 200


# scenario: rejected for groupguest — cannot restore versions
def test_restore_version_rejected_for_groupguest(a_labbook, client, as_groupguest):
    response = client.post(
        f"/api/labbooks/{a_labbook}/versions/00000000-0000-0000-0000-000000000000/restore/"
    )
    assert response.status_code != 200


# scenario: rejected for groupguest — cannot preview versions
def test_preview_version_rejected_for_groupguest(a_labbook, client, as_groupguest):
    response = client.get(
        f"/api/labbooks/{a_labbook}/versions/00000000-0000-0000-0000-000000000000/preview/"
    )
    assert response.status_code != 200


# scenario: nonexistent version
def test_restore_nonexistent_version(a_labbook, client, as_admin):
    response = client.post(
        f"/api/labbooks/{a_labbook}/versions/00000000-0000-0000-0000-000000000000/restore/"
    )
    assert response.status_code != 200


# scenario: nonexistent version preview
def test_preview_nonexistent_version(a_labbook, client, as_admin):
    response = client.get(
        f"/api/labbooks/{a_labbook}/versions/00000000-0000-0000-0000-000000000000/preview/"
    )
    assert response.status_code != 200


# ═══════════════════════════════════════════════════════════════════
# GET /api/labbooks/note_aside/{elem_pk}/ — create note aside
# ═══════════════════════════════════════════════════════════════════


# scenario: admin creates a note beside an existing element
def test_create_note_aside(a_labbook, client, as_admin):
    # fresh element at a unique y so the "beside" slot is free
    elem_pk = _create_fresh_element(client, a_labbook, position_y=1000)
    response = client.get(f"/api/labbooks/note_aside/{elem_pk}/")
    assert response.status_code == 200
    assert response.json() is True


# scenario: non-admin gets 200 with False — check_for_labbook_access
# returns None (no group), so function returns False (not a 404)
def test_note_aside_rejected_for_nonadmin(
    a_labbook, a_labbook_element_pk, client, as_nonadmin
):
    response = client.get(f"/api/labbooks/note_aside/{a_labbook_element_pk}/")
    # non-admin with no group: service returns False with 200
    assert response.status_code == 200
    assert response.json() is False


# scenario: groupadmin creates note aside — has Write access
def test_note_aside_as_groupadmin(a_labbook, client, as_groupadmin):
    elem_pk = _create_fresh_element(client, a_labbook, position_y=1100)
    response = client.get(f"/api/labbooks/note_aside/{elem_pk}/")
    assert response.status_code == 200
    assert response.json() is True


# scenario: groupuser creates note aside — has Write access
def test_note_aside_as_groupuser(a_labbook, client, as_groupuser):
    elem_pk = _create_fresh_element(client, a_labbook, position_y=1200)
    response = client.get(f"/api/labbooks/note_aside/{elem_pk}/")
    assert response.status_code == 200
    assert response.json() is True


# scenario: groupguest gets 200 with False — Read access insufficient, needs Write
def test_note_aside_rejected_for_groupguest(
    a_labbook, a_labbook_element_pk, client, as_groupguest
):
    response = client.get(f"/api/labbooks/note_aside/{a_labbook_element_pk}/")
    assert response.status_code == 200
    assert response.json() is False


# scenario: nonexistent element
# returns 200 with False (not an HTTP error)
def test_note_aside_nonexistent_element(client, as_admin):
    response = client.get(
        "/api/labbooks/note_aside/00000000-0000-0000-0000-000000000000/"
    )
    assert response.status_code == 200
    assert response.json() is False


# ═══════════════════════════════════════════════════════════════════
# GET /api/labbooks/note_below/{elem_pk}/ — create note below
# ═══════════════════════════════════════════════════════════════════


# scenario: admin creates a note below an existing element
def test_create_note_below(a_labbook, client, as_admin):
    # fresh element at a unique y so the "below" slot is free
    elem_pk = _create_fresh_element(client, a_labbook, position_y=1300)
    response = client.get(f"/api/labbooks/note_below/{elem_pk}/")
    assert response.status_code == 200
    assert response.json() is True


# scenario: non-admin gets 200 with False — check_for_labbook_access
# returns None (no group), so function returns False (not a 404)
def test_note_below_rejected_for_nonadmin(
    a_labbook, a_labbook_element_pk, client, as_nonadmin
):
    response = client.get(f"/api/labbooks/note_below/{a_labbook_element_pk}/")
    # non-admin with no group: service returns False with 200
    assert response.status_code == 200
    assert response.json() is False


# scenario: groupadmin creates note below — has Write access
def test_note_below_as_groupadmin(a_labbook, client, as_groupadmin):
    elem_pk = _create_fresh_element(client, a_labbook, position_y=1400)
    response = client.get(f"/api/labbooks/note_below/{elem_pk}/")
    assert response.status_code == 200
    assert response.json() is True


# scenario: groupuser creates note below — has Write access
def test_note_below_as_groupuser(a_labbook, client, as_groupuser):
    elem_pk = _create_fresh_element(client, a_labbook, position_y=1500)
    response = client.get(f"/api/labbooks/note_below/{elem_pk}/")
    assert response.status_code == 200
    assert response.json() is True


# scenario: groupguest gets 200 with False — Read access insufficient, needs Write
def test_note_below_rejected_for_groupguest(
    a_labbook, a_labbook_element_pk, client, as_groupguest
):
    response = client.get(f"/api/labbooks/note_below/{a_labbook_element_pk}/")
    assert response.status_code == 200
    assert response.json() is False


# scenario: nonexistent element
# returns 200 with False (not an HTTP error)
def test_note_below_nonexistent_element(client, as_admin):
    response = client.get(
        "/api/labbooks/note_below/00000000-0000-0000-0000-000000000000/"
    )
    assert response.status_code == 200
    assert response.json() is False


# ═══════════════════════════════════════════════════════════════════
# GET …/add_{pdf,zip,lxf}_export_task — export tasks
# ═══════════════════════════════════════════════════════════════════


# scenario: admin triggers PDF export — returns an identifier immediately
def test_add_pdf_export_task(a_labbook, client, as_admin):
    response = client.get(f"/api/labbooks/{a_labbook}/add_pdf_export_task")
    assert response.status_code == 200
    assert "identifier" in response.json()


# scenario: admin triggers ZIP export — returns an identifier immediately
def test_add_zip_export_task(a_labbook, client, as_admin):
    response = client.get(f"/api/labbooks/{a_labbook}/add_zip_export_task")
    assert response.status_code == 200
    assert "identifier" in response.json()


# scenario: admin triggers LXF export — returns an identifier immediately
def test_add_lxf_export_task(a_labbook, client, as_admin):
    response = client.get(f"/api/labbooks/{a_labbook}/add_lxf_export_task")
    assert response.status_code == 200
    assert "identifier" in response.json()


# scenario: admin triggers PDF export with filters
def test_add_pdf_export_task_with_filters(a_labbook, client, as_admin):
    response = client.get(
        f"/api/labbooks/{a_labbook}/add_pdf_export_task",
        params={"containTypes": [30], "users": [1]},
    )
    assert response.status_code == 200
    assert "identifier" in response.json()


# scenario: groupadmin triggers PDF export — any authenticated user
def test_add_pdf_export_task_as_groupadmin(a_labbook, client, as_groupadmin):
    response = client.get(f"/api/labbooks/{a_labbook}/add_pdf_export_task")
    assert response.status_code == 200
    assert "identifier" in response.json()


# scenario: groupuser triggers PDF export — any authenticated user
def test_add_pdf_export_task_as_groupuser(a_labbook, client, as_groupuser):
    response = client.get(f"/api/labbooks/{a_labbook}/add_pdf_export_task")
    assert response.status_code == 200
    assert "identifier" in response.json()


# scenario: groupguest triggers PDF export — any authenticated user
def test_add_pdf_export_task_as_groupguest(a_labbook, client, as_groupguest):
    response = client.get(f"/api/labbooks/{a_labbook}/add_pdf_export_task")
    assert response.status_code == 200
    assert "identifier" in response.json()


# ═══════════════════════════════════════════════════════════════════
# GET /api/labbooks/get_export/{identifier} — stream export
# ═══════════════════════════════════════════════════════════════════


# scenario: poll export with a fake identifier — returns 204 when not found
def test_get_export_status(client, as_admin):
    response = client.get(
        "/api/labbooks/get_export/00000000-0000-0000-0000-000000000000"
    )
    # service returns None → route returns 204
    assert response.status_code in (200, 204, 404, 400)


# ═══════════════════════════════════════════════════════════════════
# GET /api/labbooks/labbook_owner_group/ — get labbook by owner group
# ═══════════════════════════════════════════════════════════════════


# scenario: admin queries by owner_group — returns labbook UUID list
def test_get_labbook_by_owner_group(a_labbook, client, as_admin):
    response = client.get(
        "/api/labbooks/labbook_owner_group/",
        params={"owner_group": "Test Labbook"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert str(a_labbook) in data


# scenario: rejected for non-admin — non-admin cannot query by owner group
def test_get_labbook_by_owner_group_rejected(a_labbook, client, as_nonadmin):
    response = client.get(
        "/api/labbooks/labbook_owner_group/",
        params={"owner_group": "Test Labbook"},
    )
    assert response.status_code != 200


# scenario: rejected for groupadmin — admin-only endpoint
def test_get_labbook_by_owner_group_rejected_for_groupadmin(
    a_labbook, client, as_groupadmin
):
    response = client.get(
        "/api/labbooks/labbook_owner_group/",
        params={"owner_group": "Test Labbook"},
    )
    assert response.status_code != 200


# scenario: rejected for groupuser — admin-only endpoint
def test_get_labbook_by_owner_group_rejected_for_groupuser(
    a_labbook, client, as_groupuser
):
    response = client.get(
        "/api/labbooks/labbook_owner_group/",
        params={"owner_group": "Test Labbook"},
    )
    assert response.status_code != 200


# scenario: rejected for groupguest — admin-only endpoint
def test_get_labbook_by_owner_group_rejected_for_groupguest(
    a_labbook, client, as_groupguest
):
    response = client.get(
        "/api/labbooks/labbook_owner_group/",
        params={"owner_group": "Test Labbook"},
    )
    assert response.status_code != 200


# scenario: nonexistent owner group — admin gets 200 with [] (not 404)
def test_get_labbook_by_owner_group_nonexistent(client, as_admin):
    response = client.get(
        "/api/labbooks/labbook_owner_group/",
        params={"owner_group": "NoSuchGroup"},
    )
    # service returns [] with 200 when no match found
    assert response.status_code == 200
    assert response.json() == []


# ═══════════════════════════════════════════════════════════════════
# GET /api/labbooks/{labbook_pk}/search/ — full-text search
# ═══════════════════════════════════════════════════════════════════


# scenario: admin searches in labbook — uses mock Typesense client
def test_search_in_labbook(a_labbook, client, as_admin):
    response = client.get(
        f"/api/labbooks/{a_labbook}/search/",
        params={"search": "test"},
    )
    assert response.status_code == 200


# scenario: rejected for non-admin — non-admin without group membership gets 404
def test_search_in_labbook_rejected(a_labbook, client, as_nonadmin):
    response = client.get(
        f"/api/labbooks/{a_labbook}/search/",
        params={"search": "test"},
    )
    assert response.status_code != 200


# scenario: groupadmin searches in labbook — in-group member, has access
def test_search_in_labbook_as_groupadmin(a_labbook, client, as_groupadmin):
    response = client.get(
        f"/api/labbooks/{a_labbook}/search/",
        params={"search": "test"},
    )
    assert response.status_code == 200


# scenario: groupuser searches in labbook — in-group member, has access
def test_search_in_labbook_as_groupuser(a_labbook, client, as_groupuser):
    response = client.get(
        f"/api/labbooks/{a_labbook}/search/",
        params={"search": "test"},
    )
    assert response.status_code == 200


# scenario: groupguest searches in labbook — in-group member, has access
def test_search_in_labbook_as_groupguest(a_labbook, client, as_groupguest):
    response = client.get(
        f"/api/labbooks/{a_labbook}/search/",
        params={"search": "test"},
    )
    assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════


# scenario: full CRUD lifecycle — create → read → patch → soft-delete → restore
def test_labbook_full_lifecycle(client, as_admin):
    # create
    create_resp = client.post(
        "/api/labbooks/",
        json={"title": "Lifecycle Labbook", "description": "Testing full lifecycle."},
    )
    assert create_resp.status_code == 200
    pk = create_resp.json()["pk"]
    assert create_resp.json()["title"] == "Lifecycle Labbook"

    # read
    read_resp = client.get(f"/api/labbooks/{pk}")
    assert read_resp.status_code == 200
    assert read_resp.json()["labbook"]["description"] == "Testing full lifecycle."

    # patch title (must include strict_mode to avoid None → validation error)
    patch_resp = client.patch(
        f"/api/labbooks/{pk}",
        json={"title": "Lifecycle Labbook Updated", "strict_mode": False},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Lifecycle Labbook Updated"

    # soft delete
    del_resp = client.patch(f"/api/labbooks/{pk}/soft_delete")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    # restore
    rest_resp = client.patch(f"/api/labbooks/{pk}/restore")
    assert rest_resp.status_code == 200
    assert rest_resp.json()["deleted"] is False


# scenario: create labbook with special characters in title
def test_create_labbook_special_chars(client, as_admin):
    data = {"title": "Labbook #42 — αβγ", "description": "Unicode and symbols."}
    response = client.post("/api/labbooks/", json=data)
    assert response.status_code == 200
    assert response.json()["title"] == "Labbook #42 — αβγ"


# scenario: create labbook with HTML in description — description is HTML-sanitized
def test_create_labbook_html_description(client, as_admin):
    data = {
        "title": "HTML Description Labbook",
        "description": "<p>Rich <b>description</b></p>",
    }
    response = client.post("/api/labbooks/", json=data)
    assert response.status_code == 200
    assert "<b>description</b>" in response.json()["description"]
