class DatabaseError(Exception):
    """Базовое исключение для СУБД."""
    pass

class TableNotFoundError(DatabaseError):
    """Таблица не найдена."""
    pass

class InvalidTypeError(DatabaseError):
    """Ошибка приведения типа или нарушения ограничений типа."""
    pass

class DuplicateIDError(DatabaseError):
    """Попытка создать запись с существующим ID."""
    pass

class RecordNotFoundError(DatabaseError):
    """Запись не найдена."""
    pass
