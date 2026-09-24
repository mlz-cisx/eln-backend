from types import SimpleNamespace

import pytest

from joeseln_backend.models import models
from joeseln_backend.services.user_to_group import user_to_group_service as service
from joeseln_backend.services.user_to_group.user_to_group_schema import (
    Group_Create,
    UserToGroup_Create,
)
from test.conftest import TestSession, engine


@pytest.fixture
def seeded_db(setup_database, roles, sync_user_id_sequence):
    # savepoint keeps this test's rows isolated.
    with engine.connect() as connection:
        transaction = connection.begin()
        db = TestSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        alice = models.User(username="alice", admin=False)
        bob = models.User(username="bob", admin=False)
        admin = models.User(username="admin", admin=True)
        team = models.Group(groupname="team")
        other = models.Group(groupname="other")
        user_role = db.query(models.Role).filter_by(rolename="user").one()
        groupadmin_role = db.query(models.Role).filter_by(rolename="groupadmin").one()
        guest_role = db.query(models.Role).filter_by(rolename="guest").one()
        db.add_all([alice, bob, admin, team, other])
        db.flush()
        labbook = models.Labbook(title="Guest book", owner_group="other")
        db.add_all(
            [
                models.UserToGroupRole(
                    user_id=alice.id,
                    group_id=team.id,
                    user_group_role=user_role.id,
                    external=False,
                ),
                models.UserToGroupRole(
                    user_id=alice.id,
                    group_id=team.id,
                    user_group_role=groupadmin_role.id,
                    external=False,
                ),
                models.UserToGroupRole(
                    user_id=alice.id,
                    group_id=other.id,
                    user_group_role=guest_role.id,
                    external=False,
                ),
                labbook,
            ]
        )
        db.commit()
        try:
            yield (
                db,
                SimpleNamespace(
                    alice=alice,
                    bob=bob,
                    admin=admin,
                    team=team,
                    other=other,
                    user_role=user_role,
                    guest_role=guest_role,
                    labbook=labbook,
                ),
            )
        finally:
            db.close()
            transaction.rollback()


def test_group_and_role_queries_return_only_matching_memberships(seeded_db):
    db, data = seeded_db

    assert service.get_group_by_groupname(db, "team").id == data.team.id
    assert service.get_group_by_groupname(db, "missing") is None
    assert set(service.get_user_groups(db, "alice")) == {"team", "other"}
    assert set(service.get_user_groups_id(db, "alice")) == {
        data.team.id,
        data.other.id,
    }
    assert service.get_user_groups_role_user(db, "alice") == ["team"]
    assert service.get_groupuser(db, "alice") == ["team"]
    assert service.get_user_groups_role_groupadmin(db, "alice") == ["team"]
    assert {row[0] for row in service.get_user_group_roles(db, "alice", "team")} == {
        "user",
        "groupadmin",
    }
    assert service.get_user_group_roles(db, "bob", "team") == []
    assert {
        row[0]
        for row in service.get_user_group_roles_with_match(db, "alice", "team/project")
    } == {"user", "groupadmin"}


def test_user_lookup_adds_group_names_and_admin_groups(seeded_db):
    db, _ = seeded_db

    user = service.get_user_with_groups_by_uname(db, "alice")

    assert user.username == "alice"
    assert set(user.groups) == {"team", "other"}
    assert user.admin_groups == ["team"]


@pytest.mark.parametrize("query_mode", ["match", "equal"])
def test_guest_role_check_finds_only_guest_labbook(seeded_db, monkeypatch, query_mode):
    db, data = seeded_db
    labbook = data.labbook
    monkeypatch.setattr(service, "LABBOOK_QUERY_MODE", query_mode)

    assert service.check_for_guest_role(db, labbook.id, data.alice) == [labbook]
    assert service.check_for_guest_role(db, labbook.id, data.bob) == []


@pytest.mark.parametrize(
    "method,group,expected",
    [
        ("get_all_groupusers", "team", ["alice"]),
        ("get_all_groupadmins", "team", ["alice"]),
        ("get_all_groupguests", "other", ["alice"]),
    ],
)
def test_group_member_lists_mark_membership(seeded_db, method, group, expected):
    db, data = seeded_db
    params = {"ordering": "username", "offset": 0, "limit": 10}
    group_id = getattr(data, group).id
    function = getattr(service, method)

    assert function(db, group_id, params, data.alice) is None
    members = function(db, group_id, params, data.admin)
    assert [member.username for member in members] == expected
    assert all(member.in_group is True for member in members)


