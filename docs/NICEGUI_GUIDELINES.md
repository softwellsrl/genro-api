# NiceGUI Implementation Guidelines

This document contains best practices and configuration guidelines for NiceGUI implementation in genro-api.

## AG Grid Configuration

### Basic Grid Setup

```python
grid = ui.aggrid({
    "columnDefs": column_defs,
    "rowData": rows,
    "defaultColDef": {
        "sortable": True,
        "filter": True,
        "resizable": True
    },
    "domLayout": "normal",
    "rowSelection": "single",    # Enable row selection instead of cell selection
    "suppressCellFocus": True     # Disable cell focus, use row selection
}).classes("compact-grid")
```

### Row Selection vs Cell Selection

**Preferred**: Row selection
- Use `"rowSelection": "single"` for single row selection
- Use `"rowSelection": "multiple"` for multiple row selection
- Add `"suppressCellFocus": True` to disable cell focus

**Avoid**: Cell selection (default behavior)

### Column Width Guessing

Calculate column widths based on data type and content:

```python
total_width = 0
column_defs = []

for key in rows[0].keys():
    sample_value = rows[0][key]

    if isinstance(sample_value, (int, float)):
        # Numeric columns - narrower (80px base)
        max_len = max(len(str(row[key])) for row in rows[:min(10, len(rows))])
        width = max(80, min(max_len * 10 + 30, 150))
    elif isinstance(sample_value, bool):
        # Boolean - very narrow
        width = 70
    else:
        # Text columns - based on content length
        max_len = max(len(str(row[key])) for row in rows[:min(10, len(rows))])
        header_len = len(key.replace("_", " ").title())
        width = max(100, min(max(max_len, header_len) * 8 + 40, 400))

    column_defs.append({
        "field": key,
        "headerName": key.replace("_", " ").title(),
        "width": width
    })
    total_width += width

# Add margin for borders, scrollbar, etc.
total_width += 50

# Set grid width
grid.style(f"width: {total_width}px; height: calc(100vh - 180px);")
```

**Guidelines**:
- Numeric columns: 80-150px
- Boolean columns: 70px
- Text columns: 100-400px based on content
- Always add 50px margin for borders and scrollbar
- Sample first 10 rows for performance

### CSS Styling for Compact Display

Use explicit padding properties (not shorthand) for better control:

```python
padding_v = "2px"  # Vertical padding
padding_h = "4px"  # Horizontal padding

ui.add_head_html(f"""
    <style>
    .compact-grid .ag-cell {{
        padding-top: {padding_v} !important;
        padding-bottom: {padding_v} !important;
        padding-left: {padding_h} !important;
        padding-right: {padding_h} !important;
        line-height: 1.2 !important;
    }}
    .compact-grid .ag-header-cell {{
        padding-top: {padding_v} !important;
        padding-bottom: {padding_v} !important;
        padding-left: {padding_h} !important;
        padding-right: {padding_h} !important;
    }}
    .compact-grid .ag-row {{
        border-bottom: 1px solid #e0e0e0 !important;
    }}
    </style>
""")
```

**Important**:
- Always use explicit `padding-top`, `padding-bottom`, `padding-left`, `padding-right`
- Never use shorthand `padding: 2px 4px` as it can cause inconsistencies
- Apply to both `.ag-cell` and `.ag-header-cell`

### Row Height

**Avoid**: Fixed row height (`rowHeight: 28`)

**Preferred**: Let AG Grid use default (42px) or content-driven height

The default row height (42px) provides good readability and works well with standard content.

## Dialog Configuration

### Size Configuration

Use viewport units for responsive dialogs:

```python
dialog_width = "90vw"   # 90% of viewport width
dialog_height = "85vh"  # 85% of viewport height
```

**Avoid**: `maximized` property - it covers the entire screen including navigation

### Dialog Structure

```python
with ui.dialog() as dialog:
    with ui.card().style(f"width: {dialog_width}; height: {dialog_height}"):
        # Header
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Dialog Title").classes("text-h6")
            ui.button(icon="close", on_click=dialog.close).props("flat round dense")

        ui.separator()

        # Content area with scroll
        with ui.scroll_area().classes("w-full").style("height: calc(100% - 60px)"):
            # Your content here
            pass
```

## Tab Navigation

### Tab Ordering Strategy

1. **Primary classes first**: Main business objects
2. **Depth-first traversal**: Parent → Child → Grandchild
3. **Configuration classes last**: Always append config tabs at the end

