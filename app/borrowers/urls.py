from django.urls import path

from borrowers.views import BorrowerListCreateView

app_name = 'borrowers'

urlpatterns = [
    path('', BorrowerListCreateView.as_view(), name='borrower-list'),
]
