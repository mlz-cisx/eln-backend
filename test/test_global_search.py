"""Coverage for the global full-text search endpoint."""

import uuid

import pytest

from test.conftest import app, get_current_user, mock_get_current_user_admin


@pytest.fixture(scope="module")
def search_title():
    return f"Test Labbook {uuid.uuid4().hex}"


@pytest.fixture(scope="module")
def a_labbook(client, admin_user, search_title):
    app.dependency_overrides[get_current_user] = mock_get_current_user_admin
    response = client.post(
        "/api/labbooks/", json={"title": search_title, "description": "Search fixture"}
    )
    assert response.status_code == 200, response.text
    return response.json()["pk"]


def test_global_search_returns_labbook_matches(
    a_labbook, search_title, client, as_admin
):
    response = client.get(
        "/api/search/",
        params={"model": "labbook", "search": search_title},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["content_type_model"] == "labbooks.labbook"
    assert results[0]["display"] == search_title
    assert results[0]["pk"] == str(a_labbook)


def test_global_search_returns_file_matches(a_file, client, as_admin):
    response = client.get(
        "/api/search/",
        params={"model": "file", "search": "Test Title"},
    )

    assert response.status_code == 200
    results = response.json()
    matches = [result for result in results if result["element_pk"] == str(a_file)]
    assert len(matches) == 1
    assert matches[0]["content_type_model"] == "shared_elements.file"
    assert matches[0]["display"] == "Test Title"


def test_global_search_combines_selected_content_types(
    a_labbook, a_file, a_note, a_picture, client, as_admin, mock_typesense, monkeypatch
):
    # Fixture attachment indexes the actual documents the endpoint expects.
    documents = {
        call.args[0]["id"]: call.args[0]
        for call in mock_typesense.collections["notes"].documents.upsert.call_args_list
    }
    monkeypatch.setattr(
        mock_typesense.multi_search.perform,
        "side_effect",
        [
            {"results": [{"hits": [{"document": documents[str(pk)]}]}]}
            for pk in (a_note, a_picture)
        ],
    )
    calls_before = mock_typesense.multi_search.perform.call_count

    response = client.get(
        "/api/search/",
        params={"model": "labbook,file,note,picture", "search": "Test"},
    )

    assert response.status_code == 200
    types = {result["content_type_model"] for result in response.json()}
    assert "labbooks.labbook" in types
    assert "shared_elements.file" in types
    assert "shared_elements.note" in types
    assert "pictures.picture" in types
    matches = {result["element_pk"] for result in response.json()}
    assert {str(a_labbook), str(a_file), str(a_note), str(a_picture)} <= matches
    assert mock_typesense.multi_search.perform.call_count - calls_before == 2


def test_global_search_requires_model_and_search(client, as_admin):
    response = client.get("/api/search/")

    assert response.status_code == 422


def test_global_search_hides_results_from_inaccessible_labbooks(
    a_labbook, a_file, search_title, client, as_nonadmin
):
    labbook_response = client.get(
        "/api/search/",
        params={"model": "labbook", "search": search_title},
    )
    file_response = client.get(
        "/api/search/",
        params={"model": "file", "search": "Test Title"},
    )

    assert labbook_response.status_code == 200
    assert labbook_response.json() == []
    assert file_response.status_code == 200
    assert file_response.json() == []
