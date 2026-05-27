import unittest
from unittest.mock import patch

from src.db.backend.memory import Database, Table
from src.db.backend.errors import (
    DatabaseError,
    DuplicateIDError,
    InvalidTypeError,
    RecordNotFoundError,
    TableNotFoundError,
)
from src.db.tui import DatabaseApp


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_create_and_get_table(self):
        self.db.create_table("users", "name:str, age:int")
        table = self.db.get_table("users")
        self.assertIsInstance(table, Table)

    def test_duplicate_table(self):
        self.db.create_table("t", "x:str")
        with self.assertRaises(DatabaseError):
            self.db.create_table("t", "y:str")

    def test_delete_table(self):
        self.db.create_table("t", "x:str")
        self.db.delete_table("t")
        with self.assertRaises(TableNotFoundError):
            self.db.get_table("t")

    def test_empty_table_name(self):
        with self.assertRaises(DatabaseError):
            self.db.create_table("", "x:str")
        with self.assertRaises(DatabaseError):
            self.db.create_table("   ", "x:str")

    def test_protect_id_field_in_schema(self):
        with self.assertRaises(DatabaseError):
            self.db.create_table("t", "id:str, name:str")
        with self.assertRaises(DatabaseError):
            self.db.create_table("t", "name:str, id:int")

    def test_duplicate_fields_in_schema(self):
        with self.assertRaises(DatabaseError):
            self.db.create_table("t", "name:str, name:int")


class TestTableCRUD(unittest.TestCase):
    def setUp(self):
        self.table = Table("test", {"name": "str", "age": "int"})

    def test_create_record(self):
        rec = self.table.create_record(name="Alice", age="20")
        self.assertEqual(rec[1], "Alice")
        self.assertEqual(rec[2], 20)
        self.assertEqual(rec[0], 1)

    def test_auto_increment_id(self):
        self.table.create_record(name="A", age="1")
        self.table.create_record(name="B", age="2")
        self.assertEqual(self.table._next_id, 3)

    def test_invalid_type_conversion(self):
        with self.assertRaises(InvalidTypeError):
            self.table.create_record(name="Bob", age="abc")

    def test_select_all(self):
        self.table.create_record(name="A", age="1")
        self.table.create_record(name="B", age="2")
        self.assertEqual(len(self.table.select_record()), 2)

    def test_select_filter(self):
        self.table.create_record(name="A", age="1")
        self.table.create_record(name="B", age="2")
        res = self.table.select_record(name="A")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], "A")

    def test_select_filter_with_type_cast(self):
        self.table.create_record(name="A", age="1")
        self.table.create_record(name="B", age="2")
        res = self.table.select_record(age="2")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][2], 2)

    def test_select_filter_invalid_field(self):
        self.table.create_record(name="A", age="1")
        with self.assertRaises(InvalidTypeError):
            self.table.select_record(invalid_field="X")

    def test_select_filter_invalid_type(self):
        self.table.create_record(name="A", age="1")
        with self.assertRaises(InvalidTypeError):
            self.table.select_record(age="not_a_number")

    def test_update_record(self):
        self.table.create_record(name="Old", age="10")
        self.table.update_record(1, name="New")
        self.assertEqual(self.table.select_record(id=1)[0][1], "New")

    def test_update_missing_record(self):
        with self.assertRaises(RecordNotFoundError):
            self.table.update_record(99, name="X")

    def test_update_protect_id_field(self):
        self.table.create_record(name="A", age="1")
        with self.assertRaises(DatabaseError):
            self.table.update_record(1, id=99)

    def test_delete_record(self):
        self.table.create_record(name="X", age="5")
        self.table.delete_record(1)
        self.assertEqual(len(self.table.select_record()), 0)

    def test_delete_missing_record(self):
        with self.assertRaises(RecordNotFoundError):
            self.table.delete_record(99)


class TestSorting(unittest.TestCase):
    def setUp(self):
        self.table = Table("nums", {"val": "int"})

    def test_sort_asc(self):
        self.table.create_record(val="10")
        self.table.create_record(val="2")
        self.table.create_record(val="5")
        sorted_data = self.table.sort_records("val")
        self.assertEqual([r[1] for r in sorted_data], [2, 5, 10])

    def test_sort_desc(self):
        self.table.create_record(val="10")
        self.table.create_record(val="2")
        sorted_data = self.table.sort_records("val", reverse=True)
        self.assertEqual([r[1] for r in sorted_data], [10, 2])

    def test_sort_invalid_field(self):
        with self.assertRaises(InvalidTypeError):
            self.table.sort_records("nonexistent")


class TestSemanticTypes(unittest.TestCase):
    def setUp(self):
        self.table = Table("finance", {"income": "float_pos", "debt": "int_neg", "active": "bool"})

    def test_positive_float(self):
        rec = self.table.create_record(income="1500.50", debt="-200", active="true")
        self.assertEqual(rec[1], 1500.5)
        self.assertEqual(rec[2], -200)
        self.assertTrue(rec[3])

    def test_negative_int_constraint(self):
        with self.assertRaises(InvalidTypeError):
            self.table.create_record(income="100", debt="50", active="true")

    def test_positive_float_constraint(self):
        with self.assertRaises(InvalidTypeError):
            self.table.create_record(income="-50", debt="-10", active="false")

    def test_bool_parsing(self):
        cases = [
            ("true", True), ("1", True), ("yes", True), ("да", True),
            ("false", False), ("0", False), ("no", False), ("нет", False)
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.table._records.clear()
                self.table._next_id = 1
                rec = self.table.create_record(income="0", debt="0", active=raw)
                self.assertIs(rec[3], expected)


class TestTUI(unittest.TestCase):
    """Тесты консольного интерфейса. Безопасный mock без StopIteration."""

    def setUp(self):
        self.app = DatabaseApp()

    def _run_app(self, inputs: list[str]) -> None:
        """Запускает приложение с имитацией ввода. При исчерпании списка возвращает '0'."""
        input_iter = iter(inputs)
        
        def safe_input(prompt=""):
            try:
                return next(input_iter)
            except StopIteration:
                return "0"  # Гарантирует выход из цикла без зацикливания

        with patch("builtins.input", side_effect=safe_input), \
             patch("builtins.print"):
            self.app.run()

    def test_exit_command(self):
        self._run_app(["0"])

    def test_create_and_select_table(self):
        self._run_app(["1", "users", "name:str, age:int", "2", "1"])

    def test_add_and_display_records(self):
        self._run_app([
            "1", "t", "f:str",
            "3", "val1",
            "3", "val2",
            "4"
        ])

    def test_filter_and_update_flow(self):
        self._run_app([
            "1", "t", "f:str",
            "3", "A",
            "3", "B",
            "5", "A",
            "6", "1", "C"
        ])

    def test_delete_record_and_table(self):
        self._run_app([
            "1", "t", "f:str",
            "3", "X",
            "7", "1",
            "8", "1", "y"
        ])

    def test_sort_records_flow(self):
        self._run_app([
            "1", "t", "v:int",
            "3", "10",
            "3", "5",
            "9", "v", "n"
        ])

    def test_error_handling_in_tui(self):
        self._run_app([
            "3",           # Попытка добавить запись без выбранной таблицы
            "1", "t", "f:bad", # Ошибка: неизвестный тип
            "99",          # Неизвестная команда меню
            "2",           # Выбор таблицы при пустом списке
        ])


if __name__ == "__main__":
    unittest.main()
