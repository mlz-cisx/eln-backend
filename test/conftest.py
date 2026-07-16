import datetime
import os
import sys
from unittest.mock import MagicMock, patch

import dotenv
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from joeseln_backend.conf.content_types import (
    file_content_type,
    file_content_type_model,
    note_content_type,
    note_content_type_model,
    picture_content_type,
    picture_content_type_model,
)
from joeseln_backend.conf.mocks.mock_role import ROLE_GROUPADMIN, ROLE_GUEST, ROLE_USER
from joeseln_backend.full_text_search import typesense_service
from joeseln_backend.main import app, get_current_user, get_db, get_typesense_client
from joeseln_backend.models import models
from joeseln_backend.models.models import User
from joeseln_backend.services.role.role_schema import Role_Create
from joeseln_backend.services.role.role_service import create_role
from test.factories import MockUser

# ═══════════════════════════════════════════════════════════════════
# Database
# ═══════════════════════════════════════════════════════════════════


dotenv.load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env.test"))


DB_USER = os.getenv("DB_USER", "eln")
DB_PASSWORD = os.getenv("DB_PASSWORD", "eln")
DB_ADDR = os.getenv("DB_ADDR", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_TESTDB = os.getenv("DB_TESTDB", "eln_test")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_ADDR}:{DB_PORT}/{DB_TESTDB}"
engine = create_engine(DATABASE_URL)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create fresh tables before the test run, drop and clean up after."""
    # Import the production engine so we can dispose its pool too —
    # otherwise its connection pool (pool_size=20) keeps the process alive.
    from joeseln_backend.database.database import engine as prod_engine

    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)
    engine.dispose()
    prod_engine.dispose()


# ═══════════════════════════════════════════════════════════════════
# Users persisted in the test database
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session", autouse=True)
def admin_user(setup_database):
    db = TestSession()
    now = datetime.datetime.now()
    user = User(
        id=1,
        username="testadmin",
        email="admin@example.com",
        oidc_user=False,
        admin=True,
        deleted=False,
        first_name="Test",
        last_name="Admin",
        created_at=now,
        last_modified_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture(scope="session", autouse=True)
def normal_user(setup_database, admin_user):
    db = TestSession()
    now = datetime.datetime.now()
    user = User(
        id=2,
        username="testuser",
        email="test@example.com",
        oidc_user=False,
        admin=False,
        deleted=False,
        first_name="Test",
        last_name="User",
        created_at=now,
        last_modified_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture(scope="session", autouse=True)
def groupadmin_db_user(setup_database, admin_user):
    """DB user that will be assigned groupadmin role on labbook groups."""
    db = TestSession()
    now = datetime.datetime.now()
    user = User(
        id=3,
        username="testgroupadmin",
        email="groupadmin@example.com",
        oidc_user=False,
        admin=False,
        deleted=False,
        first_name="Group",
        last_name="Admin",
        created_at=now,
        last_modified_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture(scope="session", autouse=True)
def groupuser_db_user(setup_database, admin_user):
    """DB user that will be assigned user role on labbook groups."""
    db = TestSession()
    now = datetime.datetime.now()
    user = User(
        id=4,
        username="testgroupuser",
        email="groupuser@example.com",
        oidc_user=False,
        admin=False,
        deleted=False,
        first_name="Group",
        last_name="User",
        created_at=now,
        last_modified_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture(scope="session", autouse=True)
def groupguest_db_user(setup_database, admin_user):
    """DB user that will be assigned guest role on labbook groups."""
    db = TestSession()
    now = datetime.datetime.now()
    user = User(
        id=5,
        username="testgroupguest",
        email="groupguest@example.com",
        oidc_user=False,
        admin=False,
        deleted=False,
        first_name="Group",
        last_name="Guest",
        created_at=now,
        last_modified_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture(scope="session", autouse=True)
def sync_user_id_sequence(
    admin_user, normal_user, groupadmin_db_user, groupuser_db_user, groupguest_db_user
):
    """make sure API-created users have no primary key collision."""
    db = TestSession()
    db.execute(text("SELECT setval('user_id_seq', (SELECT MAX(id) FROM \"user\"))"))
    db.commit()
    db.close()


# ═══════════════════════════════════════════════════════════════════
# Roles
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session", autouse=True)
def roles(setup_database):
    db = TestSession()
    create_role(db, Role_Create.parse_obj(ROLE_GROUPADMIN))
    create_role(db, Role_Create.parse_obj(ROLE_USER))
    create_role(db, Role_Create.parse_obj(ROLE_GUEST))
    db.close()


# ═══════════════════════════════════════════════════════════════════
# Mock current-user factories (not DB users — used in dep overrides)
# ═══════════════════════════════════════════════════════════════════


def mock_get_current_user_admin():
    return MockUser(id=1, username="testadmin", email="admin@example.com")


def mock_get_current_user_nonadmin():
    return MockUser(id=2, username="testuser", admin=False)


def mock_get_current_user_groupadmin():
    return MockUser(id=3, username="testgroupadmin", admin=False)


def mock_get_current_user_groupuser():
    return MockUser(id=4, username="testgroupuser", admin=False)


def mock_get_current_user_groupguest():
    return MockUser(id=5, username="testgroupguest", admin=False)


# ═══════════════════════════════════════════════════════════════════
# Typesense mocks
# ═══════════════════════════════════════════════════════════════════


def _make_mock_typesense_client():
    """Return a mock of typesense Client"""
    mock = MagicMock()
    mock.collections = MagicMock()
    mock.collections.__getitem__.return_value.documents.upsert = MagicMock()
    mock.collections.__getitem__.return_value.documents.__getitem__.return_value.update = MagicMock()
    return mock


@pytest.fixture(scope="session", autouse=True)
def mock_typesense():
    """Mock Typesense client for all tests — session-scoped with proper cleanup."""
    mock_client = _make_mock_typesense_client()
    app.dependency_overrides[get_typesense_client] = lambda: mock_client
    patcher = patch.object(
        typesense_service.typesense_client, "get_client", return_value=mock_client
    )
    patcher.start()
    yield mock_client
    patcher.stop()


# ═══════════════════════════════════════════════════════════════════
# Client
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def client():
    from contextlib import asynccontextmanager

    app.dependency_overrides[get_db] = override_get_db

    # overrides lifespan with a no-op to skip WebSocket connect,
    # Typesense init, and DB migrations
    _original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    with TestClient(app) as c:
        yield c

    app.router.lifespan_context = _original_lifespan


# ═══════════════════════════════════════════════════════════════════
# Auth-override helpers (function-scoped — set once per test)
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture(scope="function")
def as_admin(client):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    yield


@pytest.fixture(scope="function")
def as_nonadmin(client):
    app.dependency_overrides[get_current_user] = mock_get_current_user_nonadmin
    yield


@pytest.fixture(scope="function")
def as_groupadmin(client):
    app.dependency_overrides[get_current_user] = mock_get_current_user_groupadmin
    yield


@pytest.fixture(scope="function")
def as_groupuser(client):
    app.dependency_overrides[get_current_user] = mock_get_current_user_groupuser
    yield


@pytest.fixture(scope="function")
def as_groupguest(client):
    app.dependency_overrides[get_current_user] = mock_get_current_user_groupguest
    yield


# ═══════════════════════════════════════════════════════════════════
# Domain entity fixtures (module-scoped — one fresh set per module)
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def a_labbook(
    client, admin_user, groupadmin_db_user, groupuser_db_user, groupguest_db_user
):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    response = client.post(
        "/api/labbooks/",
        json={"title": "Test Labbook", "description": "This is a test labbook."},
    )
    assert response.status_code == 200
    pk = response.json()["pk"]
    _assign_users_to_labbook_group(pk)
    return pk


def _assign_users_to_labbook_group(labbook_pk):
    """Assign groupadmin/user/guest test users to a labbook's owner_group."""
    db = TestSession()
    try:
        lb = db.query(models.Labbook).filter(models.Labbook.id == labbook_pk).first()
        if not lb or not lb.owner_group:
            return

        group = (
            db.query(models.Group)
            .filter(models.Group.groupname == lb.owner_group)
            .first()
        )
        if not group:
            return

        role_map = {}
        for rolename in ("groupadmin", "user", "guest"):
            role = (
                db.query(models.Role).filter(models.Role.rolename == rolename).first()
            )
            if role:
                role_map[rolename] = role.id

        if len(role_map) < 3:
            return

        now = datetime.datetime.now()
        # User 3 (groupadmin) needs BOTH groupadmin + user roles:
        #   - groupadmin role → for check_for_labbook_admin_access (versioning/restore)
        #   - user role      → for check_for_labbook_access / get_user_groups_role_user (Write access)
        # User 4 (groupuser) needs only user role.
        # User 5 (groupguest) needs only guest role.
        assignments = [
            (3, role_map["groupadmin"]),
            (3, role_map["user"]),
            (4, role_map["user"]),
            (5, role_map["guest"]),
        ]

        for user_id, role_id in assignments:
            existing = (
                db.query(models.UserToGroupRole)
                .filter(
                    models.UserToGroupRole.user_id == user_id,
                    models.UserToGroupRole.group_id == group.id,
                    models.UserToGroupRole.user_group_role == role_id,
                )
                .first()
            )
            if not existing:
                utgr = models.UserToGroupRole(
                    user_id=user_id,
                    group_id=group.id,
                    user_group_role=role_id,
                    created_at=now,
                    last_modified_at=now,
                    external=False,
                )
                db.add(utgr)

        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="module")
