# seed_data.py
import sqlite3
import pandas as pd

customers = pd.DataFrame(
    [
        (1, "anna@example.com",  "2024-01-15", "PL", "active"),
        (2, "ben@example.com",   "2024-02-03", "US", "active"),
        (3, "carla@example.com", "2024-02-20", None, "active"),
        (4, "dan@example.com",   "2024-03-01", "DE", "churned"),
        (5, None,                "2024-03-12", "PL", "active"),
        (6, "eve@example.com",   "2024-04-04", "UA", None),
        (7, "frank@example.com", "2024-04-04", "UA", "active"),
    ],
    columns=["customer_id", "email", "signup_date", "country", "status"],
)

products = pd.DataFrame(
    [
        (101, "Wireless Mouse",      "electronics", 25.00, True),
        (102, "Mechanical Keyboard", "electronics", 90.00, True),
        (103, "Coffee Mug",          "home",         8.50, True),
        (104, "Old Headphones",      "electronics", 40.00, False),
        (105, "Notebook",            "office",       3.00, True),
    ],
    columns=["product_id", "name", "category", "price", "active"],
)

orders = pd.DataFrame(
    [
        (1001, 1,    "2024-05-01", 115.00, "completed"),
        (1002, 2,    "2024-05-02",  17.00, "completed"),
        (1003, 3,    "2024-05-02",  90.00, "completed"),
        (1004, 4,    "2024-05-03", None,   "completed"),
        (1005, 7,    "2024-05-04",  25.00, "cancelled"),
        (1006, 999,  "2024-05-05",  50.00, "completed"),
        (1007, 1,    "2024-05-06",  25.00, "completed"),
    ],
    columns=["order_id", "customer_id", "order_date", "total_amount", "status"],
)

order_items = pd.DataFrame(
    [
        (1, 1001, 101, 1, 25.00),
        (2, 1001, 102, 1, 90.00),
        (3, 1002, 103, 2,  8.50),
        (4, 1003, 102, 1, 90.00),
        (5, 1004, 105, 3,  3.00),
        (6, 1005, 101, 1, 25.00),
        (7, 1006, 101, 2, 30.00),
        (8, 1007, 101, 1, 25.00),
    ],
    columns=["order_item_id", "order_id", "product_id", "quantity", "unit_price"],
)

# CSVs
customers.to_csv("customers.csv", index=False)
products.to_csv("products.csv", index=False)
orders.to_csv("orders.csv", index=False)
order_items.to_csv("order_items.csv", index=False)

# SQLite (used Day 4)
with sqlite3.connect("ecommerce.db") as conn:
    customers.to_sql("customers", conn, if_exists="replace", index=False)
    products.to_sql("products", conn, if_exists="replace", index=False)
    orders.to_sql("orders", conn, if_exists="replace", index=False)
    order_items.to_sql("order_items", conn, if_exists="replace", index=False)

print("Seeded 4 CSVs + ecommerce.db")