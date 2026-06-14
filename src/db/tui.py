from .backend.memory import MemoryDatabase
from .backend.json_db import JSONDatabase
from .backend.csv_db import CSVDatabase
from .backend.base import Database
from .backend.errors import DatabaseError

AVAILABLE_TYPES = ["str", "int", "float", "bool", "int_pos", "int_neg", "float_pos", "float_neg"]

class TUI:
    def __init__(self) -> None:
        self.db: Database = MemoryDatabase()
        self.current: str | None = None

    def _print_menu(self) -> None:
        print("\n=== Главное меню ===")
        print(f"Текущая таблица: {self.current or 'Не выбрана'}")
        print(f"Режим: {self._get_mode_name()}")
        print("1. Создать таблицу  2. Выбрать  3. Добавить  4. Показать")
        print("5. Найти  6. Обновить  7. Удалить запись  8. Удалить таблицу")
        print("9. Сортировать  10. Индекс  11. Сменить режим  0. Выход")

    def _get_mode_name(self) -> str:
        if isinstance(self.db, JSONDatabase):
            return "JSON"
        if isinstance(self.db, CSVDatabase):
            return "CSV"
        return "Memory"

    def _read_int(self, prompt: str) -> int:
        while True:
            try:
                return int(input(prompt).strip())
            except ValueError:
                print("Ошибка: введите целое число.")

    def run(self) -> None:
        while True:
            self._print_menu()
            act = input("Действие: ").strip()
            try:
                if act == "1":
                    self._create_table()
                elif act == "2":
                    self._select_table()
                elif act == "3":
                    self._insert_record()
                elif act == "4":
                    self._show_all()
                elif act == "5":
                    self._find_by_filter()
                elif act == "6":
                    self._update_record()
                elif act == "7":
                    self._delete_record()
                elif act == "8":
                    self._drop_table()
                elif act == "9":
                    self._sort_records()
                elif act == "10":
                    self._create_index()
                elif act == "11":
                    self._switch_mode()
                elif act == "0":
                    break
                else:
                    print("Неизвестная команда.")
            except DatabaseError as e:
                print(f"Ошибка: {e}")
            except Exception as e:
                print(f"Критическая ошибка: {e}")

    def _create_table(self) -> None:
        name = input("Имя таблицы: ").strip()
        if not name:
            print("Ошибка: имя не может быть пустым.")
            return
        print(f"Типы: {', '.join(AVAILABLE_TYPES)}")
        raw = input("Поля (имя:тип, ...): ").strip()
        if not raw:
            print("Ошибка: укажите поля.")
            return
        
        schema = {}
        for part in raw.split(","):
            if ":" in part:
                f, t = part.strip().split(":", 1)
                if t.strip().lower() not in AVAILABLE_TYPES:
                    print(f"Ошибка: тип '{t}' не поддерживается.")
                    return
                schema[f.strip()] = t.strip().lower()
            else:
                schema[part.strip()] = "str"
                
        self.db.create_table(name, schema)
        self.current = name
        print(f"Таблица '{name}' создана.")

    def _select_table(self) -> None:
        tbls = self.db.list_tables()
        if not tbls:
            print("Таблиц нет.")
            return
        print("\nТаблицы:")
        for i, t in enumerate(tbls, 1):
            print(f"  {i}. {t}")
        c = self._read_int("Номер: ")
        if 1 <= c <= len(tbls):
            self.current = tbls[c-1]
            print(f"Выбрана: '{self.current}'")

    def _insert_record(self) -> None:
        if not self.current:
            print("Ошибка: выберите таблицу.")
            return
        schema = self.db.get_schema(self.current)
        print(f"Добавление в '{self.current}' (Enter = пропустить):")
        kwargs = {f: input(f"  {f} ({t}): ").strip() for f, t in schema.items() if f != "id"}
        self.db.insert(self.current, **kwargs)
        print("Запись добавлена.")

    def _show_all(self) -> None:
        if not self.current:
            print("Ошибка: выберите таблицу.")
            return
        recs = self.db.select(self.current)
        print(f"\nЗаписи в '{self.current}':")
        print("  Пусто." if not recs else "\n".join(f"  {r}" for r in recs))

    def _find_by_filter(self) -> None:
        if not self.current:
            print("Ошибка: выберите таблицу.")
            return
        schema = self.db.get_schema(self.current)
        print("Фильтр (Enter = пропустить):")
        filters = {f: v for f in schema if (v := input(f"  {f}: ").strip())}
        recs = self.db.select(self.current, **filters)
        print(f"  Найдено: {len(recs)}" if recs else "  Ничего не найдено.")
        for r in recs:
            print(f"  {r}")

    def _update_record(self) -> None:
        if not self.current:
            print("Ошибка: выберите таблицу.")
            return
        rid = self._read_int("ID записи: ")
        schema = self.db.get_schema(self.current)
        print("Новые данные (Enter = не менять):")
        kwargs = {f: v for f in schema if f != "id" and (v := input(f"  {f}: ").strip())}
        if not kwargs:
            print("Ошибка: нет данных для обновления.")
            return
        self.db.update(self.current, rid, **kwargs)
        print("Запись обновлена.")

    def _delete_record(self) -> None:
        if not self.current:
            print("Ошибка: выберите таблицу.")
            return
        self.db.delete(self.current, self._read_int("ID записи: "))
        print("Запись удалена.")

    def _drop_table(self) -> None:
        tbls = self.db.list_tables()
        if not tbls:
            print("Таблиц нет.")
            return
        print("\nУдаление:")
        for i, t in enumerate(tbls, 1):
            print(f"  {i}. {t}")
        c = self._read_int("Номер: ")
        if 1 <= c <= len(tbls):
            name = tbls[c-1]
            if input(f"Удалить '{name}'? (y/n): ").strip().lower() == "y":
                self.db.drop_table(name)
                if self.current == name:
                    self.current = None
                print(f"Таблица '{name}' удалена.")

    def _sort_records(self) -> None:
        if not self.current:
            print("Ошибка: выберите таблицу.")
            return
        schema = self.db.get_schema(self.current)
        field = input("Поле: ").strip()
        if field not in schema:
            print("Ошибка: поле не найдено.")
            return
        rev = input("По убыванию? (y/n): ").strip().lower() == "y"
        for r in self.db.sort(self.current, field, rev):
            print(f"  {r}")

    def _create_index(self) -> None:
        if not self.current:
            print("Ошибка: выберите таблицу.")
            return
        schema = self.db.get_schema(self.current)
        field = input("Поле для индекса: ").strip()
        if field not in schema:
            print("Ошибка: поле не найдено.")
            return
        self.db.create_index(self.current, field)
        print(f"Индекс по '{field}' создан.")

    def _switch_mode(self) -> None:
        print("\nРежимы: 1.Memory  2.JSON  3.CSV")
        ch = input("Выбор: ").strip()
        if ch == "2":
            self.db = JSONDatabase()
        elif ch == "3":
            self.db = CSVDatabase()
        else:
            self.db = MemoryDatabase()
        self.current = None
        print(f"Режим: {self._get_mode_name()}. Таблица сброшена.")
