from django.db import IntegrityError, transaction
from django.test import TestCase

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
