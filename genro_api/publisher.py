"""Publisher for automatic API exposure from @apiready decorated classes."""

import inspect
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.routing import APIRouter
from pydantic import BaseModel, create_model
from genro_core import get_api_structure

logger = logging.getLogger(__name__)


class Publisher:
    """
    Publisher to expose @apiready classes as REST API and NiceGUI interfaces.

    The Publisher reads metadata from classes decorated with @apiready and automatically
    generates:
    - REST API endpoints with FastAPI
    - NiceGUI admin interfaces
    - OpenAPI/Swagger documentation

    Examples:
        >>> from genro_api import Publisher
        >>> from genro_storage import StorageManager
        >>>
        >>> publisher = Publisher(host="0.0.0.0", port=8080)
        >>> storage = StorageManager()
        >>> publisher.publish(storage)
        >>> publisher.run()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        title: str = "Genro API",
        version: str = "1.0.0",
        enable_rest: bool = True,
        enable_ui: bool = True,
        enable_swagger: bool = True,
    ):
        """
        Initialize the Publisher.

        Args:
            host: Host address to listen on (default: "0.0.0.0")
            port: Port to listen on (default: 8080)
            title: API title for Swagger UI (default: "Genro API")
            version: API version (default: "1.0.0")
            enable_rest: Enable REST API endpoints (default: True)
            enable_ui: Enable NiceGUI admin interface (default: True)
            enable_swagger: Enable Swagger UI documentation (default: True)
        """
        self.host = host
        self.port = port
        self.enable_rest = enable_rest
        self.enable_ui = enable_ui
        self.enable_swagger = enable_swagger

        # Initialize FastAPI app
        self.app = FastAPI(
            title=title,
            version=version,
            docs_url="/docs" if enable_swagger else None,
            redoc_url="/redoc" if enable_swagger else None,
        )

        # Registries
        self._published_instances: list[tuple[object, type]] = []
        self._rest_routers: dict[str, APIRouter] = {}
        self._ui_registry: dict[str, dict[str, Any]] = {}
        self._base_paths: set[str] = set()

        logger.info(
            f"Publisher initialized: {title} v{version} on {host}:{port}"
        )

    def publish(self, instance: object) -> None:
        """
        Publish an instance decorated with @apiready.

        The instance's class must have an `_api_base_path` attribute set by
        the @apiready_class decorator.

        Args:
            instance: Instance of a class with @apiready methods

        Raises:
            ValueError: If class doesn't have _api_base_path
            ValueError: If base_path already published

        Examples:
            >>> publisher = Publisher()
            >>> storage = StorageManager()
            >>> publisher.publish(storage)
        """
        cls = type(instance)

        # Validate class has _api_base_path
        if not hasattr(cls, "_api_base_path"):
            raise ValueError(
                f"Class {cls.__name__} must have _api_base_path attribute. "
                f"Use @apiready_class decorator on the class."
            )

        base_path = cls._api_base_path

        # Check for duplicate base paths
        if base_path in self._base_paths:
            raise ValueError(
                f"Base path '{base_path}' already published. "
                f"Each published class must have a unique base path."
            )

        self._base_paths.add(base_path)
        self._published_instances.append((instance, cls))

        logger.info(f"Publishing {cls.__name__} at {base_path}")

        # Generate REST endpoints
        if self.enable_rest:
            self._generate_rest_endpoints(instance, cls)

        # Register for UI generation
        if self.enable_ui:
            self._register_ui_components(instance, cls)

    def _generate_rest_endpoints(self, instance: object, cls: type) -> None:
        """
        Generate REST endpoints for a published class.

        Reads metadata from @apiready methods and creates FastAPI endpoints
        with proper request/response models and documentation.

        This method also recursively generates endpoints for child classes
        (discovered via eager introspection).

        Args:
            instance: Instance of the class
            cls: Class type
        """
        base_path = cls._api_base_path
        logger.debug(f"Generating REST endpoints for {cls.__name__} at {base_path}")

        # Get API structure using introspection with eager mode
        try:
            structure = get_api_structure(instance, eager=True, mode="dict")
        except Exception as e:
            logger.error(f"Failed to introspect {cls.__name__}: {e}")
            raise

        # Create router for this class
        router = APIRouter(prefix=base_path, tags=[cls.__name__])

        # Generate endpoint for each method
        for endpoint_info in structure["endpoints"]:
            self._create_endpoint(router, instance, endpoint_info)

        # Register router with app
        self._rest_routers[base_path] = router
        self.app.include_router(router)

        logger.info(
            f"REST endpoints registered for {cls.__name__}: "
            f"{len(structure['endpoints'])} endpoints"
        )

        # Recursively generate endpoints for children
        if "children" in structure:
            for child_structure in structure["children"]:
                self._generate_child_endpoints(instance, child_structure)

    def _generate_child_endpoints(self, parent_instance: object, child_structure: dict) -> None:
        """
        Generate REST endpoints for a child class discovered via eager introspection.

        Args:
            parent_instance: Parent instance that contains the child
            child_structure: Child class structure from introspection
        """
        child_class_name = child_structure["class_name"]
        child_base_path = child_structure["base_path"]

        logger.debug(f"Generating child endpoints for {child_class_name} at {child_base_path}")

        # Find the child instance from parent
        # For manager pattern: it's an instance attribute
        # For module-level classes: we need to instantiate or skip
        child_instance = None

        # Try to find as instance attribute
        for attr_name in dir(parent_instance):
            if attr_name.startswith('_'):
                continue
            try:
                attr = getattr(parent_instance, attr_name)
                if hasattr(attr, '__class__') and attr.__class__.__name__ == child_class_name:
                    child_instance = attr
                    break
            except:
                continue

        if child_instance is None:
            # Module-level class without instance - skip for now
            logger.warning(
                f"Child class {child_class_name} not found as instance attribute. "
                f"Module-level classes require instance to be published separately."
            )
            return

        # Create router for child class
        router = APIRouter(prefix=child_base_path, tags=[child_class_name])

        # Generate endpoint for each child method
        for endpoint_info in child_structure["endpoints"]:
            self._create_endpoint(router, child_instance, endpoint_info)

        # Register router with app
        self._rest_routers[child_base_path] = router
        self.app.include_router(router)

        logger.info(
            f"Child endpoints registered for {child_class_name}: "
            f"{len(child_structure['endpoints'])} endpoints"
        )

    def _register_ui_components(self, instance: object, cls: type) -> None:
        """
        Register components for UI generation.

        This is a stub for Issue #4. It will register methods for NiceGUI
        interface generation.

        Args:
            instance: Instance of the class
            cls: Class type
        """
        base_path = cls._api_base_path
        logger.debug(f"Registering UI components for {cls.__name__} at {base_path}")

        # TODO: Issue #4 - Implement UI component registration
        # For now, just store the instance
        self._ui_registry[base_path] = {
            "instance": instance,
            "class": cls,
            "methods": [],  # Will be populated in Issue #4
        }

        logger.info(f"UI components registered for {cls.__name__}")

    def run(self, **kwargs: Any) -> None:
        """
        Start the server.

        This method starts uvicorn with the FastAPI application.

        Args:
            **kwargs: Additional parameters passed to uvicorn.run()
                     Common options:
                     - reload: bool = Enable auto-reload (development)
                     - log_level: str = Logging level
                     - workers: int = Number of worker processes

        Examples:
            >>> publisher.run()  # Production
            >>> publisher.run(reload=True)  # Development with auto-reload
        """
        # Setup NiceGUI if enabled
        if self.enable_ui:
            self._setup_nicegui()

        logger.info(f"Starting server on {self.host}:{self.port}")

        if self.enable_swagger:
            logger.info(f"Swagger UI: http://{self.host}:{self.port}/docs")
        if self.enable_ui:
            logger.info(f"Admin UI: http://{self.host}:{self.port}/admin")

        # Start server
        import uvicorn

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            **kwargs,
        )

    def _setup_nicegui(self) -> None:
        """
        Configure NiceGUI interface.

        This is a stub for Issue #4. It will create the admin UI.
        """
        logger.debug("Setting up NiceGUI interface")

        # TODO: Issue #4 - Implement NiceGUI setup
        # For now, just log that it would be set up
        logger.info("NiceGUI setup (stub - to be implemented in Issue #4)")

    def get_published_classes(self) -> list[tuple[str, str]]:
        """
        Get list of published classes with their base paths.

        Returns:
            List of tuples (class_name, base_path)

        Examples:
            >>> publisher.publish(storage)
            >>> publisher.get_published_classes()
            [('StorageManager', '/storage')]
        """
        return [
            (cls.__name__, cls._api_base_path)
            for _, cls in self._published_instances
        ]

    def _create_endpoint(
        self, router: APIRouter, instance: object, endpoint_info: dict[str, Any]
    ) -> None:
        """
        Create a FastAPI endpoint from metadata.

        Args:
            router: APIRouter to add the endpoint to
            instance: Instance containing the method
            endpoint_info: Endpoint metadata from introspection

        Endpoint info structure:
            {
                "function_name": str,
                "path": str,
                "method": str (GET/POST),
                "parameters": dict,  # {param_name: {type, required, default, description}}
                "return_type": dict,  # {type, description}
                "description": str
            }
        """
        func_name = endpoint_info["function_name"]
        path = endpoint_info["path"]
        method = endpoint_info["method"]
        params = endpoint_info.get("parameters", {})
        return_type_info = endpoint_info.get("return_type", {})
        description = endpoint_info.get("description", "")

        # Get the bound method from instance
        if not hasattr(instance, func_name):
            logger.error(f"Method {func_name} not found on instance")
            return

        bound_method = getattr(instance, func_name)

        # Create Pydantic model for request parameters if any
        request_model = None
        if params:
            # Build field definitions for Pydantic
            fields = {}
            for param_name, param_info in params.items():
                param_type_str = param_info.get("type", "Any")
                param_required = param_info.get("required", True)
                param_default = param_info.get("default", ...)
                param_desc = param_info.get("description", "")

                # Map type string to Python type
                field_type = self._map_type_string(param_type_str)

                # Set default value
                if not param_required:
                    if param_default == "":
                        fields[param_name] = (field_type, "")
                    elif param_default == "None" or param_default is None:
                        fields[param_name] = (field_type | None, None)
                    else:
                        fields[param_name] = (field_type, param_default)
                else:
                    fields[param_name] = (field_type, ...)

            # Create dynamic Pydantic model
            model_name = f"{func_name.title()}Request"
            request_model = create_model(model_name, **fields)

        # Create the endpoint handler
        if method == "GET":
            # For GET, parameters come from query string
            if request_model:
                # Create a function with proper signature for FastAPI
                # We need to dynamically create parameters with Query() defaults
                def make_get_handler():
                    # Build parameters for the function signature
                    sig_params = []
                    for param_name, param_info in params.items():
                        param_type_str = param_info.get("type", "Any")
                        param_required = param_info.get("required", True)
                        param_default = param_info.get("default", ...)

                        # Map type string to Python type
                        field_type = self._map_type_string(param_type_str)

                        # Create inspect.Parameter with Query() annotation
                        if param_required:
                            default_value = Query(...)
                        else:
                            if param_default == "None" or param_default is None:
                                default_value = Query(None)
                            elif param_default == "":
                                default_value = Query("")
                            else:
                                default_value = Query(param_default)

                        sig_params.append(
                            inspect.Parameter(
                                param_name,
                                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                default=default_value,
                                annotation=field_type
                            )
                        )

                    # Create async function with the right signature
                    async def endpoint_handler(**kwargs):
                        try:
                            result = bound_method(**kwargs)
                            return result
                        except Exception as e:
                            logger.error(f"Error in {func_name}: {e}")
                            raise HTTPException(status_code=500, detail=str(e))

                    # Apply the signature
                    endpoint_handler.__signature__ = inspect.Signature(sig_params)
                    return endpoint_handler

                handler = make_get_handler()

                # Add route
                router.add_api_route(
                    path,
                    handler,
                    methods=["GET"],
                    summary=func_name,
                    description=description,
                    response_model=None,
                )
            else:
                # No parameters
                async def endpoint_handler():
                    try:
                        result = bound_method()
                        return result
                    except Exception as e:
                        logger.error(f"Error in {func_name}: {e}")
                        raise HTTPException(status_code=500, detail=str(e))

                router.add_api_route(
                    path,
                    endpoint_handler,
                    methods=["GET"],
                    summary=func_name,
                    description=description,
                    response_model=None,
                )

        elif method == "POST":
            # For POST, parameters come from request body
            if request_model:
                async def endpoint_handler(request: request_model):  # type: ignore
                    try:
                        # Convert Pydantic model to dict
                        kwargs = request.model_dump()
                        result = bound_method(**kwargs)
                        return result
                    except Exception as e:
                        logger.error(f"Error in {func_name}: {e}")
                        raise HTTPException(status_code=500, detail=str(e))

                router.add_api_route(
                    path,
                    endpoint_handler,
                    methods=["POST"],
                    summary=func_name,
                    description=description,
                    response_model=None,
                )
            else:
                # No parameters
                async def endpoint_handler():
                    try:
                        result = bound_method()
                        return result
                    except Exception as e:
                        logger.error(f"Error in {func_name}: {e}")
                        raise HTTPException(status_code=500, detail=str(e))

                router.add_api_route(
                    path,
                    endpoint_handler,
                    methods=["POST"],
                    summary=func_name,
                    description=description,
                    response_model=None,
                )

        logger.debug(f"Created {method} endpoint: {path}")

    def _map_type_string(self, type_str: str) -> type:
        """
        Map type string from introspection to Python type.

        Args:
            type_str: Type string (e.g., "str", "int", "list[str]")

        Returns:
            Python type object
        """
        # Basic types
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "dict": dict,
            "list": list,
            "Any": Any,
        }

        # Try direct mapping first
        if type_str in type_mapping:
            return type_mapping[type_str]

        # Handle complex types (list[str], dict[str, int], etc.)
        # For now, just return Any for complex types
        # TODO: Parse complex type strings properly
        logger.debug(f"Complex type {type_str} mapped to Any")
        return Any
