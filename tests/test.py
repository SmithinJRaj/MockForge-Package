import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String
from mockforge import DataEngine, DatabaseSeeder, SchemaMismatchError

# ==========================================
# 1. SETUP THE TARGET DATABASE
# ==========================================
DB_URL = "sqlite:///mock_test.db"
db_engine = create_engine(DB_URL)
metadata = MetaData()

# We are creating a strict table to intentionally trigger our safety nets!
users_table = Table(
    'users', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('full_name', String(15), nullable=False),          # Names over 15 chars will be TRUNCATED
    Column('role', String(50), nullable=False),               # Normal column
    Column('email', String(100), unique=True, nullable=False) # Duplicates will go to the DLQ!
)

# Reset the database for a clean test
metadata.drop_all(db_engine)
metadata.create_all(db_engine)

# ==========================================
# 2. DEFINE THE MOCKFORGE SCHEMA
# ==========================================
schema = {
    "full_name": {"type": "name"},
    "role": {"type": "enum", "choices": ["Admin", "User", "Guest"]},
    # We intentionally use a tiny list of emails to force UNIQUE collisions!
    "email": {"type": "enum", "choices": ["test1@gmail.com", "test2@gmail.com", "test3@gmail.com"]}
}

print("🚀 Starting MockForge Pipeline...")

try:
    # ==========================================
    # 3. RUN THE PIPELINE
    # ==========================================
    engine = DataEngine(schema=schema)
    seeder = DatabaseSeeder(db_url=DB_URL)

    # Create a memory-safe stream of 10,000 records
    data_stream = engine.stream(count=10000)

    # Seed the database
    inserted = seeder.insert_stream(
        table_name="users",
        schema=schema,
        data_stream=data_stream,
        batch_size=2000,
        dlq_file="failed_rows.json"
    )

    print(f"\n✅ Pipeline Complete! Successfully inserted {inserted} records.")
    
    if os.path.exists("failed_rows.json"):
        print("⚠️ Notice: Some records violated DB constraints and were sent to the Dead Letter Queue.")
        print("👉 Check 'failed_rows.json' to see them.")

except SchemaMismatchError as e:
    print(f"\n❌ Deployment Blocked by Pre-Flight Check:\n{e}")
except Exception as e:
    print(f"\n❌ An unexpected error occurred: {e}")