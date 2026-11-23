from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from borrowers.models import Borrower


def borrowers_url():
    """Return the URL for the borrower list and create endpoints."""
    return reverse('borrowers:borrower-list')


def create_borrower(**params):
    """Create and return a sample borrower."""
    data = {
        'name': 'John Doe',
        'email': 'john@example.com',
    }
    data.update(params)
    return Borrower.objects.create(**data)


class BorrowerListAPITests(APITestCase):
    """Tests for listing and creating borrowers."""

    def test_list_borrowers(self):
        """Test the list response contains all borrowers and expected fields."""
        first_borrower = create_borrower()
        second_borrower = create_borrower(
            name='Jane Doe',
            email='jane@example.com',
        )

        response = self.client.get(borrowers_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            response.data,
            [
                {
                    'id': first_borrower.id,
                    'name': first_borrower.name,
                    'email': first_borrower.email,
                },
                {
                    'id': second_borrower.id,
                    'name': second_borrower.name,
                    'email': second_borrower.email,
                },
            ],
        )

    def test_list_borrowers_returns_empty_list_when_none_exist(self):
        """Test listing borrowers with no records returns an empty list."""
        response = self.client.get(borrowers_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_create_borrower(self):
        """Test creating a borrower returns the ED response fields."""
        payload = {
            'name': 'John Doe',
            'email': 'john@example.com',
        }

        response = self.client.post(
            borrowers_url(),
            payload,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        borrower = Borrower.objects.get(pk=response.data['id'])
        self.assertEqual(
            response.data,
            {
                'id': borrower.id,
                'name': payload['name'],
                'email': payload['email'],
            },
        )

    def test_create_borrower_requires_name_and_email(self):
        """Test name and email are required."""
        valid_payload = {
            'name': 'John Doe',
            'email': 'john@example.com',
        }

        for field in valid_payload:
            with self.subTest(field=field):
                payload = valid_payload.copy()
                del payload[field]
                response = self.client.post(
                    borrowers_url(),
                    payload,
                    format='json',
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn(field, response.data)

    def test_create_borrower_rejects_blank_name_or_email(self):
        """Test name and email cannot be blank."""
        invalid_fields = (
            ('name', ''),
            ('name', '   '),
            ('email', ''),
        )

        for field, value in invalid_fields:
            with self.subTest(field=field, value=value):
                response = self.client.post(
                    borrowers_url(),
                    {
                        'name': 'John Doe',
                        'email': 'john@example.com',
                        field: value,
                    },
                    format='json',
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn(field, response.data)

    def test_create_borrower_rejects_invalid_email(self):
        """Test an invalid email returns a validation error."""
        response = self.client.post(
            borrowers_url(),
            {
                'name': 'John Doe',
                'email': 'not-an-email',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_create_borrower_stores_email_lowercase(self):
        """Test mixed-case email is stored and returned lowercase."""
        response = self.client.post(
            borrowers_url(),
            {
                'name': 'John Doe',
                'email': 'John.Doe@Example.COM',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        borrower = Borrower.objects.get(pk=response.data['id'])
        self.assertEqual(response.data['email'], 'john.doe@example.com')
        self.assertEqual(borrower.email, 'john.doe@example.com')

    def test_create_duplicate_email_returns_conflict(self):
        """Test exact- and mixed-case duplicate emails return HTTP 409."""
        create_borrower(email='john@example.com')
        duplicate_emails = (
            'john@example.com',
            'JOHN@example.com',
        )

        for email in duplicate_emails:
            with self.subTest(email=email):
                response = self.client.post(
                    borrowers_url(),
                    {
                        'name': 'Another Person',
                        'email': email,
                    },
                    format='json',
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_409_CONFLICT,
                )
                self.assertEqual(
                    response.data['detail'],
                    'A borrower with this email already exists.',
                )
