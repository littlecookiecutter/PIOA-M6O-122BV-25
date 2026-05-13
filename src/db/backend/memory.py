from typing import Any


DATABASE: dict[str, list[tuple]] = {}
SCHEMAS: dict[str, dict[str, str]] = {}

TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
}


def create_table(table_name: str, fields_input: str) -> None:
    """Создаёт таблицу с полями и типами."""
    if table_name in DATABASE:
        raise ValueError(f"Таблица '{table_name}' уже существует.")

    schema = {}
    raw_fields = [f.strip() for f in fields_input.split(",") if f.strip()]

    if not raw_fields:
        raise ValueError("Список полей не может быть пустым.")

    for field in raw_fields:
        if ":" in field:
            name, type_name = field.split(":", 1)
            type_name = type_name.strip().lower()
            if type_name not in TYPE_MAP:
                raise ValueError(f"Неподдерживаемый тип: {type_name}. Используйте str, int или float.")
            schema[name.strip()] = type_name
        else:
            schema[field] = "str"

    final_schema = {"id": "int", **schema}
    SCHEMAS[table_name] = final_schema
    DATABASE[table_name] = []


def _get_next_id(table_name: str) -> int:
    """Генерирует следующий ID."""
    if not DATABASE[table_name]:
        return 1
    return max(row[0] for row in DATABASE[table_name]) + 1


def _cast_value(value: str, target_type: str) -> Any:
    """Приводит значение к нужному типу."""
    if value == "":
        return None
    
    try:
        converter = TYPE_MAP[target_type]
        return converter(value)
    except ValueError:
        raise ValueError(f"Некорректный тип данных. Ожидалось: {target_type}.")


def create_record(table_name: str, values_dict: dict[str, str]) -> tuple:
    """Добавляет запись с проверкой типов."""
    if table_name not in DATABASE:
        raise KeyError(f"Таблица '{table_name}' не найдена.")

    schema = SCHEMAS[table_name]
    record_id = _get_next_id(table_name)
    
    processed_values = []
    fields = [f for f in schema.keys() if f != "id"]
    
    for field in fields:
        raw_val = values_dict.get(field, "")
        expected_type = schema[field]
        val = _cast_value(raw_val, expected_type)
        processed_values.append(val)
        
    full_record = (record_id,) + tuple(processed_values)
    DATABASE[table_name].append(full_record)
    return full_record


def select_record(table_name: str, **filters) -> list[tuple]:
    """Выборка с фильтрацией и проверкой типов."""
    if table_name not in DATABASE:
        raise KeyError(f"Таблица '{table_name}' не найдена.")

    data = DATABASE[table_name]
    schema = SCHEMAS[table_name]
    
    if not filters:
        return data.copy()

    result = []
    for row in data:
        match = True
        for field, val in filters.items():
            if field not in schema:
                continue
            
            expected_type = schema[field]
            try:
                typed_val = _cast_value(str(val), expected_type)
            except ValueError:
                raise ValueError(
                    f"Фильтр по полю '{field}' ожидает тип {expected_type}, получено: {val}"
                )

            idx = list(schema.keys()).index(field)
            if row[idx] != typed_val:
                match = False
                break
        if match:
            result.append(row)
    return result


def update_record(table_name: str, record_id: int, **kwargs) -> None:
    """Обновление записи с проверкой типов."""
    if table_name not in DATABASE:
        raise KeyError(f"Таблица '{table_name}' не найдена.")

    schema = SCHEMAS[table_name]
    
    for i, row in enumerate(DATABASE[table_name]):
        if row[0] == record_id:
            new_row = list(row)
            for field, raw_val in kwargs.items():
                if field in schema:
                    new_val = _cast_value(raw_val, schema[field])
                    idx = list(schema.keys()).index(field)
                    new_row[idx] = new_val
            
            DATABASE[table_name][i] = tuple(new_row)
            return
    raise ValueError(f"Запись с id={record_id} не найдена.")


def delete_record(table_name: str, record_id: int) -> None:
    """Удаление по ID."""
    if table_name not in DATABASE:
        raise KeyError(f"Таблица '{table_name}' не найдена.")

    for i, row in enumerate(DATABASE[table_name]):
        if row[0] == record_id:
            DATABASE[table_name].pop(i)
            return
    raise ValueError(f"Запись с id={record_id} не найдена.")


def delete_table(table_name: str) -> None:
    """Удаление таблицы."""
    if table_name not in DATABASE:
        raise KeyError(f"Таблица '{table_name}' не найдена.")
    del DATABASE[table_name]
    del SCHEMAS[table_name]
