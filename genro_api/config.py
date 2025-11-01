"""Publisher configuration with persistent storage."""

import sqlite3
from typing import Annotated

from pydantic import BaseModel, Field
from genro_core.decorators import apiready


class DialogSizeConfig(BaseModel):
    """Configuration for dialog dimensions."""
    width: str = Field(default="90vw", description="Dialog width (CSS units)")
    height: str = Field(default="85vh", description="Dialog height (CSS units)")


class GridPaddingConfig(BaseModel):
    """Configuration for grid cell padding."""
    vertical: str = Field(default="2px", description="Vertical padding")
    horizontal: str = Field(default="4px", description="Horizontal padding")


@apiready(path="/publisher_config")
class PublisherConfig:
    """
    Configuration for Publisher UI with SQLite persistence.

    Stores user preferences for dialog sizes, grid appearance, etc.
    """

    # Default configuration values
    DEFAULTS = {
        "dialog_width": "90vw",
        "dialog_height": "85vh",
        "grid_cell_padding_vertical": "2px",
        "grid_cell_padding_horizontal": "4px",
        "grid_show_borders": "true",
    }

    def __init__(self, db_path: str = ":memory:"):
        """
        Initialize configuration with SQLite database.

        Args:
            db_path: Path to SQLite database file. Use ":memory:" for in-memory.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_table()
        self._init_defaults()

    def _create_table(self) -> None:
        """Create config table if it doesn't exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publisher_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT
            )
        """)
        self.conn.commit()

    def _init_defaults(self) -> None:
        """Initialize default config values if not present."""
        cursor = self.conn.cursor()
        for key, value in self.DEFAULTS.items():
            cursor.execute(
                "INSERT OR IGNORE INTO publisher_config (key, value) VALUES (?, ?)",
                (key, value)
            )
        self.conn.commit()

    @apiready
    def get_config(
        self, key: Annotated[str, "Configuration key"]
    ) -> str:
        """Get a configuration value."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT value FROM publisher_config WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if not row:
            return self.DEFAULTS.get(key, "")
        return row["value"]

    @apiready
    def set_config(
        self,
        key: Annotated[str, "Configuration key"],
        value: Annotated[str, "Configuration value"]
    ) -> dict:
        """Set a configuration value."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO publisher_config (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()
        return {"key": key, "value": value, "status": "updated"}

    @apiready
    def list_all_config(self) -> list[dict]:
        """List all configuration values."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM publisher_config ORDER BY key")
        return [
            {"key": row["key"], "value": row["value"]}
            for row in cursor.fetchall()
        ]

    @apiready
    def set_dialog_size(self, config: DialogSizeConfig) -> dict:
        """Set dialog size preferences."""
        self.set_config("dialog_width", config.width)
        self.set_config("dialog_height", config.height)
        return {
            "width": config.width,
            "height": config.height,
            "status": "Dialog size updated. Refresh page to apply."
        }

    @apiready
    def set_grid_padding(self, config: GridPaddingConfig) -> dict:
        """Set grid cell padding."""
        self.set_config("grid_cell_padding_vertical", config.vertical)
        self.set_config("grid_cell_padding_horizontal", config.horizontal)
        return {
            "vertical": config.vertical,
            "horizontal": config.horizontal,
            "status": "Grid padding updated. Refresh page to apply."
        }

    @apiready
    def reset_to_defaults(self) -> dict:
        """Reset all configuration to default values."""
        cursor = self.conn.cursor()
        for key, value in self.DEFAULTS.items():
            cursor.execute(
                "INSERT OR REPLACE INTO publisher_config (key, value) VALUES (?, ?)",
                (key, value)
            )
        self.conn.commit()
        return {"status": "Configuration reset to defaults. Refresh page to apply."}

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
