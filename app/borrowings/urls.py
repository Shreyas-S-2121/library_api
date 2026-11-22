from django.urls import path

from borrowings.views import BorrowingListCreateView, BorrowingReturnView

app_name = 'borrowings'

urlpatterns = [
    path('', BorrowingListCreateView.as_view(), name='borrowing-list'),
    path(
        '<int:pk>/return/',
        BorrowingReturnView.as_view(),
        name='borrowing-return',
    ),
]
