# mockforge/database.py

import json
from typing import Dict, Any, Iterable
from sqlalchemy import create_engine, MetaData, Table, insert
from .exceptions import SchemaMismatchError

class DatabaseSeeder:
    def __init__(self, db_url: str):
        """Initializes the database connection using SQLAlchemy."""
        self.engine = create_engine(db_url)
        self.metadata = MetaData()

    def _pre_flight_check(self, table: Table, schema: Dict[str, Any]) -> None:
        """Compares the target table's SQL types against the user's schema."""
        for col_name, col_def in table.columns.items():
            if col_name in schema:
                schema_def = schema[col_name]
                user_type = schema_def if isinstance(schema_def, str) else schema_def.get('type', '')
                user_type = user_type.lower()
                
                db_type = str(col_def.type).upper()

                if 'INT' in db_type and user_type not in ['integer', 'boolean']:
                    raise SchemaMismatchError(f"Column '{col_name}' expects INTEGER, generating '{user_type}'.")
                
                if 'BOOL' in db_type and user_type != 'boolean':
                    raise SchemaMismatchError(f"Column '{col_name}' expects BOOLEAN, generating '{user_type}'.")
            else:
                # Brilliant addition: Checking for missing required columns!
                is_autoincrement_pk = col_def.primary_key and col_def.autoincrement
                has_default = col_def.default is not None or col_def.server_default is not None
                
                if not col_def.nullable and not is_autoincrement_pk and not has_default:
                    raise SchemaMismatchError(
                        f"Pre-Flight Failed: Table requires column '{col_name}', but it is missing from schema."
                    )

    def _insert_batch_with_fallback(self, connection, table: Table, batch: list, dead_letters: list) -> int:
        """
        Attempts to insert a batch. If it fails (e.g., UNIQUE constraint violation),
        it falls back to a row-by-row insertion to isolate the bad data.
        """
        try:
            # Fast Path: Try to insert all 10,000 records at once using a Savepoint
            with connection.begin_nested():
                connection.execute(insert(table), batch)
            return len(batch)
        
        except Exception:
            # Slow Path: The batch failed. Find the exact row that caused it.
            success_count = 0
            for record in batch:
                try:
                    with connection.begin_nested():
                        connection.execute(insert(table), [record])
                    success_count += 1
                except Exception as e:
                    # Send the failed row and the SQL error to the Dead Letter Queue
                    dead_letters.append({
                        "record": record,
                        "error": str(e)
                    })
            return success_count


    def insert_stream(self, table_name: str, schema: Dict[str, Any], data_stream: Iterable[Dict[str, Any]], batch_size: int = 10000, dlq_file: str = "failed_rows.json", strict_mode: bool = False) -> int:
        """Validates, truncates, and safely inserts data with a Dead Letter Queue fallback."""
        
        try:
            table = Table(table_name, self.metadata, autoload_with=self.engine)
        except Exception as e:
            raise ValueError(f"Could not load table '{table_name}'. Error: {e}")

        self._pre_flight_check(table, schema)

        # -----------------------------------------------------
        # STRATEGY 1: Cache the VARCHAR lengths for swift truncation
        # -----------------------------------------------------
        string_limits = {}
        for col in table.columns:
            if hasattr(col.type, 'length') and col.type.length is not None:
                string_limits[col.name] = col.type.length

        inserted_count = 0
        batch = []
        dead_letters = []

        with self.engine.begin() as connection:
            for record in data_stream:
                
                # Truncate strings instantly before appending to the batch
                for col_name, limit in string_limits.items():
                    if col_name in record and isinstance(record[col_name], str):
                        record[col_name] = record[col_name][:limit]

                batch.append(record)
                
                # -----------------------------------------------------
                # STRATEGY 2: Insert with Dead Letter Queue Fallback
                # -----------------------------------------------------
                if len(batch) >= batch_size:
                    if strict_mode:
                        connection.execute(insert(table), batch)
                        inserted_count += len(batch)
                    else:
                        inserted_count += self._insert_batch_with_fallback(connection, table, batch, dead_letters)
                    batch = [] 
            
            if batch:
                if strict_mode:
                    connection.execute(insert(table), batch)
                    inserted_count += len(batch)
                else:
                    inserted_count += self._insert_batch_with_fallback(connection, table, batch, dead_letters)

        # -----------------------------------------------------
        # Dump the bad rows to a file for the user to inspect
        # -----------------------------------------------------
        if dead_letters and not strict_mode:
            with open(dlq_file, 'w') as f:
                json.dump(dead_letters, f, indent=4)
            print(f"⚠️ WARNING: {len(dead_letters)} records failed DB constraints. Check '{dlq_file}'")

        return inserted_count