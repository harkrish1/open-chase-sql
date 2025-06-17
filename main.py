from setup_qdrant import QdrantClientWrapper
from setup_llm import LLM
import constants
from setup_chinook_db import ChinookDBWrapper
import pandas as pd
import spacy

nlp = spacy.load("en_core_web_sm")

def main(question: str):
    llm = LLM()
    qdrant_client = QdrantClientWrapper()

    nouns = [token.text for token in nlp(question) if token.pos_ in ['NOUN', 'PROPN']]
    list_of_dims = []
    list_of_kpis = []
    if len(nouns) > 0:
        for noun in nouns:
            _dims = qdrant_client.search_data(query=noun, collection_name=constants.DIM_COLLECTION_NAME)
            list_of_dims.extend([point.payload['text'] for point in _dims.points if point.score>=0.5])
            _kpis = qdrant_client.search_data(query=noun, collection_name=constants.KPI_COLLECTION_NAME)
            list_of_kpis.extend([point.payload['text'] for point in _kpis.points if point.score>=0.5])

    _dims = qdrant_client.search_data(query=question, collection_name=constants.DIM_COLLECTION_NAME)
    _kpis = qdrant_client.search_data(query=question, collection_name=constants.KPI_COLLECTION_NAME)
    list_of_dims.extend([point.payload['text'] for point in _dims.points if point.score>=0.5])
    list_of_kpis.extend([point.payload['text'] for point in _kpis.points if point.score>=0.5])

    list_of_dims = list(set(list_of_dims))  # Remove duplicates
    list_of_kpis = list(set(list_of_kpis))  # Remove duplicates
    print(list_of_dims)
    print(list_of_kpis)

    dims, kpis = llm.extract_dimensions_and_kpis(question, list_of_dims, list_of_kpis)
    print("selected dimensions:", dims)
    print("selected kpis:", kpis)

    db = ChinookDBWrapper()
    validated_dims = []
    validated_kpis = []
    table_metadata = {}
    if dims:
        for dim in dims:
            table_name = dim.split('|')[0].strip()
            column_name = dim.split('|')[1].strip()
            metadata = db.get_table_metadata(table_name)
            if not len(metadata) == 0:
                # checking if the column exists in the table
                if any(column_name == col[1] for col in metadata):
                    validated_dims.append(dim.strip())
                    table_metadata[table_name] = metadata
    if kpis:
        for kpi in kpis:
            table_name = kpi.split('|')[0].strip()
            column_name = kpi.split('|')[1].strip()
            metadata = db.get_table_metadata(table_name)
            if not len(metadata) == 0:
                # checking if the column exists in the table
                if any(column_name == col[1] for col in metadata):
                    validated_kpis.append(kpi.strip())
                    table_metadata[table_name] = metadata

    if len(validated_dims) > 0 or len(validated_kpis) > 0:
        sql_query = llm.write_sql_query(question, validated_dims, validated_kpis, table_metadata)
        return db.execute_query_returning_df(sql_query), sql_query
    else:
        return pd.DataFrame(columns=['Error'], data=[['No valid dimensions or KPIs found.']]), None

if __name__ == "__main__":
    print(main("which cities have most invoice total"))

