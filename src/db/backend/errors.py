class DatabaseError(Exception):
    """Базовое исключение СУБД."""
    pass

class TableNotFoundError(DatabaseError): pass
class TableAlreadyExistsError(DatabaseError): pass
class InvalidTypeError(DatabaseError): pass
class RecordNotFoundError(DatabaseError): pass
class FileStorageError(DatabaseError): pass
class CorruptedDataError(FileStorageError): pass
