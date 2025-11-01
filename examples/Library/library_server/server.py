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
    title="Library API Server",
    description="Example library management system with CRUD operations"
)

# Create library instance and import data
library = Library()
library.import_from_csv()

# Add library to publisher
pub.add(library, path="/library")

# Run the server
pub.run()
