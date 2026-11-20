from rest_framework import generics
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view

from core.models import Book
from books.serializers import BookReadSerializer, BookWriteSerializer

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

        return queryset.filter(**filters)

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
