"""
SQLite Database Utilities

A simple SQLite database toolkit inspired by R's DBI package.
Focused on table operations and data inspection capabilities.
Provides a clean API for examining and managing SQLite database tables.
"""

import sqlite3
import pandas as pd
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime


class SQLiteError(Exception):
    """Base exception class for SQLite operations"""

    pass


class ConnectionError(SQLiteError):
    """Connection-related errors"""

    pass


class TableNotFoundError(SQLiteError):
    """Table not found errors"""

    pass


class QueryError(SQLiteError):
    """Query execution errors"""

    pass


class SQLiteConnection:
    """
    SQLite Database Connection Class

    Provides core functionality for table operations and data inspection.
    Focuses on database table examination and management.
    Supports context manager for automatic connection lifecycle management.
    """

    def __init__(self, database_path: str):
        """
        Initialize database connection

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = Path(database_path)
        self._connection = None
        self._connect()

    def _connect(self):
        """Establish database connection"""
        try:
            # Check if database file exists
            if not self.database_path.exists():
                raise FileNotFoundError(f"Database file does not exist: {self.database_path}")

            self._connection = sqlite3.connect(str(self.database_path))
            self._connection.row_factory = sqlite3.Row  # Return dict-like row objects
        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect to database {self.database_path}: {e}")

    def __enter__(self) -> "SQLiteConnection":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def close(self):
        """Close database connection"""
        if self._connection:
            try:
                self._connection.close()
            except sqlite3.Error:
                pass  # Ignore errors during closing
            finally:
                self._connection = None

    @property
    def is_connected(self) -> bool:
        """Check if connection is valid"""
        return self._connection is not None

    def _execute_query(self, query: str, params: tuple = None) -> sqlite3.Cursor:
        """Internal method to execute queries"""
        if not self.is_connected:
            raise ConnectionError("Database connection is closed")

        try:
            cursor = self._connection.execute(query, params or ())
            return cursor
        except sqlite3.Error as e:
            raise QueryError(f"Query execution failed: {e}")

    def list_tables(self) -> List[str]:
        """
        List all table names in the database

        Returns:
            List of strings containing all table names
        """
        cursor = self._execute_query("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)
        return [row['name'] for row in cursor.fetchall()]

    def table_exists(self, table_name: str) -> bool:
        """
        Check if specified table exists

        Args:
            table_name: Name of table to check

        Returns:
            True if table exists, False otherwise
        """
        cursor = self._execute_query(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        """,
            (table_name,),
        )
        return cursor.fetchone() is not None

    def get_row_count(self, table_name: str) -> int:
        """
        Get total number of rows in table

        Args:
            table_name: Table name

        Returns:
            Number of rows in the table
        """
        if not self.table_exists(table_name):
            raise TableNotFoundError(f"Table '{table_name}' does not exist")

        cursor = self._execute_query(f"SELECT COUNT(*) FROM `{table_name}`")
        return cursor.fetchone()[0]

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get detailed column information for a table

        Args:
            table_name: Table name

        Returns:
            List of dictionaries containing column information:
            - name: Column name
            - type: Data type
            - notnull: Whether NULL values are not allowed
            - pk: Whether column is part of primary key
            - default: Default value
        """
        if not self.table_exists(table_name):
            raise TableNotFoundError(f"Table '{table_name}' does not exist")

        cursor = self._execute_query(f"PRAGMA table_info(`{table_name}`)")
        columns = []

        for row in cursor.fetchall():
            columns.append(
                {
                    "name": row["name"],
                    "type": row["type"],
                    "notnull": bool(row["notnull"]),
                    "pk": bool(row["pk"]),
                    "default": row["dflt_value"],
                }
            )

        return columns

    def preview_table(self, table_name: str, n: int = 5) -> pd.DataFrame:
        """
        Preview first N rows of a table

        Args:
            table_name: Table name
            n: Number of rows to preview (default 5)

        Returns:
            pandas DataFrame containing first N rows of data
        """
        if not self.table_exists(table_name):
            raise TableNotFoundError(f"Table '{table_name}' does not exist")

        cursor = self._execute_query(f"SELECT * FROM `{table_name}` LIMIT ?", (n,))
        rows = cursor.fetchall()

        if not rows:
            return pd.DataFrame()

        # Convert sqlite3.Row objects to list of dictionaries
        data = [dict(row) for row in rows]
        return pd.DataFrame(data)

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get basic information about a table

        Args:
            table_name: Table name

        Returns:
            Dictionary containing basic table information:
            - name: Table name
            - row_count: Number of rows
            - column_count: Number of columns
            - columns: List of column names
        """
        if not self.table_exists(table_name):
            raise TableNotFoundError(f"Table '{table_name}' does not exist")

        columns = self.get_columns(table_name)
        row_count = self.get_row_count(table_name)

        return {
            "name": table_name,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": [col["name"] for col in columns],
        }

    def get_table_summary(self, table_name: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a table

        Args:
            table_name: Table name

        Returns:
            Dictionary containing comprehensive table information
        """
        if not self.table_exists(table_name):
            raise TableNotFoundError(f"Table '{table_name}' does not exist")

        basic_info = self.get_table_info(table_name)
        columns = self.get_columns(table_name)
        preview = self.preview_table(table_name, n=3)

        summary = {
            "basic_info": basic_info,
            "columns": columns,
            "data_preview": preview.to_dict("records") if not preview.empty else [],
            "generated_at": datetime.now().isoformat(),
        }

        return summary

    def inspect_table(self, table_name: str) -> Dict[str, Any]:
        """
        Get complete information about a table in one call

        Args:
            table_name: Table name

        Returns:
            Complete table information dictionary
        """
        return self.get_table_summary(table_name)

    def overview_database(self) -> Dict[str, Any]:
        """
        Get overview information for the entire database

        Returns:
            Dictionary containing database overview information
        """
        tables = self.list_tables()

        if not tables:
            return {
                "total_tables": 0,
                "total_size": 0,
                "tables": [],
                "generated_at": datetime.now().isoformat(),
            }

        table_summaries = []
        total_size = self.database_path.stat().st_size if self.database_path.exists() else 0

        for table_name in tables:
            try:
                table_info = self.get_table_info(table_name)
                table_summaries.append(table_info)
            except Exception as e:
                # Skip problematic tables
                table_summaries.append({"name": table_name, "error": str(e)})

        # Sort by row count to find largest tables
        valid_tables = [t for t in table_summaries if "error" not in t]
        largest_tables = sorted(valid_tables, key=lambda x: x["row_count"], reverse=True)[:5]

        return {
            "total_tables": len(tables),
            "total_size": total_size,
            "tables": table_summaries,
            "largest_tables": largest_tables,
            "generated_at": datetime.now().isoformat(),
        }


def connect(database_path: str) -> SQLiteConnection:
    """
    Convenience function to create a database connection

    Args:
        database_path: Path to database file

    Returns:
        SQLiteConnection instance
    """
    return SQLiteConnection(database_path)


def quick_look(database_path: str, table_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick look at database or table information

    Args:
        database_path: Path to database file
        table_name: Specific table name (optional)

    Returns:
        Database or table summary information
    """
    with SQLiteConnection(database_path) as db:
        if table_name:
            if not db.table_exists(table_name):
                raise TableNotFoundError(f"Table '{table_name}' does not exist")
            return db.inspect_table(table_name)
        else:
            return db.overview_database()


# Aliases for backward compatibility
SQLiteDB = SQLiteConnection
connect_db = connect
