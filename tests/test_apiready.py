"""Tests for @apiready decorator."""

import pytest
from genro_api.decorators import apiready


# Old-style: methods only (no class decorator)
class OldStyleBackend:
    """Mock backend for testing old-style @apiready decorator (methods only)."""

    @apiready
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file as text."""
        return f"content of {path}"

    @apiready
    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        pass

    @apiready(method="POST")
    def get_metadata(self, path: str) -> dict:
        """Get file metadata (explicitly POST)."""
        return {"path": path, "size": 100}


# New-style: class decorated with path
@apiready(path="/storage")
class NewStyleBackend:
    """Mock backend with class-level @apiready."""

    @apiready
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file as text."""
        return f"content of {path}"

    @apiready(path="/custom")
    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        pass

    @apiready(method="POST")
    def get_metadata(self, path: str) -> dict:
        """Get file metadata (explicitly POST)."""
        return {"path": path, "size": 100}


def test_apiready_basic():
    """Test that @apiready preserves function behavior."""
    backend = OldStyleBackend()
    result = backend.read_text("/test.txt")
    assert result == "content of /test.txt"


def test_apiready_metadata_present():
    """Test that @apiready adds _api_metadata attribute."""
    assert hasattr(OldStyleBackend.read_text, "_api_metadata")
    assert hasattr(OldStyleBackend.write_bytes, "_api_metadata")


def test_apiready_http_method_inference():
    """Test HTTP method inference from function name."""
    # read* should infer GET
    metadata = OldStyleBackend.read_text._api_metadata
    assert metadata["http_method"] == "GET"

    # write* should infer POST
    metadata = OldStyleBackend.write_bytes._api_metadata
    assert metadata["http_method"] == "POST"


def test_apiready_explicit_method():
    """Test explicit HTTP method override."""
    # Explicitly set to POST even though name starts with 'get'
    metadata = OldStyleBackend.get_metadata._api_metadata
    assert metadata["http_method"] == "POST"


def test_apiready_request_fields():
    """Test request field extraction."""
    metadata = OldStyleBackend.read_text._api_metadata
    fields = metadata["request_fields"]

    # Should have 'path' (required) and 'encoding' (optional with default)
    assert "path" in fields
    assert "encoding" in fields

    # Check required vs optional
    assert fields["path"] == (str, ...)  # Required (no default)
    assert fields["encoding"] == (str, "utf-8")  # Optional with default


def test_apiready_return_type():
    """Test return type extraction."""
    # read_text returns str
    metadata = OldStyleBackend.read_text._api_metadata
    assert metadata["return_type"] == str

    # write_bytes returns None
    metadata = OldStyleBackend.write_bytes._api_metadata
    assert metadata["return_type"] is type(None)

    # get_metadata returns dict
    metadata = OldStyleBackend.get_metadata._api_metadata
    assert metadata["return_type"] == dict


def test_apiready_endpoint_path():
    """Test endpoint path defaults to function name."""
    metadata = OldStyleBackend.read_text._api_metadata
    assert metadata["endpoint_path"] == "/read_text"


def test_apiready_docstring():
    """Test docstring is captured."""
    metadata = OldStyleBackend.read_text._api_metadata
    assert metadata["docstring"] == "Read file as text."


# New tests for class-level @apiready
def test_class_apiready_base_path():
    """Test that @apiready on class sets _api_base_path."""
    assert hasattr(NewStyleBackend, "_api_base_path")
    assert NewStyleBackend._api_base_path == "/storage"


def test_class_apiready_methods_have_metadata():
    """Test that methods in apiready class have metadata."""
    assert hasattr(NewStyleBackend.read_text, "_api_metadata")
    assert hasattr(NewStyleBackend.write_bytes, "_api_metadata")
    assert hasattr(NewStyleBackend.get_metadata, "_api_metadata")


def test_class_apiready_default_path():
    """Test that methods use function name as default path."""
    metadata = NewStyleBackend.read_text._api_metadata
    assert metadata["endpoint_path"] == "/read_text"


def test_class_apiready_custom_path():
    """Test that methods can override with custom path."""
    metadata = NewStyleBackend.write_bytes._api_metadata
    assert metadata["endpoint_path"] == "/custom"


def test_class_apiready_requires_path():
    """Test that @apiready on class requires path parameter."""
    with pytest.raises(ValueError, match="requires path parameter"):
        @apiready  # Missing path parameter
        class BadBackend:
            pass


def test_class_apiready_preserves_behavior():
    """Test that class decorator doesn't break instance methods."""
    backend = NewStyleBackend()
    result = backend.read_text("/test.txt")
    assert result == "content of /test.txt"
