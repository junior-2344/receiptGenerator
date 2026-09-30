# MySQL Setup

The app connects to MySQL using MySQL Connector/Python. On startup, it creates the configured database if needed, then creates or updates its tables.

## Configure your existing MySQL user

Set the credentials for the MySQL user you already have in the same PowerShell terminal used to run the app. If the app is creating the database, that user needs permission to create databases. If an administrator creates it first, the app user only needs permission to create or alter tables in that database. `MYSQL_DATABASE` is optional and defaults to `receipt_generator`.

```powershell
$env:MYSQL_HOST = "127.0.0.1"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "your-existing-mysql-user"
$env:MYSQL_PASSWORD = "your-existing-mysql-password"
# Set these for the shop (0.165 means 16.5% tax).
$env:RECEIPT_TAX_RATE = "0.165"
$env:RECEIPT_STORE_NAME = "Your Shop Name"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If your existing user cannot create databases, have a MySQL administrator create the database and grant that user access. Replace the username and host with the exact existing MySQL account:

```sql
CREATE DATABASE receipt_generator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON receipt_generator.* TO 'your-existing-mysql-user'@'localhost';
```

## Barcode and QR scanning

Use a USB or Bluetooth scanner that types the scanned code into the focused field and sends Enter afterward. In Stock management, save each product's barcode or QR value in the `BARCODE / QR CODE` field. Codes must be unique. At checkout, scanning a saved code adds that product using its stored price; if a code is not recognized, choose the product manually from the product list. QR codes should contain the exact value saved for that product.

At checkout, select cash, card, mobile money, or other. Cash requires the amount tendered and the receipt records change due; other methods are recorded at the exact sale total. Superusers can review today's sales and payment breakdown, restock products, or select a product to update its name, barcode, price, and on-hand quantity. Keep the tax fraction and shop name in the same PowerShell session used to launch the app. The tax setting is a decimal fraction: `0.165` means 16.5%, and `0` disables tax.

To copy the existing SQLite accounts, products, receipts, and receipt lines into the empty MySQL tables, run this once before launching the app:

```powershell
.\.venv\Scripts\python.exe migrate_sqlite_to_mysql.py
```

The importer stops if any target table already contains rows and leaves the SQLite file unchanged. To migrate a different SQLite file, pass its path as the command argument.

Then start the app:

```powershell
.\.venv\Scripts\python.exe main.py
```

Without `MYSQL_USER` or `MYSQL_PASSWORD`, startup reports the missing configuration. `MYSQL_HOST` and `MYSQL_PORT` default to `127.0.0.1` and `3306`.