@pytest.mark.parametrize(
    "method,group",
    [
        ("get_all_groupusers", "team"),
        ("get_all_groupadmins", "team"),
        ("get_all_groupguests", "other"),
    ],
)
def test_group_member_search_filters_members(seeded_db, method, group):
    db, data = seeded_db
    params = {"ordering": "username", "offset": 0, "limit": 10, "search": "ali"}

    users = getattr(service, method)(db, getattr(data, group).id, params, data.admin)

    assert [user.username for user in users] == ["alice"]
    assert users[0].in_group is True


@pytest.mark.parametrize(
    "method,group",
    [
        ("get_all_groupusers", "team"),
        ("get_all_groupguests", "other"),
    ],
)
def test_group_member_lists_find_users_outside_role(seeded_db, method, group):
    db, data = seeded_db
    params = {
        "ordering": "username",
        "offset": 0,
        "limit": 10,
        "deleted": True,
        "search": "bob",
    }

    users = getattr(service, method)(db, getattr(data, group).id, params, data.admin)

    assert [user.username for user in users] == ["bob"]
    assert users[0].in_group is False


def test_groupadmin_candidates_are_non_guest_members_without_admin_role(seeded_db):
    db, data = seeded_db
    db.add(
        models.UserToGroupRole(
            user_id=data.bob.id,
            group_id=data.team.id,
            user_group_role=data.user_role.id,
            external=False,
        )
    )
    db.commit()
    params = {"ordering": "username", "offset": 0, "limit": 10, "deleted": True}

    users = service.get_all_groupadmins(db, data.team.id, params, data.admin)

    assert [user.username for user in users] == ["bob"]
    assert users[0].in_group is False


def test_admin_role_updates_and_missing_user(seeded_db):
    db, data = seeded_db

    assert service.check_for_admin_role(db, "bob") is False
    assert service.check_for_admin_role_with_user_id(db, data.admin.id) is True
    assert service.add_admin_role(db, "missing") is False
    assert service.add_admin_role(db, "bob") is True
    assert service.check_for_admin_role(db, "bob") is True
    assert service.remove_admin_role(db, "bob") is True
    assert service.check_for_admin_role(db, "bob") is False


def test_gui_create_group_checks_admin_and_persists(seeded_db):
    db, data = seeded_db

    assert (
        service.gui_create_group(db, data.alice, Group_Create(groupname="new")) is None
    )
    assert service.get_group_by_groupname(db, "new") is None
    created = service.gui_create_group(db, data.admin, Group_Create(groupname="new"))
    assert created.groupname == "new"
    assert service.get_group_by_groupname(db, "new").id == created.id


def test_membership_creation_and_deletion_respect_external_flag(seeded_db):
    db, data = seeded_db
    internal = UserToGroup_Create(
        user_id=data.bob.id,
        group_id=data.team.id,
        user_group_role=data.user_role.id,
        external=False,
    )
    external = internal.model_copy(update={"external": True})

    assert service.create_user_to_group(db, internal).external is False
    assert service.delete_user_to_group(db, external) == 0
    assert service.delete_user_to_group(db, internal) == 1
    assert service.get_user_groups_role_user(db, "bob") == []


def test_adding_user_role_removes_existing_guest_role(seeded_db):
    db, data = seeded_db
    assert (
        service.gui_add_as_guest_to_group(db, data.admin, data.bob.id, data.team.id)
        is not None
    )
    assert "team" in service.get_user_groups(db, "bob")

    membership = service.add_as_user_to_group(db, "bob", "team")

    assert membership.external is True
    assert service.get_user_groups_role_user(db, "bob") == ["team"]
    assert service.get_user_group_roles(db, "bob", "team") == [("user",)]
    assert service.remove_as_user_from_group(db, "bob", "team", external=True) == 1
    assert service.get_user_groups(db, "bob") == []


