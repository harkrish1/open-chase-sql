import requests
import sqlite3
import os
import pandas as pd

class ChinookDBWrapper:
    def __init__(self, db_path='Chinook.db'):
        self.db_path = db_path
        self.conn, self.cursor = self.load_chinook_db()

    def load_chinook_db(self):
        if not os.path.exists(self.db_path):
            # Download the file from the URL
            url = "https://storage.googleapis.com/benchmarks-artifacts/chinook/Chinook.db"
            response = requests.get(url)
            if response.status_code == 200:
                # Open a local file in binary write mode
                with open(self.db_path, "wb") as file:
                    # Write the content of the response (the file) to the local file
                    file.write(response.content)
                print(f"File downloaded and saved at {self.db_path}")
            else:
                raise Exception(f"Failed to download the file. Status code: {response.status_code}")
        conn = sqlite3.connect(self.db_path)
        # Create a cursor object to execute SQL queries
        cursor = conn.cursor()
        return conn, cursor

    def get_dimension_and_non_dimension_columns(self):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = self.cursor.fetchall()
        dimensions = {}
        non_dimensions = {}
        for table in tables:
            dim_columns = []
            non_dim_columns = []
            # Find Primary Key columns
            self.cursor.execute(f"SELECT name FROM pragma_table_info('{table[0]}') WHERE pk > 0")
            primary_keys = self.cursor.fetchall()
            if len(primary_keys) > 0:
                dim_columns.extend([pk for tup in primary_keys for pk in tup])
            self.cursor.execute(f"PRAGMA foreign_key_list({table[0]})")
            fk_relationships = self.cursor.fetchall()
            for fk in fk_relationships:
                # fk[3] is the foreign key column name
                dim_columns.append(fk[3])
            self.cursor.execute(f"SELECT * FROM pragma_table_info('{table[0]}') WHERE pk = 0")
            columns = self.cursor.fetchall()
            for col in columns:
                # col[1] is column name, col[2] is data type
                if not col[2] in ['INTEGER', 'REAL', 'NUMERIC(10,2)', 'DATETIME']:
                    dim_columns.append(col[1])
                elif col[1] not in dim_columns:
                    non_dim_columns.append(col[1])
            dimensions[table[0]] = dim_columns
            non_dimensions[table[0]] = non_dim_columns
        return dimensions, non_dimensions


    def execute_query(self, query):
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def execute_query_returning_df(self, query):
        self.cursor.execute(query)
        columns = [col[0] for col in self.cursor.description]
        results = self.cursor.fetchall()
        return pd.DataFrame(results, columns=columns)

    def get_table_metadata(self, table_name):
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.cursor.fetchall()
        return columns


# test_db = ChinookDBWrapper()
# metadata = test_db.get_table_metadata("Invoice")
# print("Metadata for table:", metadata)