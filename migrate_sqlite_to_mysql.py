import argparse
import sqlite3
from pathlib import Path

from storage import ReceiptDatabase


_TABLES = ("users", "products", "sales", "sale_items")


def migrate(source_path):
    source_path = Path(source_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {source_path}")

    database = ReceiptDatabase()
    source = sqlite3.connect(source_path)
    try:
        source_tables = {
            row[0]
            for row in source.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        copied_counts = {}
        with database._connect() as target:
            target.start_transaction()
            for table in _TABLES:
                count = target.execute(f"SELECT COUNT(*) AS row_count FROM `{table}`").fetchone()["row_count"]
                if count:
                    raise RuntimeError(
                        f"MySQL table '{table}' is not empty; migration stopped to avoid duplicate data."
                    )

            for table in _TABLES:
                if table not in source_tables:
                    copied_counts[table] = 0
                    continue
                source_columns = [row[1] for row in source.execute(f"PRAGMA table_info(`{table}`)")]
                target_columns = {
                    row["Field"] for row in target.execute(f"SHOW COLUMNS FROM `{table}`")
                }
                columns = [column for column in source_columns if column in target_columns]
                rows = source.execute(
                    f"SELECT {', '.join(f'`{column}`' for column in columns)} FROM `{table}`"
                ).fetchall()
                if rows:
                    placeholders = ", ".join(["%s"] * len(columns))
                    column_list = ", ".join(f"`{column}`" for column in columns)
                    target.executemany(
                        f"INSERT INTO `{table}` ({column_list}) VALUES ({placeholders})",
                        rows,
                    )
                copied_counts[table] = len(rows)
        return copied_counts
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description="Copy the receipt app's SQLite data into configured MySQL tables.")
    parser.add_argument(
        "sqlite_path",
        nargs="?",
        default=Path(__file__).with_name("receipt_data.sqlite3"),
        type=Path,
        help="SQLite source file (defaults to receipt_data.sqlite3 beside this script)",
    )
    args = parser.parse_args()

    try:
        counts = migrate(args.sqlite_path)
    except Exception as error:
        parser.error(str(error))
    for table, count in counts.items():
        print(f"{table}: {count} rows copied")
    print("Migration complete. The SQLite source was left unchanged.")


if __name__ == "__main__":
    main()
