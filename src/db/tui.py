from .backend.memory import Database
from .backend.errors import DatabaseError, InvalidTypeError, RecordNotFoundError, TableNotFoundError


class DatabaseApp:
    def __init__(self) -> None:
        self.db = Database()
        self.current_table_name: str | None = None

    def _print_menu(self) -> None:
        print("\n=== In-Memory База Данных ===")
        if self.current_table_name:
            print(f"Текущая таблица: {self.current_table_name}")
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
        print("9. Сортировать записи")
        print("0. Выход")

    def _read_int(self, prompt: str) -> int:
        while True:
            raw = input(prompt).strip()
            try:
                return int(raw)
            except ValueError:
                print("Ошибка: введите целое число.")

    def _ensure_table(self) -> bool:
        if not self.current_table_name:
            print("Ошибка: сначала создайте или выберите таблицу.")
            return False
        return True

    def _create_table(self) -> None:
        print("\nСоздание новой таблицы")
        name = input("Имя таблицы: ").strip()
        print("Доступные типы: str, int, float, bool, int_pos, int_neg, float_pos, float_neg")
        fields_input = input("Поля (формат имя:тип, через запятую): ").strip()
        if not fields_input:
            print("Ошибка: укажите хотя бы одно поле.")
            return
        try:
            self.db.create_table(name, fields_input)
            self.current_table_name = name
            print(f"Таблица '{name}' создана.")
        except (DatabaseError, InvalidTypeError) as e:
            print(f"Ошибка: {e}")

    def _select_table(self) -> None:
        if not self.db._tables:
            print("Таблиц нет. Сначала создайте таблицу.")
            return
        print("\nДоступные таблицы:")
        keys = list(self.db._tables.keys())
        for i, name in enumerate(keys, 1):
            fields = list(self.db._tables[name].schema.keys())
            fields.remove("id")
            print(f"{i}. {name} (поля: {', '.join(fields)})")
        choice = self._read_int("Выберите номер таблицы: ")
        if 1 <= choice <= len(keys):
            self.current_table_name = keys[choice - 1]
            print(f"Выбрана таблица: {self.current_table_name}")
        else:
            print("Ошибка: неверный номер.")

    def _add_record(self) -> None:
        if not self._ensure_table():
            return
        table = self.db.get_table(self.current_table_name)
        fields = [f for f in table.schema if f != "id"]
        print(f"\nДобавление записи в '{self.current_table_name}'")
        print("(Enter - оставить пустым)")
        kwargs = {}
        for field in fields:
            field_type = table.schema[field]
            val = input(f"{field} ({field_type}): ").strip()
            kwargs[field] = val
        try:
            record = table.create_record(**kwargs)
            print(f"Запись добавлена: {record}")
        except (InvalidTypeError, DatabaseError) as e:
            print(f"Ошибка: {e}")

    def _show_all(self) -> None:
        if not self._ensure_table():
            return
        table = self.db.get_table(self.current_table_name)
        print(f"\nВсе записи в '{self.current_table_name}':")
        records = table.select_record()
        if not records:
            print("Записей нет.")
        for r in records:
            print(r)

    def _find_by_filter(self) -> None:
        if not self._ensure_table():
            return
        table = self.db.get_table(self.current_table_name)
        fields = list(table.schema.keys())
        print(f"\nПоиск в '{self.current_table_name}'")
        print("(Enter - пропустить поле)")
        filters = {}
        for field in fields:
            val = input(f"{field}: ").strip()
            if val:
                filters[field] = val
        try:
            records = table.select_record(**filters)
            print(f"\nНайдено: {len(records)}")
            for r in records:
                print(r)
        except Exception as e:
            print(f"Ошибка при поиске: {e}")

    def _update_record(self) -> None:
        if not self._ensure_table():
            return
        table = self.db.get_table(self.current_table_name)
        record_id = self._read_int("ID записи для обновления: ")
        print("Новые данные (Enter - не менять):")
        fields = [f for f in table.schema if f != "id"]
        kwargs = {}
        for field in fields:
            val = input(f"{field}: ").strip()
            if val:
                kwargs[field] = val
        if not kwargs:
            print("Отмена.")
            return
        try:
            table.update_record(record_id, **kwargs)
            print("Запись обновлена.")
        except (RecordNotFoundError, InvalidTypeError, DatabaseError) as e:
            print(f"Ошибка: {e}")

    def _delete_record(self) -> None:
        if not self._ensure_table():
            return
        table = self.db.get_table(self.current_table_name)
        record_id = self._read_int("ID записи: ")
        try:
            table.delete_record(record_id)
            print("Запись удалена.")
        except (RecordNotFoundError, DatabaseError) as e:
            print(f"Ошибка: {e}")

    def _delete_table(self) -> None:
        if not self.db._tables:
            print("Таблиц нет.")
            return
        print("\nТаблицы для удаления:")
        keys = list(self.db._tables.keys())
        for i, name in enumerate(keys, 1):
            print(f"{i}. {name}")
        choice = self._read_int("Номер таблицы для удаления: ")
        if 1 <= choice <= len(keys):
            name_to_delete = keys[choice - 1]
            confirm = input(f"Удалить '{name_to_delete}'? (y/n): ").strip().lower()
            if confirm == "y":
                try:
                    self.db.delete_table(name_to_delete)
                    if self.current_table_name == name_to_delete:
                        self.current_table_name = None
                    print(f"Таблица '{name_to_delete}' удалена.")
                except TableNotFoundError as e:
                    print(f"Ошибка: {e}")
            else:
                print("Отмена.")
        else:
            print("Ошибка: неверный номер.")

    def _sort_records(self) -> None:
        if not self._ensure_table():
            return
        table = self.db.get_table(self.current_table_name)
        print(f"\nСортировка записей в '{self.current_table_name}'")
        print("Доступные поля:", ", ".join(table.schema.keys()))
        field = input("Поле для сортировки: ").strip()
        reverse = input("По убыванию? (y/n): ").strip().lower() == "y"
        try:
            sorted_data = table.sort_records(field, reverse)
            print(f"Отсортировано по '{field}':")
            for r in sorted_data:
                print(r)
        except (InvalidTypeError, DatabaseError) as e:
            print(f"Ошибка: {e}")

    def run(self) -> None:
        while True:
            try:
                self._print_menu()
                action = input("Выберите действие: ").strip()
                if action == "1":
                    self._create_table()
                elif action == "2":
                    self._select_table()
                elif action == "3":
                    self._add_record()
                elif action == "4":
                    self._show_all()
                elif action == "5":
                    self._find_by_filter()
                elif action == "6":
                    self._update_record()
                elif action == "7":
                    self._delete_record()
                elif action == "8":
                    self._delete_table()
                elif action == "9":
                    self._sort_records()
                elif action == "0":
                    print("Выход из программы.")
                    break
                else:
                    print("Неизвестная команда.")
            except KeyboardInterrupt:
                print("\nВыход.")
                break
            except Exception as e:
                print(f"Критическая ошибка: {e}")
