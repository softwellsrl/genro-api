"""Library management system for testing Publisher."""

import csv
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

from genro_core.enablers import apiready
from genro_core import Table, GenroMicroApplication


class ShelfTable(Table):
    """Table for shelf operations with automatic CRUD."""

    sql_name = "shelves"
    pk_field = "code"  # Shelves use 'code' as primary key instead of 'id'
    name_plural = "shelves"
    name = "shelf"
    _icon = "📚"

    @dataclass
    class Columns:
        """Shelf columns schema."""
        code: str
        name: str

    @apiready
    def list_books(self, shelf_code: Annotated[str, "Shelf code"]) -> list[dict]:
        """List all books on a shelf."""
        with self.cursor() as cursor:
            # Check if shelf exists
            cursor.execute("SELECT code FROM shelves WHERE code = ?", (shelf_code,))
            if not cursor.fetchone():
                raise KeyError(f"Shelf '{shelf_code}' not found")

            cursor.execute(
                """
                SELECT id, title, author, publisher, pages, genre, shelf_code
                FROM books WHERE shelf_code = ?
                ORDER BY title
            """,
                (shelf_code,),
            )

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    @apiready
    def count_books(self, shelf_code: Annotated[str, "Shelf code"]) -> int:
        """Count number of books on a shelf."""
        books = self.list_books(shelf_code)
        return len(books)


class BookTable(Table):
    """Table for book operations with automatic CRUD."""

    sql_name = "books"
    name_plural = "books"
    name = "book"
    _icon = "📚"

    @dataclass
    class Columns:
        """Book columns schema."""
        id: int
        title: str
        author: str
        publisher: str
        pages: int
        genre: str
        shelf_code: str

    @apiready
    def list_by_author(self, author: Annotated[str, "Author name"]) -> list[dict]:
        """List all books by a specific author."""
        with self.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, author, publisher, pages, genre, shelf_code
                FROM books WHERE LOWER(author) LIKE LOWER(?)
                ORDER BY title
            """,
                (f"%{author}%",),
            )

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    @apiready
    def list_by_genre(self, genre: Annotated[str, "Book genre"]) -> list[dict]:
        """List all books of a specific genre."""
        with self.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, author, publisher, pages, genre, shelf_code
                FROM books WHERE LOWER(genre) = LOWER(?)
                ORDER BY title
            """,
                (genre,),
            )

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    @apiready
    def move(
        self,
        book_id: Annotated[int, "Book ID to move"],
        new_shelf_code: Annotated[str, "New shelf code"],
    ) -> dict:
        """Move a book to a different shelf."""
        # Use the base update() method
        return self.update(book_id, shelf_code=new_shelf_code)


