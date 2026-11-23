from rest_framework import serializers

from books.models import Book
from borrowings.models import Borrowing
from exceptions import ConflictAPIException


class BookConflict(ConflictAPIException):
    """Conflict raised when a title/author pair is already in use.

    DRF returns 400 for validation errors by default. ED stated
    409 Conflict for duplicates, so we raise this custom exception.
    """
    default_detail = 'A book with this title and author already exists.'


class BookReadSerializer(serializers.ModelSerializer):
    """Serializer for book response data."""

    #declare available_quantity field (as its not part of model)
    available_quantity = serializers.SerializerMethodField()

    def get_available_quantity(self, obj):  #get the fields value
        """Return copies not currently borrowed."""
        active_borrowings = Borrowing.objects.filter(
            book=obj,
            returned_at__isnull=True,
        ).count()
        return obj.total_quantity - active_borrowings   #available_quantity of current book

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'author',
            'total_quantity',
            'available_quantity',
        ]


class BookWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating books."""

    total_quantity = serializers.IntegerField(min_value=0)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'total_quantity']
        read_only_fields = ['id']
        validators = []     #disables DRF's automatic unique-together check
                            #so the custom 409 is used

    def to_internal_value(self, data):
        # DRF silently ignores read-only fields by default. Reject
        # available_quantity explicitly so clients get a clear 400.
        if hasattr(data, 'keys') and 'available_quantity' in data:
            raise serializers.ValidationError({
                'available_quantity': 'This field is read-only.',
            })
        return super().to_internal_value(data)

    def validate(self, attrs):
        if self.instance is not None and not attrs:
            raise serializers.ValidationError(
                'At least one editable field must be provided.'
            )

        # On PATCH, fields not sent keep their current values, so fall
        # back to the instance to check the resulting title/author pair.
        title = attrs.get(
            'title',
            self.instance.title if self.instance is not None else None,
        )
        author = attrs.get(
            'author',
            self.instance.author if self.instance is not None else None,
        )

        # Manual duplicate check (replaces DRF's default 400) so that a
        # duplicate title/author pair returns 409 Conflict.
        matching_books = Book.objects.filter(title=title, author=author)
        if self.instance is not None:
            # Exclude the current book when checking for duplicates,
            # otherwise an unchanged title/author would match itself.
            matching_books = matching_books.exclude(pk=self.instance.pk)

        if matching_books.exists():
            raise BookConflict()

        return attrs
