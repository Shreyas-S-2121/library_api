from rest_framework import serializers
from rest_framework.exceptions import NotFound

from books.serializers import BookReadSerializer
from borrowers.serializers import BorrowerSerializer
from books.models import Book
from borrowers.models import Borrower
from borrowings.models import Borrowing


class BorrowingReadSerializer(serializers.ModelSerializer):
    """Serializer for nested borrowing response data."""

    #include full book and borrower objects in response
    book = BookReadSerializer(read_only=True)
    borrower = BorrowerSerializer(read_only=True)

    class Meta:
        model = Borrowing
        fields = ['id', 'book', 'borrower', 'borrowed_at', 'returned_at']


class BorrowingCreateSerializer(serializers.Serializer):
    """Validate borrowing references and create a borrowing record."""

    book_id = serializers.IntegerField(source='book', write_only=True)
    borrower_id = serializers.IntegerField(
        source='borrower',
        write_only=True,
    )

    def validate_book_id(self, value):
        try:
            return Book.objects.get(pk=value)
        except Book.DoesNotExist:
            raise NotFound('Book not found.')

    def validate_borrower_id(self, value):
        try:
            return Borrower.objects.get(pk=value)
        except Borrower.DoesNotExist:
            raise NotFound('Borrower not found.')

    def create(self, validated_data):
        return Borrowing.objects.create(**validated_data)
