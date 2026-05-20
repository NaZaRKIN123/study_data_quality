from validators import assert_no_nulls, assert_unique, assert_in_set, assert_row_count, assert_in_range, assert_email_format
import pytest
from pandas import testing as tm
import pandas as pd

def test_customers_have_rows(customers_df):
    assert len(customers_df) > 0

def test_customer_id_is_never_null(customers_df):
    assert_no_nulls(customers_df, ["customer_id"])

@pytest.mark.skip(reason="Failing for purposes of the exercise")
def test_status_is_in_set(customers_df):
    assert_in_set(customers_df, "status", {"active", "churned"})

@pytest.mark.skip(reason="Failing for purposes of the exercise")
def test_email_is_valid(customers_df):
    assert_email_format(customers_df, "email")

@pytest.mark.skip(reason="Failing for purposes of the exercise")
def test_upper_case_transformation(customers_df):
    transformed_df = customers_df.copy()
    transformed_df["email"] = transformed_df["email"].str.upper()
    tm.assert_frame_equal(customers_df, transformed_df)

def test_total_amount_is_in_range(orders_df):
    assert_in_range(orders_df, "total_amount", 0, 10_000)

@pytest.mark.parametrize("table_name, csv_path, pk_col", [
    ("customers", "customers.csv", "customer_id"),
    ("orders", "orders.csv", "order_id"),
    ("order_items", "order_items.csv", "order_item_id"),
    ("products", "products.csv", "product_id"),
])
def test_no_nulls_on_primary_key(table_name, csv_path, pk_col):
    df = pd.read_csv(csv_path)
    print(f"Testing {table_name} with primary key {pk_col}")
    assert_no_nulls(df, [pk_col])  