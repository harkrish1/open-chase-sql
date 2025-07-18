from qdrant_client import models, QdrantClient
from openai import OpenAI
import dotenv
import os
import pandas as pd
from setup_db import DBWrapper
import uuid


class QdrantClientWrapper:
    def __init__(self, super_folder_path: str, database_name: str):
        self.qdrant = QdrantClient(url="http://localhost:6333")
        self.openai_client = OpenAI(api_key=dotenv.get_key(".env", "OPENAI_API_KEY"))
        self.super_folder_path = super_folder_path
        self.database_descriptions_collection = database_name + "_db_descriptions"
        self.database_dimensions_collection = database_name + "_db_dimensions"
        self.database_name = database_name
        self.encoding_dimension = 256
        self.initialize_qdrant_client()

    def create_qdrant_collection(self, collection_name):
        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=self.encoding_dimension, distance=models.Distance.COSINE
            ),
        )

    def store_items(self, data: str | list, collection_name: str, payload: str | list):
        if isinstance(data, str):
            data = [data]
        if isinstance(payload, str):
            payload = [payload]

        payload = [{"text": pld} for pld in payload]
        encoded_data = self.openai_client.embeddings.create(
            input=data,
            model="text-embedding-3-small",
            dimensions=self.encoding_dimension,
        ).data
        records = []
        for i in range(len(encoded_data)):
            # use uuid in ID
            records.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=encoded_data[i].embedding,
                    payload=payload[i],
                )
            )
        self.qdrant.upsert(collection_name=collection_name, points=records)

    def search_data(self, query: str, description_or_dimension: str, limit: int = 5):
        if description_or_dimension == "description":
            collection_name = self.database_descriptions_collection
        else:
            collection_name = self.database_dimensions_collection
        query_vector = (
            self.openai_client.embeddings.create(
                input=query,
                model="text-embedding-3-small",
                dimensions=self.encoding_dimension,
            )
            .data[0]
            .embedding
        )
        search_result = self.qdrant.query_points(
            collection_name=collection_name, query=query_vector, limit=limit
        )
        return search_result

    def initialize_qdrant_client(self):

        # setting up descriptions collection
        if self.database_descriptions_collection not in [
            c.name for c in self.qdrant.get_collections().collections
        ]:
            print("creating new collection for database descriptions")
            self.create_qdrant_collection(self.database_descriptions_collection)
            folder_path = os.path.join(
                self.super_folder_path, self.database_name, "database_description"
            )
            for file in os.listdir(folder_path):
                if file.endswith(".csv"):
                    file_path = os.path.join(folder_path, file)
                    data = pd.read_csv(file_path)

                    for row in range(len(data)):
                        column_name_payload = f"{file.removesuffix('.csv')} | {str(data['original_column_name'][row])}"
                        column_name = str(data["original_column_name"][row])
                        self.store_items(
                            column_name,
                            self.database_descriptions_collection,
                            payload=column_name_payload,
                        )

                        column_description = ""
                        for value in [
                            str(data["column_name"][row]),
                            str(data["column_description"][row]),
                            str(data["value_description"][row]),
                        ]:
                            if value and value not in ["nan", "None"]:
                                column_description += value.strip() + ", "
                        if column_description:
                            column_description_payload = (
                                column_name_payload + " | " + column_description.strip()
                            )
                            self.store_items(
                                column_description,
                                self.database_descriptions_collection,
                                payload=column_description_payload,
                            )
        if self.database_dimensions_collection not in [
            c.name for c in self.qdrant.get_collections().collections
        ]:
            print("creating new collection for database dimensions")
            db_client = DBWrapper(self.super_folder_path)
            dimension_columns = db_client.get_dimension_columns(self.database_name)
            self.create_qdrant_collection(self.database_dimensions_collection)
            for table in dimension_columns:
                for column in dimension_columns[table]:
                    print(f"working on {table} table, {column} column")
                    sql_query = f"SELECT distinct `{column}` FROM `{table}` WHERE `{column}` IS NOT NULL"
                    result = db_client.execute_query_returning_df(
                        sql_query, self.database_name
                    )
                    result = [j for i in result.values for j in i]
                    payload = [f"{table} | {column} | {item}" for item in result]
                    if len(result) <= 500:  # arbitrary limit to avoid too many items
                        self.store_items(
                            data=result,
                            collection_name=self.database_dimensions_collection,
                            payload=payload,
                        )
                break


# test_qdrant_client = QdrantClientWrapper(
#     "/Users/harshitkrishnakumar/Downloads/dev_20240627/dev_databases",
#     "california_schools",
# )
# print(test_qdrant_client.search_data("k 12", "dimension"))