@apiready(path="/book")
class Book:
    """Book in the library with API methods."""

    def __init__(
        self,
        id: int,
        title: str,
        author: str,
        publisher: str,
        pages: int,
        genre: str,
        shelf_code: str,
        library: "Library",
        content: dict[int, str] | None = None
    ):
        """Initialize book with reference to library.

        Args:
            id: Book ID
            title: Book title
            author: Book author
            publisher: Publisher name
            pages: Number of pages
            genre: Book genre
            shelf_code: Shelf where book is located
            library: Reference to Library instance
            content: Optional page content dictionary
        """
        self.id = id
        self.title = title
        self.author = author
        self.publisher = publisher
        self.pages = pages
        self.genre = genre
        self.shelf_code = shelf_code
        self._library = library
        self.content = content or {}

    @apiready
    def get_page(
        self, page_number: Annotated[int, "Page number to read"]
    ) -> str:
        """Get content of a specific page."""
        return self._library.get_page_content(self.id, page_number)

    @apiready
    def read(
        self,
        from_page: Annotated[int, "Start page number"] = 1,
        to_page: Annotated[int | None, "End page number (None = last page)"] = None
    ) -> dict[int, str]:
        """Read book content from page to page."""
        return self._library.read_book(self.id, from_page, to_page)

    @apiready
    def move_to(
        self, new_shelf_code: Annotated[str, "New shelf code"]
    ) -> dict:
        """Move book to a different shelf."""
        return self._library.book.move(self.id, new_shelf_code)

    @apiready
    def get_info(self) -> dict[str, Any]:
        """Get book information."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "publisher": self.publisher,
            "pages": self.pages,
            "genre": self.genre,
            "shelf_code": self.shelf_code,
            "type": "book"
        }


@apiready(path="/library")
class Library(GenroMicroApplication):
    """
    Library management system with SQLite persistence.

    Manages shelves and books with full CRUD operations
    and various query methods. All data is stored in SQLite database.
    """

    def __init__(self, db_path: str = ":memory:"):
        """
        Initialize the library with SQLite database.

        Args:
            db_path: Path to SQLite database file. Use ":memory:" for in-memory database.
        """
        super().__init__()

        # Add database
        self.add_db('maindb', implementation='sqlite', path=db_path)

        # Register tables
        maindb = self.db('maindb')
        maindb.add_table(ShelfTable)
        maindb.add_table(BookTable)

        # Run migrations to create/update tables automatically
        maindb.migrate()

        # Note: book_content table still managed manually (not a Table)
        self._create_book_content_table()

    def _create_book_content_table(self) -> None:
        """Create book_content table (not managed by Table)."""
        maindb = self.db('maindb')
        with maindb.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS book_content (
                    book_id INTEGER NOT NULL,
                    page_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    PRIMARY KEY (book_id, page_number),
                    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                )
            """)
        maindb.connection.commit()

    def close(self) -> None:
        """Close all database connections."""
        self.close_all()

    def import_from_csv(self, data_dir: str | Path | None = None) -> None:
        """
        Import library data from CSV files.

        Args:
            data_dir: Directory containing shelves.csv and books.csv files.
                     If None, uses the example_data directory relative to this file.
        """
        if data_dir is None:
            # Default to example_data directory relative to this file
            data_dir = Path(__file__).parent.parent / "example_data"
        else:
            data_dir = Path(data_dir)

        # Import shelves
        shelves_file = data_dir / "shelves.csv"
        if shelves_file.exists():
            with open(shelves_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        self.maindb.tables.shelf.insert(code=row["code"], name=row["name"])
                    except ValueError:
                        # Shelf already exists, skip
                        pass

        # Import books
        books_file = data_dir / "books.csv"
        if books_file.exists():
            with open(books_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.maindb.tables.book.insert(
                        title=row["title"],
                        author=row["author"],
                        publisher=row["publisher"],
                        pages=int(row["pages"]),
                        genre=row["genre"],
                        shelf_code=row["shelf_code"],
                    )

    # ========== BOOK CONTENT (for Book class usage) ==========

    def get_page_content(
        self,
        book_id: Annotated[int, "Book ID"],
        page_number: Annotated[int, "Page number"],
    ) -> str:
        """Get the content of a specific page."""
        maindb = self.db('maindb')
        with maindb.cursor() as cursor:
            # Get book to check page validity
            cursor.execute("SELECT pages FROM books WHERE id = ?", (book_id,))
            row = cursor.fetchone()

            if not row:
                raise KeyError(f"Book with ID {book_id} not found")

            pages = row["pages"]
            if page_number < 1 or page_number > pages:
                raise ValueError(f"Page number must be between 1 and {pages}")

            # Get page content
            cursor.execute(
                "SELECT content FROM book_content WHERE book_id = ? AND page_number = ?",
                (book_id, page_number),
            )
            row = cursor.fetchone()

            if row:
                return row["content"]
            return "[Page content not available]"

    def read_book(
        self,
        book_id: Annotated[int, "Book ID"],
        from_page: Annotated[int, "Start page number"] = 1,
        to_page: Annotated[int | None, "End page number (None = last page)"] = None,
    ) -> dict[int, str]:
        """
        Read book content from page to page.

        Returns a dictionary mapping page numbers to their content.
        """
        maindb = self.db('maindb')
        with maindb.cursor() as cursor:
            # Get book to determine page range
            cursor.execute("SELECT pages FROM books WHERE id = ?", (book_id,))
            row = cursor.fetchone()

            if not row:
                raise KeyError(f"Book with ID {book_id} not found")

            pages = row["pages"]
            if to_page is None:
                to_page = pages

            if from_page < 1 or from_page > pages:
                raise ValueError(f"Start page must be between 1 and {pages}")

            if to_page < from_page or to_page > pages:
                raise ValueError(f"End page must be between {from_page} and {pages}")

        # Get all page content in range
        result = {}
        for page in range(from_page, to_page + 1):
            result[page] = self.get_page_content(book_id, page)

        return result

    # ========== STATISTICS ==========

    @apiready
    def get_stats(self) -> dict[str, int]:
        """Get library statistics."""
        maindb = self.db('maindb')
        with maindb.cursor() as cursor:
            # Count shelves
            cursor.execute("SELECT COUNT(*) as count FROM shelves")
            total_shelves = cursor.fetchone()["count"]

            # Count books
            cursor.execute("SELECT COUNT(*) as count FROM books")
            total_books = cursor.fetchone()["count"]

            # Sum pages
            cursor.execute("SELECT SUM(pages) as total FROM books")
            total_pages = cursor.fetchone()["total"] or 0

            # Count genres
            cursor.execute("SELECT COUNT(DISTINCT genre) as count FROM books")
            total_genres = cursor.fetchone()["count"]

            return {
                "total_shelves": total_shelves,
                "total_books": total_books,
                "total_pages": total_pages,
                "total_genres": total_genres,
            }

    @apiready
    def get_genres(self) -> list[str]:
        """Get list of all genres in the library."""
        maindb = self.db('maindb')
        with maindb.cursor() as cursor:
            cursor.execute("SELECT genre FROM books GROUP BY genre ORDER BY genre")
            return [row["genre"] for row in cursor.fetchall()]
