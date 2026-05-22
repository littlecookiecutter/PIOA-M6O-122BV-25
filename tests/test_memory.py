import unittest

from src.db.backend.memory import Database, Table
from src.db.backend.errors import (
    DatabaseError,
    DuplicateIDError,
    InvalidTypeError,
    RecordNotFoundError,
    TableNotFoundError,
)


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

    def test_update_record(self):
        self.table.create_record(name="Old", age="10")
        self.table.update_record(1, name="New")
        self.assertEqual(self.table.select_record(id=1)[0][1], "New")

    def test_update_missing_record(self):
        with self.assertRaises(RecordNotFoundError):
            self.table.update_record(99, name="X")

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


if __name__ == "__main__":
    unittest.main()
