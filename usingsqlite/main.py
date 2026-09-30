from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import html
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from pathlib import Path
from storage import ReceiptDatabase


class LoginWindow:
    BG = "#eef2ee"
    INK = "#172b24"
    MUTED = "#68776f"
    GREEN = "#176b50"
    GREEN_DARK = "#10513d"
    LINE = "#dce4dd"
    WHITE = "#ffffff"

    def __init__(self, root, database, on_login):
        self.root = root
        self.database = database
        self.on_login = on_login
        self.root.title("Sign in · Receipt Studio")
        self.root.geometry("480x590")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)

        header = tk.Frame(root, bg=self.INK, height=118)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="RECEIPT STUDIO", bg=self.INK, fg="#a9d7bd", font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=32, pady=(24, 4))
        tk.Label(header, text="Sign in to continue", bg=self.INK, fg=self.WHITE, font=("Segoe UI Semibold", 20)).pack(anchor="w", padx=32)

        form = tk.Frame(root, bg=self.WHITE, highlightbackground=self.LINE, highlightthickness=1)
        form.pack(fill="x", padx=32, pady=28)
        tk.Label(form, text="USERNAME", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=22, pady=(22, 5))
        self.username = tk.StringVar()
        self.username_entry = self._entry(form, self.username)
        self.username_entry.pack(fill="x", padx=22)
        tk.Label(form, text="PIN", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=22, pady=(16, 5))
        self.pin = tk.StringVar()
        self.pin_entry = self._entry(form, self.pin, secret=True)
        self.pin_entry.pack(fill="x", padx=22)
        self.status = tk.Label(form, text="", bg=self.WHITE, fg="#a14e42", font=("Segoe UI", 9), anchor="w", wraplength=390)
        self.status.pack(fill="x", padx=22, pady=(10, 0))
        tk.Button(form, text="Sign in", command=self._submit, bg=self.GREEN, fg=self.WHITE, activebackground=self.GREEN_DARK, activeforeground=self.WHITE, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 10), padx=18, pady=11).pack(fill="x", padx=22, pady=(14, 22))
        self.username_entry.bind("<Return>", lambda _: self.pin_entry.focus_set())
        self.pin_entry.bind("<Return>", self._submit)

        footer = tk.Frame(root, bg=self.BG)
        footer.pack(fill="x", padx=32)
        tk.Label(footer, text="Authorized staff only", bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9)).pack(side="left")
        if not self.database.has_superuser():
            tk.Button(footer, text="Create first superuser", command=self._show_superuser_setup, bg=self.BG, fg=self.GREEN, activebackground=self.BG, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 9)).pack(side="right")
        self.username_entry.focus_set()

    def _entry(self, parent, variable, secret=False):
        return tk.Entry(
            parent,
            textvariable=variable,
            show="*" if secret else "",
            bg="#fbfcfb",
            fg=self.INK,
            insertbackground=self.GREEN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.LINE,
            highlightcolor=self.GREEN,
            font=("Segoe UI", 10),
        )

    def _submit(self, _event=None):
        username = self.username.get().strip()
        pin = self.pin.get()
        if not username or not pin:
            self.status.configure(text="Enter your username and PIN.")
            return "break"
        user = self.database.verify_pin(username, pin)
        if user is None:
            self.pin.set("")
            self.status.configure(text="Username or PIN was not accepted.")
            self.pin_entry.focus_set()
            return "break"
        self.on_login(user)
        return "break"

    def _show_superuser_setup(self):
        window = tk.Toplevel(self.root)
        window.title("Set up superuser")
        window.geometry("430x490")
        window.resizable(False, False)
        window.configure(bg=self.BG)
        window.transient(self.root)
        window.grab_set()

        tk.Label(window, text="FIRST-TIME SETUP", bg=self.BG, fg=self.GREEN, font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=26, pady=(22, 4))
        tk.Label(window, text="Create the first superuser", bg=self.BG, fg=self.INK, font=("Segoe UI Semibold", 18)).pack(anchor="w", padx=26)
        form = tk.Frame(window, bg=self.BG)
        form.pack(fill="x", padx=26, pady=16)
        fields = {}
        for label, key, secret in (
            ("FULL NAME", "full_name", False),
            ("USERNAME", "username", False),
            ("PIN (4 OR MORE DIGITS)", "pin", True),
            ("CONFIRM PIN", "confirm_pin", True),
        ):
            tk.Label(form, text=label, bg=self.BG, fg=self.MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(8, 4))
            fields[key] = tk.StringVar(window)
            self._entry(form, fields[key], secret=secret).pack(fill="x")

        def create_superuser():
            if fields["pin"].get() != fields["confirm_pin"].get():
                messagebox.showerror("PINs do not match", "Enter the same PIN in both fields.", parent=window)
                return
            try:
                self.database.add_user(fields["full_name"].get(), fields["username"].get(), "", fields["pin"].get(), role="superuser")
            except ValueError as error:
                messagebox.showerror("Could not create superuser", str(error), parent=window)
                return
            window.grab_release()
            window.destroy()
            self.status.configure(text="Superuser created. Sign in with your new credentials.", fg=self.GREEN)
            self.username.set(fields["username"].get().strip())
            self.pin_entry.focus_set()

        tk.Button(window, text="Create superuser", command=create_superuser, bg=self.GREEN, fg=self.WHITE, activebackground=self.GREEN_DARK, activeforeground=self.WHITE, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 10), padx=18, pady=10).pack(anchor="e", padx=26, pady=(0, 18))


