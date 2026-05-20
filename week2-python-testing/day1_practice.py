import pandas as pd

df = pd.read_csv("customers.csv")

print(df.shape)
print(df.dtypes)
print(df.isna().sum())