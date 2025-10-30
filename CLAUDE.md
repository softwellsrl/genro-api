# Claude Code Instructions - Genro API

**Parent Document**: This project follows all policies from the central [genro-next-generation CLAUDE.md](https://github.com/genropy/genro-next-generation/blob/main/CLAUDE.md)

## Project-Specific Context

### Current Status
- Development Status: Alpha (0.1.0)
- Has Implementation: Yes

### Purpose

Genro API provides utilities for building REST APIs with automatic endpoint generation. This package contains:

1. **@apiready decorator** - Marks classes/methods for API exposure with automatic metadata generation
2. **ApiPublisher** (planned) - FastAPI integration for automatic endpoint creation
3. **GUI tools** (planned) - Tools for building admin interfaces on top of APIs

### Current Features

1. **@apiready decorator** (`genro_api/decorators/api.py`)
   - Class-level: `@apiready(path="/storage")` marks class as API-ready
   - Method-level: `@apiready` or `@apiready(path="/custom", method="POST")`
   - Auto-generates metadata from type hints
   - Infers HTTP method from function name (read*/get*/list* → GET, else POST)
   - Stores endpoint_path, request_fields, return_type, http_method, docstring

### Project-Specific Guidelines

1. **FastAPI Integration**: All API generation must use FastAPI for consistency
2. **Type-Safety First**: Leverage Pydantic for validation and schema generation
3. **Auto-Discovery**: Prefer reflection and metadata over manual configuration
4. **Test Coverage**: Maintain high test coverage for all API generation logic

### Dependencies

- **pydantic>=2.0.0**: Type validation and model generation
- **fastapi>=0.100.0**: Web framework for API generation
- **uvicorn>=0.20.0**: ASGI server for running APIs

---

**All general policies are inherited from the parent document.**
