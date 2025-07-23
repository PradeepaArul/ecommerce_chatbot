import pandas as pd
import sqlite3

conn = sqlite3.connect("ecommerce.db")

# Load CSVs into tables
pd.read_csv("ad_sales.csv").to_sql("AdSales", conn, if_exists="replace", index=False)
pd.read_csv("total_sales.csv").to_sql("TotalSales", conn, if_exists="replace", index=False)
pd.read_csv("eligibility.csv", encoding='cp1252').to_sql("Eligibility", conn, if_exists="replace", index=False)

conn.close()
print("✅ Database created: ecommerce.db")
