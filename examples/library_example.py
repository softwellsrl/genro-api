"""Example usage of Library class with sample data."""

import sys
from pathlib import Path

# Add parent directory to path to import fixtures
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.fixtures.library import Library


def populate_library(library: Library) -> None:
    """Populate library with sample shelves and books."""

    # Add shelves
    print("Adding shelves...")
    library.add_shelf("A1", "Science Fiction")
    library.add_shelf("A2", "Fantasy")
    library.add_shelf("B1", "Mystery")
    library.add_shelf("B2", "Classic Literature")
    library.add_shelf("C1", "Technical Books")

    # Add Science Fiction books
    print("\nAdding Science Fiction books...")
    dune = library.add_book(
        "Dune",
        "Frank Herbert",
        "Chilton Books",
        412,
        "Science Fiction",
        "A1"
    )

    foundation = library.add_book(
        "Foundation",
        "Isaac Asimov",
        "Gnome Press",
        255,
        "Science Fiction",
        "A1"
    )

    neuromancer = library.add_book(
        "Neuromancer",
        "William Gibson",
        "Ace Books",
        271,
        "Science Fiction",
        "A1"
    )

    # Add Fantasy books
    print("Adding Fantasy books...")
    lotr = library.add_book(
        "The Lord of the Rings",
        "J.R.R. Tolkien",
        "George Allen & Unwin",
        1178,
        "Fantasy",
        "A2"
    )

    hobbit = library.add_book(
        "The Hobbit",
        "J.R.R. Tolkien",
        "George Allen & Unwin",
        310,
        "Fantasy",
        "A2"
    )

    game_of_thrones = library.add_book(
        "A Game of Thrones",
        "George R.R. Martin",
        "Bantam Spectra",
        694,
        "Fantasy",
        "A2"
    )

    # Add Mystery books
    print("Adding Mystery books...")
    sherlock = library.add_book(
        "The Hound of the Baskervilles",
        "Arthur Conan Doyle",
        "George Newnes",
        256,
        "Mystery",
        "B1"
    )

    poirot = library.add_book(
        "Murder on the Orient Express",
        "Agatha Christie",
        "Collins Crime Club",
        256,
        "Mystery",
        "B1"
    )

    # Add Classic Literature
    print("Adding Classic Literature books...")
    moby_dick = library.add_book(
        "Moby-Dick",
        "Herman Melville",
        "Harper & Brothers",
        635,
        "Classic Literature",
        "B2"
    )

    pride = library.add_book(
        "Pride and Prejudice",
        "Jane Austen",
        "T. Egerton",
        432,
        "Classic Literature",
        "B2"
    )

    # Add Technical books
    print("Adding Technical books...")
    python_book = library.add_book(
        "Fluent Python",
        "Luciano Ramalho",
        "O'Reilly Media",
        792,
        "Technical",
        "C1"
    )

    clean_code = library.add_book(
        "Clean Code",
        "Robert C. Martin",
        "Prentice Hall",
        464,
        "Technical",
        "C1"
    )

    print("\n✓ Library populated successfully!")


def display_library_info(library: Library) -> None:
    """Display library statistics and contents."""

    print("\n" + "="*60)
    print("LIBRARY STATISTICS")
    print("="*60)

    stats = library.get_stats()
    print(f"Total Shelves: {stats['total_shelves']}")
    print(f"Total Books: {stats['total_books']}")
    print(f"Total Pages: {stats['total_pages']}")
    print(f"Total Genres: {stats['total_genres']}")

    print("\n" + "="*60)
    print("SHELVES")
    print("="*60)

    for shelf in library.list_shelves():
        books = library.list_books_by_shelf(shelf.code)
        print(f"\n[{shelf.code}] {shelf.name} - {len(books)} books")
        for book in books:
            print(f"  • {book.title} by {book.author} ({book.pages} pages)")

    print("\n" + "="*60)
    print("GENRES")
    print("="*60)

    for genre in library.get_genres():
        books = library.list_books_by_genre(genre)
        print(f"\n{genre}: {len(books)} books")
        for book in books:
            print(f"  • {book.title} by {book.author}")

    print("\n" + "="*60)
    print("BOOKS BY TOLKIEN")
    print("="*60)

    tolkien_books = library.list_books_by_author("Tolkien")
    for book in tolkien_books:
        print(f"  • {book.title} ({book.pages} pages, on shelf {book.shelf_code})")


def main():
    """Main example function."""

    print("="*60)
    print("LIBRARY MANAGEMENT SYSTEM - Example")
    print("="*60)

    # Create library with in-memory database
    print("\nCreating library with in-memory SQLite database...")
    library = Library(":memory:")

    # Populate with sample data
    populate_library(library)

    # Display library information
    display_library_info(library)

    # Example: Move a book
    print("\n" + "="*60)
    print("MOVING A BOOK")
    print("="*60)

    print("\nMoving 'Neuromancer' from A1 to C1 (Technical Books)...")
    library.move_book(3, "C1")  # Neuromancer ID is 3

    print("\nBooks on shelf C1 (Technical Books):")
    for book in library.list_books_by_shelf("C1"):
        print(f"  • {book.title} by {book.author}")

    # Close database connection
    library.close()

    print("\n" + "="*60)
    print("Example completed!")
    print("="*60)


if __name__ == "__main__":
    main()
