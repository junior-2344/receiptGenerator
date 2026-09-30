from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import hmac
import os
import secrets
from mysql.connector import Error as DatabaseError
from mysql.connector import connect


_PIN_ITERATIONS = 240_000
_CENT = Decimal("0.01")


class _MySQLConnection:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor(dictionary=True)

    def execute(self, statement, parameters=()):
        self.cursor.execute(statement, parameters)
        return self.cursor

    def executemany(self, statement, parameters):
        self.cursor.executemany(statement, parameters)
        return self.cursor

    def start_transaction(self):
        self.connection.start_transaction()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.cursor.close()
        self.connection.close()


class ReceiptDatabase:
    def __init__(self, connection_config=None):
        self.connection_config = connection_config or self._environment_config()
        self._initialize()

    @staticmethod
    def _environment_config():
        required = ("MYSQL_USER", "MYSQL_PASSWORD")
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            raise RuntimeError(f"Set the MySQL connection variables before starting the app: {', '.join(missing)}")
        try:
            port = int(os.environ.get("MYSQL_PORT", "3306"))
        except ValueError as error:
            raise RuntimeError("MYSQL_PORT must be a number between 1 and 65535.") from error
        if not 1 <= port <= 65535:
            raise RuntimeError("MYSQL_PORT must be a number between 1 and 65535.")
        return {
            "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
            "port": port,
            "user": os.environ["MYSQL_USER"],
            "password": os.environ["MYSQL_PASSWORD"],
            "database": os.environ.get("MYSQL_DATABASE", "receipt_generator"),
            "charset": "utf8mb4",
            "use_unicode": True,
        }

    def _ensure_database(self):
        try:
            connection = connect(**self.connection_config)
        except DatabaseError as error:
            if error.errno != 1049:
                raise
        else:
            connection.close()
            return

        server_config = dict(self.connection_config)
        database = server_config.pop("database")
        escaped_database = database.replace("`", "``")
        connection = connect(**server_config)
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{escaped_database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            finally:
                cursor.close()
        finally:
            connection.close()

    @contextmanager
    def _connect(self):
        connection = _MySQLConnection(connect(**self.connection_config))
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        self._ensure_database()
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    full_name VARCHAR(255) NOT NULL,
                    phone VARCHAR(255) NOT NULL DEFAULT '',
                    role VARCHAR(20) NOT NULL,
                    pin_salt VARBINARY(16) NOT NULL,
                    pin_hash VARBINARY(32) NOT NULL,
                    created_at VARCHAR(40) NOT NULL,
                    active TINYINT UNSIGNED NOT NULL DEFAULT 1,
                    CONSTRAINT chk_users_role CHECK (role IN ('superuser', 'cashier'))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS sales (
                    sale_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    receipt_number VARCHAR(255) NOT NULL UNIQUE,
                    seller_id BIGINT UNSIGNED NOT NULL,
                    seller_name VARCHAR(255) NOT NULL,
                    store_name VARCHAR(255) NOT NULL,
                    sold_at VARCHAR(40) NOT NULL,
                    subtotal_cents BIGINT UNSIGNED NOT NULL,
                    tax_cents BIGINT UNSIGNED NOT NULL,
                    tax_rate DECIMAL(8,6) NOT NULL DEFAULT 0.070000,
                    total_cents BIGINT UNSIGNED NOT NULL,
                    payment_method VARCHAR(30) NOT NULL DEFAULT 'Cash',
                    amount_received_cents BIGINT UNSIGNED NOT NULL DEFAULT 0,
                    change_cents BIGINT UNSIGNED NOT NULL DEFAULT 0,
                    reversed_at VARCHAR(40),
                    reversed_by_id BIGINT UNSIGNED,
                    CONSTRAINT fk_sales_seller FOREIGN KEY (seller_id) REFERENCES users(user_id),
                    CONSTRAINT fk_sales_reverser FOREIGN KEY (reversed_by_id) REFERENCES users(user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS products (
                    product_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    barcode VARCHAR(255) NULL UNIQUE,
                    unit_price_cents BIGINT UNSIGNED NOT NULL,
                    stock_quantity BIGINT UNSIGNED NOT NULL DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS sale_items (
                    sale_item_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    sale_id BIGINT UNSIGNED NOT NULL,
                    product_id BIGINT UNSIGNED,
                    item_name VARCHAR(255) NOT NULL,
                    unit_price_cents BIGINT UNSIGNED NOT NULL,
                    quantity BIGINT UNSIGNED NOT NULL,
                    CONSTRAINT fk_sale_items_sale FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE,
                    CONSTRAINT fk_sale_items_product FOREIGN KEY (product_id) REFERENCES products(product_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
            )
            sales_columns = {row["Field"] for row in connection.execute("SHOW COLUMNS FROM sales")}
            if "reversed_at" not in sales_columns:
                connection.execute("ALTER TABLE sales ADD COLUMN reversed_at VARCHAR(40)")
            if "reversed_by_id" not in sales_columns:
                connection.execute("ALTER TABLE sales ADD COLUMN reversed_by_id BIGINT UNSIGNED NULL")
            for column, definition in (("payment_method", "VARCHAR(30) NOT NULL DEFAULT 'Cash'"), ("amount_received_cents", "BIGINT UNSIGNED NOT NULL DEFAULT 0"), ("change_cents", "BIGINT UNSIGNED NOT NULL DEFAULT 0"), ("tax_rate", "DECIMAL(8,6) NOT NULL DEFAULT 0.070000")):
                if column not in sales_columns:
                    connection.execute(f"ALTER TABLE sales ADD COLUMN {column} {definition}")
            product_columns = {row["Field"] for row in connection.execute("SHOW COLUMNS FROM products")}
            if "barcode" not in product_columns:
                connection.execute("ALTER TABLE products ADD COLUMN barcode VARCHAR(255) NULL UNIQUE")
            sale_item_columns = {row["Field"] for row in connection.execute("SHOW COLUMNS FROM sale_items")}
            if "product_id" not in sale_item_columns:
                connection.execute("ALTER TABLE sale_items ADD COLUMN product_id BIGINT UNSIGNED NULL")

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
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (username, full_name, phone.strip(), role, salt, pin_hash, datetime.now().astimezone().isoformat(timespec="seconds")),
                )
            except DatabaseError as error:
                if error.errno == 1062:
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
        query = "SELECT * FROM users WHERE username = %s AND active = 1"
        parameters = [username.strip()]
        if role:
            query += " AND role = %s"
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
            query += " AND role = %s"
            parameters.append(role)
        query += " ORDER BY full_name"
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
                    "SELECT product_id, name, barcode, unit_price_cents, stock_quantity FROM products ORDER BY name"
                )
            ]

    def add_stock(self, actor_id, name, unit_price, quantity, barcode=None):
        name = name.strip()
        barcode = barcode.strip() or None if barcode is not None else None
        try:
            unit_price_cents = self._price_cents(unit_price)
            quantity = int(quantity)
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("Enter a valid price and a whole-number quantity.") from error
        if not name or unit_price_cents < 0 or quantity < 1:
            raise ValueError("Enter a product name, a non-negative price, and a quantity of at least 1.")

        with self._connect() as connection:
            connection.start_transaction()
            actor = connection.execute(
                "SELECT 1 FROM users WHERE user_id = %s AND role = 'superuser' AND active = 1",
                (actor_id,),
            ).fetchone()
            if actor is None:
                raise ValueError("Only an active superuser can add stock.")
            product = connection.execute(
                "SELECT product_id FROM products WHERE name = %s FOR UPDATE",
                (name,),
            ).fetchone()
            if product is None:
                connection.execute(
                    "INSERT INTO products (name, barcode, unit_price_cents, stock_quantity) VALUES (%s, %s, %s, %s)",
                    (name, barcode, unit_price_cents, quantity),
                )
            else:
                connection.execute(
                    "UPDATE products SET barcode = COALESCE(%s, barcode), unit_price_cents = %s, stock_quantity = stock_quantity + %s WHERE product_id = %s",
                    (barcode, unit_price_cents, quantity, product["product_id"]),
                )

    def update_product(self, actor_id, product_id, name, unit_price, stock_quantity, barcode=None):
        name = name.strip()
        barcode = barcode.strip() or None if barcode is not None else None
        try:
            price_cents = self._price_cents(unit_price)
            stock_quantity = int(stock_quantity)
            product_id = int(product_id)
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("Enter a valid price and a whole-number stock quantity.") from error
        if not name or price_cents < 0 or stock_quantity < 0:
            raise ValueError("Enter a product name, non-negative price and stock quantity.")
        with self._connect() as connection:
            actor = connection.execute("SELECT 1 FROM users WHERE user_id = %s AND role = 'superuser' AND active = 1", (actor_id,)).fetchone()
            if actor is None:
                raise ValueError("Only an active superuser can edit products.")
            try:
                connection.execute("UPDATE products SET name = %s, barcode = %s, unit_price_cents = %s, stock_quantity = %s WHERE product_id = %s", (name, barcode, price_cents, stock_quantity, product_id))
            except DatabaseError as error:
                if error.errno == 1062:
                    raise ValueError("That product name or barcode is already in use.") from error
                raise

    def create_sale(self, receipt_number, seller_id, store_name, items, tax_rate=Decimal("0.07"), payment_method="Cash", amount_received=None):
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
            connection.start_transaction()
            seller = connection.execute(
                "SELECT full_name FROM users WHERE user_id = %s AND role = 'cashier' AND active = 1",
                (seller_id,),
            ).fetchone()
            if seller is None:
                raise ValueError("The selected cashier is not active.")

            sale_items = []
            for product_id, quantity in prepared_items:
                product = connection.execute(
                    "SELECT name, unit_price_cents, stock_quantity FROM products WHERE product_id = %s FOR UPDATE",
                    (product_id,),
                ).fetchone()
                if product is None:
                    raise ValueError("A selected product is no longer available.")
                if product["stock_quantity"] < quantity:
                    raise ValueError(f"Insufficient stock for {product['name']}; {product['stock_quantity']} remaining.")
                connection.execute(
                    "UPDATE products SET stock_quantity = stock_quantity - %s WHERE product_id = %s",
                    (quantity, product_id),
                )
                sale_items.append((product_id, product["name"], product["unit_price_cents"], quantity))

            subtotal_cents = sum(unit_price * quantity for _, _, unit_price, quantity in sale_items)
            tax_cents = int((Decimal(subtotal_cents) * Decimal(str(tax_rate))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            total_cents = subtotal_cents + tax_cents
            payment_method = str(payment_method).strip().title()
            if payment_method not in ("Cash", "Card", "Mobile Money", "Other"):
                raise ValueError("Choose a supported payment method.")
            try:
                received_cents = self._price_cents(total_cents / 100 if amount_received is None else amount_received)
            except (InvalidOperation, TypeError, ValueError) as error:
                raise ValueError("Enter a valid amount received.") from error
            if received_cents < total_cents:
                raise ValueError("Amount received must cover the sale total.")
            if payment_method != "Cash" and received_cents != total_cents:
                raise ValueError("For non-cash payments, amount received must equal the sale total.")
            change_cents = received_cents - total_cents
            cursor = connection.execute(
                """INSERT INTO sales
                   (receipt_number, seller_id, seller_name, store_name, sold_at, subtotal_cents, tax_cents, tax_rate, total_cents, payment_method, amount_received_cents, change_cents)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (receipt_number, seller_id, seller["full_name"], store_name, sold_at, subtotal_cents, tax_cents, Decimal(str(tax_rate)), total_cents, payment_method, received_cents, change_cents),
            )
            sale_id = cursor.lastrowid
            connection.executemany(
                """INSERT INTO sale_items (sale_id, product_id, item_name, unit_price_cents, quantity)
                   VALUES (%s, %s, %s, %s, %s)""",
                [(sale_id, product_id, name, unit_price, quantity) for product_id, name, unit_price, quantity in sale_items],
            )
        return sale_id

    def reverse_sale(self, sale_id, superuser_id, pin):
        with self._connect() as connection:
            connection.start_transaction()
            superuser = connection.execute(
                "SELECT pin_salt, pin_hash FROM users WHERE user_id = %s AND role = 'superuser' AND active = 1",
                (superuser_id,),
            ).fetchone()
            if superuser is None or not hmac.compare_digest(self._pin_digest(pin, superuser["pin_salt"]), superuser["pin_hash"]):
                raise ValueError("The superuser code was not accepted.")

            sale = connection.execute("SELECT reversed_at FROM sales WHERE sale_id = %s FOR UPDATE", (sale_id,)).fetchone()
            if sale is None:
                raise ValueError("The selected sale could not be found.")
            if sale["reversed_at"] is not None:
                raise ValueError("This sale has already been reversed.")
            items = connection.execute(
                "SELECT product_id, quantity FROM sale_items WHERE sale_id = %s",
                (sale_id,),
            ).fetchall()
            for item in items:
                if item["product_id"] is not None:
                    connection.execute(
                        "UPDATE products SET stock_quantity = stock_quantity + %s WHERE product_id = %s",
                        (item["quantity"], item["product_id"]),
                    )
            connection.execute(
                "UPDATE sales SET reversed_at = %s, reversed_by_id = %s WHERE sale_id = %s",
                (datetime.now().astimezone().isoformat(timespec="seconds"), superuser_id, sale_id),
            )

    def list_sales(self):
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT s.sale_id, s.receipt_number, s.sold_at, s.seller_name, s.store_name,
                          s.payment_method, s.amount_received_cents, s.change_cents,
                          s.reversed_at, s.reversed_by_id,
                          s.subtotal_cents, s.tax_cents, s.tax_rate, s.total_cents,
                          GROUP_CONCAT(CONCAT(i.item_name, ' x', i.quantity) SEPARATOR ', ') AS item_summary
                   FROM sales AS s
                   JOIN sale_items AS i ON i.sale_id = s.sale_id
                   GROUP BY s.sale_id
                   ORDER BY s.sale_id DESC"""
            )
            return [dict(row) for row in rows]

    def get_sale(self, sale_id):
        with self._connect() as connection:
            sale = connection.execute("SELECT * FROM sales WHERE sale_id = %s", (sale_id,)).fetchone()
            if sale is None:
                return None
            result = dict(sale)
            result["items"] = [
                dict(row)
                for row in connection.execute(
                    "SELECT product_id, item_name, unit_price_cents, quantity FROM sale_items WHERE sale_id = %s ORDER BY sale_item_id",
                    (sale_id,),
                )
            ]
            return result
