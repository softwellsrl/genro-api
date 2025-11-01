"""Example FastAPI server for Library management system using Publisher."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from genro_api import Publisher
from genro_api.config import PublisherConfig
from tests.fixtures.library import Library


def main():
    """Start the library API server."""

    # Create library instance with in-memory database
    library = Library(":memory:")

    # Add some sample data
    print("Populating library with sample data...")

    # Add shelves
    library.add_shelf("A1", "Science Fiction")
    library.add_shelf("A2", "Fantasy")
    library.add_shelf("A3", "Space Opera")
    library.add_shelf("B1", "Mystery")
    library.add_shelf("B2", "Thriller")
    library.add_shelf("B3", "Crime")
    library.add_shelf("C1", "Horror")
    library.add_shelf("C2", "Historical Fiction")
    library.add_shelf("D1", "Romance")
    library.add_shelf("D2", "Adventure")

    # Science Fiction books (A1)
    library.add_book("Dune", "Frank Herbert", "Chilton Books", 412, "Science Fiction", "A1")
    library.add_book("Foundation", "Isaac Asimov", "Gnome Press", 255, "Science Fiction", "A1")
    library.add_book("Neuromancer", "William Gibson", "Ace Books", 271, "Science Fiction", "A1")
    library.add_book("Snow Crash", "Neal Stephenson", "Bantam Books", 440, "Science Fiction", "A1")
    library.add_book("The Left Hand of Darkness", "Ursula K. Le Guin", "Ace Books", 304, "Science Fiction", "A1")
    library.add_book("Hyperion", "Dan Simmons", "Doubleday", 482, "Science Fiction", "A1")

    # Fantasy books (A2)
    library.add_book("The Lord of the Rings", "J.R.R. Tolkien", "George Allen & Unwin", 1178, "Fantasy", "A2")
    library.add_book("The Hobbit", "J.R.R. Tolkien", "George Allen & Unwin", 310, "Fantasy", "A2")
    library.add_book("A Game of Thrones", "George R.R. Martin", "Bantam Books", 694, "Fantasy", "A2")
    library.add_book("The Name of the Wind", "Patrick Rothfuss", "DAW Books", 662, "Fantasy", "A2")
    library.add_book("The Way of Kings", "Brandon Sanderson", "Tor Books", 1007, "Fantasy", "A2")
    library.add_book("Harry Potter and the Philosopher's Stone", "J.K. Rowling", "Bloomsbury", 223, "Fantasy", "A2")

    # Space Opera books (A3)
    library.add_book("The Expanse: Leviathan Wakes", "James S.A. Corey", "Orbit Books", 561, "Space Opera", "A3")
    library.add_book("Ender's Game", "Orson Scott Card", "Tor Books", 324, "Space Opera", "A3")
    library.add_book("Old Man's War", "John Scalzi", "Tor Books", 320, "Space Opera", "A3")
    library.add_book("Consider Phlebas", "Iain M. Banks", "Macmillan", 471, "Space Opera", "A3")
    library.add_book("A Fire Upon the Deep", "Vernor Vinge", "Tor Books", 613, "Space Opera", "A3")

    # Mystery books (B1)
    library.add_book("The Hound of the Baskervilles", "Arthur Conan Doyle", "George Newnes", 256, "Mystery", "B1")
    library.add_book("Murder on the Orient Express", "Agatha Christie", "Collins Crime Club", 256, "Mystery", "B1")
    library.add_book("The Big Sleep", "Raymond Chandler", "Alfred A. Knopf", 231, "Mystery", "B1")
    library.add_book("The Maltese Falcon", "Dashiell Hammett", "Alfred A. Knopf", 217, "Mystery", "B1")
    library.add_book("In the Woods", "Tana French", "Viking Press", 429, "Mystery", "B1")

    # Thriller books (B2)
    library.add_book("The Girl with the Dragon Tattoo", "Stieg Larsson", "Norstedts", 465, "Thriller", "B2")
    library.add_book("Gone Girl", "Gillian Flynn", "Crown Publishing", 415, "Thriller", "B2")
    library.add_book("The Silence of the Lambs", "Thomas Harris", "St. Martin's Press", 338, "Thriller", "B2")
    library.add_book("The Bourne Identity", "Robert Ludlum", "Richard Marek Publishers", 523, "Thriller", "B2")
    library.add_book("Red Dragon", "Thomas Harris", "G.P. Putnam's Sons", 348, "Thriller", "B2")

    # Crime books (B3)
    library.add_book("The Godfather", "Mario Puzo", "G.P. Putnam's Sons", 448, "Crime", "B3")
    library.add_book("L.A. Confidential", "James Ellroy", "Mysterious Press", 496, "Crime", "B3")
    library.add_book("The Postman Always Rings Twice", "James M. Cain", "Alfred A. Knopf", 128, "Crime", "B3")
    library.add_book("American Psycho", "Bret Easton Ellis", "Vintage Books", 399, "Crime", "B3")
    library.add_book("No Country for Old Men", "Cormac McCarthy", "Alfred A. Knopf", 309, "Crime", "B3")

    # Horror books (C1)
    library.add_book("The Shining", "Stephen King", "Doubleday", 447, "Horror", "C1")
    library.add_book("It", "Stephen King", "Viking Press", 1138, "Horror", "C1")
    library.add_book("Dracula", "Bram Stoker", "Archibald Constable", 418, "Horror", "C1")
    library.add_book("Frankenstein", "Mary Shelley", "Lackington, Hughes", 280, "Horror", "C1")
    library.add_book("The Exorcist", "William Peter Blatty", "Harper & Row", 340, "Horror", "C1")

    # Historical Fiction books (C2)
    library.add_book("All the Light We Cannot See", "Anthony Doerr", "Scribner", 531, "Historical Fiction", "C2")
    library.add_book("The Book Thief", "Markus Zusak", "Picador", 552, "Historical Fiction", "C2")
    library.add_book("Wolf Hall", "Hilary Mantel", "Fourth Estate", 653, "Historical Fiction", "C2")
    library.add_book("The Pillars of the Earth", "Ken Follett", "William Morrow", 973, "Historical Fiction", "C2")
    library.add_book("The Nightingale", "Kristin Hannah", "St. Martin's Press", 440, "Historical Fiction", "C2")

    # Romance books (D1)
    library.add_book("Pride and Prejudice", "Jane Austen", "T. Egerton", 432, "Romance", "D1")
    library.add_book("Outlander", "Diana Gabaldon", "Delacorte Press", 627, "Romance", "D1")
    library.add_book("The Notebook", "Nicholas Sparks", "Warner Books", 214, "Romance", "D1")
    library.add_book("Me Before You", "Jojo Moyes", "Penguin Books", 369, "Romance", "D1")
    library.add_book("The Time Traveler's Wife", "Audrey Niffenegger", "MacAdam/Cage", 518, "Romance", "D1")

    # Adventure books (D2)
    library.add_book("Treasure Island", "Robert Louis Stevenson", "Cassell & Co", 292, "Adventure", "D2")
    library.add_book("The Count of Monte Cristo", "Alexandre Dumas", "Pétion", 1276, "Adventure", "D2")
    library.add_book("Journey to the Center of the Earth", "Jules Verne", "Pierre-Jules Hetzel", 183, "Adventure", "D2")
    library.add_book("Robinson Crusoe", "Daniel Defoe", "William Taylor", 364, "Adventure", "D2")
    library.add_book("The Three Musketeers", "Alexandre Dumas", "Baudry", 700, "Adventure", "D2")

    print(f"Library populated with 10 shelves and 55 books!")
    print()

    # Create configuration instance with in-memory database
    config = PublisherConfig(":memory:")

    # Create and configure publisher
    publisher = Publisher(
        host="127.0.0.1",
        port=8000,
        title="Library API",
        version="1.0.0",
        enable_rest=True,
        enable_ui=True,  # NiceGUI admin interface enabled
        enable_swagger=True,
        config=config,  # Pass config instance for UI to read preferences
    )

    # Publish the library instance
    print("Publishing Library API...")
    publisher.publish(library)

    # Publish the configuration instance so it appears as a tab
    print("Publishing Configuration API...")
    publisher.publish(config)

    print()
    print("=" * 60)
    print("Library API Server Starting")
    print("=" * 60)
    print()
    print("Admin Interface:")
    print("  Admin Console: http://127.0.0.1:8000/admin")
    print()
    print("API Endpoints:")
    print("  Library: http://127.0.0.1:8000/library/*")
    print("  ShelfManager: http://127.0.0.1:8000/shelf/*")
    print("  Book: http://127.0.0.1:8000/book/*")
    print()
    print("Documentation:")
    print("  Swagger UI: http://127.0.0.1:8000/docs")
    print("  ReDoc: http://127.0.0.1:8000/redoc")
    print()
    print("Example endpoints:")
    print("  GET  /library/list_shelves")
    print("  GET  /library/list_all_books")
    print("  POST /library/add_book")
    print("  GET  /shelf/list_books?shelf_code=A1")
    print("  POST /shelf/count_books")
    print()
    print("=" * 60)
    print()

    # Start the server
    publisher.run(reload=False)


if __name__ == "__main__":
    main()
