from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Book, Borrower, Borrowing


def borrowings_url():
    """Return the URL for the borrowing list and create endpoints."""
    return reverse('borrowings:borrowing-list')


def borrowing_return_url(borrowing_id):
    """Return the URL for returning a borrowing."""
    return reverse('borrowings:borrowing-return', args=[borrowing_id])


def create_book(**params):
    """Create and return a sample book."""
    data = {
        'title': 'Clean Code',
        'author': 'Robert C. Martin',
        'total_quantity': 3,
    }
    data.update(params)
    return Book.objects.create(**data)


def create_borrower(**params):
    """Create and return a sample borrower."""
    data = {
        'name': 'John Doe',
        'email': 'john@example.com',
    }
    data.update(params)
    return Borrower.objects.create(**data)


def create_borrowing(book, borrower, returned_at=None):
    """Create and return a borrowing for the given book and borrower."""
    return Borrowing.objects.create(
        book=book, borrower=borrower, returned_at=returned_at,
    )


class BorrowingListAPITests(APITestCase):
    """Tests for listing, creating, and returning borrowings."""

    def test_list_borrowings_returns_active_and_returned(self):
        """Test the nested list response for active and returned records."""
        book = create_book()
        active_borrower = create_borrower()
        returned_borrower = create_borrower(
            name='Jane Doe',
            email='jane@example.com',
        )
        active = create_borrowing(book, active_borrower)
        returned = create_borrowing(
            book,
            returned_borrower,
            returned_at=timezone.now(),
        )

        response = self.client.get(borrowings_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = {item['id']: item for item in response.data}
        self.assertEqual(set(records), {active.id, returned.id})
        expected_book = {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'total_quantity': book.total_quantity,
            'available_quantity': 2,
        }
        fields = {'id', 'book', 'borrower', 'borrowed_at', 'returned_at'}
        for borrowing, borrower in (
            (active, active_borrower),
            (returned, returned_borrower),
        ):
            item = records[borrowing.id]
            self.assertEqual(set(item), fields)
            self.assertEqual(item['book'], expected_book)
            self.assertEqual(
                item['borrower'],
                {
                    'id': borrower.id,
                    'name': borrower.name,
                    'email': borrower.email,
                },
            )
            self.assertTrue(item['borrowed_at'])
            self.assertEqual(
                item['returned_at'] is not None,
                borrowing.returned_at is not None,
            )

    def test_list_borrowings_filters(self):
        """Test ID/status filters and one combined filter."""
        first_book = create_book()
        second_book = create_book(
            title='Dune',
            author='Frank Herbert',
        )
        first_borrower = create_borrower()
        second_borrower = create_borrower(
            name='Jane Doe',
            email='jane@example.com',
        )
        active_pair = create_borrowing(first_book, first_borrower)
        returned_pair = create_borrowing(
            first_book,
            first_borrower,
            returned_at=timezone.now(),
        )
        returned_other = create_borrowing(
            first_book,
            second_borrower,
            returned_at=timezone.now(),
        )
        active_other_book = create_borrowing(second_book, first_borrower)

        cases = (
            ({'book': first_book.id}, [active_pair, returned_pair,
                                       returned_other]),
            ({'borrower': first_borrower.id}, [active_pair, returned_pair,
                                                active_other_book]),
            ({'active': 'true'}, [active_pair, active_other_book]),
            ({'active': 'false'}, [returned_pair, returned_other]),
            (
                {
                    'book': first_book.id,
                    'borrower': first_borrower.id,
                    'active': 'true',
                },
                [active_pair],
            ),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                response = self.client.get(borrowings_url(), query)
                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )
                self.assertCountEqual(
                    [item['id'] for item in response.data],
                    [borrowing.id for borrowing in expected],
                )

        invalid_response = self.client.get(
            borrowings_url(),
            {'book': 'not-an-id'},
        )
        self.assertEqual(
            invalid_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_borrow_return_and_borrow_again(self):
        """Test lifecycle responses, persisted state, and availability."""
        book = create_book(total_quantity=1)
        borrower = create_borrower()
        payload = {'book_id': book.id, 'borrower_id': borrower.id}

        first_response = self.client.post(
            borrowings_url(),
            payload,
            format='json',
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        first = Borrowing.objects.get(pk=first_response.data['id'])
        self.assertEqual(
            first_response.data,
            {
                'id': first.id,
                'book': {
                    'id': book.id,
                    'title': book.title,
                    'author': book.author,
                    'total_quantity': 1,
                    'available_quantity': 0,
                },
                'borrower': {
                    'id': borrower.id,
                    'name': borrower.name,
                    'email': borrower.email,
                },
                'borrowed_at': first_response.data['borrowed_at'],
                'returned_at': None,
            },
        )
        self.assertTrue(first.borrowed_at)
        self.assertTrue(first_response.data['borrowed_at'])
        self.assertIsNone(first.returned_at)

        return_response = self.client.post(
            borrowing_return_url(first.id),
        )

        self.assertEqual(return_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(return_response.data),
            {'id', 'book', 'borrower', 'borrowed_at', 'returned_at'},
        )
        self.assertEqual(return_response.data['id'], first.id)
        self.assertEqual(
            return_response.data['book']['available_quantity'],
            1,
        )
        self.assertIsNotNone(return_response.data['returned_at'])
        first.refresh_from_db()
        self.assertIsNotNone(first.returned_at)

        second_response = self.client.post(
            borrowings_url(),
            payload,
            format='json',
        )

        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        second = Borrowing.objects.get(pk=second_response.data['id'])
        self.assertNotEqual(second.id, first.id)
        self.assertIsNone(second.returned_at)
        self.assertIsNotNone(first.returned_at)
        self.assertEqual(
            second_response.data['book']['available_quantity'],
            0,
        )

    def test_create_requires_valid_ids(self):
        """Test missing and malformed request IDs return 400."""
        book = create_book()
        borrower = create_borrower()
        valid_payload = {'book_id': book.id, 'borrower_id': borrower.id}
        cases = (
            ('book_id', None, True),
            ('borrower_id', None, True),
            ('book_id', 'not-an-id', False),
            ('borrower_id', 'not-an-id', False),
        )

        for field, value, missing in cases:
            with self.subTest(field=field, value=value, missing=missing):
                payload = valid_payload.copy()
                if missing:
                    del payload[field]
                else:
                    payload[field] = value
                response = self.client.post(
                    borrowings_url(),
                    payload,
                    format='json',
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn(field, response.data)

        self.assertEqual(Borrowing.objects.count(), 0)

    def test_create_with_nonexistent_reference_returns_not_found(self):
        """Test nonexistent Book or Borrower references return 404."""
        book = create_book()
        borrower = create_borrower()
        cases = (
            {'book_id': 999999, 'borrower_id': borrower.id},
            {'book_id': book.id, 'borrower_id': 999999},
        )

        for payload in cases:
            with self.subTest(payload=payload):
                response = self.client.post(
                    borrowings_url(),
                    payload,
                    format='json',
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_404_NOT_FOUND,
                )

        self.assertEqual(Borrowing.objects.count(), 0)

    def test_create_when_book_is_out_of_stock_returns_conflict(self):
        """Test an unavailable Book cannot acquire another active record."""
        book = create_book(total_quantity=1)
        existing = create_borrowing(book, create_borrower())
        borrower = create_borrower(
            name='Jane Doe',
            email='jane@example.com',
        )

        response = self.client.post(
            borrowings_url(),
            {'book_id': book.id, 'borrower_id': borrower.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Borrowing.objects.count(), 1)
        existing.refresh_from_db()
        self.assertIsNone(existing.returned_at)

    def test_duplicate_active_borrowing_returns_conflict(self):
        """Test a second active borrowing for the same pair returns 409."""
        book = create_book(total_quantity=2)
        borrower = create_borrower()
        existing = create_borrowing(book, borrower)

        response = self.client.post(
            borrowings_url(),
            {'book_id': book.id, 'borrower_id': borrower.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Borrowing.objects.count(), 1)
        existing.refresh_from_db()
        self.assertIsNone(existing.returned_at)

    def test_return_unknown_or_already_returned_borrowing(self):
        """Test unknown returns return 404 and repeated returns return 409."""
        returned_at = timezone.now()
        borrowing = create_borrowing(
            create_book(),
            create_borrower(),
            returned_at=returned_at,
        )

        unknown_response = self.client.post(borrowing_return_url(999999))
        repeat_response = self.client.post(
            borrowing_return_url(borrowing.id),
        )

        self.assertEqual(
            unknown_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            repeat_response.status_code,
            status.HTTP_409_CONFLICT,
        )
        borrowing.refresh_from_db()
        self.assertEqual(borrowing.returned_at, returned_at)
