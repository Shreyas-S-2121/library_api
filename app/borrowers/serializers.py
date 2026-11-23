from rest_framework import serializers
from rest_framework.exceptions import APIException

from borrowers.models import Borrower


class BorrowerConflict(APIException):
    """Conflict raised when a borrower email is already in use."""

    status_code = 409
    default_detail = 'A borrower with this email already exists.'
    default_code = 'conflict'


class BorrowerSerializer(serializers.ModelSerializer):
    """Serializer for borrower response and create data."""

    # Disable DRF's automatic uniqueness validator, which returns 400.
    # Duplicate emails are handled below so they return 409 instead.
    email = serializers.EmailField(validators=[])

    class Meta:
        model = Borrower
        fields = ['id', 'name', 'email']
        read_only_fields = ['id']

    def validate_email(self, value):
        """Reject an email already assigned to a borrower, regardless of case."""
        if Borrower.objects.filter(email__iexact=value).exists():   #case-insensitive
                                                                    #exact match
            raise BorrowerConflict()

        return value