class ReceiptApp:
    BG = "#eef2ee"
    INK = "#172b24"
    MUTED = "#68776f"
    GREEN = "#176b50"
    GREEN_DARK = "#10513d"
    LINE = "#dce4dd"
    WHITE = "#ffffff"
    TAX_RATE = 0.07

    def __init__(self, root, database, current_user):
        self.root = root
        self.database = database
        self.current_user = current_user
        self.root.title("Receipt Studio")
        self.root.geometry("1120x790")
        self.root.minsize(940, 680)
        self.root.configure(bg=self.BG)

        self.items = []
        self.receipt_number = datetime.now().strftime("%y%m%d-%H%M%S-%f")
        self.store_name = tk.StringVar(value="Corner Market")
        self.item_name = tk.StringVar()
        self.item_price = tk.StringVar()
        self.item_quantity = tk.StringVar(value="1")
        self.products_by_name = {}
        self.seller_selection = tk.StringVar()
        self.cashiers_by_label = {}
        self.sale_id = None
        self.saved_sale = None
        self.status = tk.StringVar(value="Ready for your first item")
        self.selected_printer = tk.StringVar()
        self.printer_status = tk.StringVar(value="Loading printers...")
        self.default_printer_name = ""

        self._configure_styles()
        self._build_layout()
        self._refresh_printers()
        self._refresh_cashiers()
        self._refresh_products()
        self._refresh_receipt()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Receipt.Treeview",
            background=self.WHITE,
            foreground=self.INK,
            fieldbackground=self.WHITE,
            rowheight=34,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Receipt.Treeview.Heading",
            background="#f3f6f3",
            foreground=self.MUTED,
            relief="flat",
            font=("Segoe UI Semibold", 9),
        )
        style.map("Receipt.Treeview", background=[("selected", "#dcebe3")], foreground=[("selected", self.INK)])
        style.configure("Receipt.Vertical.TScrollbar", background="#e5ebe6", troughcolor=self.WHITE, borderwidth=0)

    def _build_layout(self):
        header = tk.Frame(self.root, bg=self.INK, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=self.INK)
        brand.pack(side="left", padx=28, pady=17)
        tk.Label(brand, text="RECEIPT STUDIO", bg=self.INK, fg="#a9d7bd", font=("Segoe UI Semibold", 9)).pack(anchor="w")
        tk.Label(brand, text="Make the sale. Print the proof.", bg=self.INK, fg=self.WHITE, font=("Segoe UI Semibold", 19)).pack(anchor="w", pady=(2, 0))

        tk.Label(
            header,
            text="●  READY",
            bg=self.INK,
            fg="#9fe0b8",
            font=("Segoe UI Semibold", 9),
        ).pack(side="right", padx=30)
        tk.Label(
            header,
            text=f"SIGNED IN  {self.current_user['full_name']} (@{self.current_user['username']})",
            bg=self.INK,
            fg="#d7e7dc",
            font=("Segoe UI Semibold", 9),
        ).pack(side="right", padx=(0, 12))
        tk.Button(header, text="LOG OUT", command=self._logout, bg=self.INK, fg="#d7e7dc", activebackground=self.GREEN_DARK, activeforeground=self.WHITE, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 9), padx=10, pady=8).pack(side="right", padx=(0, 8))
        tk.Button(header, text="SUPERUSER", command=self._open_superuser, bg=self.INK, fg="#d7e7dc", activebackground=self.GREEN_DARK, activeforeground=self.WHITE, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 9), padx=12, pady=8).pack(side="right", padx=(0, 8))
        if self.current_user["role"] == "superuser":
            tk.Button(header, text="STOCK", command=self._open_stock_manager, bg=self.INK, fg="#d7e7dc", activebackground=self.GREEN_DARK, activeforeground=self.WHITE, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 9), padx=12, pady=8).pack(side="right", padx=(0, 8))
        tk.Button(header, text="PURCHASES", command=self._open_history, bg=self.INK, fg="#d7e7dc", activebackground=self.GREEN_DARK, activeforeground=self.WHITE, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 9), padx=12, pady=8).pack(side="right", padx=(0, 8))

        content = tk.Frame(self.root, bg=self.BG)
        content.pack(fill="both", expand=True, padx=22, pady=20)
        content.grid_columnconfigure(0, weight=6, uniform="columns")
        content.grid_columnconfigure(1, weight=5, uniform="columns")
        content.grid_rowconfigure(0, weight=1)

        left = tk.Frame(content, bg=self.BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = tk.Frame(content, bg=self.BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_sale_panel(left)
        self._build_items_panel(left)
        self._build_preview_panel(right)

        footer = tk.Frame(self.root, bg=self.BG)
        footer.pack(fill="x", padx=26, pady=(0, 12))
        tk.Label(footer, textvariable=self.status, bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9)).pack(side="left")
        tk.Label(footer, text="Tax  7%", bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9)).pack(side="right")

    def _panel(self, parent, title, subtitle=None):
        panel = tk.Frame(parent, bg=self.WHITE, highlightbackground=self.LINE, highlightthickness=1)
        heading = tk.Frame(panel, bg=self.WHITE)
        heading.pack(fill="x", padx=18, pady=(15, 10))
        tk.Label(heading, text=title, bg=self.WHITE, fg=self.INK, font=("Segoe UI Semibold", 12)).pack(anchor="w")
        if subtitle:
            tk.Label(heading, text=subtitle, bg=self.WHITE, fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))
        return panel

    def _build_sale_panel(self, parent):
        panel = self._panel(parent, "Sale details", "Your shop name appears at the top of the receipt.")
        panel.pack(fill="x", pady=(0, 12))
        fields = tk.Frame(panel, bg=self.WHITE)
        fields.pack(fill="x", padx=18, pady=(0, 16))
        tk.Label(fields, text="BUSINESS NAME", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(0, 5))
        self.store_entry = self._entry(fields, self.store_name)
        self.store_entry.pack(fill="x")
        tk.Label(fields, text="SELLER", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(10, 5))
        self.seller_selector = ttk.Combobox(fields, textvariable=self.seller_selection, state="readonly")
        self.seller_selector.pack(fill="x")
        self.seller_selector.bind("<<ComboboxSelected>>", lambda _: self._refresh_receipt())
        self.store_name.trace_add("write", lambda *_: self._refresh_receipt())

    def _entry(self, parent, variable, width=None):
        return tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            bg="#fbfcfb",
            fg=self.INK,
            insertbackground=self.GREEN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.LINE,
            highlightcolor=self.GREEN,
            font=("Segoe UI", 10),
        )

    def _build_items_panel(self, parent):
        panel = self._panel(parent, "Line items", "Select a stocked product and quantity to build the sale.")
        panel.pack(fill="both", expand=True)

        form = tk.Frame(panel, bg=self.WHITE)
        form.pack(fill="x", padx=18, pady=(0, 15))
        tk.Label(form, text="PRODUCT", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).grid(row=0, column=0, sticky="w", pady=(0, 5))
        tk.Label(form, text="PRICE (K)", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 5))
        tk.Label(form, text="QTY", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).grid(row=0, column=2, sticky="w", padx=(8, 0), pady=(0, 5))
        form.grid_columnconfigure(0, weight=1)
        self.name_entry = ttk.Combobox(form, textvariable=self.item_name, state="readonly")
        self.name_entry.grid(row=1, column=0, sticky="ew")
        self.item_price_entry = self._entry(form, self.item_price, 10)
        self.item_price_entry.configure(state="readonly")
        self.item_price_entry.grid(row=1, column=1, padx=(8, 0), sticky="ew")
        self.item_quantity_entry = self._entry(form, self.item_quantity, 5)
        self.item_quantity_entry.grid(row=1, column=2, padx=(8, 0), sticky="ew")
        self.add_item_button = tk.Button(
            form,
            text="＋  Add item",
            command=self._add_item,
            bg=self.GREEN,
            fg=self.WHITE,
            activebackground=self.GREEN_DARK,
            activeforeground=self.WHITE,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI Semibold", 9),
            padx=12,
            pady=8,
        )
        self.add_item_button.grid(row=1, column=3, padx=(8, 0))
        self.name_entry.bind("<<ComboboxSelected>>", self._select_product)
        self.item_price_entry.bind("<Return>", lambda _: self._add_item())
        self.stock_status = tk.Label(form, text="", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI", 8), anchor="w")
        self.stock_status.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(5, 0))

        table_frame = tk.Frame(panel, bg=self.WHITE)
        table_frame.pack(fill="both", expand=True, padx=18)
        columns = ("item", "price", "qty", "amount")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", style="Receipt.Treeview", selectmode="extended")
        self.table.heading("item", text="ITEM", anchor="w")
        self.table.heading("price", text="PRICE", anchor="e")
        self.table.heading("qty", text="QTY", anchor="center")
        self.table.heading("amount", text="AMOUNT", anchor="e")
        self.table.column("item", anchor="w", width=180, stretch=True)
        self.table.column("price", anchor="e", width=82, stretch=False)
        self.table.column("qty", anchor="center", width=54, stretch=False)
        self.table.column("amount", anchor="e", width=100, stretch=False)
        self.table.pack(fill="both", expand=True)
        self.table.bind("<Delete>", lambda _: self._remove_selected())

        actions = tk.Frame(panel, bg=self.WHITE)
        actions.pack(fill="x", padx=18, pady=12)
        self.remove_button = tk.Button(actions, text="Remove selected", command=self._remove_selected, bg=self.WHITE, fg=self.MUTED, activebackground="#f3f6f3", relief="flat", cursor="hand2", font=("Segoe UI", 9))
        self.remove_button.pack(side="left")
        self.clear_button = tk.Button(actions, text="Clear sale", command=self._clear_sale, bg=self.WHITE, fg="#a14e42", activebackground="#fbf2f0", relief="flat", cursor="hand2", font=("Segoe UI", 9))
        self.clear_button.pack(side="right")
        self.new_sale_button = tk.Button(actions, text="New sale", command=self._new_sale, bg=self.WHITE, fg=self.GREEN, activebackground="#f3f6f3", relief="flat", cursor="hand2", font=("Segoe UI", 9), state="disabled")
        self.new_sale_button.pack(side="right", padx=(0, 10))

    def _build_preview_panel(self, parent):
        panel = self._panel(parent, "Receipt preview", "Updates as you add items.")
        panel.pack(fill="both", expand=True)

        printer_row = tk.Frame(panel, bg=self.WHITE)
        printer_row.pack(fill="x", padx=18, pady=(0, 12))
        tk.Label(printer_row, text="PRINTER", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(0, 5))
        printer_controls = tk.Frame(printer_row, bg=self.WHITE)
        printer_controls.pack(fill="x")
        self.printer_selector = ttk.Combobox(
            printer_controls,
            textvariable=self.selected_printer,
            state="readonly",
        )
        self.printer_selector.pack(side="left", fill="x", expand=True)
        tk.Button(
            printer_controls,
            text="↻",
            command=self._refresh_printers,
            bg=self.WHITE,
            fg=self.INK,
            activebackground="#f3f6f3",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 12),
            padx=10,
        ).pack(side="left", padx=(5, 0))
        tk.Button(
            printer_controls,
            text="Set as default",
            command=self._set_default_printer,
            bg=self.WHITE,
            fg=self.GREEN,
            activebackground="#f3f6f3",
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.LINE,
            cursor="hand2",
            font=("Segoe UI Semibold", 9),
            padx=10,
            pady=7,
        ).pack(side="left", padx=(6, 0))
        tk.Label(printer_row, textvariable=self.printer_status, bg=self.WHITE, fg=self.MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(5, 0))

        paper_frame = tk.Frame(panel, bg="#f2f5f1", padx=18, pady=16)
        paper_frame.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        paper_frame.grid_rowconfigure(0, weight=1)
        paper_frame.grid_columnconfigure(0, weight=1)
        self.preview = tk.Text(
            paper_frame,
            wrap="none",
            bg=self.WHITE,
            fg=self.INK,
            relief="flat",
            padx=22,
            pady=22,
            font=("Consolas", 9),
            spacing1=1,
            spacing3=1,
            state="disabled",
        )
        self.preview.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(paper_frame, orient="vertical", command=self.preview.yview, style="Receipt.Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=scrollbar.set)

        buttons = tk.Frame(panel, bg=self.WHITE)
        buttons.pack(fill="x", padx=18, pady=(0, 18))
        tk.Button(buttons, text="Save HTML", command=self._save_receipt, bg=self.WHITE, fg=self.INK, activebackground="#f3f6f3", relief="flat", highlightthickness=1, highlightbackground=self.LINE, cursor="hand2", font=("Segoe UI Semibold", 9), padx=14, pady=10).pack(side="left")
        tk.Button(buttons, text="Complete sale", command=self._complete_sale, bg="#e5eee8", fg=self.GREEN_DARK, activebackground="#d5e6db", relief="flat", cursor="hand2", font=("Segoe UI Semibold", 9), padx=12, pady=10).pack(side="left", padx=(8, 0))
        tk.Button(buttons, text="Print receipt  →", command=self._print_receipt, bg=self.GREEN, fg=self.WHITE, activebackground=self.GREEN_DARK, activeforeground=self.WHITE, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 10), padx=18, pady=10).pack(side="right")

    def _add_item(self):
        if self.sale_id is not None:
            self.status.set("Start a new sale before changing this completed sale")
            return
        name = self.item_name.get().strip()
        product = self.products_by_name.get(name)
        try:
            quantity = int(self.item_quantity.get())
        except ValueError:
            messagebox.showerror("Check the item details", "Choose a product and enter a whole-number quantity.", parent=self.root)
            return
        if product is None or quantity < 1:
            messagebox.showerror("Check the item details", "Choose an available product and a quantity of at least 1.", parent=self.root)
            return
        already_in_sale = sum(item["quantity"] for item in self.items if item["product_id"] == product["product_id"])
        available = product["stock_quantity"] - already_in_sale
        if quantity > available:
            messagebox.showerror("Insufficient stock", f"Only {available} more of {product['name']} are available.", parent=self.root)
            return

        self.items.append({
            "product_id": product["product_id"],
            "name": product["name"],
            "price": Decimal(product["unit_price_cents"]) / 100,
            "quantity": quantity,
        })
        self.item_name.set("")
        self.item_price.set("")
        self.item_quantity.set("1")
        self.stock_status.configure(text="")
        self.name_entry.focus_set()
        self.status.set(f"Added {name}")
        self._refresh_receipt()

    def _remove_selected(self):
        if self.sale_id is not None:
            self.status.set("Completed sales cannot be edited")
            return
        selected = self.table.selection()
        if not selected:
            self.status.set("Select one or more items to remove")
            return
        indexes = sorted((int(item_id) for item_id in selected), reverse=True)
        for index in indexes:
            del self.items[index]
        self.status.set("Selected item removed")
        self._refresh_receipt()

    def _clear_sale(self):
        if self.sale_id is not None:
            self.status.set("Completed sales are kept in purchase history")
            return
        if not self.items:
            self.status.set("There are no items to clear")
            return
        self.items.clear()
        self.receipt_number = datetime.now().strftime("%y%m%d-%H%M%S-%f")
        self.status.set("Draft sale cleared")
        self._refresh_receipt()

    def _new_sale(self):
        self.items.clear()
        self.sale_id = None
        self.saved_sale = None
        self.receipt_number = datetime.now().strftime("%y%m%d-%H%M%S-%f")
        self.store_entry.configure(state="normal")
        self.seller_selector.configure(state="disabled" if self.current_user["role"] == "cashier" else "readonly")
        for control in (self.name_entry, self.item_price_entry, self.item_quantity_entry, self.add_item_button, self.remove_button, self.clear_button):
            control.configure(state="normal")
        self.name_entry.configure(state="readonly")
        self.item_price_entry.configure(state="readonly")
        self.new_sale_button.configure(state="disabled")
        self.status.set("New sale started")
        self._refresh_receipt()

    def _refresh_cashiers(self):
        users = self.database.list_users(role="cashier")
        self.cashiers_by_label = {
            f"{user['full_name']} (@{user['username']})": user
            for user in users
        }
        labels = list(self.cashiers_by_label)
        if self.current_user["role"] == "cashier":
            own_label = next(
                (label for label, user in self.cashiers_by_label.items() if user["user_id"] == self.current_user["user_id"]),
                "",
            )
            self.seller_selector.configure(values=[own_label] if own_label else [], state="disabled")
            self.seller_selection.set(own_label)
        else:
            self.seller_selector.configure(values=labels, state="readonly")
        if self.current_user["role"] != "cashier" and self.seller_selection.get() not in self.cashiers_by_label:
            self.seller_selection.set("")
        if not labels and self.current_user["role"] == "superuser":
            self.status.set("Add a cashier in Superuser before completing a sale")

    def _refresh_products(self):
        products = self.database.list_products()
        self.products_by_name = {product["name"]: product for product in products}
        if hasattr(self, "name_entry"):
            self.name_entry.configure(values=list(self.products_by_name))
            if self.item_name.get() not in self.products_by_name:
                self.item_name.set("")
                self.item_price.set("")
        if not products:
            self.status.set("Add stock using Stock before recording a sale")

    def _select_product(self, _event=None):
        product = self.products_by_name.get(self.item_name.get())
        if product is None:
            self.item_price.set("")
            self.stock_status.configure(text="")
            return
        self.item_price.set(f"{product['unit_price_cents'] / 100:.2f}")
        reserved = sum(item["quantity"] for item in self.items if item["product_id"] == product["product_id"])
        self.stock_status.configure(text=f"In stock: {product['stock_quantity'] - reserved}")

    def _complete_sale(self):
        if self.sale_id is not None:
            self.status.set("This sale is already recorded")
            return
        if not self.items:
            messagebox.showinfo("No items yet", "Add at least one item before completing a sale.", parent=self.root)
            return
        if self.current_user["role"] == "cashier":
            verified_seller = self.current_user
        else:
            seller = self.cashiers_by_label.get(self.seller_selection.get())
            if seller is None:
                messagebox.showinfo("Select a seller", "Choose the cashier who made this sale.", parent=self.root)
                return
            pin = simpledialog.askstring(
                "Verify cashier",
                f"Enter the PIN for {seller['full_name']}: ",
                show="*",
                parent=self.root,
            )
            if pin is None:
                return
            verified_seller = self.database.verify_pin(seller["username"], pin, role="cashier")
            if verified_seller is None:
                messagebox.showerror("PIN not accepted", "The cashier PIN was not accepted.", parent=self.root)
                return
        try:
            self.sale_id = self.database.create_sale(
                self.receipt_number,
                verified_seller["user_id"],
                self.store_name.get().strip() or "Your Store",
                self.items,
                tax_rate=self.TAX_RATE,
            )
        except (sqlite3.Error, ValueError) as error:
            messagebox.showerror("Could not save sale", str(error), parent=self.root)
            return
        self.saved_sale = self.database.get_sale(self.sale_id)
        self.items = [
            {
                "product_id": item["product_id"],
                "name": item["item_name"],
                "price": Decimal(item["unit_price_cents"]) / 100,
                "quantity": item["quantity"],
            }
            for item in self.saved_sale["items"]
        ]
        self._refresh_products()
        self.store_entry.configure(state="disabled")
        self.seller_selector.configure(state="disabled")
        for control in (self.name_entry, self.item_price_entry, self.item_quantity_entry, self.add_item_button, self.remove_button, self.clear_button):
            control.configure(state="disabled")
        self.new_sale_button.configure(state="normal")
        self.status.set(f"Sale recorded for {verified_seller['full_name']}")
        self._refresh_receipt()

    def _open_superuser(self):
        if self.current_user["role"] != "superuser":
            messagebox.showerror("Access denied", "Only a signed-in superuser can manage users.", parent=self.root)
            return
        self._open_user_manager()

    def _open_stock_manager(self):
        if self.current_user["role"] != "superuser":
            messagebox.showerror("Access denied", "Only a signed-in superuser can manage stock.", parent=self.root)
            return

        window = tk.Toplevel(self.root)
        window.title("Stock management")
        window.geometry("720x540")
        window.minsize(620, 440)
        window.configure(bg=self.BG)
        tk.Label(window, text="INVENTORY", bg=self.BG, fg=self.GREEN, font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=24, pady=(20, 4))
        tk.Label(window, text="Add or restock products", bg=self.BG, fg=self.INK, font=("Segoe UI Semibold", 19)).pack(anchor="w", padx=24)

        form_panel = tk.Frame(window, bg=self.WHITE, highlightbackground=self.LINE, highlightthickness=1)
        form_panel.pack(fill="x", padx=24, pady=16)
        form = tk.Frame(form_panel, bg=self.WHITE)
        form.pack(fill="x", padx=16, pady=14)
        fields = {}
        for column, (label, key, width) in enumerate((
            ("PRODUCT", "name", 24),
            ("UNIT PRICE (K)", "price", 14),
            ("QUANTITY TO ADD", "quantity", 14),
        )):
            tk.Label(form, text=label, bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).grid(row=0, column=column, sticky="w", padx=(0, 10), pady=(0, 5))
            fields[key] = tk.StringVar(window)
            self._entry(form, fields[key], width).grid(row=1, column=column, sticky="ew", padx=(0, 10))
            form.grid_columnconfigure(column, weight=1)

        table_frame = tk.Frame(window, bg=self.WHITE, highlightbackground=self.LINE, highlightthickness=1)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        columns = ("product", "price", "stock")
        products_table = ttk.Treeview(table_frame, columns=columns, show="headings", style="Receipt.Treeview")
        for column, title in (("product", "PRODUCT"), ("price", "UNIT PRICE"), ("stock", "IN STOCK")):
            products_table.heading(column, text=title, anchor="w")
        products_table.column("product", width=300, anchor="w")
        products_table.column("price", width=140, anchor="e")
        products_table.column("stock", width=110, anchor="center")
        products_table.pack(fill="both", expand=True, padx=14, pady=14)

        def refresh_products():
            self._refresh_products()
            products_table.delete(*products_table.get_children())
            for product in self.database.list_products():
                products_table.insert(
                    "", "end",
                    values=(product["name"], self._money(product["unit_price_cents"] / 100), product["stock_quantity"]),
                )

        def add_stock():
            try:
                self.database.add_stock(
                    self.current_user["user_id"],
                    fields["name"].get(),
                    fields["price"].get(),
                    fields["quantity"].get(),
                )
            except (sqlite3.Error, ValueError) as error:
                messagebox.showerror("Could not add stock", str(error), parent=window)
                return
            fields["name"].set("")
            fields["price"].set("")
            fields["quantity"].set("")
            refresh_products()
            self.status.set("Inventory updated")

        tk.Button(form_panel, text="Add stock", command=add_stock, bg=self.GREEN, fg=self.WHITE, activebackground=self.GREEN_DARK, activeforeground=self.WHITE, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 9), padx=14, pady=8).pack(anchor="e", padx=16, pady=(0, 14))
        refresh_products()

    def _logout(self):
        if self.items and self.sale_id is None and not messagebox.askyesno(
            "Discard this draft?",
            "Logging out will discard the current unsaved sale.",
            parent=self.root,
        ):
            return
        _show_login(self.root, self.database)

    def _open_user_manager(self):
        window = tk.Toplevel(self.root)
        window.title("Superuser · Users")
        window.geometry("780x560")
        window.minsize(680, 480)
        window.configure(bg=self.BG)

        heading = tk.Frame(window, bg=self.BG)
        heading.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(heading, text="SUPERUSER", bg=self.BG, fg=self.GREEN, font=("Segoe UI Semibold", 9)).pack(anchor="w")
        tk.Label(heading, text="User access", bg=self.BG, fg=self.INK, font=("Segoe UI Semibold", 19)).pack(anchor="w")

        content = tk.Frame(window, bg=self.BG)
        content.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        form_panel = tk.Frame(content, bg=self.WHITE, highlightbackground=self.LINE, highlightthickness=1)
        form_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(form_panel, text="ADD CASHIER", bg=self.WHITE, fg=self.INK, font=("Segoe UI Semibold", 11)).pack(anchor="w", padx=16, pady=(16, 8))
        form = tk.Frame(form_panel, bg=self.WHITE)
        form.pack(fill="x", padx=16)
        fields = {}
        for label, key, secret in (
            ("FULL NAME", "full_name", False),
            ("USERNAME", "username", False),
            ("PHONE (OPTIONAL)", "phone", False),
            ("PIN", "pin", True),
        ):
            tk.Label(form, text=label, bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(9, 4))
            fields[key] = tk.StringVar(window)
            entry = self._entry(form, fields[key])
            if secret:
                entry.configure(show="*")
            entry.pack(fill="x")

        users_panel = tk.Frame(content, bg=self.WHITE, highlightbackground=self.LINE, highlightthickness=1)
        users_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        tk.Label(users_panel, text="ACTIVE USERS", bg=self.WHITE, fg=self.INK, font=("Segoe UI Semibold", 11)).pack(anchor="w", padx=16, pady=(16, 8))
        table_frame = tk.Frame(users_panel, bg=self.WHITE)
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        columns = ("name", "username", "role", "phone")
        users_table = ttk.Treeview(table_frame, columns=columns, show="headings", style="Receipt.Treeview")
        for column, title in (("name", "NAME"), ("username", "USERNAME"), ("role", "ROLE"), ("phone", "PHONE")):
            users_table.heading(column, text=title, anchor="w")
        users_table.column("name", width=150, anchor="w")
        users_table.column("username", width=120, anchor="w")
        users_table.column("role", width=90, anchor="w")
        users_table.column("phone", width=110, anchor="w")
        users_table.pack(fill="both", expand=True)

        def refresh_users():
            users_table.delete(*users_table.get_children())
            for user in self.database.list_users():
                users_table.insert("", "end", values=(user["full_name"], user["username"], user["role"], user["phone"]))

        def add_cashier():
            try:
                self.database.add_user(fields["full_name"].get(), fields["username"].get(), fields["phone"].get(), fields["pin"].get())
            except (ValueError, sqlite3.IntegrityError) as error:
                messagebox.showerror("Could not add cashier", str(error), parent=window)
                return
            for value in fields.values():
                value.set("")
            refresh_users()
            self._refresh_cashiers()
            self.status.set("Cashier added")

        tk.Button(form_panel, text="Add cashier", command=add_cashier, bg=self.GREEN, fg=self.WHITE, activebackground=self.GREEN_DARK, activeforeground=self.WHITE, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 9), padx=14, pady=9).pack(anchor="w", padx=16, pady=16)
        refresh_users()

    def _open_history(self):
        window = tk.Toplevel(self.root)
        window.title("Purchase history")
        window.geometry("980x620")
        window.minsize(800, 500)
        window.configure(bg=self.BG)

        header = tk.Frame(window, bg=self.BG)
        header.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(header, text="PURCHASES", bg=self.BG, fg=self.GREEN, font=("Segoe UI Semibold", 9)).pack(anchor="w")
        tk.Label(header, text="Sales history", bg=self.BG, fg=self.INK, font=("Segoe UI Semibold", 19)).pack(anchor="w")
        tk.Button(header, text="Refresh", command=lambda: refresh_sales(), bg=self.WHITE, fg=self.INK, activebackground="#f3f6f3", relief="flat", cursor="hand2", font=("Segoe UI Semibold", 9), padx=12, pady=7).pack(side="right")

        content = tk.Frame(window, bg=self.BG)
        content.pack(fill="both", expand=True, padx=24, pady=(0, 22))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        sales_panel = tk.Frame(content, bg=self.WHITE, highlightbackground=self.LINE, highlightthickness=1)
        sales_panel.grid(row=0, column=0, sticky="nsew")
        columns = ("date", "receipt", "seller", "items", "total", "status")
        if self.current_user["role"] == "superuser":
            tk.Button(header, text="Reverse selected", command=lambda: reverse_selected(), bg="#f8e9e6", fg="#923f35", activebackground="#f1d8d3", relief="flat", cursor="hand2", font=("Segoe UI Semibold", 9), padx=12, pady=7).pack(side="right", padx=(0, 8))
        sales_table = ttk.Treeview(sales_panel, columns=columns, show="headings", style="Receipt.Treeview", selectmode="browse")
        for column, title in (("date", "DATE"), ("receipt", "RECEIPT"), ("seller", "SOLD BY"), ("items", "ITEMS"), ("total", "TOTAL"), ("status", "STATUS")):
            sales_table.heading(column, text=title, anchor="w" if column != "total" else "e")
        sales_table.column("date", width=130, stretch=False)
        sales_table.column("receipt", width=150, stretch=False)
        sales_table.column("seller", width=120, stretch=False)
        sales_table.column("items", width=230, stretch=True)
        sales_table.column("total", width=90, stretch=False, anchor="e")
        sales_table.column("status", width=80, stretch=False)
        sales_table.pack(fill="both", expand=True, padx=16, pady=16)

        detail_window = tk.Toplevel(window)
        detail_window.withdraw()

        def show_details(_event=None):
            selected = sales_table.selection()
            if not selected:
                return
            sale = self.database.get_sale(int(selected[0]))
            if sale is None:
                return
            if not detail_window.winfo_exists():
                return
            detail_window.deiconify()
            detail_window.title(f"Receipt {sale['receipt_number']}")
            detail_window.geometry("460x560")
            for child in detail_window.winfo_children():
                child.destroy()
            detail = tk.Text(detail_window, bg=self.WHITE, fg=self.INK, relief="flat", padx=24, pady=24, font=("Consolas", 10), state="normal")
            detail.pack(fill="both", expand=True)
            lines = [
                sale["store_name"].upper().center(38),
                "RECEIPT".center(38),
                "-" * 38,
                f"No. {sale['receipt_number']}",
                f"Sold: {sale['sold_at']}",
                f"Seller: {sale['seller_name']}",
                "-" * 38,
                f"{'ITEM':<20}{'QTY':>4}{'AMOUNT':>14}",
                "-" * 38,
            ]
            if sale["reversed_at"]:
                lines.insert(2, "REVERSED".center(38))
            for item in sale["items"]:
                amount = item["unit_price_cents"] * item["quantity"] / 100
                lines.append(f"{item['item_name'][:19]:<20}{item['quantity']:>4}{self._money(amount):>14}")
            lines.extend([
                "-" * 38,
                f"{'Subtotal':<24}{self._money(sale['subtotal_cents'] / 100):>14}",
                f"{'Tax (7%)':<24}{self._money(sale['tax_cents'] / 100):>14}",
                "=" * 38,
                f"{'TOTAL':<24}{self._money(sale['total_cents'] / 100):>14}",
                "=" * 38,
            ])
            detail.insert("1.0", "\n".join(lines))
            detail.configure(state="disabled")

        sales_table.bind("<<TreeviewSelect>>", show_details)

        def refresh_sales():
            sales_table.delete(*sales_table.get_children())
            for sale in self.database.list_sales():
                sold_at = sale["sold_at"].replace("T", " ")[:19]
                sales_table.insert(
                    "",
                    "end",
                    iid=str(sale["sale_id"]),
                    values=(sold_at, sale["receipt_number"], sale["seller_name"], sale["item_summary"], self._money(sale["total_cents"] / 100), "REVERSED" if sale["reversed_at"] else "COMPLETED"),
                )

        def reverse_selected():
            if self.current_user["role"] != "superuser":
                messagebox.showerror("Access denied", "Only a signed-in superuser can reverse a sale.", parent=window)
                return
            selected = sales_table.selection()
            if not selected:
                messagebox.showinfo("Select a sale", "Choose a sale from the history first.", parent=window)
                return
            sale_id = int(selected[0])
            sale = self.database.get_sale(sale_id)
            if sale is None:
                messagebox.showerror("Sale unavailable", "The selected sale could not be found.", parent=window)
                return
            if sale["reversed_at"]:
                messagebox.showinfo("Already reversed", "This sale has already been reversed.", parent=window)
                return
            if not messagebox.askyesno(
                "Reverse sale",
                f"Reverse receipt {sale['receipt_number']} and return its items to stock?",
                parent=window,
            ):
                return
            pin = simpledialog.askstring(
                "Superuser authorization",
                "Enter your superuser PIN to reverse this sale:",
                show="*",
                parent=window,
            )
            if pin is None:
                return
            try:
                self.database.reverse_sale(sale_id, self.current_user["user_id"], pin)
            except (sqlite3.Error, ValueError) as error:
                messagebox.showerror("Could not reverse sale", str(error), parent=window)
                return
            refresh_sales()
            self._refresh_products()
            self.status.set(f"Receipt {sale['receipt_number']} reversed and stock restored")

        refresh_sales()

    def _totals(self):
        subtotal = sum(
            (Decimal(str(item["price"])) * item["quantity"] for item in self.items),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax = (subtotal * Decimal(str(self.TAX_RATE))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return subtotal, tax, subtotal + tax

    @staticmethod
    def _money(amount):
        return f"K{amount:,.2f}"

    def _refresh_receipt(self):
        if not hasattr(self, "table"):
            return
        for item_id in self.table.get_children():
            self.table.delete(item_id)
        for index, item in enumerate(self.items):
            amount = item["price"] * item["quantity"]
            self.table.insert("", "end", iid=str(index), values=(item["name"], self._money(item["price"]), item["quantity"], self._money(amount)))

        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", self._receipt_text())
        self.preview.configure(state="disabled")

    def _receipt_text(self):
        store = self.store_name.get().strip() or "Your Store"
        timestamp = self.saved_sale["sold_at"] if self.saved_sale else datetime.now().strftime("%Y-%m-%d  %H:%M")
        subtotal, tax, total = self._totals()
        width = 38
        seller = self.saved_sale["seller_name"] if self.saved_sale else None
        if seller is None:
            selected_seller = self.cashiers_by_label.get(self.seller_selection.get())
            seller = selected_seller["full_name"] if selected_seller else None
        lines = [
            store.upper().center(width),
            "RECEIPT".center(width),
            "-" * width,
            f"No. {self.receipt_number}",
            timestamp,
            "-" * width,
            f"{'ITEM':<19}{'QTY':>4}{'AMOUNT':>15}",
            "-" * width,
        ]
        if seller:
            lines.insert(5, f"Seller: {seller}")
        if not self.items:
            lines.extend(["", "   Your receipt will appear here.", "   Add an item to get started.", ""])
        else:
            for item in self.items:
                name = item["name"]
                amount = item["price"] * item["quantity"]
                lines.append(f"{name[:18]:<19}{item['quantity']:>4}{self._money(amount):>15}")
        lines.extend([
            "-" * width,
            f"{'Subtotal':<23}{self._money(subtotal):>15}",
            f"{'Tax (7%)':<23}{self._money(tax):>15}",
            "=" * width,
            f"{'TOTAL':<23}{self._money(total):>15}",
            "=" * width,
            "",
            "       Thank you for shopping with us!",
        ])
        return "\n".join(lines)

    def _receipt_html(self):
        store = html.escape(self.store_name.get().strip() or "Your Store")
        seller = self.saved_sale["seller_name"] if self.saved_sale else None
        if seller is None:
            selected_seller = self.cashiers_by_label.get(self.seller_selection.get())
            seller = selected_seller["full_name"] if selected_seller else None
        seller_line = f"<br>Sold by: {html.escape(seller)}" if seller else ""
        timestamp = self.saved_sale["sold_at"] if self.saved_sale else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subtotal, tax, total = self._totals()
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(item['name'])}<small>{self._money(item['price'])} each</small></td>"
            f"<td class='qty'>{item['quantity']}</td>"
            f"<td class='amount'>{self._money(item['price'] * item['quantity'])}</td>"
            "</tr>"
            for item in self.items
        )
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Receipt {html.escape(self.receipt_number)}</title>
<style>
  @page {{ size: 80mm auto; margin: 4mm; }}
  * {{ box-sizing: border-box; }}
  body {{ width: 72mm; margin: 0 auto; color: #172b24; font: 12px/1.45 'Courier New', monospace; }}
  header {{ text-align: center; padding: 5mm 0 3mm; }}
  h1 {{ margin: 0 0 2mm; font: bold 17px/1.2 Arial, sans-serif; text-transform: uppercase; overflow-wrap: anywhere; }}
  .receipt-title {{ font-weight: bold; letter-spacing: 2px; }}
  .meta {{ border-top: 1px dashed #68776f; border-bottom: 1px dashed #68776f; padding: 3mm 0; margin: 2mm 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 2mm 0; border-bottom: 1px dashed #68776f; }}
  td {{ padding: 2mm 0; vertical-align: top; }}
  td small {{ display: block; color: #68776f; font-size: 10px; }}
  .qty {{ text-align: center; width: 10mm; }}
  .amount {{ text-align: right; white-space: nowrap; }}
  .totals {{ border-top: 1px dashed #68776f; margin-top: 2mm; padding-top: 2mm; }}
  .total {{ font-weight: bold; font-size: 15px; border-top: 1px dashed #68776f; margin-top: 2mm; padding-top: 2mm; }}
  .row {{ display: flex; justify-content: space-between; gap: 4mm; padding: 1mm 0; }}
  footer {{ text-align: center; padding: 5mm 0 2mm; }}
  @media screen {{ body {{ margin: 12mm auto; padding: 5mm; box-shadow: 0 1mm 5mm #0002; }} }}
</style>
</head>
<body>
  <header><h1>{store}</h1><div class="receipt-title">RECEIPT</div></header>
    <div class="meta">No. {html.escape(self.receipt_number)}<br>{timestamp}{seller_line}</div>
  <table><thead><tr><th>ITEM</th><th class="qty">QTY</th><th class="amount">AMOUNT</th></tr></thead><tbody>{rows}</tbody></table>
  <section class="totals">
    <div class="row"><span>Subtotal</span><span>{self._money(subtotal)}</span></div>
    <div class="row"><span>Tax (7%)</span><span>{self._money(tax)}</span></div>
    <div class="row total"><span>TOTAL</span><span>{self._money(total)}</span></div>
  </section>
  <footer>Thank you for shopping with us!</footer>
</body>
</html>"""

    def _refresh_printers(self):
        try:
            import win32print

            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            printers = sorted({printer["pPrinterName"] for printer in win32print.EnumPrinters(flags, None, 2)})
            try:
                default_printer = win32print.GetDefaultPrinter()
            except Exception:
                default_printer = ""
        except ImportError:
            self.printer_selector.configure(values=())
            self.printer_status.set("Install dependencies from requirements.txt to use printers")
            return
        except Exception as error:
            self.printer_selector.configure(values=())
            self.printer_status.set(f"Could not load printers: {error}")
            return

        self.printer_selector.configure(values=printers)
        self.default_printer_name = default_printer
        current = self.selected_printer.get()
        if current not in printers:
            self.selected_printer.set(default_printer if default_printer in printers else (printers[0] if printers else ""))
        self.printer_status.set(f"Windows default: {default_printer}" if default_printer else "No Windows default printer is set")

    def _set_default_printer(self):
        printer_name = self.selected_printer.get()
        if not printer_name:
            messagebox.showinfo("Select a printer", "Choose an installed printer first.", parent=self.root)
            return
        try:
            import win32print

            win32print.SetDefaultPrinter(printer_name)
            self.default_printer_name = printer_name
            self.printer_status.set(f"Windows default: {printer_name}")
            self.status.set(f"{printer_name} set as the default printer")
        except ImportError:
            messagebox.showerror("Printing support unavailable", "Install the packages listed in requirements.txt.", parent=self.root)
        except Exception as error:
            messagebox.showerror("Could not set default printer", str(error), parent=self.root)

    def _print_receipt(self):
        if not self.items:
            messagebox.showinfo("No items yet", "Add at least one item before printing a receipt.", parent=self.root)
            return
        if self.sale_id is None:
            messagebox.showinfo("Complete sale first", "Record the sale with a cashier PIN before printing its receipt.", parent=self.root)
            return
        printer_name = self.selected_printer.get()
        if not printer_name:
            messagebox.showinfo("Select a printer", "Choose an installed printer before printing.", parent=self.root)
            return

        printer_dc = None
        document_started = False
        try:
            import win32con
            import win32ui

            printer_dc = win32ui.CreateDC()
            printer_dc.CreatePrinterDC(printer_name)
            printer_dc.StartDoc(f"Receipt {self.receipt_number}")
            document_started = True

            dpi_x = printer_dc.GetDeviceCaps(win32con.LOGPIXELSX)
            dpi_y = printer_dc.GetDeviceCaps(win32con.LOGPIXELSY)
            page_width = printer_dc.GetDeviceCaps(win32con.HORZRES)
            page_height = printer_dc.GetDeviceCaps(win32con.VERTRES)
            margin_x = max(1, round(dpi_x * 0.08))
            margin_y = max(1, round(dpi_y * 0.06))
            font_height = max(1, round(dpi_y * 9 / 72))
            font = win32ui.CreateFont({"name": "Courier New", "height": -font_height, "weight": 400})
            printer_dc.SelectObject(font)
            text_width = printer_dc.GetTextExtent("0" * 38)[0]
            available_width = page_width - 2 * margin_x
            if text_width > available_width:
                font_height = max(1, int(font_height * available_width / text_width))
                font = win32ui.CreateFont({"name": "Courier New", "height": -font_height, "weight": 400})
                printer_dc.SelectObject(font)

            line_height = max(font_height + 2, round(dpi_y * 0.18))
            lines_per_page = max(1, (page_height - 2 * margin_y) // line_height)
            lines = self._receipt_text().splitlines()
            self.status.set(f"Sending receipt to {printer_name}...")
            self.root.update_idletasks()

            for page_start in range(0, len(lines), lines_per_page):
                printer_dc.StartPage()
                for line_number, line in enumerate(lines[page_start:page_start + lines_per_page]):
                    printer_dc.TextOut(margin_x, margin_y + line_number * line_height, line)
                printer_dc.EndPage()
            printer_dc.EndDoc()
            document_started = False
            self.status.set(f"Receipt sent to {printer_name}")
        except Exception as error:
            if document_started and printer_dc:
                try:
                    printer_dc.AbortDoc()
                except Exception:
                    pass
            self.status.set("Printing failed")
            messagebox.showerror("Could not print receipt", str(error), parent=self.root)
        finally:
            if printer_dc:
                printer_dc.DeleteDC()

    def _save_receipt(self):
        if not self.items:
            messagebox.showinfo("No items yet", "Add at least one item before saving a receipt.", parent=self.root)
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save receipt",
            defaultextension=".html",
            initialfile=f"receipt-{self.receipt_number}.html",
            filetypes=[("HTML receipt", "*.html")],
        )
        if not path:
            return
        try:
            Path(path).write_text(self._receipt_html(), encoding="utf-8")
            self.status.set(f"Receipt saved to {Path(path).name}")
        except OSError as error:
            messagebox.showerror("Could not save receipt", str(error), parent=self.root)


def _show_authenticated_app(root, database, user):
    for child in root.winfo_children():
        child.destroy()
    ReceiptApp(root, database, user)


def _show_login(root, database):
    for child in root.winfo_children():
        child.destroy()
    LoginWindow(root, database, lambda user: _show_authenticated_app(root, database, user))


def main():
    root = tk.Tk()
    database = ReceiptDatabase()
    _show_login(root, database)
    root.mainloop()


if __name__ == "__main__":
    main()