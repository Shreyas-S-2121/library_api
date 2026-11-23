from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from books.models import Book
from borrowers.models import Borrower
from borrowings.models import Borrowing


class BorrowingModelTests(TestCase):
    """Tests for the Borrowing model."""

    def test_create_borrowing(self):
        """Test creating a borrowing sets its timestamp and active state."""
        book = Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=1,
        )
        borrower = Borrower.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        before_create = timezone.now()
        borrowing = Borrowing.objects.create(
            book=book,
            borrower=borrower,
        )
        after_create = timezone.now()

        self.assertIsNotNone(borrowing.pk)
        self.assertEqual(borrowing.book, book)
        self.assertEqual(borrowing.borrower, borrower)
        self.assertGreaterEqual(borrowing.borrowed_at, before_create)
        self.assertLessEqual(borrowing.borrowed_at, after_create)
        self.assertIsNone(borrowing.returned_at)

    def test_duplicate_active_borrowing_for_same_pair_is_rejected(self):
        """Test the database rejects a duplicate active book/borrower pair."""
        book = Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=1,
        )
        borrower = Borrower.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        Borrowing.objects.create(book=book, borrower=borrower)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Borrowing.objects.create(
                    book=book,
                    borrower=borrower,
                )

    def test_active_borrowing_uniqueness_is_scoped_to_book_and_borrower_pair(
        self,
    ):
        """Test distinct book/borrower pairs can be active concurrently."""
        first_book = Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=2,
        )
        second_book = Book.objects.create(
            title='Dune',
            author='Frank Herbert',
            total_quantity=1,
        )
        first_borrower = Borrower.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        second_borrower = Borrower.objects.create(
            name='Jane Doe',
            email='jane@example.com',
        )

        Borrowing.objects.create(
            book=first_book,
            borrower=first_borrower,
        )
        Borrowing.objects.create(
            book=first_book,
            borrower=second_borrower,
        )
        Borrowing.objects.create(
            book=second_book,
            borrower=first_borrower,
        )

        self.assertEqual(Borrowing.objects.count(), 3)

    def test_borrower_can_borrow_same_book_again_after_return(self):
        """Test a returned book/borrower pair can be borrowed again."""
        book = Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=1,
        )
        borrower = Borrower.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        first_borrowing = Borrowing.objects.create(
            book=book,
            borrower=borrower,
        )
        first_borrowing.returned_at = timezone.now()
        first_borrowing.save(update_fields=['returned_at'])

        second_borrowing = Borrowing.objects.create(
            book=book,
            borrower=borrower,
        )

        self.assertIsNotNone(first_borrowing.returned_at)
        self.assertIsNone(second_borrowing.returned_at)
        self.assertEqual(
            Borrowing.objects.filter(
                book=book,
                borrower=borrower,
            ).count(),
            2,
        )

    def test_book_with_borrowing_history_is_protected_from_deletion(self):
        """Test active and returned borrowings protect their Book."""
        for is_returned in (False, True):
            with self.subTest(is_returned=is_returned):
                borrower_email = (
                    'john-returned@example.com'
                    if is_returned else 'john@example.com'
                )
                book_title = 'Returned Code' if is_returned else 'Clean Code'
                book = Book.objects.create(
                    title=book_title,
                    author='Robert C. Martin',
                    total_quantity=1,
                )
                borrower = Borrower.objects.create(
                    name='John Doe',
                    email=borrower_email,
                )
                borrowing = Borrowing.objects.create(
                    book=book,
                    borrower=borrower,
                )
                if is_returned:
                    borrowing.returned_at = timezone.now()
                    borrowing.save(update_fields=['returned_at'])

                with self.assertRaises(ProtectedError):
                    book.delete()

    def test_borrower_with_borrowing_history_is_protected_from_deletion(self):
        """Test active and returned borrowings protect their Borrower."""
        for is_returned in (False, True):
            with self.subTest(is_returned=is_returned):
                borrower_email = (
                    'john-returned@example.com'
                    if is_returned else 'john@example.com'
                )
                book_title = 'Returned Code' if is_returned else 'Clean Code'
                book = Book.objects.create(
                    title=book_title,
                    author='Robert C. Martin',
                    total_quantity=1,
                )
                borrower = Borrower.objects.create(
                    name='John Doe',
                    email=borrower_email,
                )
                borrowing = Borrowing.objects.create(
                    book=book,
                    borrower=borrower,
                )
                if is_returned:
                    borrowing.returned_at = timezone.now()
                    borrowing.save(update_fields=['returned_at'])

                with self.assertRaises(ProtectedError):
                    borrower.delete()
