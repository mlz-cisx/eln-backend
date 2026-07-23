import pytest

from joeseln_backend.main import app, get_current_user
from test.conftest import mock_get_current_user_admin

# ═══════════════════════════════════════════════════════════════════
# Shared fixtures
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def a_created_user(client):
    """Create a non-admin user via the admin API, return its id."""
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    data = {
        "username": "createduser",
        "email": "createduser@example.com",
        "first_name": "Created",
        "last_name": "User",
        "password": "123",
        "password_confirmed": "123",
    }
    response = client.post("/api/admin/users", json=data)
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="module")
def a_second_user(client):
    """Create a second non-admin user, return full response json."""
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    data = {
        "username": "seconduser",
        "email": "second@example.com",
        "first_name": "Second",
        "last_name": "User",
        "password": "pass123",
        "password_confirmed": "pass123",
    }
    response = client.post("/api/admin/users", json=data)
    assert response.status_code == 200
    return response.json()


# ═══════════════════════════════════════════════════════════════════
# GET /api/admin/users — list users
# ═══════════════════════════════════════════════════════════════════


# scenario: basic listing — returns a list of non-admin users
def test_get_users(a_created_user, client, as_admin):
    response = client.get("/api/admin/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# scenario: rejected for non-admin — non-admin cannot list users
def test_get_users_rejected_for_nonadmin(a_created_user, client, as_nonadmin):
    response = client.get("/api/admin/users")
    assert response.status_code != 200


# scenario: search by username / name — filters results
def test_get_users_with_search(a_created_user, client, as_admin):
    response = client.get("/api/admin/users", params={"search": "created"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    usernames = [u["username"] for u in data]
    assert "createduser" in usernames


# scenario: search with no match — returns empty list
def test_get_users_with_search_no_match(a_created_user, client, as_admin):
    response = client.get("/api/admin/users", params={"search": "zzz_nonexistent_zzz"})
    assert response.status_code == 200
    assert len(response.json()) == 0


# scenario: show deleted users (deleted=True) — soft-deleted users appear when requested
def test_get_users_show_deleted(a_created_user, client, as_admin):
    # first soft-delete to have one deleted user
    client.patch(f"/api/admin/users/{a_created_user}/soft_delete")
    response = client.get("/api/admin/users", params={"deleted": True})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # restore for other tests
    client.patch(f"/api/admin/users/{a_created_user}/restore")


# scenario: ordering by field — results respect the ordering param
def test_get_users_with_ordering(a_created_user, client, as_admin):
    response = client.get("/api/admin/users", params={"ordering": "username"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# scenario: pagination (limit / offset) — slices the result set
def test_get_users_with_pagination(a_created_user, client, as_admin):
    response = client.get("/api/admin/users", params={"limit": 1})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 1

    response = client.get("/api/admin/users", params={"offset": 0, "limit": 1})
    assert response.status_code == 200
    assert len(response.json()) <= 1


# scenario: exclude deleted (deleted=False) — no soft-deleted users in the result
def test_get_users_deleted_false(a_created_user, client, as_admin):
    response = client.get("/api/admin/users", params={"deleted": False})
    assert response.status_code == 200
    for u in response.json():
        assert u["deleted"] is False


# ═══════════════════════════════════════════════════════════════════
# POST /api/admin/users — create user
# ═══════════════════════════════════════════════════════════════════


# scenario: successful creation — all fields returned, password excluded
def test_create_user(client, as_admin):
    data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "first_name": "New",
        "last_name": "User",
        "password": "secure123",
        "password_confirmed": "secure123",
    }
    response = client.post("/api/admin/users", json=data)
    assert response.status_code == 200
    assert response.json()["username"] == "newuser"
    assert response.json()["email"] == "newuser@example.com"
    assert response.json()["first_name"] == "New"
    assert response.json()["last_name"] == "User"
    assert "password" not in response.json()


# scenario: rejected for non-admin — non-admin cannot create users
def test_create_user_rejected_for_nonadmin(client, as_nonadmin):
    data = {
        "username": "shouldfail",
        "email": "fail@example.com",
        "first_name": "Fail",
        "last_name": "User",
        "password": "secret",
        "password_confirmed": "secret",
    }
    response = client.post("/api/admin/users", json=data)
    assert response.status_code != 200


# scenario: password mismatch → 404 — service returns None when passwords don't match
def test_create_user_password_mismatch(client, as_admin):
    data = {
        "username": "mismatch",
        "email": "mismatch@example.com",
        "first_name": "Mismatch",
        "last_name": "User",
        "password": "abc",
        "password_confirmed": "xyz",
    }
    response = client.post("/api/admin/users", json=data)
    assert response.status_code == 404


# scenario: missing required fields → 422 — FastAPI rejects incomplete payloads
def test_create_user_missing_fields(client, as_admin):
    response = client.post("/api/admin/users", json={"username": "incomplete"})
    assert response.status_code == 422


# scenario: duplicate username → 404 — unique constraint violation
def test_create_duplicate_username(a_created_user, client, as_admin):
    data = {
        "username": "createduser",
        "email": "dup@example.com",
        "first_name": "Dup",
        "last_name": "User",
        "password": "123",
        "password_confirmed": "123",
    }
    response = client.post("/api/admin/users", json=data)
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# GET /api/admin/users/{user_id} — get single user
# ═══════════════════════════════════════════════════════════════════


# scenario: fetch existing user — returns user object and privileges
def test_get_user(a_created_user, client, as_admin):
    response = client.get(f"/api/admin/users/{a_created_user}")
    assert response.status_code == 200
    assert response.json()["user"]
    assert response.json()["privileges"]
    assert response.json()["user"]["username"] == "createduser"


# scenario: rejected for non-admin — non-admin cannot get user by ID
def test_get_user_rejected_for_nonadmin(a_created_user, client, as_nonadmin):
    response = client.get(f"/api/admin/users/{a_created_user}")
    assert response.status_code != 200


# scenario: nonexistent user → 404
def test_get_nonexistent_user(client, as_admin):
    response = client.get("/api/admin/users/999999")
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# PATCH /api/admin/users/{user_id} — patch user
# ═══════════════════════════════════════════════════════════════════


# scenario: successful patch — username, email, first/last name updated
def test_patch_user(a_created_user, client, as_admin):
    patch_data = {
        "username": "patcheduser",
        "user_email": "patched@example.com",
        "first_name": "Patched",
        "last_name": "Name",
    }
    response = client.patch(f"/api/admin/users/{a_created_user}", json=patch_data)
    assert response.status_code == 200
    assert response.json()["username"] == "patcheduser"
    assert response.json()["email"] == "patched@example.com"
    assert response.json()["first_name"] == "Patched"
    assert response.json()["last_name"] == "Name"


# scenario: rejected for non-admin — non-admin cannot patch users
def test_patch_user_rejected_for_nonadmin(a_created_user, client, as_nonadmin):
    patch_data = {
        "username": "hacked",
        "user_email": "hacked@example.com",
        "first_name": "Hack",
        "last_name": "User",
    }
    response = client.patch(f"/api/admin/users/{a_created_user}", json=patch_data)
    assert response.status_code != 200


# scenario: nonexistent user → 404
def test_patch_nonexistent_user(client, as_admin):
    patch_data = {
        "username": "ghost",
        "user_email": "ghost@example.com",
        "first_name": "Ghost",
        "last_name": "User",
    }
    response = client.patch("/api/admin/users/999999", json=patch_data)
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# PATCH — soft delete & restore user
# ═══════════════════════════════════════════════════════════════════


# scenario: soft-delete then restore lifecycle — delete hides, restore reveals
def test_soft_delete_and_restore_user(a_second_user, client, as_admin):
    uid = a_second_user["id"]

    # soft delete
    response = client.patch(f"/api/admin/users/{uid}/soft_delete")
    assert response.status_code == 200

    # scenario: double-delete → 404 — already-deleted user cannot be deleted again
    response = client.patch(f"/api/admin/users/{uid}/soft_delete")
    assert response.status_code == 404

    # scenario: deleted user hidden from default listing
    response = client.get("/api/admin/users")
    usernames = [u["username"] for u in response.json()]
    assert a_second_user["username"] not in usernames

    # restore
    response = client.patch(f"/api/admin/users/{uid}/restore")
    assert response.status_code == 200

    # scenario: restored user visible again in default listing
    response = client.get("/api/admin/users")
    usernames = [u["username"] for u in response.json()]
    assert a_second_user["username"] in usernames


# scenario: rejected for non-admin — non-admin cannot soft-delete
def test_soft_delete_rejected_for_nonadmin(a_created_user, client, as_nonadmin):
    response = client.patch(f"/api/admin/users/{a_created_user}/soft_delete")
    assert response.status_code != 200


# scenario: rejected for non-admin — non-admin cannot restore
def test_restore_rejected_for_nonadmin(a_created_user, client, as_nonadmin):
    response = client.patch(f"/api/admin/users/{a_created_user}/restore")
    assert response.status_code != 200


# scenario: restore non-deleted user → 404 — cannot restore an active user
def test_restore_non_deleted_user(a_created_user, client, as_admin):
    response = client.patch(f"/api/admin/users/{a_created_user}/restore")
    assert response.status_code == 404


# scenario: nonexistent user → 404 — soft-delete
def test_soft_delete_nonexistent_user(client, as_admin):
    response = client.patch("/api/admin/users/999999/soft_delete")
    assert response.status_code == 404


# scenario: nonexistent user → 404 — restore
def test_restore_nonexistent_user(client, as_admin):
    response = client.patch("/api/admin/users/999999/restore")
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# GET /api/admin/admins — list admins
# ═══════════════════════════════════════════════════════════════════


# scenario: basic listing — testadmin from conftest is present
def test_get_admins(admin_user, client, as_admin):
    response = client.get("/api/admin/admins")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    usernames = [a["username"] for a in data]
    assert "testadmin" in usernames


# scenario: rejected for non-admin — non-admin cannot list admins
def test_get_admins_rejected_for_nonadmin(client, as_nonadmin):
    response = client.get("/api/admin/admins")
    assert response.status_code != 200


# scenario: search by username — filters admin list
def test_get_admins_with_search(admin_user, client, as_admin):
    response = client.get("/api/admin/admins", params={"search": "testadmin"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["username"] == "testadmin"


# ═══════════════════════════════════════════════════════════════════
# Admin promotion & demotion
# ═══════════════════════════════════════════════════════════════════


# scenario: promote then demote lifecycle — admin flag toggles correctly
def test_set_and_remove_admin(a_second_user, client, as_admin):
    uid = a_second_user["id"]

    # promote to admin
    response = client.patch(f"/api/admin/admins/{uid}/restore")
    assert response.status_code == 200
    assert response.json()["admin"] is True

    # demote from admin
    response = client.patch(f"/api/admin/admins/{uid}/soft_delete")
    assert response.status_code == 200
    assert response.json()["admin"] is False


# scenario: rejected for non-admin — non-admin cannot promote
def test_set_admin_rejected_for_nonadmin(a_second_user, client, as_nonadmin):
    response = client.patch(f"/api/admin/admins/{a_second_user['id']}/restore")
    assert response.status_code != 200


# scenario: rejected for non-admin — non-admin cannot demote
def test_remove_admin_rejected_for_nonadmin(a_second_user, client, as_nonadmin):
    response = client.patch(f"/api/admin/admins/{a_second_user['id']}/soft_delete")
    assert response.status_code != 200


# scenario: double-promote → 404 — already-admin user cannot be promoted again
def test_double_promote_admin(a_second_user, client, as_admin):
    uid = a_second_user["id"]
    # first promote
    client.patch(f"/api/admin/admins/{uid}/restore")
    # second promote should fail
    response = client.patch(f"/api/admin/admins/{uid}/restore")
    assert response.status_code == 404
    # clean up
    client.patch(f"/api/admin/admins/{uid}/soft_delete")


# scenario: double-demote → 404 — non-admin user cannot be demoted
def test_double_demote_admin(a_second_user, client, as_admin):
    uid = a_second_user["id"]
    response = client.patch(f"/api/admin/admins/{uid}/soft_delete")
    assert response.status_code == 404


# scenario: nonexistent user → 404 — promote
def test_promote_nonexistent_user(client, as_admin):
    response = client.patch("/api/admin/admins/999999/restore")
    assert response.status_code == 404


# scenario: nonexistent user → 404 — demote
def test_demote_nonexistent_user(client, as_admin):
    response = client.patch("/api/admin/admins/999999/soft_delete")
    assert response.status_code == 404


# scenario: deleted param (deleted=True) — inverts admin filter to show non-admins
def test_get_admins_with_deleted_param(client, as_admin):
    response = client.get("/api/admin/admins", params={"deleted": True})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# scenario: ordering by field — admins can be sorted
def test_get_admins_with_ordering(client, as_admin):
    response = client.get("/api/admin/admins", params={"ordering": "username"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    usernames = [a["username"] for a in data]
    assert "testadmin" in usernames


# ═══════════════════════════════════════════════════════════════════
# Password — admin patches user password
# ═══════════════════════════════════════════════════════════════════


# scenario: successful password patch — admin can set a new password for any user
def test_patch_user_password(a_second_user, client, as_admin):
    response = client.patch(
        f"/api/admin/users/{a_second_user['id']}/foo",
        json={"password_patch": "newpass456"},
    )
    assert response.status_code == 200


# scenario: rejected for non-admin — non-admin cannot patch others' passwords
def test_patch_user_password_rejected_for_nonadmin(a_second_user, client, as_nonadmin):
    response = client.patch(
        f"/api/admin/users/{a_second_user['id']}/foo",
        json={"password_patch": "hacked"},
    )
    assert response.status_code != 200


# scenario: nonexistent user → 404
def test_patch_password_nonexistent_user(client, as_admin):
    response = client.patch(
        "/api/admin/users/999999/foo",
        json={"password_patch": "newpass"},
    )
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# PUT /api/change_password — change own password
# ═══════════════════════════════════════════════════════════════════


# scenario: admin changes own password → 200 "ok"
def test_change_own_password(client, as_admin):
    response = client.put("/api/change_password", json={"password": "newsecret"})
    assert response.status_code == 200
    assert response.json() == "ok"


# scenario: non-admin changes own password → 200 "ok"
def test_change_own_password_as_nonadmin(client, as_nonadmin):
    response = client.put("/api/change_password", json={"password": "newsecret2"})
    assert response.status_code == 200
    assert response.json() == "ok"


# ═══════════════════════════════════════════════════════════════════
# GET /api/users/me — current user
# ═══════════════════════════════════════════════════════════════════


# scenario: admin identity — returns testadmin profile
def test_users_me_as_admin(client, as_admin):
    response = client.get("/api/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["email"] == "admin@example.com"


# scenario: non-admin identity — returns testuser profile
def test_users_me_as_nonadmin(client, as_nonadmin):
    response = client.get("/api/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


# ═══════════════════════════════════════════════════════════════════
# POST /api/token — login (local auth)
# ═══════════════════════════════════════════════════════════════════


# scenario: successful login — returns access_token and token_type
def test_login_success(client, as_admin):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    data = {
        "username": "loginuser",
        "email": "loginuser@example.com",
        "first_name": "Login",
        "last_name": "User",
        "password": "mypassword",
        "password_confirmed": "mypassword",
    }
    create_resp = client.post("/api/admin/users", json=data)
    assert create_resp.status_code == 200

    response = client.post(
        "/api/token",
        data={"username": "loginuser", "password": "mypassword"},
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data


# scenario: wrong password → 401 — authentication fails
def test_login_wrong_password(client, as_admin):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    data = {
        "username": "wrongpwuser",
        "email": "wrongpw@example.com",
        "first_name": "Wrong",
        "last_name": "PW",
        "password": "correct",
        "password_confirmed": "correct",
    }
    create_resp = client.post("/api/admin/users", json=data)
    assert create_resp.status_code == 200

    response = client.post(
        "/api/token",
        data={"username": "wrongpwuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401


# scenario: nonexistent user → 401 — user not found in database
def test_login_nonexistent_user(client):
    response = client.post(
        "/api/token",
        data={"username": "nonexistentuser", "password": "whatever"},
    )
    assert response.status_code == 401


# scenario: soft-deleted user → 401 — deleted users are rejected at auth
def test_login_deleted_user(client, as_admin):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    data = {
        "username": "deaduser",
        "email": "dead@example.com",
        "first_name": "Dead",
        "last_name": "User",
        "password": "deadpass",
        "password_confirmed": "deadpass",
    }
    create_resp = client.post("/api/admin/users", json=data)
    assert create_resp.status_code == 200
    uid = create_resp.json()["id"]

    # soft-delete the user
    client.patch(f"/api/admin/users/{uid}/soft_delete")

    # attempt to login as deleted user
    response = client.post(
        "/api/token",
        data={"username": "deaduser", "password": "deadpass"},
    )
    assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# POST /api/refresh-token — refresh access token
# ═══════════════════════════════════════════════════════════════════


# scenario: refresh valid token → new access_token returned
def test_refresh_token(client, as_admin):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    data = {
        "username": "refreshuser",
        "email": "refresh@example.com",
        "first_name": "Refresh",
        "last_name": "User",
        "password": "refreshpass",
        "password_confirmed": "refreshpass",
    }
    create_resp = client.post("/api/admin/users", json=data)
    assert create_resp.status_code == 200

    # login
    login_resp = client.post(
        "/api/token",
        data={"username": "refreshuser", "password": "refreshpass"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # refresh
    response = client.post(
        "/api/refresh-token",
        json={"access_token": token, "token_type": "bearer"},
    )
    assert response.status_code == 200
    refreshed = response.json()
    assert "access_token" in refreshed
    assert refreshed["token_type"] == "bearer"


# scenario: invalid / malformed token → 403
def test_refresh_token_with_invalid_token(client):
    response = client.post(
        "/api/refresh-token",
        json={"access_token": "invalid.token.here", "token_type": "bearer"},
    )
    assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════
# GET /api/transfer — transfer token
# ═══════════════════════════════════════════════════════════════════


# scenario: returns access_token, token_type, and token_validity
def test_get_transfer_token(client, as_admin):
    response = client.get("/api/transfer")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert "token_validity" in data
