from datetime import datetime

items = []

print("\v" + "=" * 55)
print("             DIGITAL RECEIPT")
print("=" * 55 + "\v")

count = int(input("\nNumber of items: "))

for i in range(count):
    name = input(f"item{i + 1}: ").strip()
    price = float(input("Price: "))
    quantity = int(input("Quantity: "))

    if name and price >= 0 and quantity > 0:
        items.append(
            (name, price, quantity)
        )

subtotal = sum(price * quantity for _, price, quantity in items)

tax = subtotal * 0.07
total = subtotal + tax

print("\n" + "=" * 55)
print("Item               Quantity     Amount")
print("=" * 55)

for name, price, quantity in items:
    amount = price * quantity
    print(
        f"{name[:18]:<20}"
        f"{quantity:>3}     "
        f"K{amount:>15.2f}"
          )

print("=" * 55)
print(f"{'Subtotal':<35}{subtotal:>10.2f}")
print(f"{'Tax (7%)':<35}{tax:>10.2f}")
print(f"{'Total':<35}{total:>10.2f}")
print(f"{'Date':<35}{datetime.now().strftime('%Y-%m-%d %H:%M:%S'):>10}")
print("=" * 55)
