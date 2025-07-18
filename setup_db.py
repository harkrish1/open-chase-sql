import sqlite3
import pandas as pd
import os


class DBWrapper:
    def __init__(self, super_folder_path):
        self.super_folder_path = super_folder_path
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()

    def detach_old_databases(self):
        self.cursor.execute("PRAGMA database_list")
        databases = self.cursor.fetchall()
        for db in databases:
            if db[1] not in ["main"]:
                print("Detaching old databases...")
                self.cursor.execute(f"DETACH DATABASE {db[1]}")

    def attach_new_database(self, db_name):
        # only if it is a new database that is not already attached, we detach old ones and attach new one
        self.cursor.execute("PRAGMA database_list")
        dbs = self.cursor.fetchall()
        dbs = [db[1] for db in dbs]
        if db_name not in dbs:
            self.detach_old_databases()
            db_path = os.path.join(self.super_folder_path, db_name, db_name + ".sqlite")
            self.cursor.execute(f"ATTACH DATABASE '{db_path}' AS {db_name}")

    def test_connection(self, db_name):
        self.attach_new_database(db_name)
        cur = self.cursor.execute(
            f"SELECT name FROM {db_name}.sqlite_master WHERE type='table'"
        )
        return cur.fetchall()

    def get_dimension_columns(self, db_name):
        self.attach_new_database(db_name)
        self.cursor.execute(
            f"SELECT name FROM {db_name}.sqlite_master WHERE type='table'"
        )
        tables = self.cursor.fetchall()
        dimensions = {}
        for table in tables:
            dim_columns = []
            # Find Primary Key columns
            self.cursor.execute(
                f"SELECT name FROM {db_name}.pragma_table_info('{table[0]}') WHERE pk > 0"
            )

            primary_keys = self.cursor.fetchall()
            if len(primary_keys) > 0:
                dim_columns.extend([pk for tup in primary_keys for pk in tup])
            self.cursor.execute(
                f"SELECT * FROM {db_name}.pragma_foreign_key_list('{table[0]}')"
            )
            fk_relationships = self.cursor.fetchall()
            for fk in fk_relationships:
                # fk[3] is the foreign key column name
                dim_columns.append(fk[3])
            self.cursor.execute(
                f"SELECT * FROM {db_name}.pragma_table_info('{table[0]}') WHERE pk = 0"
            )
            columns = self.cursor.fetchall()
            for col in columns:
                # col[1] is column name, col[2] is data type
                if not col[2] in ["INTEGER", "REAL", "NUMERIC(10,2)", "DATETIME"]:
                    dim_columns.append(col[1])
            dimensions[table[0]] = list(set(dim_columns))
        return dimensions

    def execute_query_returning_df(self, query, db_name):
        if not query:
            raise ValueError("SQL query is empty. Please provide a valid query.")
        self.attach_new_database(db_name)
        self.cursor.execute(query)
        columns = [col[0] for col in self.cursor.description]
        results = self.cursor.fetchall()
        return pd.DataFrame(results, columns=columns)

    def get_table_metadata(self, table_name, db_name):
        self.attach_new_database(db_name)
        self.cursor.execute(
            f"SELECT * FROM {db_name}.pragma_table_info('{table_name}')"
        )
        columns = self.cursor.fetchall()
        return columns

    def get_table_top3_rows(self, table_name, db_name):
        self.attach_new_database(db_name)
        self.cursor.execute(f"SELECT * FROM {db_name}.{table_name} LIMIT 3")
        return self.cursor.fetchall()


# test_db = DBWrapper("/Users/harshitkrishnakumar/Downloads/dev_20240627/dev_databases")
# print(test_db.test_connection("european_football_2"))
# print(test_db.test_connection("financial"))
# print(
#     test_db.execute_query_returning_df(
#         "SELECT `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM frpm WHERE `County Name` = 'Alameda' ORDER BY (CAST(`Free Meal Count (K-12)` AS REAL) / `Enrollment (K-12)`) DESC LIMIT 1",
#         "california_schools",
#     )
# )
# print(test_db.get_dimension_columns("california_schools"))
# print(
#     test_db.execute_query_returning_df(
#         "SELECT `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)` FROM frpm WHERE `Educational Option Type` = 'Continuation School' AND `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)` IS NOT NULL ORDER BY `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)` ASC LIMIT 3",
#         "california_schools",
#     )
# )
