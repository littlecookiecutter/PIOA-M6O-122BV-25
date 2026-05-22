from typing import Any

from .errors import (
    DatabaseError,
    DuplicateIDError,
    InvalidTypeError,
    RecordNotFoundError,
    TableNotFoundError,
)


def _cast_str(val: str) -> str:
    return val.strip()

def _cast_int(val: str) -> int:
    return int(val)

def _cast_int_pos(val: str) -> int:
    v = int(val)
    if v < 0:
        raise InvalidTypeError("Ожидается неотрицательное целое число (>= 0)")
    return v

def _cast_int_neg(val: str) -> int:
    v = int(val)
    if v > 0:
        raise InvalidTypeError("Ожидается неположительное целое число (<= 0)")
    return v

def _cast_float(val: str) -> float:
    return float(val)

def _cast_float_pos(val: str) -> float:
    v = float(val)
    if v < 0:
        raise InvalidTypeError("Ожидается неотрицательное число (>= 0.0)")
    return v

def _cast_float_neg(val: str) -> float:
    v = float(val)
    if v > 0:
        raise InvalidTypeError("Ожидается неположительное число (<= 0.0)")
    return v

def _cast_bool(val: str) -> bool:
    norm = val.strip().lower()
    if norm in ("true", "1", "yes", "да", "on"):
        return True
    if norm in ("false", "0", "no", "нет", "off"):
        return False
    raise InvalidTypeError("Ожидается логическое значение (true/false, 1/0, yes/no)")


TYPE_MAP = {
    "str": _cast_str,
    "int": _cast_int,
    "int_pos": _cast_int_pos,
    "int_neg": _cast_int_neg,
    "float": _cast_float,
    "float_pos": _cast_float_pos,
    "float_neg": _cast_float_neg,
    "bool": _cast_bool,
}


class Table:
    def __init__(self, name: str, schema: dict[str, str]) -> None:
        self.name = name
        self.schema = {"id": "int", **schema}
        self._records: list[tuple] = []
        self._next_id = 1

    def _cast(self, value: str, target_type: str) -> Any:
        if value == "":
            return None
        try:
            converter = TYPE_MAP[target_type]
            return converter(value)
        except KeyError:
            raise InvalidTypeError(f"Неизвестный тип: {target_type}")
        except ValueError:
            raise InvalidTypeError(f"Не удалось преобразовать '{value}' к типу {target_type}")

    def create_record(self, **kwargs) -> tuple:
        for field in kwargs:
            if field not in self.schema:
                raise InvalidTypeError(f"Поле '{field}' отсутствует в схеме.")

        for field, raw in kwargs.items():
            kwargs[field] = self._cast(raw, self.schema[field])

        if self._next_id in (r[0] for r in self._records):
            raise DuplicateIDError(f"Запись с id={self._next_id} уже существует.")

        fields = [f for f in self.schema if f != "id"]
        record = (self._next_id,) + tuple(kwargs.get(f) for f in fields)
        self._records.append(record)
        self._next_id += 1
        return record

    def select_record(self, **filters) -> list[tuple]:
        if not filters:
            return self._records.copy()

        result = []
        for row in self._records:
            match = True
            for field, val in filters.items():
                if field not in self.schema:
                    continue
                try:
                    typed_val = self._cast(str(val), self.schema[field])
                except InvalidTypeError:
                    continue
                idx = list(self.schema.keys()).index(field)
                if row[idx] != typed_val:
                    match = False
                    break
            if match:
                result.append(row)
        return result

    def update_record(self, record_id: int, **kwargs) -> None:
        for i, row in enumerate(self._records):
            if row[0] == record_id:
                new_row = list(row)
                for field, raw in kwargs.items():
                    if field in self.schema:
                        idx = list(self.schema.keys()).index(field)
                        new_row[idx] = self._cast(raw, self.schema[field])
                self._records[i] = tuple(new_row)
                return
        raise RecordNotFoundError(f"Запись с id={record_id} не найдена.")

    def delete_record(self, record_id: int) -> None:
        for i, row in enumerate(self._records):
            if row[0] == record_id:
                self._records.pop(i)
                return
        raise RecordNotFoundError(f"Запись с id={record_id} не найдена.")

    def sort_records(self, field: str, reverse: bool = False) -> list[tuple]:
        if field not in self.schema:
            raise InvalidTypeError(f"Поле '{field}' отсутствует в схеме.")
        idx = list(self.schema.keys()).index(field)
        return sorted(self._records, key=lambda r: (r[idx] is None, r[idx]), reverse=reverse)


class Database:
    def __init__(self) -> None:
        self._tables: dict[str, Table] = {}

    def create_table(self, name: str, fields_input: str) -> None:
        if name in self._tables:
            raise DatabaseError(f"Таблица '{name}' уже существует.")

        schema = {}
        for part in fields_input.split(","):
            part = part.strip()
            if ":" in part:
                fname, ftype = part.split(":", 1)
                ftype = ftype.strip().lower()
                if ftype not in TYPE_MAP:
                    raise InvalidTypeError(f"Неподдерживаемый тип: {ftype}")
                schema[fname.strip()] = ftype
            else:
                schema[part] = "str"

        self._tables[name] = Table(name, schema)

    def delete_table(self, name: str) -> None:
        if name not in self._tables:
            raise TableNotFoundError(f"Таблица '{name}' не найдена.")
        del self._tables[name]

    def get_table(self, name: str) -> Table:
        if name not in self._tables:
            raise TableNotFoundError(f"Таблица '{name}' не найдена.")
        return self._tables[name]
