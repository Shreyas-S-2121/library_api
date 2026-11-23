from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from core import models


class BookModelTests(TestCase):
    """Tests for the Book model."""

    def test_create_book(self):
        """Test creating a book with valid data."""
        book = models.Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=5,
        )

        self.assertIsNotNone(book.pk)
        self.assertEqual(book.title, 'Clean Code')
        self.assertEqual(book.author, 'Robert C. Martin')
        self.assertEqual(book.total_quantity, 5)

    def test_create_book_with_zero_quantity(self):
        """Test that a book can have zero total copies."""
        book = models.Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=0,
        )

        self.assertEqual(book.total_quantity, 0)

    def test_negative_total_quantity_is_rejected(self):
        """Test that the database rejects a negative total quantity."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                models.Book.objects.create(
                    title='Clean Code',
                    author='Robert C. Martin',
                    total_quantity=-1,
                )

    def test_duplicate_title_and_author_are_rejected(self):
        """Test that the title and author combination must be unique."""
        models.Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=5,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                models.Book.objects.create(
                    title='Clean Code',
                    author='Robert C. Martin',
                    total_quantity=3,
                )

    def test_title_or_author_can_be_reused_in_another_combination(self):
        """Test that only the title and author combination must be unique."""
        models.Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=5,
        )

        same_title = models.Book.objects.create(
            title='Clean Code',
            author='Another Author',
            total_quantity=2,
        )
        same_author = models.Book.objects.create(
            title='A Different Book',
            author='Robert C. Martin',
            total_quantity=1,
        )

        self.assertNotEqual(same_title.pk, same_author.pk)


class BorrowerModelTests(TestCase):
    """Tests for the Borrower model."""

    def test_create_borrower(self):
        """Test creating a borrower with valid data."""
        borrower = models.Borrower.objects.create(
            name='John Doe',
            email='john@example.com',
        )

        self.assertIsNotNone(borrower.pk)
        self.assertEqual(borrower.name, 'John Doe')
        self.assertEqual(borrower.email, 'john@example.com')

    def test_borrower_email_is_stored_lowercase(self):
        """Test a mixed-case email is stored in lowercase."""
        borrower = models.Borrower.objects.create(
            name='John Doe',
            email='John.Doe@Example.COM',
        )

        self.assertEqual(borrower.email, 'john.doe@example.com')

    def test_borrower_name_and_email_are_trimmed(self):
        """Test surrounding whitespace is stripped from borrower fields."""
        borrower = models.Borrower.objects.create(
            name='  John Doe  ',
            email='  John.Doe@Example.COM  ',
        )

        self.assertEqual(borrower.name, 'John Doe')
        self.assertEqual(borrower.email, 'john.doe@example.com')

    def test_blank_name_or_email_is_rejected(self):
        """Test full validation rejects blank names and emails."""
        for field in ('name', 'email'):
            with self.subTest(field=field):
                borrower = models.Borrower(
                    name='John Doe',
                    email='john@example.com',
                )
                setattr(borrower, field, '')

                with self.assertRaises(ValidationError):
                    borrower.full_clean()

    def test_invalid_email_is_rejected(self):
        """Test full validation identifies an invalid email."""
        borrower = models.Borrower(
            name='John Doe',
            email='not-an-email',
        )

        with self.assertRaises(ValidationError) as context:
            borrower.full_clean()

        self.assertIn('email', context.exception.message_dict)

    def test_duplicate_email_is_rejected(self):
        """Test normalized duplicate emails violate database uniqueness."""
        models.Borrower.objects.create(
            name='John Doe',
            email='JOHN@example.com',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                models.Borrower.objects.create(
                    name='Another Person',
                    email='john@example.com',
                )


class BorrowingModelTests(TestCase):
    """Tests for the Borrowing model."""

    def test_create_borrowing(self):
        """Test creating a borrowing sets its timestamp and active state."""
        book = models.Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=1,
        )
        borrower = models.Borrower.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        before_create = timezone.now()
        borrowing = models.Borrowing.objects.create(
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
        book = models.Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=1,
        )
        borrower = models.Borrower.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        models.Borrowing.objects.create(book=book, borrower=borrower)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                models.Borrowing.objects.create(
                    book=book,
                    borrower=borrower,
                )

    def test_active_borrowing_uniqueness_is_scoped_to_book_and_borrower_pair(
        self,
    ):
        """Test distinct book/borrower pairs can be active concurrently."""
        first_book = models.Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=2,
        )
        second_book = models.Book.objects.create(
            title='Dune',
            author='Frank Herbert',
            total_quantity=1,
        )
        first_borrower = models.Borrower.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        second_borrower = models.Borrower.objects.create(
            name='Jane Doe',
            email='jane@example.com',
        )

        models.Borrowing.objects.create(
            book=first_book,
            borrower=first_borrower,
        )
        models.Borrowing.objects.create(
            book=first_book,
            borrower=second_borrower,
        )
        models.Borrowing.objects.create(
            book=second_book,
            borrower=first_borrower,
        )

        self.assertEqual(models.Borrowing.objects.count(), 3)

    def test_borrower_can_borrow_same_book_again_after_return(self):
        """Test a returned book/borrower pair can be borrowed again."""
        book = models.Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            total_quantity=1,
        )
        borrower = models.Borrower.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        first_borrowing = models.Borrowing.objects.create(
            book=book,
            borrower=borrower,
        )
        first_borrowing.returned_at = timezone.now()
        first_borrowing.save(update_fields=['returned_at'])

        second_borrowing = models.Borrowing.objects.create(
            book=book,
            borrower=borrower,
        )

        self.assertIsNotNone(first_borrowing.returned_at)
        self.assertIsNone(second_borrowing.returned_at)
        self.assertEqual(
            models.Borrowing.objects.filter(
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
                book = models.Book.objects.create(
                    title=book_title,
                    author='Robert C. Martin',
                    total_quantity=1,
                )
                borrower = models.Borrower.objects.create(
                    name='John Doe',
                    email=borrower_email,
                )
                borrowing = models.Borrowing.objects.create(
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
                book = models.Book.objects.create(
                    title=book_title,
                    author='Robert C. Martin',
                    total_quantity=1,
                )
                borrower = models.Borrower.objects.create(
                    name='John Doe',
                    email=borrower_email,
                )
                borrowing = models.Borrowing.objects.create(
                    book=book,
                    borrower=borrower,
                )
                if is_returned:
                    borrowing.returned_at = timezone.now()
                    borrowing.save(update_fields=['returned_at'])

                with self.assertRaises(ProtectedError):
                    borrower.delete()
