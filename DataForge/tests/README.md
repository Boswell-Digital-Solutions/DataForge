# DataForge Test Suite

Comprehensive test suite for DataForge knowledge base management system.

## Overview

The test suite is organized into three main categories:

- **Unit Tests** (`test_unit/`): Fast tests for individual functions and classes
- **Integration Tests** (`test_integration/`): Tests with database interactions
- **API Tests** (`test_api/`): End-to-end API endpoint tests

## Quick Start

### Install Test Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

Or use the test runner script:

```bash
chmod +x run_tests.sh
./run_tests.sh
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest tests/test_unit/ -v

# Integration tests
pytest tests/test_integration/ -v

# API tests
pytest tests/test_api/ -v
```

### Run Tests by Marker

```bash
# Authentication tests
pytest -m auth -v

# Search functionality tests
pytest -m search -v

# Admin API tests
pytest -m admin -v

# Embedding tests
pytest -m embeddings -v
```

## Test Coverage

Generate coverage report:

```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

View HTML coverage report:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── test_unit/                     # Unit tests
│   ├── test_auth.py              # Authentication utilities
│   ├── test_models.py            # Database models
│   ├── test_rate_limit.py        # Rate limiting
│   └── test_embeddings.py        # Text chunking and embeddings
├── test_integration/              # Integration tests
│   └── test_crud_operations.py   # CRUD operations with database
└── test_api/                      # API endpoint tests
    ├── test_auth_endpoints.py    # /auth/* endpoints
    ├── test_admin_endpoints.py   # /admin/* endpoints
    ├── test_search_endpoints.py  # /api/search endpoints
    └── test_health_endpoints.py  # Health and info endpoints
```

## Available Fixtures

### Database Fixtures

- `db`: Fresh database session for each test
- `client`: FastAPI TestClient with database override

### Model Fixtures

- `test_user`: Regular user account
- `test_admin`: Admin user account
- `test_domain`: Test domain
- `test_tag`: Test tag

### Auth Fixtures

- `auth_headers`: Authentication headers for admin user

### Mock Fixtures

- `mock_embedding`: Mock 1536-dimensional embedding vector

## Writing Tests

### Example Unit Test

```python
import pytest
from app.utils.auth import get_password_hash, verify_password

@pytest.mark.unit
def test_password_hashing():
    password = "secret"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
```

### Example API Test

```python
import pytest

@pytest.mark.api
def test_create_domain(client, auth_headers):
    response = client.post(
        "/admin/domains",
        headers=auth_headers,
        json={"id": "test", "label": "Test Domain"}
    )
    assert response.status_code == 200
```

### Example Integration Test

```python
import pytest
from app.api import crud

@pytest.mark.integration
def test_create_domain(db):
    domain = crud.create_domain(db, domain_data)
    assert domain.id == "test"
```

## Test Markers

Available pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (database required)
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.search` - Search functionality tests
- `@pytest.mark.admin` - Admin API tests
- `@pytest.mark.embeddings` - Embedding generation tests
- `@pytest.mark.slow` - Slow tests

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=app
```

## Troubleshooting

### SQLite vs PostgreSQL

Tests use SQLite in-memory database for speed. Some PostgreSQL-specific features (like pgvector) are mocked in tests.

### Async Tests

Some tests use `pytest-asyncio` for async functions:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Mocking External APIs

Embedding API calls are mocked to avoid requiring API keys:

```python
from unittest.mock import patch

@patch('app.utils.embeddings.generate_embedding')
async def test_search(mock_embed, client):
    mock_embed.return_value = [0.1] * 1536
    # Test code here
```

## Best Practices

1. **Keep tests isolated**: Each test should be independent
2. **Use fixtures**: Reuse common setup code
3. **Mock external services**: Don't call real APIs in tests
4. **Test edge cases**: Empty inputs, invalid data, etc.
5. **Clear test names**: Describe what is being tested
6. **Fast tests**: Unit tests should run in milliseconds

## Coverage Goals

- **Overall**: > 80%
- **Critical paths**: > 90% (auth, search, CRUD)
- **Utilities**: > 85%

## Running Tests in Docker

```bash
docker-compose exec dataforge pytest
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)

