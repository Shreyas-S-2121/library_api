from django.db import models

from books.models import Book
from borrowers.models import Borrower


class Borrowing(models.Model):
    """A record of a book borrowed by a borrower."""

    book = models.ForeignKey(Book, on_delete=models.PROTECT)
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT)
    borrowed_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('book', 'borrower'),
                condition=models.Q(returned_at__isnull=True),
                name='borrowing_active_unique',
            ),
        ]
