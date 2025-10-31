"""Test Publisher endpoint generation."""

import pytest
from fastapi.testclient import TestClient
from genro_api import Publisher
from tests.fixtures.library import Library


@pytest.fixture
def library():
    """Create library with sample data."""
    lib = Library(":memory:")
    lib.add_shelf("A1", "Science Fiction")
    lib.add_book("Dune", "Frank Herbert", "Chilton Books", 412, "Science Fiction", "A1")
    yield lib
    lib.close()


@pytest.fixture
def client(library):
    """Create test client with published library."""
    publisher = Publisher(
        title="Library API Test",
        version="1.0.0",
        enable_rest=True,
        enable_ui=False,
        enable_swagger=True,
    )
    publisher.publish(library)
    return TestClient(publisher.app)


def test_list_shelves(client):
    """Test GET /library/list_shelves."""
    response = client.get("/library/list_shelves")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["code"] == "A1"


def test_list_all_books(client):
    """Test GET /library/list_all_books."""
    response = client.get("/library/list_all_books")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["title"] == "Dune"


def test_get_stats(client):
    """Test GET /library/get_stats."""
    response = client.get("/library/get_stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_shelves" in data
    assert "total_books" in data
    assert data["total_shelves"] == 1
    assert data["total_books"] == 1


def test_shelf_list_books(client):
    """Test GET /shelf/list_books with query parameter."""
    response = client.get("/shelf/list_books", params={"shelf_code": "A1"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_shelf_count_books(client):
    """Test POST /shelf/count_books."""
    response = client.post("/shelf/count_books", json={"shelf_code": "A1"})
    assert response.status_code == 200
    assert response.json() == 1


def test_openapi_schema(client):
    """Test OpenAPI schema generation."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Library API Test"
    assert schema["info"]["version"] == "1.0.0"
    assert len(schema["paths"]) > 0

    # Check that Library endpoints exist
    assert "/library/list_shelves" in schema["paths"]
    assert "/library/list_all_books" in schema["paths"]

    # Check that Shelf endpoints exist
    assert "/shelf/list_books" in schema["paths"]
    assert "/shelf/count_books" in schema["paths"]
