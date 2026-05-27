from .backend import memory

current_table: str | None = None


def _print_menu() -> None:
    print("\n=== In-Memory База Данных ===")
    if current_table:
        print(f"Текущая таблица: {current_table}")
    else:
        print("[!] Таблица не выбрана")
    print("1. Создать таблицу")
    print("2. Выбрать таблицу")
    print("3. Добавить запись")
    print("4. Показать все записи")
    print("5. Найти по фильтру")
    print("6. Обновить запись")
    print("7. Удалить запись")
    print("8. Удалить таблицу")
    print("0. Выход")


def _read_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            return int(raw)
        except ValueError:
            print("Ошибка: введите целое число.")


def _create_table_ui() -> None:
    global current_table
    print("\nСоздание новой таблицы")
    name = input("Имя таблицы: ").strip()
    
    print("Пример: name:str, age:int, salary:float")
    fields_input = input("Поля (имя:тип): ").strip()

    if not fields_input:
        print("Ошибка: укажите хотя бы одно поле.")
        return

    try:
        memory.create_table(name, fields_input)
        current_table = name
        print(f"Таблица '{name}' создана.")
    except ValueError as e:
        print(f"Ошибка: {e}")


def _select_table_ui() -> None:
    global current_table
    if not memory.DATABASE:
        print("Таблиц нет. Сначала создайте таблицу.")
        return

    print("\nДоступные таблицы:")
    keys = list(memory.DATABASE.keys())
    for i, name in enumerate(keys, 1):
        fields = list(memory.SCHEMAS[name].keys())
        fields.remove("id") 
        print(f"{i}. {name} (поля: {', '.join(fields)})")

    choice = _read_int("Выберите номер таблицы: ")
    if 1 <= choice <= len(keys):
        current_table = keys[choice - 1]
        print(f"Выбрана таблица: {current_table}")
    else:
        print("Ошибка: неверный номер.")


def _delete_table_ui() -> None:
    global current_table
    if not memory.DATABASE:
        print("Таблиц нет.")
        return

    print("\nТаблицы для удаления:")
    keys = list(memory.DATABASE.keys())
    for i, name in enumerate(keys, 1):
        print(f"{i}. {name}")

    choice = _read_int("Номер таблицы для удаления: ")
    if 1 <= choice <= len(keys):
        name_to_delete = keys[choice - 1]
        confirm = input(f"Удалить '{name_to_delete}'? (y/n): ").strip().lower()
        if confirm == "y":
            try:
                memory.delete_table(name_to_delete)
                if current_table == name_to_delete:
                    current_table = None
                print(f"Таблица '{name_to_delete}' удалена.")
            except KeyError as e:
                print(f"Ошибка: {e}")
        else:
            print("Отмена.")
    else:
        print("Ошибка: неверный номер.")


def _ensure_table() -> bool:
    if not current_table:
        print("Ошибка: сначала создайте или выберите таблицу.")
        return False
    return True


def _add_record() -> None:
    if not _ensure_table():
        return

    schema = memory.SCHEMAS[current_table]
    fields = [f for f in schema.keys() if f != "id"]

    print(f"\nДобавление записи в '{current_table}'")
    print("(Enter - оставить пустым)")

    kwargs = {}
    for field in fields:
        field_type = schema[field]
        val = input(f"{field} ({field_type}): ").strip()
        kwargs[field] = val

    try:
        record = memory.create_record(current_table, kwargs)
        print(f"Запись добавлена: {record}")
    except (ValueError, KeyError) as e:
        print(f"Ошибка: {e}")


def _show_all() -> None:
    if not _ensure_table():
        return
    print(f"\nВсе записи в '{current_table}':")
    records = memory.select_record(current_table)
    if not records:
        print("Записей нет.")
    for r in records:
        print(r)


def _find_by_filter() -> None:
    if not _ensure_table():
        return

    schema = memory.SCHEMAS[current_table]
    fields = list(schema.keys())

    print(f"\nПоиск в '{current_table}'")
    print("(Enter - пропустить поле)")

    filters = {}
    for field in fields:
        val = input(f"{field}: ").strip()
        if val:
            filters[field] = val

    try:
        records = memory.select_record(current_table, **filters)
        print(f"\nНайдено: {len(records)}")
        for r in records:
            print(r)
    except (ValueError, KeyError) as e:
        print(f"Ошибка: {e}")


def _update_record() -> None:
    if not _ensure_table():
        return

    schema = memory.SCHEMAS[current_table]
    fields = [f for f in schema.keys() if f != "id"]

    record_id = _read_int("ID записи для обновления: ")
    print("Новые данные (Enter - не менять):")

    kwargs = {}
    for field in fields:
        val = input(f"{field}: ").strip()
        if val:
            kwargs[field] = val

    if not kwargs:
        print("Отмена.")
        return

    try:
        memory.update_record(current_table, record_id, **kwargs)
        print("Запись обновлена.")
    except (ValueError, KeyError) as e:
        print(f"Ошибка: {e}")


def _delete_record() -> None:
    if not _ensure_table():
        return
    print(f"\nУдаление записи из '{current_table}'")
    record_id = _read_int("ID записи: ")
    try:
        memory.delete_record(current_table, record_id)
        print("Запись удалена.")
    except (ValueError, KeyError) as e:
        print(f"Ошибка: {e}")


def run() -> None:
    """Запуск основного цикла интерфейса."""
    while True:
        try:
            _print_menu()
            action = input("Выберите действие: ").strip()

            if action == "1":
                _create_table_ui()
            elif action == "2":
                _select_table_ui()
            elif action == "3":
                _add_record()
            elif action == "4":
                _show_all()
            elif action == "5":
                _find_by_filter()
            elif action == "6":
                _update_record()
            elif action == "7":
                _delete_record()
            elif action == "8":
                _delete_table_ui()
            elif action == "0":
                print("Выход из программы.")
                break
            else:
                print("Неизвестная команда.")
        except KeyboardInterrupt:
            print("\nВыход.")
            break
        except (ValueError, KeyError) as e:
            print(f"Ошибка: {e}")
