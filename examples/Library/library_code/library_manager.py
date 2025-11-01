"""Library management system for testing Publisher."""

import csv
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

from genro_core.decorators import apiready


@dataclass
class Shelf:
    """Simple shelf data class."""
    code: str
    name: str


@apiready(path="/shelf")
class ShelfManager:
    """Manager for shelf operations with API methods."""

    def __init__(self, library: "Library"):
        """Initialize shelf manager with reference to library.

        Args:
            library: Reference to Library instance
        """
        self._library = library

    @apiready
    def list_books(self, shelf_code: Annotated[str, "Shelf code"]) -> list[dict]:
        """List all books on a shelf."""
        return self._library.list_books_by_shelf(shelf_code)

    @apiready
    def count_books(self, shelf_code: Annotated[str, "Shelf code"]) -> int:
        """Count number of books on a shelf."""
        books = self._library.list_books_by_shelf(shelf_code)
        return len(books)

    @apiready
    def get_info(self, shelf_code: Annotated[str, "Shelf code"]) -> dict[str, str]:
        """Get shelf information."""
        shelf = self._library.get_shelf(shelf_code)
        return {
            "code": shelf.code,
            "name": shelf.name,
            "type": "shelf"
        }


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
    ) -> "Book":
        """Move book to a different shelf."""
        return self._library.move_book(self.id, new_shelf_code)

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
class Library:
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
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

        # Create shelf manager (will be discovered by eager introspection)
        self.shelf = ShelfManager(self)

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Shelves table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shelves (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

        # Books table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                publisher TEXT NOT NULL,
                pages INTEGER NOT NULL,
                genre TEXT NOT NULL,
                shelf_code TEXT NOT NULL,
                FOREIGN KEY (shelf_code) REFERENCES shelves(code)
            )
        """)

        # Book content table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS book_content (
                book_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                PRIMARY KEY (book_id, page_number),
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        """)

        self.conn.commit()

    def _row_to_shelf(self, row: sqlite3.Row) -> Shelf:
        """Convert database row to Shelf object."""
        return Shelf(code=row["code"], name=row["name"])

    def _row_to_book(self, row: sqlite3.Row) -> Book:
        """Convert database row to Book object."""
        # Load page content for this book
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT page_number, content FROM book_content WHERE book_id = ?",
            (row["id"],),
        )
        content = {row["page_number"]: row["content"] for row in cursor.fetchall()}

        return Book(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            publisher=row["publisher"],
            pages=row["pages"],
            genre=row["genre"],
            shelf_code=row["shelf_code"],
            library=self,
            content=content,
        )

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

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
                        self.add_shelf(code=row["code"], name=row["name"])
                    except ValueError:
                        # Shelf already exists, skip
                        pass

        # Import books
        books_file = data_dir / "books.csv"
        if books_file.exists():
            with open(books_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.add_book(
                        title=row["title"],
                        author=row["author"],
                        publisher=row["publisher"],
                        pages=int(row["pages"]),
                        genre=row["genre"],
                        shelf_code=row["shelf_code"],
                    )

    # ========== SHELF MANAGEMENT ==========

    @apiready
    def add_shelf(
        self,
        code: Annotated[str, "Shelf code (unique identifier)"],
        name: Annotated[str, "Shelf name"],
    ) -> Shelf:
        """Add a new shelf to the library."""
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO shelves (code, name) VALUES (?, ?)", (code, name)
            )
            self.conn.commit()
            return Shelf(code=code, name=name)
        except sqlite3.IntegrityError:
            raise ValueError(f"Shelf with code '{code}' already exists")

    @apiready
    def remove_shelf(self, code: Annotated[str, "Shelf code to remove"]) -> None:
        """Remove a shelf from the library."""
        cursor = self.conn.cursor()

        # Check if shelf exists
        cursor.execute("SELECT code FROM shelves WHERE code = ?", (code,))
        if not cursor.fetchone():
            raise KeyError(f"Shelf '{code}' not found")

        # Check if shelf has books
        cursor.execute(
            "SELECT COUNT(*) as count FROM books WHERE shelf_code = ?", (code,)
        )
        count = cursor.fetchone()["count"]
        if count > 0:
            raise ValueError(
                f"Cannot remove shelf '{code}': it contains {count} books"
            )

        cursor.execute("DELETE FROM shelves WHERE code = ?", (code,))
        self.conn.commit()

    @apiready
    def list_shelves(self) -> list[Shelf]:
        """List all shelves in the library."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT code, name FROM shelves ORDER BY code")
        return [self._row_to_shelf(row) for row in cursor.fetchall()]

    @apiready
    def get_shelf(self, code: Annotated[str, "Shelf code"]) -> Shelf:
        """Get a shelf by its code."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT code, name FROM shelves WHERE code = ?", (code,))
        row = cursor.fetchone()

        if not row:
            raise KeyError(f"Shelf '{code}' not found")

        return self._row_to_shelf(row)

    # ========== BOOK MANAGEMENT ==========

    @apiready
    def add_book(
        self,
        title: Annotated[str, "Book title"],
        author: Annotated[str, "Book author"],
        publisher: Annotated[str, "Publisher name"],
        pages: Annotated[int, "Number of pages"],
        genre: Annotated[str, "Book genre"],
        shelf_code: Annotated[str, "Shelf code where book will be placed"],
    ) -> Book:
        """Add a new book to the library."""
        cursor = self.conn.cursor()

        # Validate shelf exists
        cursor.execute("SELECT code FROM shelves WHERE code = ?", (shelf_code,))
        if not cursor.fetchone():
            raise KeyError(f"Shelf '{shelf_code}' not found")

        # Insert book
        cursor.execute(
            """
            INSERT INTO books (title, author, publisher, pages, genre, shelf_code)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (title, author, publisher, pages, genre, shelf_code),
        )
        self.conn.commit()

        book_id = cursor.lastrowid
        return Book(
            id=book_id,
            title=title,
            author=author,
            publisher=publisher,
            pages=pages,
            genre=genre,
            shelf_code=shelf_code,
            library=self,
        )

    @apiready
    def remove_book(self, book_id: Annotated[int, "Book ID to remove"]) -> None:
        """Remove a book from the library."""
        cursor = self.conn.cursor()

        # Check if book exists
        cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
        if not cursor.fetchone():
            raise KeyError(f"Book with ID {book_id} not found")

        # Delete book (content is deleted via CASCADE)
        cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self.conn.commit()

    @apiready
    def get_book(self, book_id: Annotated[int, "Book ID"]) -> Book:
        """Get a book by its ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, title, author, publisher, pages, genre, shelf_code
            FROM books WHERE id = ?
        """,
            (book_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise KeyError(f"Book with ID {book_id} not found")

        return self._row_to_book(row)

    @apiready
    def move_book(
        self,
        book_id: Annotated[int, "Book ID to move"],
        new_shelf_code: Annotated[str, "New shelf code"],
    ) -> Book:
        """Move a book to a different shelf."""
        cursor = self.conn.cursor()

        # Check if book exists
        cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
        if not cursor.fetchone():
            raise KeyError(f"Book with ID {book_id} not found")

        # Check if new shelf exists
        cursor.execute("SELECT code FROM shelves WHERE code = ?", (new_shelf_code,))
        if not cursor.fetchone():
            raise KeyError(f"Shelf '{new_shelf_code}' not found")

        # Update book shelf
        cursor.execute(
            "UPDATE books SET shelf_code = ? WHERE id = ?", (new_shelf_code, book_id)
        )
        self.conn.commit()

        return self.get_book(book_id)

    # ========== BOOK QUERIES ==========

    @apiready
    def list_books_by_shelf(
        self, shelf_code: Annotated[str, "Shelf code"]
    ) -> list[dict]:
        """List all books on a specific shelf."""
        cursor = self.conn.cursor()

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

        # Return dictionaries to avoid serialization issues with Book objects
        return [
            {
                "id": row[0],
                "title": row[1],
                "author": row[2],
                "publisher": row[3],
                "pages": row[4],
                "genre": row[5],
                "shelf_code": row[6],
            }
            for row in cursor.fetchall()
        ]

    @apiready
    def list_books_by_genre(self, genre: Annotated[str, "Book genre"]) -> list[Book]:
        """List all books of a specific genre."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, title, author, publisher, pages, genre, shelf_code
            FROM books WHERE LOWER(genre) = LOWER(?)
            ORDER BY title
        """,
            (genre,),
        )

        return [self._row_to_book(row) for row in cursor.fetchall()]

    @apiready
    def list_books_by_author(
        self, author: Annotated[str, "Author name"]
    ) -> list[Book]:
        """List all books by a specific author."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, title, author, publisher, pages, genre, shelf_code
            FROM books WHERE LOWER(author) LIKE LOWER(?)
            ORDER BY title
        """,
            (f"%{author}%",),
        )

        return [self._row_to_book(row) for row in cursor.fetchall()]

    @apiready
    def list_all_books(self) -> list[dict]:
        """List all books in the library."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, title, author, publisher, pages, genre, shelf_code
            FROM books
            ORDER BY title
        """
        )

        # Return dictionaries to avoid serialization issues with Book objects
        return [
            {
                "id": row[0],
                "title": row[1],
                "author": row[2],
                "publisher": row[3],
                "pages": row[4],
                "genre": row[5],
                "shelf_code": row[6],
            }
            for row in cursor.fetchall()
        ]

    # ========== BOOK CONTENT ==========

    @apiready
    def get_page_content(
        self,
        book_id: Annotated[int, "Book ID"],
        page_number: Annotated[int, "Page number"],
    ) -> str:
        """Get the content of a specific page."""
        cursor = self.conn.cursor()

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

    @apiready
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
        cursor = self.conn.cursor()

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
        cursor = self.conn.cursor()

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
        cursor = self.conn.cursor()
        cursor.execute("SELECT genre FROM books GROUP BY genre ORDER BY genre")
        return [row["genre"] for row in cursor.fetchall()]
