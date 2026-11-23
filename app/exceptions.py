from rest_framework import status
from rest_framework.exceptions import APIException


class ConflictAPIException(APIException):
    """Base exception for API conflicts."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The request conflicts with the current state.'
    default_code = 'conflict'