def test_removing_gui_user_role_also_removes_groupadmin_role(seeded_db):
    db, data = seeded_db
    assert (
        service.gui_add_as_user_to_group(db, data.admin, data.bob.id, data.team.id)
        is not None
    )
    assert (
        service.gui_add_as_groupadmin_to_group(
            db, data.admin, data.bob.id, data.team.id
        )
        is not None
    )
    assert set(row[0] for row in service.get_user_group_roles(db, "bob", "team")) == {
        "user",
        "groupadmin",
    }

    assert (
        service.gui_remove_as_user_from_group(db, data.admin, data.bob.id, data.team.id)
        == 1
    )

    assert service.get_user_group_roles(db, "bob", "team") == []


def test_groupadmin_and_guest_role_round_trips(seeded_db):
    db, data = seeded_db

    assert service.add_as_groupadmin_to_group(db, "bob", "team") is not None
    assert service.get_user_groups_role_groupadmin(db, "bob") == ["team"]
    assert service.remove_as_groupadmin_from_group(db, "bob", "team") == 1
    assert service.get_user_group_roles(db, "bob", "team") == []

    assert (
        service.gui_add_as_guest_to_group(db, data.admin, data.bob.id, data.team.id)
        is not None
    )
    assert (
        service.gui_remove_as_guest_from_group(
            db, data.admin, data.bob.id, data.team.id
        )
        == 1
    )
    assert service.get_user_groups(db, "bob") == []


def test_gui_groupadmin_role_round_trip(seeded_db):
    db, data = seeded_db

    assert (
        service.gui_add_as_groupadmin_to_group(
            db, data.admin, data.bob.id, data.team.id
        )
        is not None
    )
    assert service.get_user_groups_role_groupadmin(db, "bob") == ["team"]
    assert (
        service.gui_remove_as_groupadmin_from_group(
            db, data.admin, data.bob.id, data.team.id
        )
        == 1
    )
    assert service.get_user_groups_role_groupadmin(db, "bob") == []


@pytest.mark.parametrize(
    "method,args",
    [
        ("gui_add_as_user_to_group", (2, "team")),
        ("gui_remove_as_user_from_group", (2, "team")),
        ("gui_add_as_groupadmin_to_group", (2, "team")),
        ("gui_remove_as_groupadmin_from_group", (2, "team")),
        ("gui_add_as_guest_to_group", (2, "team")),
        ("gui_remove_as_guest_from_group", (2, "team")),
    ],
)
def test_gui_membership_changes_require_admin(seeded_db, method, args):
    db, data = seeded_db
    user_id, group_name = args
    group_id = getattr(data, group_name).id

    assert getattr(service, method)(db, data.alice, user_id, group_id) is None
    assert service.get_user_groups(db, "bob") == []


def test_delete_group_removes_its_memberships(seeded_db):
    db, data = seeded_db

    assert service.gui_delete_group(db, data.alice, data.team.id) is None
    assert service.gui_delete_group(db, data.admin, data.team.id) == "ok"
    assert service.get_group_by_groupname(db, "team") is None
    assert service.get_user_groups(db, "alice") == ["other"]


def test_remove_all_group_roles_preserves_other_groups(seeded_db):
    db, _data = seeded_db

    service.remove_all_group_roles(db, "alice", "team")

    assert service.get_user_group_roles(db, "alice", "team") == []
    assert service.get_user_groups(db, "alice") == ["other"]


def test_oidc_sync_creates_missing_groups_and_updates_memberships(seeded_db):
    db, data = seeded_db
    old_membership = (
        db.query(models.UserToGroupRole)
        .filter_by(
            user_id=data.alice.id,
            group_id=data.team.id,
            user_group_role=data.user_role.id,
        )
        .one()
    )
    old_membership.external = True
    db.commit()
    data.alice.groups = ["new"]

    service.update_oidc_user_groups(db, data.alice)

    assert service.get_group_by_groupname(db, "new") is not None
    assert service.get_user_groups_role_user(db, "alice") == ["new"]
    assert service.get_user_groups_role_groupadmin(db, "alice") == []
    new_membership = (
        db.query(models.UserToGroupRole)
        .filter_by(
            user_id=data.alice.id, group_id=service.get_group_by_groupname(db, "new").id
        )
        .one()
    )
    assert new_membership.external is True
