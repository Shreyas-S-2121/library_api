from rest_framework import generics

from borrowers.models import Borrower
from borrowers.serializers import BorrowerSerializer


class BorrowerListCreateView(generics.ListCreateAPIView):
    """List borrowers or create a borrower."""

    queryset = Borrower.objects.all()
    serializer_class = BorrowerSerializer
