from django.db import models


class Book(models.Model):
    """A book held by the library."""

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    total_quantity = models.IntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_quantity__gte=0),
                name='book_total_qty_nonnegative',
            ),
            models.UniqueConstraint(
                fields=('title', 'author'),
                name='book_title_author_unique',
            ),
        ]