# Library Management API

A minimal REST API for managing books and library borrowings, built using Django and Django REST Framework.

The application allows a librarian to manage books and borrowers, borrow and return books, and track book availability.

## Tech Stack

- Python 3.13
- Django 5.2
- Django REST Framework
- PostgreSQL
- Docker
- Docker Compose
- drf-spectacular for OpenAPI documentation

## Features

The API will support:

- Adding, viewing, updating, deleting, and filtering books
- Managing borrowers
- Borrowing and returning books
- Tracking borrowing history
- Preventing a borrower from borrowing the same book more than once at a time
- Preventing borrowing when no copies are available
- OpenAPI documentation
- Automated tests
- Sample library data through fixtures

Authentication and purchasing are outside the scope of this project.

## Project Setup

### Prerequisites

Make sure the following are installed:

- Docker
- Docker Compose
- Git

No local Python or PostgreSQL installation is required.

### Clone the Repository

```bash
git clone <repository-url>
cd library_api
```

### Build the Application

```bash
docker compose build
```

### Run the Application

```bash
docker compose up
```

The API will be available at:

```text
http://localhost:8000/
```

To stop the application:

```bash
docker compose down
```

## Database

PostgreSQL runs as a separate Docker Compose service.

Database migrations are applied when the application starts.

To run migrations manually:

```bash
docker compose run --rm app sh -c "python manage.py migrate"
```

## Running Tests

Run all automated tests:

```bash
docker compose run --rm app sh -c "python manage.py test"
```

Run Django system checks:

```bash
docker compose run --rm app sh -c "python manage.py check"
```

## Linting

Run Flake8:

```bash
docker compose run --rm app sh -c "flake8"
```

## API Overview

The API is organised around three main resources:

- Books
- Borrowers
- Borrowings

Books can be listed, filtered, created, updated, and deleted.

Borrowers can be created and listed.

Borrowings represent a borrower borrowing a book. A borrowing is active until the book is returned.

Detailed endpoint documentation will be available through the OpenAPI documentation.

## API Documentation

OpenAPI documentation is generated using `drf-spectacular`. With the application running:

- Interactive Swagger UI: <http://localhost:8000/api/docs/>
- OpenAPI schema: <http://localhost:8000/api/schema/>

Validate the generated schema with Docker Compose:

```bash
docker compose run --rm app sh -c "python manage.py spectacular --validate"
```

## Library Fixture

A minimal `library-data` fixture provides 3 books, 2 borrowers, and 3
borrowings. It includes active and returned history, a fully borrowed book,
and a zero-quantity book.

Load it into a clean database using:

```bash
docker compose run --rm app sh -c "python manage.py loaddata library-data"
```

The fixture uses fixed primary keys to connect its records. Loading it into a
populated database can update existing records with matching IDs; do not load
it into a database containing data you want to preserve.

## Useful Commands

### Create migrations

```bash
docker compose run --rm app sh -c "python manage.py makemigrations"
```

### Apply migrations

```bash
docker compose run --rm app sh -c "python manage.py migrate"
```

### Run tests

```bash
docker compose run --rm app sh -c "python manage.py test"
```

### Run linting

```bash
docker compose run --rm app sh -c "flake8"
```

### Run Django checks

```bash
docker compose run --rm app sh -c "python manage.py check"
```

### Wait for the database

```bash
docker compose run --rm app sh -c "python manage.py wait_for_db"
```

## Development

Application source code is stored inside the `app/` directory and is mounted into the Docker development container.

Changes made locally are therefore reflected inside the running container without rebuilding the image for every code change.
