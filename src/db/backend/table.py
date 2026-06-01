from typing import Any
from .errors import InvalidTypeError, RecordNotFoundError

class Table:
    def __init__(self, name: str, schema: dict[str, str], records: list[dict] | None = None, next_id: int = 1) -> None:
        self.name = name
        self.schema = schema
        self._records: list[dict] = records or []
        self._next_id = next_id
        self._indexes: dict[str, dict[Any, list[int]]] = {}

    @staticmethod
    def _cast(value: Any, target_type: str) -> Any:
        if value is None or value == "":
            return None
        try:
            if target_type == "str": return str(value).strip()
            if target_type == "int": return int(value)
            if target_type == "float": return float(value)
            if target_type == "bool": return str(value).lower() in ("true", "1", "yes", "on", "да")
            
            if target_type in ("int_pos", "int_neg"):
                v = int(value)
                if target_type == "int_pos" and v < 0: raise ValueError
                if target_type == "int_neg" and v > 0: raise ValueError
                return v
                
            if target_type in ("float_pos", "float_neg"):
                v = float(value)
                if target_type == "float_pos" and v < 0: raise ValueError
                if target_type == "float_neg" and v > 0: raise ValueError
                return v
        except ValueError:
            raise InvalidTypeError(f"Неверный тип для '{value}'. Ожидалось: {target_type}")

    def insert(self, **kwargs) -> dict:
        for field, raw in kwargs.items():
            if field not in self.schema:
                raise InvalidTypeError(f"Поле '{field}' не в схеме.")
            kwargs[field] = self._cast(raw, self.schema[field])

        record = {"id": self._next_id, **kwargs}
        self._records.append(record)
        self._next_id += 1
        self._update_indexes("insert", record, len(self._records) - 1)
        return record

    def select(self, **filters) -> list[dict]:
        if not filters:
            return [r.copy() for r in self._records]

        # Игнорируем поля, которых нет в схеме
        valid_filters = {k: v for k, v in filters.items() if k in self.schema}
        if not valid_filters:
            return [r.copy() for r in self._records]

        idx_field = next((f for f in valid_filters if f in self._indexes), None)
        if idx_field:
            # Приводим значение фильтра к типу схемы для поиска
            val = self._cast(valid_filters[idx_field], self.schema[idx_field])
            candidates = [self._records[i] for i in self._indexes[idx_field].get(val, [])]
            return [r.copy() for r in candidates if all(r.get(k) == v for k, v in valid_filters.items())]

        return [r.copy() for r in self._records if all(r.get(k) == v for k, v in valid_filters.items())]

    def update(self, record_id: int, **kwargs) -> None:
        for i, rec in enumerate(self._records):
            if rec["id"] == record_id:
                old = rec.copy()
                for f, raw in kwargs.items():
                    if f != "id" and f in self.schema:
                        rec[f] = self._cast(raw, self.schema[f])
                self._update_indexes("update", rec, i, old)
                return
        raise RecordNotFoundError(f"Запись id={record_id} не найдена.")

    def delete(self, record_id: int) -> None:
        for i, rec in enumerate(self._records):
            if rec["id"] == record_id:
                self._update_indexes("delete", rec, i)
                self._records.pop(i)
                return
        raise RecordNotFoundError(f"Запись id={record_id} не найдена.")

    def sort(self, field: str, reverse: bool = False) -> list[dict]:
        if field not in self.schema:
            raise InvalidTypeError(f"Поле '{field}' не в схеме.")
        return sorted(self._records, key=lambda r: (r[field] is None, r[field]), reverse=reverse)

    def create_index(self, field: str) -> None:
        if field not in self.schema:
            raise InvalidTypeError(f"Поле '{field}' не в схеме.")
        self._indexes[field] = {}
        for i, rec in enumerate(self._records):
            self._indexes[field].setdefault(rec.get(field), []).append(i)

    def _update_indexes(self, action: str, rec: dict, idx: int, old: dict | None = None) -> None:
        for field, index in self._indexes.items():
            if action == "insert":
                index.setdefault(rec.get(field), []).append(idx)
            elif action == "delete":
                val = rec.get(field)
                if val in index:
                    index[val].remove(idx)
                    index[val] = [i - 1 if i > idx else i for i in index[val]]
            elif action == "update" and old:
                for f in self._indexes:
                    ov, nv = old.get(f), rec.get(f)
                    if ov != nv:
                        if ov in index: index[ov].remove(idx)
                        index.setdefault(nv, []).append(idx)
                    else:
                        index[nv] = [i - 1 if i > idx else i for i in index[nv]]

    def to_dict(self) -> dict:
        return {"schema": self.schema, "records": self._records, "next_id": self._next_id, "indexes": self._indexes}

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "Table":
        t = cls(name, data["schema"], data["records"], data["next_id"])
        t._indexes = data.get("indexes", {})
        return t
