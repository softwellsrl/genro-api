# Genro API

API utilities and FastAPI integration for the Genro framework.

## Status

**Development Status:** Alpha

This package provides tools for building REST APIs with automatic endpoint generation.

## Features

- **@apiready Decorator**: Mark classes and methods for automatic API exposure
- **ApiPublisher** (planned): FastAPI integration for automatic endpoint generation
- **Type-safe**: Leverages Pydantic for automatic validation and schema generation
- **OpenAPI/Swagger**: Automatic API documentation generation

## Installation

```bash
pip install genro-api
```

## Usage

### @apiready Decorator

Mark classes and methods as API-ready:

```python
from genro_api import apiready

@apiready(path="/storage")
class StorageBackend:
    @apiready
    def read_text(self, path: str, encoding: str = 'utf-8') -> str:
        """Read file content."""
        ...

    @apiready(method='POST')
    def write_text(self, path: str, content: str) -> None:
        """Write file content."""
        ...
```

The decorator auto-generates:
- Pydantic request/response models from type hints
- HTTP method detection (GET for read-only, POST for mutations)
- OpenAPI/Swagger documentation
- Input validation

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black genro_api tests

# Lint
ruff genro_api tests
```

## License

MIT License - see LICENSE file for details.

## Links

- [Documentation](https://github.com/genropy/genro-api)
- [Issues](https://github.com/genropy/genro-api/issues)
- [Genro Project](https://github.com/genropy/genro-next-generation)
