from django.db import models


class Borrower(models.Model):
    """A library borrower."""

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    def save(self, *args, **kwargs):
        """Normalize borrower fields before saving."""
        self.name = self.name.strip()
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)
