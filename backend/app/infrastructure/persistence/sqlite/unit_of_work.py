from backend.app.infrastructure.persistence.sqlite.database import SqliteDatabase

class UnitOfWork:
    def __init__(self, database: SqliteDatabase):
        self.database = database

    def __enter__(self):
        self.conn = self.database.get_connection()

        self.account_repository
        self.


        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()