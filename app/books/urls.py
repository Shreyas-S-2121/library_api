from django.urls import path

from books.views import BookDetailView, BookListCreateView

app_name = 'books'

urlpatterns = [
    path('', BookListCreateView.as_view(), name='book-list'),
    path('<int:pk>/', BookDetailView.as_view(), name='book-detail'),
]
