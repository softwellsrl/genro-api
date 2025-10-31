# Publisher Architecture

## Overview

The **Publisher** is the central component of `genro-api` that automatically exposes Python classes as REST APIs and web admin interfaces, based on metadata from the `@apiready` decorator.

## Key Concept

The Publisher implements an "automatic publication" pattern where:

1. **Business classes** (e.g., `StorageManager`) are decorated with `@apiready`
2. The **Publisher** reads metadata and automatically generates:
   - **REST/OpenAPI endpoints** for machine-to-machine communication
   - **NiceGUI interface** for admin dashboards
   - **Interactive Swagger documentation**

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Script                        │
│                                                               │
│  from genro_api import Publisher                            │
│  from genro_storage import StorageManager                   │
│  from my_lib import MyClass                                 │
│                                                               │
│  p = Publisher(host="0.0.0.0", port=8080)                  │
│  p.publish(StorageManager())                                │
│  p.publish(MyClass())                                       │
│  p.run()                                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Publisher                               │
│                                                               │
│  1. Metadata Introspection                                  │
│     - Reads _api_metadata from each method                  │
│     - Reads _api_base_path from class                       │
│     - Analyzes type hints and Annotated types               │
│                                                               │
│  2. REST API Generation (FastAPI)                           │
│     - Creates router for each class                         │
│     - Generates endpoints for each @apiready method         │
│     - Configures Swagger/OpenAPI docs                       │
│                                                               │
│  3. UI Generation (NiceGUI)                                 │
│     - Creates dynamic forms based on backend_schemas        │
│     - Generates automatic CRUD interfaces                   │
│     - Provides file browser and resource management         │
│                                                               │
│  4. Server Orchestration                                     │
│     - Starts FastAPI + NiceGUI                              │
│     - Manages routing and middleware                        │
│     - Configures CORS, logging, etc.                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
    ┌──────────────────┐      ┌──────────────────┐
    │   REST API       │      │   NiceGUI        │
    │   /api/*         │      │   /admin/*       │
    │                  │      │                  │
    │ - Swagger UI     │      │ - Dynamic Forms  │
    │ - OpenAPI spec   │      │ - CRUD Interface │
    │ - JSON responses │      │ - File Browser   │
    └──────────────────┘      └──────────────────┘
```

## @apiready Decorator Extension

The `@apiready` decorator is extended to support multiple targets:

```python
from typing import Literal, Union

def apiready(
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "POST",
    path: str | None = None,
    *,
    targets: list[Literal["rest", "ui"]] | None = None
):
    """
    Decorates a method to expose it via API.

    Args:
        method: HTTP method (default: POST)
        path: Custom path (default: function name)
        targets: List of targets ["rest", "ui"]
                 - "rest": Expose as REST API (Swagger)
                 - "ui": Expose in NiceGUI for building interfaces
                 - None: Expose in both (default)

    Examples:
        @apiready(targets=["rest", "ui"])  # Both
        def get_backend_types(self) -> list[str]:
            ...

        @apiready(targets=["rest"])  # REST API only
        def add_mount(self, config: dict) -> None:
            ...

        @apiready(targets=["ui"])  # UI only
        def get_backend_schema(self, backend_type: str) -> dict:
            ...
    """
```

### Metadata Structure

Metadata saved by `@apiready`:

```python
func._api_metadata = {
    "method": "POST",
    "path": "/storage/add_mount",
    "function_name": "add_mount",
    "targets": ["rest", "ui"],  # NEW
    "parameters": {
        "config": {
            "type": "dict[str, Any]",
            "annotation": Annotated[dict[str, Any], "Mount configuration"],
            "required": True,
            "default": None,
            "description": "Mount configuration"
        }
    },
    "return_type": {
        "type": "None",
        "annotation": None
    }
}
```

## Publisher Class

```python
class Publisher:
    """
    Publisher to expose @apiready classes as REST API and NiceGUI.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        title: str = "Genro API",
        version: str = "1.0.0",
        enable_rest: bool = True,
        enable_ui: bool = True,
        enable_swagger: bool = True
    ):
        """
        Initialize the Publisher.

        Args:
            host: Host to listen on
            port: Port to listen on
            title: Title for Swagger UI
            version: API version
            enable_rest: Enable REST endpoints
            enable_ui: Enable NiceGUI interface
            enable_swagger: Enable Swagger UI
        """
        self.host = host
        self.port = port
        self.app = FastAPI(title=title, version=version)
        self.enable_rest = enable_rest
        self.enable_ui = enable_ui
        self.enable_swagger = enable_swagger

        self._published_instances: list[tuple[object, type]] = []
        self._rest_routers: dict[str, APIRouter] = {}
        self._ui_registry: dict[str, dict] = {}

    def publish(self, instance: object) -> None:
        """
        Publish an instance decorated with @apiready.

        Args:
            instance: Instance of a class with @apiready methods

        Raises:
            ValueError: If class doesn't have _api_base_path
        """
        cls = type(instance)

        # Verify class has _api_base_path
        if not hasattr(cls, '_api_base_path'):
            raise ValueError(f"Class {cls.__name__} must have _api_base_path")

        self._published_instances.append((instance, cls))

        # Generate REST endpoints
        if self.enable_rest:
            self._generate_rest_endpoints(instance, cls)

        # Register for UI generation
        if self.enable_ui:
            self._register_ui_components(instance, cls)

    def _generate_rest_endpoints(self, instance: object, cls: type) -> None:
        """
        Generate REST endpoints for a published class.

        Args:
            instance: Class instance
            cls: Instance class
        """
        base_path = cls._api_base_path
        router = APIRouter(prefix=base_path, tags=[cls.__name__])

        # Iterate over class methods
        for method_name in dir(instance):
            method = getattr(instance, method_name)

            # Skip private methods and those without metadata
            if method_name.startswith('_') or not hasattr(method, '_api_metadata'):
                continue

            metadata = method._api_metadata

            # Check target
            targets = metadata.get('targets', ['rest', 'ui'])
            if 'rest' not in targets:
                continue

            # Create FastAPI endpoint
            self._create_fastapi_endpoint(router, instance, method, metadata)

        self.app.include_router(router)
        self._rest_routers[base_path] = router

    def _create_fastapi_endpoint(
        self,
        router: APIRouter,
        instance: object,
        method: callable,
        metadata: dict
    ) -> None:
        """
        Create a FastAPI endpoint for a method.

        Args:
            router: FastAPI router
            instance: Class instance
            method: Method to expose
            metadata: Method metadata
        """
        http_method = metadata['method']
        path = metadata['path'].replace(metadata.get('base_path', ''), '')

        # Create dynamic signature for FastAPI
        # ... (see detailed implementation below)

    def _register_ui_components(self, instance: object, cls: type) -> None:
        """
        Register components for UI generation.

        Args:
            instance: Class instance
            cls: Instance class
        """
        base_path = cls._api_base_path
        ui_methods = []

        for method_name in dir(instance):
            method = getattr(instance, method_name)

            if method_name.startswith('_') or not hasattr(method, '_api_metadata'):
                continue

            metadata = method._api_metadata
            targets = metadata.get('targets', ['rest', 'ui'])

            if 'ui' in targets:
                ui_methods.append({
                    'name': method_name,
                    'method': method,
                    'metadata': metadata
                })

        self._ui_registry[base_path] = {
            'instance': instance,
            'class': cls,
            'methods': ui_methods
        }

    def run(self, **kwargs) -> None:
        """
        Start the server.

        Args:
            **kwargs: Additional parameters for uvicorn
        """
        # Setup NiceGUI if enabled
        if self.enable_ui:
            self._setup_nicegui()

        # Start server
        import uvicorn
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            **kwargs
        )

    def _setup_nicegui(self) -> None:
        """
        Configure NiceGUI interface.
        """
        from nicegui import ui

        @ui.page("/admin")
        async def admin_page():
            """Main admin page."""
            ui.label("Genro Admin").classes("text-h3")

            # Create tab for each published class
            with ui.tabs() as tabs:
                for base_path, registry in self._ui_registry.items():
                    cls_name = registry['class'].__name__
                    ui.tab(cls_name)

            with ui.tab_panels(tabs):
                for base_path, registry in self._ui_registry.items():
                    with ui.tab_panel(registry['class'].__name__):
                        await self._render_class_ui(registry)

    async def _render_class_ui(self, registry: dict) -> None:
        """
        Render UI for a class.

        Args:
            registry: Class registry
        """
        # Dynamic UI implementation
        # ...
```

## Dynamic Form Generation for UI

For NiceGUI, the Publisher generates dynamic forms based on:

1. **Backend Schemas** (for complex configurations)
2. **Method Parameters** (for simple API calls)

### Example: Storage Mount Form

```python
# Publisher reads get_backend_schema(backend_type: str) -> dict
# and automatically generates:

async def create_mount_form():
    backend_type = ui.select(
        ["local", "s3", "gcs", "azure", ...],
        label="Backend Type"
    )

    # When user selects a type:
    schema = await api_call("/storage/get_backend_schema",
                           params={"backend_type": backend_type.value})

    # Generate fields dynamically
    form_data = {}
    for field in schema['fields']:
        if field['type'] == 'text':
            form_data[field['name']] = ui.input(
                label=field['label'],
                placeholder=field.get('placeholder', ''),
                value=field.get('default', '')
            )
        elif field['type'] == 'password':
            form_data[field['name']] = ui.input(
                label=field['label'],
                password=True
            )
        # ... other types

    # Submit button
    ui.button("Create", on_click=lambda: submit_form(form_data))
```

## Example Usage

### Application Script

```python
from genro_api import Publisher, apiready
from genro_storage import StorageManager

# Setup publisher
publisher = Publisher(
    host="0.0.0.0",
    port=8080,
    title="My Storage API",
    version="1.0.0"
)

# Create instances
storage = StorageManager()

# Publish instances
publisher.publish(storage)

# Run server
if __name__ == "__main__":
    publisher.run()
```

### Accessing APIs

**REST API:**
```bash
# Get backend types
curl http://localhost:8080/storage/get_backend_types

# Get schema for S3
curl http://localhost:8080/storage/get_backend_schema?backend_type=s3

# Add mount
curl -X POST http://localhost:8080/storage/add_mount \
  -H "Content-Type: application/json" \
  -d '{"name": "uploads", "type": "s3", "bucket": "my-bucket", "region": "us-east-1"}'
```

**Swagger UI:**
```
http://localhost:8080/docs
```

**Admin UI:**
```
http://localhost:8080/admin
```

## Implementation Phases

### Phase 1: Core Publisher
- [ ] Basic Publisher class structure
- [ ] Metadata introspection from @apiready
- [ ] REST endpoint generation with FastAPI
- [ ] Basic Swagger UI integration

### Phase 2: UI Generation
- [ ] NiceGUI integration
- [ ] Dynamic form generation from schemas
- [ ] CRUD interfaces

### Phase 3: Advanced Features
- [ ] Authentication/Authorization
- [ ] Rate limiting
- [ ] Caching
- [ ] WebSocket support
- [ ] File upload/download handling

### Phase 4: Testing & Documentation
- [ ] Test classes and examples
- [ ] Integration tests
- [ ] Performance benchmarks
- [ ] User documentation

## Test Classes

To validate the Publisher, we create test classes:

```python
@apiready_class(base_path="/calculator")
class Calculator:
    """Simple calculator for testing."""

    @apiready(method="POST", targets=["rest"])
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @apiready(method="POST", targets=["rest"])
    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b


@apiready_class(base_path="/counter")
class Counter:
    """Stateful counter for testing."""

    def __init__(self):
        self.count = 0

    @apiready(method="GET", targets=["rest", "ui"])
    def get(self) -> int:
        """Get current count."""
        return self.count

    @apiready(method="POST", targets=["rest", "ui"])
    def increment(self, amount: int = 1) -> int:
        """Increment counter."""
        self.count += amount
        return self.count

    @apiready(method="POST", targets=["ui"])
    def reset(self) -> None:
        """Reset counter to zero."""
        self.count = 0
```

## Benefits

1. **Separation of Concerns**: Business logic separated from API exposure
2. **DRY Principle**: Single decorator for REST + UI
3. **Type Safety**: Python type hints become API validation
4. **Auto-Documentation**: Swagger generated automatically
5. **Rapid Development**: Admin UI generated without boilerplate code
6. **Flexibility**: Granular control over what to expose and where

## Design Decisions

### Why @apiready metadata?
- **Passive**: Doesn't modify method behavior
- **Introspectable**: Readable via reflection
- **Flexible**: Easy to extend with new parameters

### Why FastAPI?
- Modern, async-native
- Automatic OpenAPI/Swagger generation
- Type validation via Pydantic
- Great performance

### Why NiceGUI?
- Python-native (no JavaScript)
- Reactive components
- Easy integration with FastAPI
- Material Design components

## Future Extensions

- **GraphQL Support**: Generate GraphQL schema from metadata
- **gRPC Support**: Generate service definitions
- **WebSocket Endpoints**: Real-time communication
- **Admin Plugins**: Plugin system to extend UI
- **Multi-tenancy**: Multi-tenant support with isolation
- **API Versioning**: Automatic API version management
