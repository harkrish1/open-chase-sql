from qdrant_client import models, QdrantClient
from openai import OpenAI
from setup_chinook_db import ChinookDBWrapper
import constants
import dotenv

class QdrantClientWrapper:
    def __init__(self):
        self.qdrant = QdrantClient(path = "./qdrant_data")
        self.openai_client = OpenAI(
            api_key= dotenv.get_key('.env', 'OPENAI_API_KEY')
        )
        self.encoding_dimension = 256
        self.dim_collection_name = constants.DIM_COLLECTION_NAME
        self.kpi_collection_name = constants.KPI_COLLECTION_NAME
        self.initialize_qdrant_client()


    def create_qdrant_collection(self, collection_name):
        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=self.encoding_dimension,
                distance=models.Distance.COSINE
            )
        )

    def store_single_string(self, data: str, collection_name: str, current_id: int ,payload:str = None):
        payload = {"text": payload if payload else data}
        encoded_data = self.openai_client.embeddings.create(
            input=data,
            model="text-embedding-3-small",
            dimensions=self.encoding_dimension,
        ).data[0].embedding

        record = models.Record(
            id=current_id,  # Using 0 as default ID, consider implementing ID management
            vector=encoded_data,
            payload=payload
        )

        self.qdrant.upsert(
            collection_name=collection_name,
            points=[record]
        )

    def search_data(self, query: str,collection_name:str ,limit: int = 5 ):
        query_vector = self.openai_client.embeddings.create(
            input=query,
            model="text-embedding-3-small",
            dimensions=self.encoding_dimension,
        ).data[0].embedding
        search_result = self.qdrant.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit
        )
        return search_result

    def initialize_qdrant_client(self):
        chinook_client = ChinookDBWrapper()
        dimension_columns, non_dimension_columns = chinook_client.get_dimension_and_non_dimension_columns()
        # Check if collections exist, if not create them
        if self.dim_collection_name not in [c.name for c in self.qdrant.get_collections().collections]:
            current_id = 0
            self.create_qdrant_collection(self.dim_collection_name)
            for table in dimension_columns:
                for column in dimension_columns[table]:
                    sql_query = f"SELECT distinct {column} FROM {table} WHERE {column} IS NOT NULL"
                    result = chinook_client.execute_query(sql_query)
                    for item in result:
                        self.store_single_string(data=f"{table} | {column} | {item[0]}",
                                                 payload=f"{table} | {column} | {item[0]}",
                                                 collection_name=self.dim_collection_name, current_id=current_id)
                        current_id += 1

        if self.kpi_collection_name not in [c.name for c in self.qdrant.get_collections().collections]:
            current_id = 0
            self.create_qdrant_collection(self.kpi_collection_name)
            for table in non_dimension_columns:
                for column in non_dimension_columns[table]:
                    sql_query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL limit 3"
                    result = chinook_client.execute_query(sql_query)
                    combined_items = ', '.join([str(item[0]) for item in result])
                    self.store_single_string(data = f"{table} | {column}",
                                             payload = f"{table} | {column} | {combined_items}",
                                             collection_name=self.kpi_collection_name, current_id=current_id)
                    current_id += 1


