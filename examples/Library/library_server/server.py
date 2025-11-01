"""Minimal server boilerplate for Library API."""

import sys
from pathlib import Path

# Add library_code to Python path
library_code_path = Path(__file__).parent.parent / "library_code"
sys.path.insert(0, str(library_code_path))

from library_manager import Library
from genro_api import Publisher

# Create publisher
pub = Publisher(
    host="127.0.0.1",
    port=8000,
    title="Library API Server"
)

# Create library instance and import data
library = Library()
library.import_from_csv()

print("Populating library with sample data...")
stats = library.get_stats()
print(f"Library populated with {stats['total_shelves']} shelves and {stats['total_books']} books!")

# Publish library to API
pub.publish(library)

# Run the server
pub.run()
