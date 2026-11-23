from exceptions import ConflictAPIException


class BorrowingConflict(ConflictAPIException):
    """Conflict raised when a requested borrowing cannot be completed."""

    default_detail = 'The borrowing conflicts with the current state.'


class BookBorrowingConflict(ConflictAPIException):
    """Conflict raised when a requested change violates borrowing rules."""

    default_detail = 'The requested change conflicts with borrowing records.'
