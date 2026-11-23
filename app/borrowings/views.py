from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)

from core.models import Book, Borrowing
from borrowings.serializers import (
    BorrowingCreateSerializer,
    BorrowingReadSerializer,
)


class BorrowingConflict(APIException):
    """Conflict raised when a requested borrowing cannot be completed."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The borrowing conflicts with the current state.'
    default_code = 'conflict'


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(
                name='book',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by Book ID.',
            ),
            OpenApiParameter(
                name='borrower',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by Borrower ID.',
            ),
            OpenApiParameter(
                name='active',
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by active or returned status.',
            ),
        ],
    ),
    post=extend_schema(
        request=BorrowingCreateSerializer,
        responses={status.HTTP_201_CREATED: BorrowingReadSerializer},
    ),
)
class BorrowingListCreateView(generics.ListCreateAPIView):
    """List borrowing history or create an active borrowing."""

    serializer_class = BorrowingReadSerializer

    def get_queryset(self):
        queryset = Borrowing.objects.select_related('book', 'borrower')

        #for filtering by book id or borrower id
        for field in ('book', 'borrower'):
            value = self.request.query_params.get(field)
            if value is not None:
                try:
                    filter_id = int(value)
                except ValueError:
                    raise ValidationError({
                        field: 'A valid integer is required.',
                    })
                queryset = queryset.filter(**{f'{field}_id': filter_id})

        #for filtering by 'active' borrowings
        active = self.request.query_params.get('active')
        if active is not None:
            if active not in ('true', 'false'):
                raise ValidationError({
                    'active': 'active must be either true or false.',
                })
            queryset = queryset.filter(
                returned_at__isnull=(active == 'true'),
            )

        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BorrowingCreateSerializer
        return BorrowingReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        borrower = serializer.validated_data['borrower']

        # Lock the book so concurrent requests cannot borrow beyond stock.
        with transaction.atomic():
            book = get_object_or_404(
                Book.objects.select_for_update(),
                pk=serializer.validated_data['book'].pk,
            )
            active_borrowings = Borrowing.objects.filter(
                book=book,
                returned_at__isnull=True,
            )
            if active_borrowings.filter(borrower=borrower).exists():
                raise BorrowingConflict()
            if active_borrowings.count() >= book.total_quantity:
                raise BorrowingConflict()

            borrowing = serializer.save(book=book)
            borrowing = Borrowing.objects.select_related(
                'book',
                'borrower',
            ).get(pk=borrowing.pk)

        return Response(
            BorrowingReadSerializer(borrowing).data,
            status=status.HTTP_201_CREATED,
        )


class BorrowingReturnView(APIView):
    """Return an active borrowing."""

    @extend_schema(
        request=None,
        responses={status.HTTP_200_OK: BorrowingReadSerializer},
    )
    def post(self, request, pk):
        # Lock the borrowing so concurrent requests cannot return it twice.
        with transaction.atomic():
            borrowing = get_object_or_404(
                Borrowing.objects.select_for_update(),
                pk=pk,
            )
            if borrowing.returned_at is not None:
                raise BorrowingConflict()

            borrowing.returned_at = timezone.now()
            borrowing.save(update_fields=['returned_at'])
            borrowing = Borrowing.objects.select_related(
                'book',
                'borrower',
            ).get(pk=borrowing.pk)

        return Response(BorrowingReadSerializer(borrowing).data)
