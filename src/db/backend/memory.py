from .base import Database
from .table import Table
from .errors import TableNotFoundError

class MemoryDatabase(Database):
    def __init__(self) -> None:
        self._tables: dict[str, Table] = {}

    def _table_exists(self, name: str) -> bool:
        return name in self._tables

    def _load_table(self, name: str) -> Table:
        if name not in self._tables:
            raise TableNotFoundError(f"Таблица '{name}' не найдена.")
        return self._tables[name]

    def _save_table(self, name: str, table: Table) -> None:
        self._tables[name] = table

    def _get_table_names(self) -> list[str]:
        return list(self._tables.keys())

    def _drop_table(self, name: str) -> None:
        del self._tables[name]
