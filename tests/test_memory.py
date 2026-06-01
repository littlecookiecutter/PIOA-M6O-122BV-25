import unittest
import tempfile
import json
import pathlib
from unittest.mock import patch, MagicMock

from src.db.backend.memory import MemoryDatabase
from src.db.backend.json_db import JSONDatabase
from src.db.backend.csv_db import CSVDatabase
from src.db.backend.table import Table
from src.db.backend.errors import TableNotFoundError, CorruptedDataError, InvalidTypeError
from src.db.tui import TUI
import src.db.__main__ as main_module


class TestBackendCommon(unittest.TestCase):
    def _run_crud(self, db):
        db.create_table("t", {"name": "str", "age": "int"})
        db.insert("t", name="A", age="20")
        db.insert("t", name="B", age="25")
        self.assertEqual(len(db.select("t")), 2)
        res = db.select("t", name="A")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "A")
        db.update("t", 1, name="C")
        self.assertEqual(db.select("t", id=1)[0]["name"], "C")
        db.delete("t", 2)
        self.assertEqual(len(db.select("t")), 1)
        db.drop_table("t")
        with self.assertRaises(TableNotFoundError):
            db.select("t")

    def test_memory_crud(self):
        self._run_crud(MemoryDatabase())

    def test_json_crud(self):
        with tempfile.TemporaryDirectory() as d:
            self._run_crud(JSONDatabase(d))

    def test_csv_crud(self):
        with tempfile.TemporaryDirectory() as d:
            self._run_crud(CSVDatabase(d))


class TestTypeCasting(unittest.TestCase):
    def test_cast_empty_values(self):
        self.assertIsNone(Table._cast("", "str"))
        self.assertIsNone(Table._cast(None, "int"))
    
    def test_cast_bool_variations(self):
        self.assertTrue(Table._cast("true", "bool"))
        self.assertTrue(Table._cast("1", "bool"))
        self.assertTrue(Table._cast("yes", "bool"))
        self.assertTrue(Table._cast("да", "bool"))
        self.assertFalse(Table._cast("false", "bool"))
        self.assertFalse(Table._cast("0", "bool"))
        self.assertFalse(Table._cast("no", "bool"))
    
    def test_cast_semantic_boundaries(self):
        self.assertEqual(Table._cast("0", "int_pos"), 0)
        self.assertEqual(Table._cast("0", "int_neg"), 0)
        self.assertEqual(Table._cast("0.0", "float_pos"), 0.0)
        
        with self.assertRaises(InvalidTypeError):
            Table._cast("-1", "int_pos")
        with self.assertRaises(InvalidTypeError):
            Table._cast("1", "int_neg")
        with self.assertRaises(InvalidTypeError):
            Table._cast("-0.1", "float_pos")
    
    def test_cast_invalid_type(self):
        with self.assertRaises(InvalidTypeError):
            Table._cast("abc", "int")
        with self.assertRaises(InvalidTypeError):
            Table._cast("xyz", "float")


class TestIndexing(unittest.TestCase):
    def test_index_speedup(self):
        with tempfile.TemporaryDirectory() as d:
            db = JSONDatabase(d)
            db.create_table("t", {"status": "str"})
            for i in range(100):
                db.insert("t", status="active" if i % 2 == 0 else "inactive")
            db.create_index("t", "status")
            res = db.select("t", status="active")
            self.assertEqual(len(res), 50)
    
    def test_index_update_on_change(self):
        table = Table("t", {"val": "int"})
        table.create_index("val")
        table.insert(val="10")
        table.insert(val="20")
        
        # Обновление: значение меняется, индекс должен обновиться
        table.update(1, val="30")
        # Ищем по целому числу, так как _cast преобразует "30" -> 30
        res = table.select(val=30)
        self.assertEqual(len(res), 1)
        
        res = table.select(val=10)  # старое значение не должно находиться
        self.assertEqual(len(res), 0)
        
        # Удаление: индекс должен уменьшиться
        table.delete(2)
        res = table.select(val=30)
        self.assertEqual(len(res), 1)


class TestTUI(unittest.TestCase):
    def setUp(self):
        self.app = TUI()
        self.app.db = MemoryDatabase()

    def _run_flow(self, inputs: list[str]) -> None:
        safe_inputs = list(inputs) + ["0"]
        with patch("builtins.input", side_effect=safe_inputs), \
             patch("builtins.print"):
            self.app.run()

    def test_exit_immediately(self):
        self._run_flow(["0"])

    def test_create_and_select(self):
        self._run_flow(["1", "users", "name:str", "2", "1"])

    def test_crud_flow(self):
        self._run_flow(["1", "t", "f:str", "3", "val", "4", "0"])

    def test_switch_mode(self):
        self._run_flow(["11", "2", "0"])

    def test_switch_mode_error(self):
        # Тест для покрытия except в _switch_mode
        self._run_flow(["11", "invalid", "0"])

    def test_error_handling_empty_name(self):
        self._run_flow(["1", "", "x:str", "0"])

    def test_error_handling_invalid_type(self):
        self._run_flow(["1", "t", "f:badtype", "0"])

    def test_error_handling_invalid_menu_choice(self):
        self._run_flow(["99", "0"])

    def test_error_handling_empty_filter(self):
        self._run_flow(["1", "t", "f:str", "3", "val", "5", "", "0"])

    def test_error_handling_update_no_fields(self):
        self._run_flow(["1", "t", "f:str", "3", "val", "6", "1", "", "0"])


class TestMainEntry(unittest.TestCase):
    def test_main_exists(self):
        self.assertTrue(hasattr(main_module, "main"))
        self.assertTrue(callable(main_module.main))
    
    @patch("src.db.tui.TUI.run")
    def test_main_calls_run(self, mock_run):
        main_module.main()
        mock_run.assert_called_once()


class TestEdgeCases(unittest.TestCase):
    def test_table_select_with_unknown_filter_field(self):
        table = Table("t", {"name": "str"})
        table.insert(name="A")
        # Фильтр по несуществующему полю игнорируется
        res = table.select(unknown="X")
        self.assertEqual(len(res), 1)
    
    def test_csv_parse_with_extra_columns(self):
        with tempfile.TemporaryDirectory() as d:
            db = CSVDatabase(d)
            db.create_table("t", {"name": "str"})
            csv_p, meta_p = db._paths("t")
            with csv_p.open("w", encoding="utf-8", newline="") as f:
                f.write("id,name,extra\n1,A,ignored\n")
            with meta_p.open("w", encoding="utf-8") as f:
                json.dump({"schema": {"name": "str"}, "next_id": 2, "indexes": {}}, f)
            
            loaded = db._load_table("t")
            self.assertEqual(len(loaded._records), 1)
            self.assertEqual(loaded._records[0]["name"], "A")
    
    def test_json_corrupted_structure(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "t.json"
            p.write_text('{"wrong": "structure"}')
            db = JSONDatabase(d)
            with self.assertRaises(CorruptedDataError):
                db.select("t")


if __name__ == "__main__":
    unittest.main()
