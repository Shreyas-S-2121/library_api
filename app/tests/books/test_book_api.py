from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book
from borrowings.models import Borrowing
from tests.helpers import create_book, create_borrower, create_borrowing


def books_url():
    """Return the URL for the book list and create endpoints."""
    return reverse('books:book-list')


def book_detail_url(book_id):
    """Return the URL for a book detail endpoint."""
    return reverse('books:book-detail', args=[book_id])

class BookListAPITests(APITestCase):
    """Tests for listing and creating books."""

    def test_list_books(self):
        """Test the list response fields and values."""
        book = create_book()

        response = self.client.get(books_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            [
                {
                    'id': book.id,
                    'title': book.title,
                    'author': book.author,
                    'total_quantity': book.total_quantity,
                    'available_quantity': book.total_quantity,
                },
            ],
        )

    def test_list_books_filters_by_exact_title(self):
        """Test title filtering uses exact matching."""
        matching_book = create_book()
        create_book(title='Clean Code Complete')

        response = self.client.get(books_url(), {'title': 'Clean Code'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book_ids = [book['id'] for book in response.data]
        self.assertEqual(book_ids, [matching_book.id])

    def test_list_books_filters_by_exact_author(self):
        """Test author filtering uses exact matching."""
        matching_book = create_book()
        create_book(author='Robert C. Martinez')

        response = self.client.get(
            books_url(),
            {'author': 'Robert C. Martin'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book_ids = [book['id'] for book in response.data]
        self.assertEqual(book_ids, [matching_book.id])

    def test_list_books_combines_title_and_author_filters(self):
        """Test title and author filters are both applied."""
        matching_book = create_book()
        create_book(author='Another Author')
        create_book(title='Another Book')

        response = self.client.get(
            books_url(),
            {'title': 'Clean Code', 'author': 'Robert C. Martin'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book_ids = [book['id'] for book in response.data]
        self.assertEqual(book_ids, [matching_book.id])

    def test_list_books_filters_by_availability(self):
        """Test true and false availability filters."""
        available_book = create_book(
            title='Available Book',
            total_quantity=2,
        )
        unavailable_book = create_book(
            title='Unavailable Book',
            total_quantity=1,
        )
        zero_quantity_book = create_book(
            title='Empty Book',
            total_quantity=0,
        )
        borrower = create_borrower()
        create_borrowing(unavailable_book, borrower)

        for value, expected_ids in (
            ('true', [available_book.id]),
            ('false', [unavailable_book.id, zero_quantity_book.id]),
        ):
            with self.subTest(available=value):
                response = self.client.get(
                    books_url(),
                    {'available': value},
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertCountEqual(
                    [item['id'] for item in response.data],
                    expected_ids,
                )

    def test_list_books_combines_availability_with_title_and_author(self):
        """Test availability combines with the exact title/author filters."""
        target_book = create_book(total_quantity=1)
        create_book(
            title='Clean Code',
            author='Another Author',
            total_quantity=2,
        )
        create_book(
            title='Another Book',
            total_quantity=2,
        )
        borrower = create_borrower()
        create_borrowing(target_book, borrower)

        for value, expected_ids in (
            ('true', []),
            ('false', [target_book.id]),
        ):
            with self.subTest(available=value):
                response = self.client.get(
                    books_url(),
                    {
                        'title': 'Clean Code',
                        'author': 'Robert C. Martin',
                        'available': value,
                    },
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    [item['id'] for item in response.data],
                    expected_ids,
                )

    def test_list_books_rejects_invalid_availability(self):
        """Test an invalid availability value returns 400."""
        response = self.client.get(books_url(), {'available': 'maybe'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['detail'],
            'available must be either true or false.',
        )

    def test_create_book(self):
        """Test creating a book returns the ED write-response fields."""
        payload = {
            'title': 'Clean Code',
            'author': 'Robert C. Martin',
            'total_quantity': 5,
        }

        response = self.client.post(books_url(), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        book = Book.objects.get(
            title=payload['title'],
            author=payload['author'],
        )
        self.assertEqual(
            response.data,
            {
                'id': book.id,
                'title': payload['title'],
                'author': payload['author'],
                'total_quantity': payload['total_quantity'],
            },
        )
        self.assertEqual(book.total_quantity, payload['total_quantity'])

    def test_create_book_with_zero_quantity(self):
        """Test that creating a book with zero copies succeeds."""
        response = self.client.post(
            books_url(),
            {
                'title': 'Clean Code',
                'author': 'Robert C. Martin',
                'total_quantity': 0,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        book = Book.objects.get(
            title='Clean Code',
            author='Robert C. Martin',
        )
        self.assertEqual(book.total_quantity, 0)

    def test_create_book_requires_all_fields(self):
        """Test title, author, and total quantity are required."""
        valid_payload = {
            'title': 'Clean Code',
            'author': 'Robert C. Martin',
            'total_quantity': 5,
        }

        for field in valid_payload:
            with self.subTest(field=field):
                payload = valid_payload.copy()
                del payload[field]
                response = self.client.post(
                    books_url(),
                    payload,
                    format='json',
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn(field, response.data)

    def test_create_book_rejects_blank_title_or_author(self):
        """Test title and author cannot be blank."""
        for field in ('title', 'author'):
            with self.subTest(field=field):
                response = self.client.post(
                    books_url(),
                    {
                        'title': 'Clean Code',
                        'author': 'Robert C. Martin',
                        'total_quantity': 5,
                        field: '',
                    },
                    format='json',
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn(field, response.data)

    def test_create_book_rejects_negative_or_non_integer_quantity(self):
        """Test total quantity must be an integer greater than or equal to zero."""
        for quantity in (-1, 'not-an-integer'):
            with self.subTest(quantity=quantity):
                response = self.client.post(
                    books_url(),
                    {
                        'title': 'Clean Code',
                        'author': 'Robert C. Martin',
                        'total_quantity': quantity,
                    },
                    format='json',
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn('total_quantity', response.data)

    def test_create_book_rejects_fractional_quantity(self):
        """Test total quantity does not accept a fractional number."""
        response = self.client.post(
            books_url(),
            {
                'title': 'Clean Code',
                'author': 'Robert C. Martin',
                'total_quantity': 1.5,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('total_quantity', response.data)

    def test_create_duplicate_title_and_author_returns_conflict(self):
        """Test a duplicate title/author pair returns HTTP 409."""
        create_book()

        response = self.client.post(
            books_url(),
            {
                'title': 'Clean Code',
                'author': 'Robert C. Martin',
                'total_quantity': 3,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_rejects_available_quantity(self):
        """Test clients cannot provide the derived available quantity."""
        response = self.client.post(
            books_url(),
            {
                'title': 'Clean Code',
                'author': 'Robert C. Martin',
                'total_quantity': 5,
                'available_quantity': 2,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('available_quantity', response.data)


class BookDetailAPITests(APITestCase):
    """Tests for retrieving, updating, and deleting a book."""

    def test_retrieve_book_returns_exact_fields(self):
        """Test the detail response has exactly the ED fields and values."""
        book = create_book()

        response = self.client.get(book_detail_url(book.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                'id': book.id,
                'title': 'Clean Code',
                'author': 'Robert C. Martin',
                'total_quantity': 5,
                'available_quantity': 5,
            },
        )

    def test_retrieve_missing_book_returns_not_found(self):
        """Test retrieving an unknown book returns 404."""
        response = self.client.get(book_detail_url(999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_only_total_quantity_returns_success(self):
        """Test updating only quantity succeeds without a false duplicate."""
        book = create_book()

        response = self.client.patch(
            book_detail_url(book.id),
            {'total_quantity': 7},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'total_quantity': 7,
            },
        )
        book.refresh_from_db()
        self.assertEqual(book.total_quantity, 7)

    def test_patch_empty_data_returns_bad_request(self):
        """Test an empty PATCH returns 400."""
        book = create_book()

        response = self.client.patch(
            book_detail_url(book.id),
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_book_rejects_invalid_input(self):
        """Test PATCH rejects blank title/author and invalid quantity."""
        book = create_book()
        invalid_payloads = [
            {'title': ''},
            {'author': ''},
            {'total_quantity': -1},
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.patch(
                    book_detail_url(book.id),
                    payload,
                    format='json',
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn(next(iter(payload)), response.data)

    def test_patch_duplicate_title_and_author_returns_conflict(self):
        """Test updating to another book's pair returns HTTP 409."""
        book = create_book()
        other_book = create_book(
            title='The Clean Coder',
            author='Robert C. Martin',
        )

        response = self.client.patch(
            book_detail_url(book.id),
            {
                'title': other_book.title,
                'author': other_book.author,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_patch_rejects_available_quantity(self):
        """Test clients cannot update the derived available quantity."""
        book = create_book()

        response = self.client.patch(
            book_detail_url(book.id),
            {'available_quantity': 2},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('available_quantity', response.data)

    def test_patch_missing_book_returns_not_found(self):
        """Test updating an unknown book returns 404."""
        response = self.client.patch(
            book_detail_url(999),
            {'total_quantity': 7},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_book(self):
        """Test deleting a book returns 204 and removes it."""
        book = create_book()

        response = self.client.delete(book_detail_url(book.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(pk=book.id).exists())

    def test_delete_missing_book_returns_not_found(self):
        """Test deleting an unknown book returns 404."""
        response = self.client.delete(book_detail_url(999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_is_not_supported(self):
        """Test the API does not expose a full-update endpoint."""
        book = create_book()

        response = self.client.put(
            book_detail_url(book.id),
            {
                'title': 'Clean Code',
                'author': 'Robert C. Martin',
                'total_quantity': 5,
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_availability_counts_only_active_borrowings(self):
        """Test active borrowings affect availability in list and detail."""
        book = create_book(total_quantity=3)
        active_borrower = create_borrower()
        returned_borrower = create_borrower(
            name='Jane Doe',
            email='jane@example.com',
        )
        create_borrowing(book, active_borrower)
        create_borrowing(
            book,
            returned_borrower,
            returned_at=timezone.now(),
        )

        list_response = self.client.get(books_url())
        detail_response = self.client.get(book_detail_url(book.id))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        listed_book = next(
            item for item in list_response.data if item['id'] == book.id
        )
        self.assertEqual(listed_book['available_quantity'], 2)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['available_quantity'], 2)

    def test_quantity_cannot_fall_below_active_borrowings(self):
        """Test quantity cannot drop below, but may equal, active loans."""
        book = create_book(total_quantity=2)
        borrowers = (
            create_borrower(),
            create_borrower(name='Jane Doe', email='jane@example.com'),
        )
        for borrower in borrowers:
            create_borrowing(book, borrower)

        response = self.client.patch(
            book_detail_url(book.id),
            {'total_quantity': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        book.refresh_from_db()
        self.assertEqual(book.total_quantity, 2)

        response = self.client.patch(
            book_detail_url(book.id),
            {'total_quantity': 2},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book.refresh_from_db()
        self.assertEqual(book.total_quantity, 2)

    def test_delete_with_active_or_returned_borrowing_returns_conflict(self):
        """Test either type of borrowing history protects a Book."""
        histories = (
            ('Active Book', 'john@example.com', None),
            ('Returned Book', 'jane@example.com', timezone.now()),
        )
        for title, email, returned_at in histories:
            with self.subTest(returned=returned_at is not None):
                book = create_book(title=title, total_quantity=1)
                borrower = create_borrower(
                    name='Jane Doe',
                    email=email,
                )
                borrowing = create_borrowing(
                    book=book,
                    borrower=borrower,
                    returned_at=returned_at,
                )

                response = self.client.delete(book_detail_url(book.id))

                self.assertEqual(
                    response.status_code,
                    status.HTTP_409_CONFLICT,
                )
                self.assertTrue(Book.objects.filter(pk=book.id).exists())
                self.assertTrue(
                    Borrowing.objects.filter(pk=borrowing.id).exists(),
                )