def a_group(client, admin_user):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    response = client.post("/api/admin/groups", json={"groupname": "Test"})
    assert response.status_code == 200
    return response.json()["pk"]


@pytest.fixture(scope="module")
def a_file(client, a_labbook):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    file_content = b"test content"
    file_name = "testfile"
    response = client.post(
        "/api/files/",
        data={
            "title": "Test Title",
            "name": "Test Name",
            "description": "Test description",
        },
        files={"path": (file_name, file_content, "application/octet-stream")},
    )
    assert response.status_code == 200
    pk = response.json()["pk"]

    # add to labbook
    lb_data = {
        "position_x": 0,
        "position_y": 0,
        "width": 15,
        "height": 15,
        "child_object_id": pk,
        "child_object_content_type": file_content_type,
        "child_object_content_type_model": file_content_type_model,
    }
    r = client.post(f"/api/labbooks/{a_labbook}/elements/", json=lb_data)
    assert r.status_code == 200
    return pk


@pytest.fixture(scope="module")
def a_note(client, a_labbook):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    response = client.post(
        "/api/notes/",
        json={"subject": "Test Note", "content": "This is a test note"},
    )
    assert response.status_code == 200
    pk = response.json()["pk"]

    lb_data = {
        "position_x": 0,
        "position_y": 0,
        "width": 15,
        "height": 15,
        "child_object_id": pk,
        "child_object_content_type": note_content_type,
        "child_object_content_type_model": note_content_type_model,
    }
    r = client.post(f"/api/labbooks/{a_labbook}/elements/", json=lb_data)
    assert r.status_code == 200
    return pk


