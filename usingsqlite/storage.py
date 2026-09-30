from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import hmac
from pathlib import Path
import secrets
import sqlite3


_PIN_ITERATIONS = 240_000
_CENT = Decimal("0.01")


class ReceiptDatabase:
    def __init__(self, database_path=None):
        self.path = Path(database_path) if database_path else Path(__file__).with_name("receipt_data.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL CHECK (role IN ('superuser', 'cashier')),
                    pin_salt BLOB NOT NULL,
                    pin_hash BLOB NOT NULL,
                    created_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id INTEGER PRIMARY KEY,
                    receipt_number TEXT NOT NULL UNIQUE,
                    seller_id INTEGER NOT NULL REFERENCES users(user_id),
                    seller_name TEXT NOT NULL,
                    store_name TEXT NOT NULL,
                    sold_at TEXT NOT NULL,
                    subtotal_cents INTEGER NOT NULL,
                    tax_cents INTEGER NOT NULL,
                    total_cents INTEGER NOT NULL,
                    reversed_at TEXT,
                    reversed_by_id INTEGER REFERENCES users(user_id)
                );
                CREATE TABLE IF NOT EXISTS products (
                    product_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
                    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0)
                );
                CREATE TABLE IF NOT EXISTS sale_items (
                    sale_item_id INTEGER PRIMARY KEY,
                    sale_id INTEGER NOT NULL REFERENCES sales(sale_id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(product_id),
                    item_name TEXT NOT NULL,
                    unit_price_cents INTEGER NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0)
                );
                """
            )
            sales_columns = {row[1] for row in connection.execute("PRAGMA table_info(sales)")}
            if "reversed_at" not in sales_columns:
                connection.execute("ALTER TABLE sales ADD COLUMN reversed_at TEXT")
            if "reversed_by_id" not in sales_columns:
                connection.execute("ALTER TABLE sales ADD COLUMN reversed_by_id INTEGER REFERENCES users(user_id)")
            sale_item_columns = {row[1] for row in connection.execute("PRAGMA table_info(sale_items)")}
            if "product_id" not in sale_item_columns:
                connection.execute("ALTER TABLE sale_items ADD COLUMN product_id INTEGER REFERENCES products(product_id)")

    @staticmethod
    def _pin_digest(pin, salt):
        return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, _PIN_ITERATIONS)

    def add_user(self, full_name, username, phone, pin, role="cashier"):
        full_name = full_name.strip()
        username = username.strip()
        if not full_name or not username:
            raise ValueError("Enter a full name and username.")
        if len(pin) < 4 or not pin.isdigit():
            raise ValueError("PIN must contain at least four digits.")
        if role not in ("superuser", "cashier"):
            raise ValueError("Invalid user role.")

        salt = secrets.token_bytes(16)
        pin_hash = self._pin_digest(pin, salt)
        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    """INSERT INTO users
                       (username, full_name, phone, role, pin_salt, pin_hash, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (username, full_name, phone.strip(), role, salt, pin_hash, datetime.now().astimezone().isoformat(timespec="seconds")),
                )
            except sqlite3.IntegrityError as error:
                if "users.username" in str(error):
                    raise ValueError("That username is already taken. Choose another.") from error
                raise
            return cursor.lastrowid

    def has_superuser(self):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM users WHERE role = 'superuser' AND active = 1 LIMIT 1"
            ).fetchone()
            return row is not None

    def verify_pin(self, username, pin, role=None):
        query = "SELECT * FROM users WHERE username = ? AND active = 1"
        parameters = [username.strip()]
        if role:
            query += " AND role = ?"
            parameters.append(role)
        with self._connect() as connection:
            user = connection.execute(query, parameters).fetchone()
        if user is None:
            return None
        candidate = self._pin_digest(pin, user["pin_salt"])
        if not hmac.compare_digest(candidate, user["pin_hash"]):
            return None
        return {key: user[key] for key in ("user_id", "username", "full_name", "phone", "role")}

    def list_users(self, role=None):
        query = "SELECT user_id, username, full_name, phone, role, created_at FROM users WHERE active = 1"
        parameters = []
        if role:
            query += " AND role = ?"
            parameters.append(role)
        query += " ORDER BY full_name COLLATE NOCASE"
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(query, parameters)]

    @staticmethod
    def _price_cents(price):
        return int((Decimal(str(price)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def list_products(self):
        with self._connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT product_id, name, unit_price_cents, stock_quantity FROM products ORDER BY name COLLATE NOCASE"
                )
            ]

    def add_stock(self, actor_id, name, unit_price, quantity):
        name = name.strip()
        try:
            unit_price_cents = self._price_cents(unit_price)
            quantity = int(quantity)
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("Enter a valid price and a whole-number quantity.") from error
        if not name or unit_price_cents < 0 or quantity < 1:
            raise ValueError("Enter a product name, a non-negative price, and a quantity of at least 1.")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            actor = connection.execute(
                "SELECT 1 FROM users WHERE user_id = ? AND role = 'superuser' AND active = 1",
                (actor_id,),
            ).fetchone()
            if actor is None:
                raise ValueError("Only an active superuser can add stock.")
            connection.execute(
                """INSERT INTO products (name, unit_price_cents, stock_quantity) VALUES (?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       unit_price_cents = excluded.unit_price_cents,
                       stock_quantity = products.stock_quantity + excluded.stock_quantity""",
                (name, unit_price_cents, quantity),
            )

    def create_sale(self, receipt_number, seller_id, store_name, items, tax_rate=Decimal("0.07")):
        if not items:
            raise ValueError("A sale must contain at least one item.")
        try:
            prepared_items = [(int(item["product_id"]), int(item["quantity"])) for item in items]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Sale items must be selected from stocked products.") from error
        if any(product_id < 1 or quantity < 1 for product_id, quantity in prepared_items):
            raise ValueError("Sale items contain invalid details.")
        sold_at = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            seller = connection.execute(
                "SELECT full_name FROM users WHERE user_id = ? AND role = 'cashier' AND active = 1",
                (seller_id,),
            ).fetchone()
            if seller is None:
                raise ValueError("The selected cashier is not active.")

            sale_items = []
            for product_id, quantity in prepared_items:
                product = connection.execute(
                    "SELECT name, unit_price_cents, stock_quantity FROM products WHERE product_id = ?",
                    (product_id,),
                ).fetchone()
                if product is None:
                    raise ValueError("A selected product is no longer available.")
                if product["stock_quantity"] < quantity:
                    raise ValueError(f"Insufficient stock for {product['name']}; {product['stock_quantity']} remaining.")
                connection.execute(
                    "UPDATE products SET stock_quantity = stock_quantity - ? WHERE product_id = ?",
                    (quantity, product_id),
                )
                sale_items.append((product_id, product["name"], product["unit_price_cents"], quantity))

            subtotal_cents = sum(unit_price * quantity for _, _, unit_price, quantity in sale_items)
            tax_cents = int((Decimal(subtotal_cents) * Decimal(str(tax_rate))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            total_cents = subtotal_cents + tax_cents
            cursor = connection.execute(
                """INSERT INTO sales
                   (receipt_number, seller_id, seller_name, store_name, sold_at, subtotal_cents, tax_cents, total_cents)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (receipt_number, seller_id, seller["full_name"], store_name, sold_at, subtotal_cents, tax_cents, total_cents),
            )
            sale_id = cursor.lastrowid
            connection.executemany(
                """INSERT INTO sale_items (sale_id, product_id, item_name, unit_price_cents, quantity)
                   VALUES (?, ?, ?, ?, ?)""",
                [(sale_id, product_id, name, unit_price, quantity) for product_id, name, unit_price, quantity in sale_items],
            )
        return sale_id

    def reverse_sale(self, sale_id, superuser_id, pin):
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            superuser = connection.execute(
                "SELECT pin_salt, pin_hash FROM users WHERE user_id = ? AND role = 'superuser' AND active = 1",
                (superuser_id,),
            ).fetchone()
            if superuser is None or not hmac.compare_digest(self._pin_digest(pin, superuser["pin_salt"]), superuser["pin_hash"]):
                raise ValueError("The superuser code was not accepted.")

            sale = connection.execute("SELECT reversed_at FROM sales WHERE sale_id = ?", (sale_id,)).fetchone()
            if sale is None:
                raise ValueError("The selected sale could not be found.")
            if sale["reversed_at"] is not None:
                raise ValueError("This sale has already been reversed.")
            items = connection.execute(
                "SELECT product_id, quantity FROM sale_items WHERE sale_id = ?",
                (sale_id,),
            ).fetchall()
            for item in items:
                if item["product_id"] is not None:
                    connection.execute(
                        "UPDATE products SET stock_quantity = stock_quantity + ? WHERE product_id = ?",
                        (item["quantity"], item["product_id"]),
                    )
            connection.execute(
                "UPDATE sales SET reversed_at = ?, reversed_by_id = ? WHERE sale_id = ?",
                (datetime.now().astimezone().isoformat(timespec="seconds"), superuser_id, sale_id),
            )

    def list_sales(self):
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT s.sale_id, s.receipt_number, s.sold_at, s.seller_name, s.store_name,
                          s.reversed_at, s.reversed_by_id,
                          s.subtotal_cents, s.tax_cents, s.total_cents,
                          group_concat(i.item_name || ' x' || i.quantity, ', ') AS item_summary
                   FROM sales AS s
                   JOIN sale_items AS i ON i.sale_id = s.sale_id
                   GROUP BY s.sale_id
                   ORDER BY s.sale_id DESC"""
            )
            return [dict(row) for row in rows]

    def get_sale(self, sale_id):
        with self._connect() as connection:
            sale = connection.execute("SELECT * FROM sales WHERE sale_id = ?", (sale_id,)).fetchone()
            if sale is None:
                return None
            result = dict(sale)
            result["items"] = [
                dict(row)
                for row in connection.execute(
                    "SELECT product_id, item_name, unit_price_cents, quantity FROM sale_items WHERE sale_id = ? ORDER BY sale_item_id",
                    (sale_id,),
                )
            ]
            return result