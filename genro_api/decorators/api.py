"""API-ready decorator for automatic API endpoint generation.

This module provides the @apiready decorator that marks classes and methods for
automatic API endpoint generation with Pydantic-based request/response models.

Example:
    @apiready(path="/storage")  # Mark class as API-ready with base path
    class MyBackend:
        @apiready  # → /storage/read_file
        def read_file(self, path: str, encoding: str = 'utf-8') -> str:
            '''Read file content.'''
            ...

        @apiready(path="/custom", method='POST')  # → /storage/custom
        def delete_file(self, path: str) -> None:
            '''Delete file.'''
            ...
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable, get_type_hints


def apiready(
    target: Callable | None = None,
    *,
    path: str | None = None,
    method: str | None = None
) -> Callable:
    """Decorator to mark classes and methods as API-ready.

    Can be applied to:
    1. Classes: @apiready(path="/storage") - marks class as API-ready with base path
    2. Methods: @apiready or @apiready(path="/custom") - marks method for API exposure

    For classes:
        Sets _api_base_path attribute used by methods to build full endpoint paths.

    For methods:
        Analyzes function signature and type hints to automatically generate
        Pydantic request/response models and HTTP method specifications.
        Methods can only be marked as apiready if their class is also marked.

    Args:
        target: The class or function to decorate
        path: API path (required for classes, optional for methods)
        method: Optional HTTP method for methods ('GET' or 'POST'). If not provided,
               inferred from function name (read*/get*/list* → GET, else POST)

    Returns:
        For classes: Class with _api_base_path attribute set
        For methods: Decorated function with _api_metadata attribute containing:
            - request_fields: Parameter types and defaults
            - return_type: Return type
            - http_method: HTTP method (GET or POST)
            - endpoint_path: Relative path (defaults to function name)
            - docstring: Function documentation

    Usage:
        @apiready(path="/storage")
        class MyBackend:
            @apiready                       # → /storage/read_text
            def read_text(self, path: str) -> str: ...

            @apiready(path="/files")        # → /storage/files
            def list_files(self) -> list: ...

            @apiready(method='POST')        # → /storage/write_text (POST)
            def write_text(self, path: str, content: str) -> None: ...
    """

    def class_decorator(cls: type) -> type:
        """Decorator for classes - sets _api_base_path."""
        if path is None:
            raise ValueError(
                f"@apiready on class {cls.__name__} requires path parameter: "
                f"@apiready(path='/your-path')"
            )
        cls._api_base_path = path
        return cls

    def method_decorator(f: Callable) -> Callable:
        """Decorator for methods - creates API metadata."""
        # Get function signature and type hints
        sig = inspect.signature(f)
        type_hints = get_type_hints(f)

        # Extract return type
        return_type = type_hints.get("return", Any)

        # Build request fields from parameters (skip 'self' and 'cls')
        request_fields = {}
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            # Get type from type hints, default to Any if not specified
            param_type = type_hints.get(param_name, Any)

            # Handle default values
            if param.default is inspect.Parameter.empty:
                # Required parameter
                request_fields[param_name] = (param_type, ...)
            else:
                # Optional parameter with default
                request_fields[param_name] = (param_type, param.default)

        # Infer HTTP method if not provided
        http_method = method
        if http_method is None:
            func_name = f.__name__
            # GET for read-only operations
            if any(
                func_name.startswith(prefix)
                for prefix in ["read", "get", "list", "exists", "is_", "has_"]
            ):
                http_method = "GET"
            else:
                # POST for mutations
                http_method = "POST"

        # Determine endpoint path (relative to class base path)
        endpoint_path = path if path is not None else f"/{f.__name__}"
        if not endpoint_path.startswith("/"):
            endpoint_path = f"/{endpoint_path}"

        # Store metadata on the function
        f._api_metadata = {
            "request_fields": request_fields,
            "return_type": return_type,
            "http_method": http_method,
            "endpoint_path": endpoint_path,  # Relative path
            "docstring": f.__doc__,
        }

        # Preserve original function behavior
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        # Copy metadata to wrapper
        wrapper._api_metadata = f._api_metadata

        return wrapper

    # Determine if decorating a class or a method/function
    if target is None:
        # Called with arguments: @apiready(path="/storage") or @apiready(method='POST')
        # Return a decorator that will be applied to the actual target
        def deferred_decorator(actual_target):
            if inspect.isclass(actual_target):
                return class_decorator(actual_target)
            else:
                return method_decorator(actual_target)
        return deferred_decorator
    else:
        # Called without arguments: @apiready
        # Apply directly to target
        if inspect.isclass(target):
            return class_decorator(target)
        else:
            return method_decorator(target)