```python
def _get_ordered_ui_registry(self) -> list[tuple[str, dict]]:
    """Get UI registry in correct display order."""
    ordered_paths = []
    visited = set()
    config_paths = []

    # Separate config classes from others
    root_paths = []
    for base_path, registry in self._ui_registry.items():
        if registry.get("parent_path") is None:
            class_name = registry["class_name"].lower()
            if "config" in class_name:
                config_paths.append(base_path)
            else:
                root_paths.append(base_path)

    # Depth-first traversal function
    def depth_first_traverse(path):
        if path in visited:
            return
        visited.add(path)
        ordered_paths.append(path)

        # Find children
        for child_path, child_reg in self._ui_registry.items():
            if child_reg.get("parent_path") == path:
                depth_first_traverse(child_path)

    # Traverse root classes depth-first
    for root_path in sorted(root_paths):
        depth_first_traverse(root_path)

    # Add config classes at the end
    for config_path in sorted(config_paths):
        if config_path not in visited:
            ordered_paths.append(config_path)

    return [(path, self._ui_registry[path]) for path in ordered_paths]
```

### Tab Content Isolation

Each tab should display only its own methods, not inherited or child methods.

**Example**: If you have Library → ShelfManager → Book hierarchy:
- Library tab shows only Library methods
- ShelfManager tab shows only ShelfManager methods
- Book tab shows only Book methods

## UI Registration

### Two-Phase Registration Pattern

Use two-phase registration to avoid circular references:

```python
def _register_ui_components(self, instance: object, cls: type) -> None:
    """Register UI components using two-phase approach."""

    # Phase 1: Collect all classes to register
    classes_to_register = {}  # {base_path: (instance, structure, parent_path)}

    def collect_classes(inst, struct, parent_path=None):
        """Recursively collect all classes to register."""
        cls_path = struct.get("base_path") or parent_path
        if cls_path and cls_path not in classes_to_register:
            classes_to_register[cls_path] = (inst, struct, parent_path)

            # Recurse into children
            for child_info in struct.get("children", []):
                # Find and collect child instances...
                pass

    collect_classes(instance, structure, None)

    # Phase 2: Register all collected classes
    for path, (inst, struct, parent) in classes_to_register.items():
        # Register in _ui_registry...
        pass
```

**Benefits**:
- Avoids circular parent references
- Ensures all classes are found before registration
- Prevents duplicate registration

## Configuration with Pydantic

### Configuration Class Pattern

```python
from pydantic import BaseModel, Field

class DialogSizeConfig(BaseModel):
    """Dialog size configuration."""
    width: str = Field(default="90vw", description="Dialog width (CSS units)")
    height: str = Field(default="85vh", description="Dialog height (CSS units)")

class GridPaddingConfig(BaseModel):
    """Grid cell padding configuration."""
    vertical: str = Field(default="2px", description="Vertical padding")
    horizontal: str = Field(default="4px", description="Horizontal padding")

@apiready(path="/publisher_config")
class PublisherConfig:
    """Publisher configuration with persistence."""

    @apiready
    def set_dialog_size(self, config: DialogSizeConfig) -> dict:
        """Set dialog size preferences."""
        self.set_config("dialog_width", config.width)
        self.set_config("dialog_height", config.height)
        return {"status": "success", "width": config.width, "height": config.height}

    @apiready
    def set_grid_padding(self, config: GridPaddingConfig) -> dict:
        """Set grid cell padding preferences."""
        self.set_config("grid_cell_padding_vertical", config.vertical)
        self.set_config("grid_cell_padding_horizontal", config.horizontal)
        return {"status": "success", "vertical": config.vertical, "horizontal": config.horizontal}
```

**Guidelines**:
- Use Pydantic `BaseModel` for nested parameter structures
- Use `Field` with `description` for documentation
- Config methods should return status dict
- Store config values in SQLite for persistence

## Performance Considerations

### Grid Performance

- Sample only first 10 rows for column width calculation
- Use `domLayout: "normal"` for large datasets (not `autoHeight`)
- Enable virtual scrolling (default in AG Grid)

### WebSocket Efficiency

- Use NiceGUI's automatic WebSocket handling
- Avoid manual socket.io code
- Let NiceGUI manage connection lifecycle

## Common Pitfalls

### ❌ Don't:
- Use shorthand CSS padding (`padding: 2px 4px`)
- Use `maximized` for dialogs
- Mix row and cell selection
- Register UI components multiple times
- Create circular parent references

### ✅ Do:
- Use explicit CSS padding properties
- Use viewport units for dialog sizing
- Enable row selection with `suppressCellFocus`
- Use two-phase registration
- Validate parent relationships before registration

## Testing

When testing NiceGUI interfaces:

1. **Check grid display**: Verify column widths are appropriate
2. **Test row selection**: Ensure entire row highlights
3. **Verify padding**: Check cells have uniform padding
4. **Test dialog sizing**: Ensure dialog is responsive and doesn't cover navigation
5. **Check tab ordering**: Verify depth-first ordering with config last

## Debugging

Enable debug logging to verify:

```python
print(f"DEBUG: UI Registry contents: {list(self._ui_registry.keys())}")
for path, reg in self._ui_registry.items():
    print(f"DEBUG:   {path}: {reg['class_name']} (parent: {reg.get('parent_path')})")
```

---

**Last Updated**: 2025-01-30
**Author**: Genropy Team
