from books.models import Book
from borrowers.models import Borrower
from borrowings.models import Borrowing


def create_book(**overrides):
    """Create and return a sample book."""
    fields = {
        'title': 'Clean Code',
        'author': 'Robert C. Martin',
        'total_quantity': 5,
    }
    fields.update(overrides)
    return Book.objects.create(**fields)


def create_borrower(**overrides):
    """Create and return a sample borrower."""
    fields = {
        'name': 'John Doe',
        'email': 'john@example.com',
    }
    fields.update(overrides)
    return Borrower.objects.create(**fields)


def create_borrowing(book, borrower, **overrides):
    """Create and return a borrowing for the given book and borrower."""
    return Borrowing.objects.create(
        book=book,
        borrower=borrower,
        **overrides,
    )