@pytest.fixture(scope="module")
def a_picture(client, a_labbook):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    picture_content = b"test content"
    picture_name = "testpic"
    response = client.post(
        "/api/pictures/",
        data={"title": "Test Title", "width": 15, "height": 15},
        files={
            "rendered_image": (
                picture_name,
                picture_content,
                "application/octet-stream",
            ),
        },
    )
    assert response.status_code == 200
    pk = response.json()["pk"]

    lb_data = {
        "position_x": 0,
        "position_y": 0,
        "width": 15,
        "height": 15,
        "child_object_id": pk,
        "child_object_content_type": picture_content_type,
        "child_object_content_type_model": picture_content_type_model,
    }
    r = client.post(f"/api/labbooks/{a_labbook}/elements/", json=lb_data)
    assert r.status_code == 200
    return pk


@pytest.fixture(scope="module")
def a_second_labbook(client, admin_user):
    """Create a second labbook (for duplicate-title and lifecycle tests)."""
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    response = client.post(
        "/api/labbooks/",
        json={"title": "Second Labbook", "description": "Another one."},
    )
    assert response.status_code == 200
    pk = response.json()["pk"]
    _assign_users_to_labbook_group(pk)
    return pk


@pytest.fixture(scope="module")
def a_labbook_element_pk(client, a_labbook):
    """Create an element in the labbook and return its pk."""
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    note_resp = client.post(
        "/api/notes/",
        json={"subject": "Fixture Note", "content": "For element tests"},
    )
    assert note_resp.status_code == 200
    note_pk = note_resp.json()["pk"]

    elem_data = {
        "position_x": 0,
        "position_y": 200,
        "width": 15,
        "height": 10,
        "child_object_id": note_pk,
        "child_object_content_type": note_content_type,
        "child_object_content_type_model": note_content_type_model,
    }
    response = client.post(f"/api/labbooks/{a_labbook}/elements/", json=elem_data)
    assert response.status_code == 200
    return response.json()["pk"]


# ═══════════════════════════════════════════════════════════════════
# Ensure pytest process can exit.
# ═══════════════════════════════════════════════════════════════════


def pytest_unconfigure(config):
    # make sure test summary is printed
    sys.stdout.flush()
    sys.stderr.flush()

    # fastapi spawns a thread that never exits
    # therefore force-exit to make pytest terminate
    os._exit(0)
