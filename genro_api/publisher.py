"""Publisher for automatic API exposure from @apiready decorated classes."""

import inspect
import logging
from typing import Any, Optional

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
        config: Any = None,
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
            config: Optional PublisherConfig instance for UI preferences
        """
        self.host = host
        self.port = port
        self.enable_rest = enable_rest
        self.enable_ui = enable_ui
        self.enable_swagger = enable_swagger
        self.config = config

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

        Collects @apiready methods and stores them for NiceGUI interface generation.
        Also registers child classes recursively.

        Args:
            instance: Instance of the class
            cls: Class type
        """
        base_path = cls._api_base_path
        logger.debug(f"Registering UI components for {cls.__name__} at {base_path}")

        # Get API structure using introspection
        try:
            structure = get_api_structure(instance, eager=True, mode="dict")
        except Exception as e:
            logger.error(f"Failed to introspect {cls.__name__} for UI: {e}")
            return

        # First, collect all classes to register (using set to avoid duplicates)
        classes_to_register = {}  # {base_path: (instance, structure, parent_path)}

        def collect_classes(inst, struct, parent_path=None):
            """Recursively collect all classes to register."""
            cls_path = struct.get("base_path") or parent_path
            if cls_path and cls_path not in classes_to_register:
                classes_to_register[cls_path] = (inst, struct, parent_path)

                # Recurse into children
                for child_info in struct.get("children", []):
                    child_path = child_info.get("base_path")
                    child_class_name = child_info.get("class_name")

                    # Find child instance
                    child_instance = None
                    for attr_name in dir(inst):
                        try:
                            attr = getattr(inst, attr_name)
                            if hasattr(attr, '__class__') and attr.__class__.__name__ == child_class_name:
                                child_instance = attr
                                break
                        except:
                            continue

                    if child_instance:
                        collect_classes(child_instance, child_info, cls_path)

        # Collect all classes starting from root
        collect_classes(instance, structure, None)

        # Now register all collected classes
        for path, (inst, struct, parent) in classes_to_register.items():
            ui_methods = []
            for endpoint_info in struct.get("endpoints", []):
                ui_methods.append({
                    "name": endpoint_info["function_name"],
                    "path": endpoint_info["path"],
                    "method": endpoint_info["method"],
                    "parameters": endpoint_info.get("parameters", {}),
                    "description": endpoint_info.get("description", ""),
                    "bound_method": getattr(inst, endpoint_info["function_name"])
                })

            registry_entry = {
                "instance": inst,
                "class": type(inst),
                "class_name": struct.get("class_name") or type(inst).__name__,
                "methods": ui_methods,
                "parent_path": parent,
            }

            # Add CRUD metadata if available
            if "additem" in struct:
                registry_entry["additem"] = struct["additem"]
            if "delitem" in struct:
                registry_entry["delitem"] = struct["delitem"]

            self._ui_registry[path] = registry_entry

            logger.info(f"UI components registered for {type(inst).__name__}: {len(ui_methods)} methods")

    def run(self, **kwargs: Any) -> None:
        """
        Start the server.

        This method starts uvicorn with the FastAPI application and NiceGUI integration.

        Args:
            **kwargs: Additional parameters passed to uvicorn.run() or ui.run()
                     Common options:
                     - reload: bool = Enable auto-reload (development)
                     - log_level: str = Logging level
                     - workers: int = Number of worker processes

        Examples:
            >>> publisher.run()  # Production
            >>> publisher.run(reload=True)  # Development with auto-reload
        """
        logger.info(f"Starting server on {self.host}:{self.port}")

        if self.enable_swagger:
            logger.info(f"Swagger UI: http://{self.host}:{self.port}/docs")
        if self.enable_ui:
            logger.info(f"Admin UI: http://{self.host}:{self.port}/admin")

        # Setup NiceGUI if enabled and start with integrated server
        if self.enable_ui:
            self._setup_nicegui()

            # Use NiceGUI's run method which integrates with FastAPI
            from nicegui import ui

            # NiceGUI mounts itself on the FastAPI app, then we run with uvicorn
            ui.run_with(
                self.app,
                mount_path="/",  # Mount NiceGUI at root
                storage_secret="genro-secret-key"  # Required for NiceGUI
            )

            # Now run with uvicorn
            import uvicorn
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                **kwargs,
            )
        else:
            # Use standard uvicorn if no UI
            import uvicorn

            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                **kwargs,
            )

    def _get_ordered_ui_registry(self) -> list[tuple[str, dict]]:
        """
        Get UI registry ordered by depth-first traversal with config classes last.

        Returns:
            List of (base_path, registry) tuples in the correct order
        """
        # Debug: log what's in the registry
        print(f"DEBUG: UI Registry contents: {list(self._ui_registry.keys())}")
        for path, reg in self._ui_registry.items():
            print(f"DEBUG:   {path}: {reg['class_name']} (parent: {reg.get('parent_path')})")

        ordered_paths = []
        visited = set()
        config_paths = []

        def depth_first_traverse(base_path: str):
            """Recursively traverse and collect paths depth-first."""
            if base_path in visited:
                return
            visited.add(base_path)
            ordered_paths.append(base_path)

            # Find all children of this path
            for child_path, child_registry in self._ui_registry.items():
                if child_registry.get("parent_path") == base_path:
                    depth_first_traverse(child_path)

        # Separate config classes from others
        root_paths = []
        for base_path, registry in self._ui_registry.items():
            if registry.get("parent_path") is None:
                # Check if it's a config class (ends with _config or contains "config" in name)
                class_name = registry["class_name"].lower()
                if "config" in class_name:
                    config_paths.append(base_path)
                else:
                    root_paths.append(base_path)

        # Traverse root classes depth-first
        print(f"DEBUG: Root paths to traverse: {root_paths}")
        print(f"DEBUG: Config paths to append: {config_paths}")

        for root_path in sorted(root_paths):  # Sort alphabetically for consistency
            depth_first_traverse(root_path)

        # Add config classes at the end
        for config_path in sorted(config_paths):
            if config_path not in visited:
                ordered_paths.append(config_path)

        print(f"DEBUG: Final ordered paths: {ordered_paths}")

        # Return ordered list of (base_path, registry) tuples
        return [(path, self._ui_registry[path]) for path in ordered_paths]

    def _setup_nicegui(self) -> None:
        """
        Configure NiceGUI admin interface.

        Creates an admin dashboard with tabs for each published class
        and dynamic forms for calling methods.
        """
        logger.debug("Setting up NiceGUI interface")

        try:
            from nicegui import ui
        except ImportError:
            logger.error("NiceGUI not installed. Install with: pip install nicegui")
            return

        # Create admin page
        @ui.page("/admin")
        async def admin_page():
            """Main admin dashboard page."""

            # Add global CSS for dialogs and grids
            ui.add_head_html("""
            <style>
            /* Resizable dialog support */
            .resizeable-dialog .q-card {
                resize: both;
                overflow: auto;
                min-width: 300px;
                min-height: 200px;
            }

            /* Auto-expanding dialogs */
            .resizeable-dialog .q-dialog__inner {
                align-items: flex-start !important;
            }

            .resizeable-dialog .q-card {
                width: auto !important;
                max-width: 95vw;
                max-height: 90vh;
            }

            /* Compact AG Grid with Quartz theme */
            .ag-theme-quartz .ag-row {
                height: 24px !important;
            }
            .ag-theme-quartz .ag-cell {
                line-height: 22px !important;
                padding-top: 2px !important;
                padding-bottom: 2px !important;
            }
            .ag-theme-quartz .ag-header-cell {
                line-height: 22px !important;
                padding-top: 3px !important;
                padding-bottom: 3px !important;
            }
            </style>
            """)

            # Header
            with ui.header().classes("items-center justify-between"):
                ui.label("Genro Admin Console").classes("text-h4")
                ui.label(f"API v{self.app.version}").classes("text-subtitle2")

            # Main content
            with ui.column().classes("w-full p-4"):
                if not self._ui_registry:
                    ui.label("No classes published yet.").classes("text-h6 text-grey")
                    return

                # Get ordered registry (depth-first with config classes last)
                ordered_registry = self._get_ordered_ui_registry()

                # Create tabs for each published class
                with ui.tabs().classes("w-full") as tabs:
                    tab_refs = {}
                    for base_path, registry in ordered_registry:
                        class_name = registry["class_name"]
                        tab_refs[class_name] = ui.tab(class_name)

                # Tab panels (use same order as tabs)
                first_tab_name = ordered_registry[0][1]["class_name"] if ordered_registry else None
                with ui.tab_panels(tabs, value=first_tab_name).classes("w-full"):
                    for base_path, registry in ordered_registry:
                        class_name = registry["class_name"]

                        with ui.tab_panel(class_name):
                            await self._render_class_panel(registry)

        logger.info("NiceGUI admin interface configured at /admin")

    async def _render_class_panel(self, registry: dict[str, Any]) -> None:
        """
        Render UI panel for a published class.

        Args:
            registry: Class registry with methods and instance
        """
        from nicegui import ui

        class_name = registry["class_name"]
        methods = registry["methods"]

        ui.label(f"{class_name} API Methods").classes("text-h5 mb-4")

        if not methods:
            ui.label("No methods available.").classes("text-grey")
            return

        # Create buttons for each method
        with ui.grid(columns=3).classes("w-full gap-2"):
            for method_info in methods:
                self._render_method_button(method_info)

    def _render_method_button(self, method_info: dict[str, Any]) -> None:
        """
        Render a button for a method that opens a dialog with form.

        Args:
            method_info: Method metadata and bound method
        """
        from nicegui import ui

        method_name = method_info["name"]
        description = method_info["description"]
        parameters = method_info["parameters"]
        bound_method = method_info["bound_method"]
        http_method = method_info["method"]

        # Beautify method name: add_shelf -> Add Shelf
        button_label = method_name.replace("_", " ").title()

        # Choose button color based on HTTP method
        if http_method == "GET":
            button_color = "primary"
        elif method_name.startswith(("add", "create")):
            button_color = "positive"
        elif method_name.startswith(("remove", "delete")):
            button_color = "negative"
        elif method_name.startswith(("update", "move", "edit")):
            button_color = "warning"
        else:
            button_color = "secondary"

        # Check if method needs dialog or can be executed directly
        is_destructive = method_name.startswith(("remove", "delete"))
        has_parameters = bool(parameters)
        needs_dialog = has_parameters or is_destructive

        if needs_dialog:
            def open_method_dialog():
                """Open dialog with method form."""
                # Large dialog that floats over the page
                # Get dialog dimensions from config
                dialog_height = self.config.get_config("dialog_height") if self.config else "85vh"

                with ui.dialog().classes('resizeable-dialog') as dialog:
                    card = ui.card().classes("w-full max-w-4xl resize-both overflow-auto")
                    with card:
                        # Dialog header
                        ui.label(button_label).classes("text-h6")
                        if description:
                            ui.label(description).classes("text-caption text-grey mb-4")

                        # Confirmation message for destructive operations without parameters
                        if is_destructive and not has_parameters:
                            ui.separator()
                            ui.label("Are you sure you want to proceed?").classes("text-warning")

                        # Parameters form
                        input_widgets = {}

                        if parameters:
                            ui.separator()
                            with ui.column().classes("w-full gap-2 mt-2"):
                                for param_name, param_info in parameters.items():
                                    param_type = param_info.get("type", "str")
                                    param_desc = param_info.get("description", "")
                                    param_required = param_info.get("required", True)
                                    param_default = param_info.get("default", "")

                                    label_text = param_name.replace("_", " ").title()
                                    if param_required:
                                        label_text += " *"

                                    # Create appropriate input based on type
                                    if param_type in ["str", "string"]:
                                        input_widgets[param_name] = ui.input(
                                            label=label_text,
                                            placeholder=param_desc,
                                            value=param_default if param_default != "..." else ""
                                        ).classes("w-full")
                                    elif param_type in ["int", "integer"]:
                                        input_widgets[param_name] = ui.number(
                                            label=label_text,
                                            placeholder=param_desc,
                                            value=int(param_default) if param_default and param_default != "..." else None
                                        ).classes("w-full")
                                    elif param_type == "float":
                                        input_widgets[param_name] = ui.number(
                                            label=label_text,
                                            placeholder=param_desc,
                                            value=float(param_default) if param_default and param_default != "..." else None,
                                            format="%.2f"
                                        ).classes("w-full")
                                    elif param_type in ["bool", "boolean"]:
                                        input_widgets[param_name] = ui.checkbox(
                                            text=label_text,
                                            value=bool(param_default) if param_default else False
                                        )
                                    else:
                                        # Default to text input for complex types
                                        input_widgets[param_name] = ui.input(
                                            label=f"{label_text} ({param_type})",
                                            placeholder=param_desc,
                                            value=str(param_default) if param_default and param_default != "..." else ""
                                        ).classes("w-full")

                        ui.separator()

                        # Result display area
                        result_container = ui.column().classes("w-full mt-2")

                        async def execute_method():
                            """Execute the method with form parameters."""
                            result_container.clear()

                            with result_container:
                                ui.label("Executing...").classes("text-grey")

                            try:
                                # Collect parameters
                                kwargs = {}
                                if parameters:
                                    for param_name, widget in input_widgets.items():
                                        value = widget.value
                                        # Convert empty strings to None for optional parameters
                                        if value == "" and not parameters[param_name].get("required", True):
                                            value = None
                                        kwargs[param_name] = value

                                # Call the method
                                result = bound_method(**kwargs)

                                # Display result
                                result_container.clear()
                                with result_container:
                                    self._render_result(result, button_label)

                            except Exception as e:
                                result_container.clear()
                                with result_container:
                                    ui.label("Error:").classes("text-subtitle2 text-red")
                                    ui.label(str(e)).classes("text-red")

                        # Action buttons
                        with ui.row().classes("w-full justify-end gap-2 mt-4"):
                            ui.button("Cancel", on_click=dialog.close, color="grey")
                            ui.button("Execute", on_click=execute_method, color=button_color)

                dialog.open()

            # Create the button that opens dialog
            ui.button(button_label, on_click=open_method_dialog, color=button_color).classes("w-full")
        else:
            # Execute directly without dialog (no parameters, not destructive)
            async def execute_directly():
                """Execute method directly and show result in a dialog."""
                # Get dialog dimensions from config
                dialog_width = self.config.get_config("dialog_width") if self.config else "90vw"
                dialog_height = self.config.get_config("dialog_height") if self.config else "85vh"

                # Create dialog
                with ui.dialog().classes('resizeable-dialog') as result_dialog:
                    card = ui.card().style(f"height: {dialog_height};")
                    with card:
                        # Close button at top right
                        with ui.row().classes("w-full justify-between items-center mb-2"):
                            ui.label(button_label).classes("text-h6")
                            ui.button(icon="close", on_click=result_dialog.close).props("flat round dense")

                        result_container = ui.column().classes("w-full")

                        with result_container:
                            ui.label("Executing...").classes("text-grey")

                        try:
                            # Call the method
                            result = bound_method()

                            # Display result
                            result_container.clear()
                            with result_container:
                                self._render_result(result, button_label)

                        except Exception as e:
                            result_container.clear()
                            with result_container:
                                ui.label("Error:").classes("text-subtitle2 text-red")
                                ui.label(str(e)).classes("text-red")
                            # Use default width for errors
                            card.style(f"width: {dialog_width}; height: {dialog_height};")

                result_dialog.open()

            # Create the button that executes directly
            ui.button(button_label, on_click=execute_directly, color=button_color).classes("w-full")

    def _extract_entity_name(self, method_name: str) -> str:
        """
        Extract entity name from method name for display.

        Examples:
            list_books -> Books
            list_shelves -> Shelves
            get_stats -> Stats
            list_all_books -> Books

        Args:
            method_name: Method name (e.g., "list_books")

        Returns:
            Entity name in title case (e.g., "Books")
        """
        # Remove common prefixes
        for prefix in ["list_all_", "list_", "get_all_", "get_"]:
            if method_name.startswith(prefix):
                entity = method_name[len(prefix):]
                return entity.replace("_", " ").title()

        # Fallback to method name
        return method_name.replace("_", " ").title()

    def _render_result(self, result: Any, method_label: str = "") -> None:
        """
        Render the result of a method call in a user-friendly format.

        Renders results with AG Grid (for lists) or appropriate UI elements.
        For list results, creates a grid with selection support and detail view.

        Args:
            result: The result to render
            method_label: Method name for title (e.g., "List Shelves")
        """
        from nicegui import ui
        from dataclasses import is_dataclass, asdict

        if result is None:
            ui.label("Success!").classes("text-green")
        elif isinstance(result, list):
            if not result:
                ui.label("Empty list").classes("text-grey")
            else:
                # Try to convert objects to dicts
                first_item = result[0]

                # Convert list items to dicts if they are objects
                if isinstance(first_item, dict):
                    rows = result
                elif is_dataclass(first_item):
                    # Dataclass objects - convert to dict
                    rows = [asdict(item) for item in result]
                elif hasattr(first_item, '__dict__'):
                    # Objects with __dict__ - convert to dict
                    rows = [item.__dict__ for item in result]
                else:
                    # Simple values - render as list
                    rows = None

                if rows:
                    # Title with count using entity name (e.g., "Books: 52" instead of "List All Books: 52")
                    count = len(rows)
                    # Extract entity from method_label (e.g., "List All Books" -> "Books")
                    entity = method_label.replace("List All", "").replace("List", "").strip()
                    if not entity:
                        entity = "Items"
                    title = f"{entity}: {count}"
                    ui.label(title).classes("text-h6 text-center w-full mb-1")

                    # Build column definitions
                    column_defs = []
                    for key in rows[0].keys():
                        column_defs.append({
                            "headerName": key.replace("_", " ").title(),
                            "field": key
                        })

                    # Create AG Grid with autoHeight
                    grid = ui.aggrid({
                        "columnDefs": column_defs,
                        "rowData": rows,
                        "defaultColDef": {
                            "sortable": True,
                            "filter": True,
                            "resizable": True
                        },
                        "domLayout": "autoHeight",  # Auto-adjust height to content
                        "rowSelection": "single",
                        "suppressCellFocus": True
                    }).classes("ag-theme-quartz")

                    # Detail container for showing selected row details
                    detail_container = ui.column().classes("mt-3 w-full")

                    # Handler for row click (shows details below grid)
                    @grid.on('rowClicked')
                    async def handle_row_click(e):
                        row = e.args.get('data')
                        if row:
                            detail_container.clear()
                            with detail_container:
                                with ui.card().classes('p-3 w-full').style('max-width: 800px'):
                                    # Build markdown for selected row
                                    md_lines = []
                                    for key, value in row.items():
                                        label = key.replace("_", " ").title()
                                        md_lines.append(f"**{label}:** {value}")
                                    ui.markdown("\n\n".join(md_lines))
                else:
                    # Simple list - render as items
                    with ui.column().classes("w-full"):
                        for item in result:
                            ui.label(str(item)).classes("text-body2")
        elif isinstance(result, dict):
            ui.json_editor({"content": {"json": result}}).classes("w-full")
        else:
            ui.label(str(result)).classes("text-body1")

    async def _render_method_card(self, method_info: dict[str, Any]) -> None:
        """
        Render a card for a single method with dynamic form.

        Args:
            method_info: Method metadata and bound method
        """
        from nicegui import ui

        method_name = method_info["name"]
        description = method_info["description"]
        parameters = method_info["parameters"]
        bound_method = method_info["bound_method"]
        http_method = method_info["method"]

        # Method card
        with ui.card().classes("w-full"):
            # Header
            with ui.row().classes("w-full items-center"):
                ui.badge(http_method, color="primary" if http_method == "GET" else "secondary")
                ui.label(method_name).classes("text-h6")

            if description:
                ui.label(description).classes("text-caption text-grey")

            ui.separator()

            # Parameters form
            if parameters:
                ui.label("Parameters:").classes("text-subtitle2 mt-2")

                # Store input widgets
                input_widgets = {}

                with ui.column().classes("w-full gap-2 mt-2"):
                    for param_name, param_info in parameters.items():
                        param_type = param_info.get("type", "str")
                        param_desc = param_info.get("description", "")
                        param_required = param_info.get("required", True)
                        param_default = param_info.get("default", "")

                        label_text = param_name
                        if param_required:
                            label_text += " *"
                        if param_desc:
                            label_text += f" - {param_desc}"

                        # Create appropriate input based on type
                        if param_type in ["str", "string"]:
                            input_widgets[param_name] = ui.input(
                                label=label_text,
                                value=param_default if param_default != "..." else ""
                            ).classes("w-full")
                        elif param_type in ["int", "integer"]:
                            input_widgets[param_name] = ui.number(
                                label=label_text,
                                value=int(param_default) if param_default and param_default != "..." else None
                            ).classes("w-full")
                        elif param_type == "float":
                            input_widgets[param_name] = ui.number(
                                label=label_text,
                                value=float(param_default) if param_default and param_default != "..." else None,
                                format="%.2f"
                            ).classes("w-full")
                        elif param_type in ["bool", "boolean"]:
                            input_widgets[param_name] = ui.checkbox(
                                text=label_text,
                                value=bool(param_default) if param_default else False
                            )
                        else:
                            # Default to text input for complex types
                            input_widgets[param_name] = ui.input(
                                label=f"{label_text} ({param_type})",
                                value=str(param_default) if param_default and param_default != "..." else ""
                            ).classes("w-full")

            # Result container
            result_container = ui.column().classes("w-full mt-4")

            # Execute button
            async def execute_method():
                """Execute the method with form parameters."""
                result_container.clear()

                with result_container:
                    ui.separator()
                    ui.label("Executing...").classes("text-grey")

                try:
                    # Collect parameters
                    kwargs = {}
                    if parameters:
                        for param_name, widget in input_widgets.items():
                            value = widget.value
                            # Convert empty strings to None for optional parameters
                            if value == "" and not parameters[param_name].get("required", True):
                                value = None
                            kwargs[param_name] = value

                    # Call the method
                    result = bound_method(**kwargs)

                    # Display result
                    result_container.clear()
                    with result_container:
                        ui.separator()
                        ui.label("Result:").classes("text-subtitle2 text-green")

                        # Format result based on type
                        if isinstance(result, (list, dict)):
                            ui.json_editor({"content": {"json": result}},
                                         on_select=None,
                                         on_change=None).classes("w-full")
                        elif result is None:
                            ui.label("Success (no return value)").classes("text-grey")
                        else:
                            ui.label(str(result)).classes("text-body1")

                except Exception as e:
                    result_container.clear()
                    with result_container:
                        ui.separator()
                        ui.label("Error:").classes("text-subtitle2 text-red")
                        ui.label(str(e)).classes("text-red")

            ui.button("Execute", on_click=execute_method, color="primary").classes("mt-2")

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
