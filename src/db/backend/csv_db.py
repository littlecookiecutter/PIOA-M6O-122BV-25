import csv
import json
from pathlib import Path
from .base import Database
from .table import Table
from .errors import TableNotFoundError, CorruptedDataError

class CSVDatabase(Database):
    def __init__(self, directory: str = "data/csv") -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _paths(self, name: str) -> tuple[Path, Path]:
        return self._dir / f"{name}.csv", self._dir / f"{name}.meta.json"

    def _table_exists(self, name: str) -> bool:
        return self._paths(name)[0].exists()

    def _get_table_names(self) -> list[str]:
        return [p.stem for p in self._dir.glob("*.csv")]

    @staticmethod
    def _parse_csv_row(row: dict, schema: dict[str, str]) -> dict:
        parsed = {}
        for key, val in row.items():
            if key == "id":
                parsed[key] = int(val)
            elif key in schema:
                parsed[key] = Table._cast(val, schema[key])
        return parsed

    def _load_table(self, name: str) -> Table:
        csv_p, meta_p = self._paths(name)
        if not csv_p.exists():
            raise TableNotFoundError(f"Таблица '{name}' не найдена.")
        try:
            if not meta_p.exists():
                raise FileNotFoundError("Отсутствует метафайл")
            with meta_p.open("r", encoding="utf-8") as f:
                meta = json.load(f)
            if not isinstance(meta, dict) or "schema" not in meta or "next_id" not in meta:
                raise ValueError("Некорректный метафайл")
            with csv_p.open("r", encoding="utf-8") as f:
                records = [self._parse_csv_row(row, meta["schema"]) for row in csv.DictReader(f)]
            return Table.from_dict(name, {**meta, "records": records})
        except (json.JSONDecodeError, csv.Error, KeyError, ValueError, FileNotFoundError) as e:
            raise CorruptedDataError(f"Битые данные: {e}")

    def _save_table(self, name: str, table: Table) -> None:
        csv_p, meta_p = self._paths(name)
        meta = table.to_dict()
        meta.pop("records", None)
        with meta_p.open("w", encoding="utf-8") as f:
            json.dump(meta, f)
        if table._records:
            with csv_p.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(table.schema.keys()) + ["id"])
                writer.writeheader()
                for rec in table._records:
                    writer.writerow(rec)
        else:
            csv_p.touch()

    def _drop_table(self, name: str) -> None:
        for p in self._paths(name):
            p.unlink(missing_ok=True)
