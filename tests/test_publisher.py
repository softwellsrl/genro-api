"""Tests for Publisher class."""

import pytest
from genro_api import Publisher
from tests.fixtures.library import Library


class TestPublisherCore:
    """Test core Publisher functionality."""

    def test_publisher_initialization(self):
        """Test Publisher can be initialized with default parameters."""
        publisher = Publisher()

        assert publisher.host == "0.0.0.0"
        assert publisher.port == 8080
        assert publisher.enable_rest is True
        assert publisher.enable_ui is True
        assert publisher.enable_swagger is True
        assert publisher.app is not None

    def test_publisher_custom_parameters(self):
        """Test Publisher can be initialized with custom parameters."""
        publisher = Publisher(
            host="127.0.0.1",
            port=9000,
            title="Test API",
            version="2.0.0",
            enable_rest=False,
            enable_ui=False,
            enable_swagger=False,
        )

        assert publisher.host == "127.0.0.1"
        assert publisher.port == 9000
        assert publisher.enable_rest is False
        assert publisher.enable_ui is False
        assert publisher.enable_swagger is False

    def test_publish_valid_instance(self):
        """Test publishing a valid instance with _api_base_path."""
        publisher = Publisher()
        library = Library()

        # Should not raise
        publisher.publish(library)

        # Verify it was registered
        published = publisher.get_published_classes()
        assert len(published) == 1
        assert published[0] == ("Library", "/library")

    def test_publish_invalid_instance_no_base_path(self):
        """Test publishing instance without _api_base_path raises error."""
        publisher = Publisher()

        class InvalidClass:
            """Class without _api_base_path."""

            pass

        invalid_instance = InvalidClass()

        with pytest.raises(ValueError, match="_api_base_path"):
            publisher.publish(invalid_instance)

    def test_publish_duplicate_base_path(self):
        """Test publishing two instances with same base_path raises error."""
        publisher = Publisher()
        library1 = Library()
        library2 = Library()

        publisher.publish(library1)

        with pytest.raises(ValueError, match="already published"):
            publisher.publish(library2)

    def test_publish_multiple_instances(self):
        """Test publishing multiple instances with different base paths."""
        publisher = Publisher()

        # Create a second class with different base path
        class AnotherClass:
            _api_base_path = "/another"

        library = Library()
        another = AnotherClass()

        publisher.publish(library)
        publisher.publish(another)

        published = publisher.get_published_classes()
        assert len(published) == 2
        assert ("Library", "/library") in published
        assert ("AnotherClass", "/another") in published

    def test_get_published_classes_empty(self):
        """Test get_published_classes returns empty list initially."""
        publisher = Publisher()
        assert publisher.get_published_classes() == []


class TestPublisherWithLibrary:
    """Test Publisher with Library fixture."""

    def test_library_has_base_path(self):
        """Test Library class has required _api_base_path attribute."""
        assert hasattr(Library, "_api_base_path")
        assert Library._api_base_path == "/library"

    def test_publish_library(self):
        """Test publishing Library instance."""
        publisher = Publisher()
        library = Library()

        publisher.publish(library)

        # Verify Library is in published classes
        published = publisher.get_published_classes()
        assert len(published) == 1
        assert published[0][0] == "Library"
        assert published[0][1] == "/library"

    def test_library_instance_preserved(self):
        """Test that published Library instance is preserved."""
        publisher = Publisher()
        library = Library()

        # Add some data to library
        library.add_shelf("A1", "Science Fiction")
        library.add_book(
            "Dune",
            "Frank Herbert",
            "Chilton Books",
            412,
            "Science Fiction",
            "A1",
        )

        publisher.publish(library)

        # Verify the instance is preserved (has the data)
        assert len(publisher._published_instances) == 1
        stored_instance, stored_class = publisher._published_instances[0]

        assert isinstance(stored_instance, Library)
        # Use public methods to verify data (SQLite version)
        assert len(stored_instance.list_shelves()) == 1
        assert len(stored_instance.list_all_books()) == 1


# Note: Tests for _generate_rest_endpoints and _register_ui_components
# will be added when those features are implemented (Issues #3 and #4)
