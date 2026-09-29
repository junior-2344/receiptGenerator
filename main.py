from datetime import datetime
import html
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path


class ReceiptApp:
    BG = "#eef2ee"
    INK = "#172b24"
    MUTED = "#68776f"
    GREEN = "#176b50"
    GREEN_DARK = "#10513d"
    LINE = "#dce4dd"
    WHITE = "#ffffff"
    TAX_RATE = 0.07

    def __init__(self, root):
        self.root = root
        self.root.title("Receipt Studio")
        self.root.geometry("1120x790")
        self.root.minsize(940, 680)
        self.root.configure(bg=self.BG)

        self.items = []
        self.receipt_number = datetime.now().strftime("%y%m%d-%H%M%S")
        self.store_name = tk.StringVar(value="Corner Market")
        self.item_name = tk.StringVar()
        self.item_price = tk.StringVar()
        self.item_quantity = tk.StringVar(value="1")
        self.status = tk.StringVar(value="Ready for your first item")
        self.selected_printer = tk.StringVar()
        self.printer_status = tk.StringVar(value="Loading printers...")
        self.default_printer_name = ""

        self._configure_styles()
        self._build_layout()
        self._refresh_printers()
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
        self._entry(fields, self.store_name).pack(fill="x")
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
        panel = self._panel(parent, "Line items", "Enter a product, price and quantity to build the sale.")
        panel.pack(fill="both", expand=True)

        form = tk.Frame(panel, bg=self.WHITE)
        form.pack(fill="x", padx=18, pady=(0, 15))
        tk.Label(form, text="ITEM", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).grid(row=0, column=0, sticky="w", pady=(0, 5))
        tk.Label(form, text="PRICE (K)", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 5))
        tk.Label(form, text="QTY", bg=self.WHITE, fg=self.MUTED, font=("Segoe UI Semibold", 8)).grid(row=0, column=2, sticky="w", padx=(8, 0), pady=(0, 5))
        form.grid_columnconfigure(0, weight=1)
        self.name_entry = self._entry(form, self.item_name)
        self.name_entry.grid(row=1, column=0, sticky="ew")
        self._entry(form, self.item_price, 10).grid(row=1, column=1, padx=(8, 0), sticky="ew")
        self._entry(form, self.item_quantity, 5).grid(row=1, column=2, padx=(8, 0), sticky="ew")
        add_button = tk.Button(
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
        add_button.grid(row=1, column=3, padx=(8, 0))
        self.name_entry.bind("<Return>", lambda _: self._add_item())
        self.item_price_entry = form.grid_slaves(row=1, column=1)[0]
        self.item_price_entry.bind("<Return>", lambda _: self._add_item())

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
        tk.Button(actions, text="Remove selected", command=self._remove_selected, bg=self.WHITE, fg=self.MUTED, activebackground="#f3f6f3", relief="flat", cursor="hand2", font=("Segoe UI", 9)).pack(side="left")
        tk.Button(actions, text="Clear sale", command=self._clear_sale, bg=self.WHITE, fg="#a14e42", activebackground="#fbf2f0", relief="flat", cursor="hand2", font=("Segoe UI", 9)).pack(side="right")

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
        tk.Button(buttons, text="Print receipt  →", command=self._print_receipt, bg=self.GREEN, fg=self.WHITE, activebackground=self.GREEN_DARK, activeforeground=self.WHITE, relief="flat", cursor="hand2", font=("Segoe UI Semibold", 10), padx=18, pady=10).pack(side="right")

    def _add_item(self):
        name = self.item_name.get().strip()
        try:
            price = float(self.item_price.get())
            quantity = int(self.item_quantity.get())
        except ValueError:
            messagebox.showerror("Check the item details", "Enter a valid price and a whole-number quantity.", parent=self.root)
            return
        if not name or price < 0 or quantity < 1:
            messagebox.showerror("Check the item details", "Enter an item name, a price of 0 or more, and a quantity of at least 1.", parent=self.root)
            return

        self.items.append({"name": name, "price": price, "quantity": quantity})
        self.item_name.set("")
        self.item_price.set("")
        self.item_quantity.set("1")
        self.name_entry.focus_set()
        self.status.set(f"Added {name}")
        self._refresh_receipt()

    def _remove_selected(self):
        selected = self.table.selection()
        if not selected:
            return
        indexes = sorted((int(item_id) for item_id in selected), reverse=True)
        for index in indexes:
            del self.items[index]
        self.status.set("Selected item removed")
        self._refresh_receipt()

    def _clear_sale(self):
        if not self.items:
            return
        if messagebox.askyesno("Clear this sale?", "All line items will be removed.", parent=self.root):
            self.items.clear()
            self.status.set("Sale cleared")
            self._refresh_receipt()

    def _totals(self):
        subtotal = sum(item["price"] * item["quantity"] for item in self.items)
        tax = subtotal * self.TAX_RATE
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
        timestamp = datetime.now().strftime("%Y-%m-%d  %H:%M")
        subtotal, tax, total = self._totals()
        width = 38
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
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
  <div class="meta">No. {html.escape(self.receipt_number)}<br>{timestamp}</div>
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


def main():
    root = tk.Tk()
    ReceiptApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()