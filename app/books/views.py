from django.db import transaction
from django.db.models import Count, F, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view

from books.models import Book
from books.serializers import BookReadSerializer, BookWriteSerializer
from borrowings.exceptions import BookBorrowingConflict


#to make the optional filtering query params appear in swagger UI and docs
@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(
                name='title',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name='author',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name='available',
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
        ],
    ),
)
class BookListCreateView(generics.ListCreateAPIView):
    """List books with optional exact filters, or create a book."""

    queryset = Book.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        filters = {}

        for field in ('title', 'author'):
            value = self.request.query_params.get(field)
            if value is not None:
                filters[f'{field}'] = value

        queryset = queryset.filter(**filters)
        available = self.request.query_params.get('available')
        if available is not None:
            if available not in ('true', 'false'):
                raise ValidationError({
                    'detail': 'available must be either true or false.',
                })

            #available_quantity not in db (or model),
            # so add it to queryset to support fitlering based on availability of book
            queryset = queryset.annotate(
                available_quantity=F('total_quantity') - Count(
                    'borrowing',
                    filter=Q(borrowing__returned_at__isnull=True),
                ),
            )
            if available == 'true':
                queryset = queryset.filter(available_quantity__gt=0)
            else:
                queryset = queryset.filter(available_quantity=0)

        return queryset

    def get_serializer_class(self):
        if self.request.method in ('GET', 'HEAD'):
            return BookReadSerializer
        return BookWriteSerializer


class BookDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, partially update, or delete a book."""

    queryset = Book.objects.all()
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']   #PUT intentionally
                                                                        #not supported

    def get_serializer_class(self):
        if self.request.method in ('GET', 'HEAD'):
            return BookReadSerializer
        return BookWriteSerializer

    def perform_update(self, serializer):

        # Lock the book so quantity updates cannot conflict with new borrowings.
        with transaction.atomic():
            book = get_object_or_404(
                Book.objects.select_for_update(),
                pk=serializer.instance.pk,
            )
            active_count = book.borrowing_set.filter(
                returned_at__isnull=True,
            ).count()
            total_quantity = serializer.validated_data.get(
                'total_quantity',
                book.total_quantity,
            )
            if total_quantity < active_count:
                raise BookBorrowingConflict()

            serializer.instance = book
            serializer.save()

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise BookBorrowingConflict()
