from abc import ABC, abstractmethod
from .table import Table
from .errors import TableNotFoundError, TableAlreadyExistsError

class Database(ABC):
    def create_table(self, name: str, schema: dict[str, str]) -> None:
        if self._table_exists(name):
            raise TableAlreadyExistsError(f"Таблица '{name}' уже существует.")
        self._save_table(name, Table(name, schema))

    def insert(self, table_name: str, **kwargs) -> dict:
        t = self._load_table(table_name)
        rec = t.insert(**kwargs)
        self._save_table(table_name, t)
        return rec

    def select(self, table_name: str, **filters) -> list[dict]:
        return self._load_table(table_name).select(**filters)

    def update(self, table_name: str, record_id: int, **kwargs) -> None:
        t = self._load_table(table_name)
        t.update(record_id, **kwargs)
        self._save_table(table_name, t)

    def delete(self, table_name: str, record_id: int) -> None:
        t = self._load_table(table_name)
        t.delete(record_id)
        self._save_table(table_name, t)

    def sort(self, table_name: str, field: str, reverse: bool = False) -> list[dict]:
        return self._load_table(table_name).sort(field, reverse)

    def create_index(self, table_name: str, field: str) -> None:
        t = self._load_table(table_name)
        t.create_index(field)
        self._save_table(table_name, t)

    def drop_table(self, table_name: str) -> None:
        if not self._table_exists(table_name):
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        self._drop_table(table_name)

    def list_tables(self) -> list[str]:
        return self._get_table_names()

    def get_schema(self, table_name: str) -> dict[str, str]:
        return self._load_table(table_name).schema

    @abstractmethod
    def _table_exists(self, name: str) -> bool: pass
    @abstractmethod
    def _load_table(self, name: str) -> Table: pass
    @abstractmethod
    def _save_table(self, name: str, table: Table) -> None: pass
    @abstractmethod
    def _get_table_names(self) -> list[str]: pass
    @abstractmethod
    def _drop_table(self, name: str) -> None: pass
