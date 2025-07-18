from setup_qdrant import QdrantClientWrapper
from setup_llm import LLM
from setup_db import DBWrapper
import pandas as pd
import os
import json


def write_and_execute_sql_query(
    llm, db, question, hint, validated_cols, table_metadata, table_top_3_rows, db_name
):
    openai_error = False
    sql_query = llm.write_sql_query(
        question=question,
        hint=hint,
        columns=validated_cols,
        table_metadata=table_metadata,
        table_top_3_rows=table_top_3_rows,
    )
    if sql_query:
        try:
            res = db.execute_query_returning_df(sql_query, db_name), sql_query
        except Exception:
            openai_error = True
            res = (
                pd.DataFrame(
                    columns=["Error"], data=[["Error in executing SQL query."]]
                ),
                None,
            )
    if res[0].empty:
        openai_error = True

    if openai_error:
        sql_query = llm.write_sql_query_claude(
            question=question,
            hint=hint,
            columns=validated_cols,
            table_metadata=table_metadata,
            table_top_3_rows=table_top_3_rows,
        )
    try:
        res = db.execute_query_returning_df(sql_query, db_name), sql_query
    except Exception as e:
        sql_query = llm.write_sql_query_claude(
            question=question,
            hint=hint,
            columns=validated_cols,
            table_metadata=table_metadata,
            table_top_3_rows=table_top_3_rows,
            previous_response=sql_query,
            follow_up_message=f"The SQL Query you wrote resulted in the error: {str(e)}. Please think whether anything can be changed that could fix the error. If you think there is nothing that can be changed, then give me the SQL query again. If it is not correct, then fix it and give me only the SQL query.",
        )
        try:
            res = db.execute_query_returning_df(sql_query, db_name), sql_query
        except Exception:
            res = (
                pd.DataFrame(
                    columns=["Error"], data=[["Error in executing SQL query."]]
                ),
                None,
            )
    if res[0].empty:
        sql_query = llm.write_sql_query_claude(
            question=question,
            hint=hint,
            columns=validated_cols,
            table_metadata=table_metadata,
            table_top_3_rows=table_top_3_rows,
            previous_response=sql_query,
            follow_up_message=f"The SQL Query you wrote resulted in an empty dataframe. Please think whether anything can be changed that could give a non empty result. If you think there is nothing that can be changed, then give me the SQL query again. If it is not correct, then fix it and give me only the SQL query.",
        )
        bkp_res = res
        try:
            res = db.execute_query_returning_df(sql_query, db_name), sql_query
        except:
            res = bkp_res
    return res


def run_single_question(question: str, hint: str, db_name: str):
    llm = LLM()
    qdrant_client = QdrantClientWrapper(
        super_folder_path="/Users/harshitkrishnakumar/Downloads/dev_20240627/dev_databases",
        database_name=db_name,
    )

    key_words = llm.extract_keywords(question, hint)
    if not key_words:
        # print("No keywords extracted, Trying again")
        key_words = llm.extract_keywords(question, hint)
    # print("extracted keywords using LLM:", key_words)

    column_descriptions = []
    column_values = []
    if len(key_words) > 0:
        for noun in key_words:
            _cols = qdrant_client.search_data(
                query=noun, description_or_dimension="description"
            )
            column_descriptions.extend(
                [point.payload["text"] for point in _cols.points if point.score >= 0.5]
            )
            _cols = qdrant_client.search_data(
                query=noun, description_or_dimension="dimension"
            )
            column_values.extend(
                [point.payload["text"] for point in _cols.points if point.score >= 0.5]
            )

    column_descriptions = list(set(column_descriptions))
    column_values = list(set(column_values))
    cols_list = column_descriptions + column_values
    # print("qdrant found cols:", cols_list)
    cols = llm.extract_key_entities(question, hint, cols_list)
    if not cols:
        # print("No columns extracted, trying again")
        cols = llm.extract_key_entities(question, hint, cols_list)
    # print("LLM selected cols:", cols)
    if not cols:
        cols = cols_list

    db = DBWrapper(
        super_folder_path="/Users/harshitkrishnakumar/Downloads/dev_20240627/dev_databases"
    )
    validated_cols = []
    table_metadata = {}
    table_top_3_rows = {}
    if cols:
        for col in cols:
            table_name = col.split("|")[0].strip()
            column_name = col.split("|")[1].strip()

            metadata = db.get_table_metadata(table_name, db_name)
            top3_rows = db.get_table_top3_rows(table_name, db_name)
            if not len(metadata) == 0:
                # checking if the column exists in the table
                if any(column_name == col[1] for col in metadata):
                    validated_cols.append(col.strip())
                    table_metadata[table_name] = metadata
                    table_top_3_rows[table_name] = top3_rows

    if len(validated_cols) > 0:
        return write_and_execute_sql_query(
            llm,
            db,
            question,
            hint,
            validated_cols,
            table_metadata,
            table_top_3_rows,
            db_name,
        )
    else:
        return (
            pd.DataFrame(
                columns=["Error"], data=[["No valid dimensions or KPIs found."]]
            ),
            None,
        )


if __name__ == "__main__":
    # result = run_single_question(
    #     question="What is the telephone number for the school with the lowest average score in reading in Fresno Unified?",
    #     hint="Fresno Unified is a name of district;",
    #     db_name="california_schools",
    # )
    # print(result[0])
    # print(result[1])

    files = os.listdir("outputs")
    finished_question_ids = [file[:-5] for file in files if file.endswith(".json")]

    with open(
        "/Users/harshitkrishnakumar/Downloads/dev_20240627/dev.json", "r"
    ) as file:
        questions = json.load(file)
    for question in questions:
        if str(question["question_id"]) in finished_question_ids:
            print(
                f"Skipping question {question['question_id']} as it is already processed."
            )
            continue
        print(f"Question: {question['question']}")
        result = run_single_question(
            question=question["question"],
            hint=question["evidence"],
            db_name=question["db_id"],
        )
        db = DBWrapper(
            super_folder_path="/Users/harshitkrishnakumar/Downloads/dev_20240627/dev_databases"
        )
        output_dict = {
            "question_id": question["question_id"],
            "question": question["question"],
            "db_id": question["db_id"],
            "SQL": question["SQL"],
            "expert_result": str(
                db.execute_query_returning_df(question["SQL"], question["db_id"])
            ),
            "generated_result": str(result[0]),
            "generated_sql": result[1],
        }
        # save this to a json file:
        with open(
            f"outputs/{question['question_id']}.json",
            "w",
        ) as output_file:
            json.dump(output_dict, output_file, indent=4)
            output_file.write("\n")
        print("done with question", question["question_id"])


# next things to do:
# to save costs, do openai first, if it fails, then do anthropic
# from the outputs, mostly openAI is working, however in some cases the sql query execution fails.
# So when it fails we can use anthropic as a backup to fix the query
