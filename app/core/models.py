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


class Borrower(models.Model):
    """A library borrower."""

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    def save(self, *args, **kwargs):
        """Normalize borrower fields before saving."""
        self.name = self.name.strip()
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


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