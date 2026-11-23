from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from borrowers.models import Borrower


class BorrowerModelTests(TestCase):
    """Tests for the Borrower model."""

    def test_create_borrower(self):
        """Test creating a borrower with valid data."""
        borrower = Borrower.objects.create(
            name='John Doe',
            email='john@example.com',
        )

        self.assertIsNotNone(borrower.pk)
        self.assertEqual(borrower.name, 'John Doe')
        self.assertEqual(borrower.email, 'john@example.com')

    def test_borrower_email_is_stored_lowercase(self):
        """Test a mixed-case email is stored in lowercase."""
        borrower = Borrower.objects.create(
            name='John Doe',
            email='John.Doe@Example.COM',
        )

        self.assertEqual(borrower.email, 'john.doe@example.com')

    def test_borrower_name_and_email_are_trimmed(self):
        """Test surrounding whitespace is stripped from borrower fields."""
        borrower = Borrower.objects.create(
            name='  John Doe  ',
            email='  John.Doe@Example.COM  ',
        )

        self.assertEqual(borrower.name, 'John Doe')
        self.assertEqual(borrower.email, 'john.doe@example.com')

    def test_blank_name_or_email_is_rejected(self):
        """Test full validation rejects blank names and emails."""
        for field in ('name', 'email'):
            with self.subTest(field=field):
                borrower = Borrower(
                    name='John Doe',
                    email='john@example.com',
                )
                setattr(borrower, field, '')

                with self.assertRaises(ValidationError):
                    borrower.full_clean()

    def test_invalid_email_is_rejected(self):
        """Test full validation identifies an invalid email."""
        borrower = Borrower(
            name='John Doe',
            email='not-an-email',
        )

        with self.assertRaises(ValidationError) as context:
            borrower.full_clean()

        self.assertIn('email', context.exception.message_dict)

    def test_duplicate_email_is_rejected(self):
        """Test normalized duplicate emails violate database uniqueness."""
        Borrower.objects.create(
            name='John Doe',
            email='JOHN@example.com',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Borrower.objects.create(
                    name='Another Person',
                    email='john@example.com',
                )
