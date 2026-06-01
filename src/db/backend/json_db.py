import json
from pathlib import Path
from .base import Database
from .table import Table
from .errors import TableNotFoundError, CorruptedDataError

class JSONDatabase(Database):
    def __init__(self, directory: str = "data/json") -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self._dir / f"{name}.json"

    def _table_exists(self, name: str) -> bool:
        return self._path(name).exists()

    def _get_table_names(self) -> list[str]:
        return [p.stem for p in self._dir.glob("*.json")]

    def _load_table(self, name: str) -> Table:
        p = self._path(name)
        if not p.exists():
            raise TableNotFoundError(f"Таблица '{name}' не найдена.")
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return Table.from_dict(name, data)
        except (json.JSONDecodeError, KeyError) as e:
            raise CorruptedDataError(f"Битые данные: {e}")

    def _save_table(self, name: str, table: Table) -> None:
        with self._path(name).open("w", encoding="utf-8") as f:
            json.dump(table.to_dict(), f, ensure_ascii=False, indent=2)

    def _drop_table(self, name: str) -> None:
        self._path(name).unlink(missing_ok=True)
