import pytest
import pandas as pd

@pytest.fixture
def sample_users():
    return [
        {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "age": 30,
        },
        {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "age": 25,
        },
    ]

@pytest.fixture
def customers_df():
    return pd.read_csv("customers.csv")

@pytest.fixture
def orders_df():
    return pd.read_csv("orders.csv")

@pytest.fixture
def order_items_df():
    return pd.read_csv("order_items.csv")

@pytest.fixture
def products_df():
    return pd.read_csv("products.csv")