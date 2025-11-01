# Genro API Examples

This directory contains working examples of the Genro API Publisher.

## Library Management System

A complete example demonstrating the Publisher with a library management system.

### Files

- **`library_example.py`** - Standalone example showing library usage (no API)
- **`library_server.py`** - Full API server with REST endpoints and Admin UI

### Running the Library Server

1. **Install dependencies:**
   ```bash
   cd /path/to/genro-api
   pip install -e .
   ```

2. **Start the server:**
   ```bash
   python examples/library_server.py
   ```

3. **Access the interfaces:**

   - **Admin Console**: http://127.0.0.1:8000/admin
   - **Swagger UI**: http://127.0.0.1:8000/docs
   - **ReDoc**: http://127.0.0.1:8000/redoc

### Using the Admin Console

The Admin Console is a web-based interface built with NiceGUI that allows you to:

1. **Browse published classes** - Each tab represents a published class (Library, ShelfManager, Book)

2. **Call API methods** - Each method is displayed as a card with:
   - HTTP method badge (GET/POST)
   - Method name and description
   - Dynamic form for parameters
   - Execute button
   - Result display

3. **Interactive testing** - Fill in parameters and click "Execute" to call methods directly

#### Example: Adding a Shelf

1. Go to http://127.0.0.1:8000/admin
2. Click on the "Library" tab
3. Scroll to the "add_shelf" method card
4. Fill in:
   - **code**: "E1"
   - **name**: "Biography"
5. Click "Execute"
6. See the result displayed below the button

#### Example: Listing Books

1. Click on the "Library" tab
2. Find the "list_books_by_shelf" method
3. Fill in:
   - **shelf_code**: "A1" (Science Fiction)
4. Click "Execute"
5. See the list of books in JSON format

### Using the REST API

You can also call the API directly using curl or any HTTP client:

```bash
# List all shelves
curl http://127.0.0.1:8000/library/list_shelves

# Get books on shelf A1
curl http://127.0.0.1:8000/library/list_books_by_shelf?shelf_code=A1

# Add a new book (POST with JSON body)
curl -X POST http://127.0.0.1:8000/library/add_book \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Martian",
    "author": "Andy Weir",
    "publisher": "Crown Publishing",
    "pages": 369,
    "genre": "Science Fiction",
    "shelf_code": "A1"
  }'

# Get library statistics
curl http://127.0.0.1:8000/library/get_stats
```

### Sample Data

The server starts with pre-populated data:

- **10 shelves** across different genres (A1-D2)
- **55 books** from various authors and genres
- Includes Science Fiction, Fantasy, Mystery, Horror, and more

### Features Demonstrated

1. **@apiready Decorator**
   - Class-level decoration (`@apiready(path="/library")`)
   - Method-level decoration (`@apiready`)
   - Type hints for automatic parameter validation
   - Annotated types for parameter descriptions

2. **Publisher**
   - Automatic REST API generation
   - NiceGUI admin interface
   - OpenAPI/Swagger documentation
   - Multi-class support (Library, ShelfManager, Book)

3. **NiceGUI Admin Interface**
   - Automatic form generation from type hints
   - Support for different parameter types (str, int, bool, etc.)
   - Real-time method execution
   - Result display (JSON, text, error handling)
   - WebSocket-based SPA (no page reloads)

4. **Polymorphism**
   - Multiple classes (Library, ShelfManager, Book) published independently
   - Each class has its own base path
   - Publisher treats all classes uniformly
   - Admin UI automatically adapts to any @apiready class

### Architecture

```
library_server.py
    ↓
Publisher
    ├── REST API (FastAPI)
    │   ├── /library/* endpoints
    │   ├── /shelf/* endpoints
    │   └── /book/* endpoints
    │
    └── Admin UI (NiceGUI)
        ├── /admin page
        ├── Tabs for each class
        └── Dynamic forms for methods
```

### Next Steps

- Try modifying the Library class to add new methods
- Create your own @apiready class and publish it
- Explore the typed shelves/books feature (see temp/typed_library_design.md)

## Other Examples

More examples coming soon:
- Storage backend example
- Multi-tenancy example
- Authentication example
