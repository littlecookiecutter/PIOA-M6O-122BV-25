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
            val_str = str(value).strip()
            if target_type == "str": return val_str
            if target_type == "int": return int(val_str)
            if target_type == "float": return float(val_str)
            if target_type == "bool": return val_str.lower() in ("true", "1", "yes", "on", "да")
            
            if target_type in ("int_pos", "int_neg"):
                v = int(val_str)
                if target_type == "int_pos" and v < 0: raise ValueError
                if target_type == "int_neg" and v > 0: raise ValueError
                return v
                
            if target_type in ("float_pos", "float_neg"):
                v = float(val_str)
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

        casted_filters = {}
        for k, v in filters.items():
            if k == "id":
                casted_filters[k] = int(v)
            elif k in self.schema:
                casted_filters[k] = self._cast(v, self.schema[k])
            else:
                raise InvalidTypeError(f"Поле '{k}' отсутствует в схеме.")

        idx_field = next((f for f in casted_filters if f in self._indexes), None)
        if idx_field:
            val = casted_filters[idx_field]
            candidates = [self._records[i] for i in self._indexes[idx_field].get(val, [])]
            return [r.copy() for r in candidates if all(r.get(k) == v for k, v in casted_filters.items())]

        return [r.copy() for r in self._records if all(r.get(k) == v for k, v in casted_filters.items())]

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
        for field, idx_dict in self._indexes.items():
            if action == "insert":
                idx_dict.setdefault(rec.get(field), []).append(idx)
            elif action == "delete":
                val = rec.get(field)
                if val in idx_dict:
                    idx_dict[val].remove(idx)
                    idx_dict[val] = [i - 1 if i > idx else i for i in idx_dict[val]]
            elif action == "update" and old:
                ov, nv = old.get(field), rec.get(field)
                if ov != nv:
                    if ov in idx_dict:
                        idx_dict[ov].remove(idx)
                    idx_dict.setdefault(nv, []).append(idx)
                else:
                    idx_dict[nv] = [i - 1 if i > idx else i for i in idx_dict[nv]]

    def to_dict(self) -> dict:
        return {"schema": self.schema, "records": self._records, "next_id": self._next_id, "indexes": self._indexes}

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "Table":
        if not isinstance(data.get("schema"), dict) or not isinstance(data.get("records"), list):
            raise KeyError("Некорректная структура данных таблицы")
        
        t = cls(name, data["schema"], data["records"], data.get("next_id", 1))
        raw_indexes = data.get("indexes", {})
        t._indexes = {}
        for field, idx_map in raw_indexes.items():
            if field in t.schema:
                cast_type = int if t.schema[field] in ("int", "int_pos", "int_neg") else \
                            float if t.schema[field] in ("float", "float_pos", "float_neg") else \
                            bool if t.schema[field] == "bool" else str
                normalized = {}
                for k, v in idx_map.items():
                    try:
                        normalized[cast_type(k)] = v
                    except (ValueError, TypeError):
                        normalized[k] = v
                t._indexes[field] = normalized
            else:
                t._indexes[field] = idx_map
        return t
