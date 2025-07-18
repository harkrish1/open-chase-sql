from openai import OpenAI
import ast
import dotenv
import anthropic

dotenv.load_dotenv()


class LLM:
    def __init__(self):
        self.openai_client = OpenAI()
        self.anthropic_client = anthropic.Anthropic()

    def write_sql_query(
        self,
        question: str,
        hint: str,
        columns: list,
        table_metadata: dict,
        table_top_3_rows: dict,
    ):
        with open("write_sql_query_prompt.txt") as f:
            prompt = f.read()
        prompt = prompt.format(QUESTION=question, HINT=hint, COLUMNS=str(columns))
        for table in table_metadata:
            prompt += f"\nThe PRAGMA table_info metadata for {table} is:\n{str(table_metadata[table])}\n"
        for table in table_top_3_rows:
            prompt += f"\nThe three sample rows for {table} is:\n{str(table_top_3_rows[table])}\n"
        prompt += (
            "Write the SQL query that can be used to answer the user's question. You don't always need to use all "
            "the columns, do not apply any filters if the user's question doesn't require it. "
            "The SQL query is:"
            ""
        )
        response = self.openai_client.responses.create(
            model="o4-mini",
            input=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            top_p=1,
            reasoning={"effort": "medium"},
        )
        return response.output_text

    def write_sql_query_claude(
        self,
        question: str,
        hint: str,
        columns: list,
        table_metadata: dict,
        table_top_3_rows: dict,
        previous_response: str = None,
        follow_up_message: str = None,
    ):
        with open("write_sql_query_prompt.txt") as f:
            prompt = f.read()
        prompt = prompt.format(QUESTION=question, HINT=hint, COLUMNS=str(columns))
        for table in table_metadata:
            prompt += f"\nThe PRAGMA table_info metadata for {table} is:\n{str(table_metadata[table])}\n"
        for table in table_top_3_rows:
            prompt += f"\nThe three sample rows for {table} is:\n{str(table_top_3_rows[table])}\n"
        prompt += (
            "Write the SQL query that can be used to answer the user's question. You don't always need to use all "
            "the columns, do not apply any filters if the user's question doesn't require it. "
            "The SQL query is:"
            ""
        )
        messages = [
            {
                "role": "user",
                "content": prompt,
            },
        ]
        if previous_response and follow_up_message:
            messages.extend(
                [
                    {
                        "role": "assistant",
                        "content": previous_response,
                    },
                    {
                        "role": "user",
                        "content": follow_up_message,
                    },
                ]
            )
        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            thinking={"type": "enabled", "budget_tokens": 10000},
            messages=messages,
        )
        final_response = ""
        for block in response.content:
            if block.type == "thinking":
                print("Thinking:", block.thinking)
            if block.type == "text":
                final_response += block.text
        return final_response.strip()

    def extract_key_entities(self, question: str, hint: str, column_list: list):
        prompt = f"""You are a data Analyst agent. Your client is a human who is asking an analytical question. \ 
Your job is to read the question and pick all the columns that can be used to answer the user's question from a list. 
You will be given a short listed list of available columns in the format of "[Column Name | Table Name |  Column Description (if available)]" .
You will also be given a hint that can be used to answer the user's question.
Analyze the Hint: The hint is designed to direct attention toward certain elements relevant to answering the question. 
For example, if the user asks "What is the total sales in 2023?" 
and the list of columns is 
["sale year | Sales", "hiring year | employee | describes the year employee was hired ", "year | orders"], 
you should return ["sale year | Sales"]
If the user asks "revenue in 2023 by country?", 
and the list of columns is 
["revenue year | revenue", "year | orders", "country code | Country | code of country"], 
you should return ["revenue year | revenue", "country code | Country | code of the country"]. 

Always return a well formatted list of strings and don't include any other text. \
If you don't find any columns, return None.

The user is asking:
{question}
the hint is:
{hint}
The list of columns is:
{str(column_list)}
Pick all the columns that can be used to answer the user's question, read each column carefully and pick the ones that are relevant.
The columns that can be used to answer the user's question are:
"""
        response = self.openai_client.responses.create(
            model="o4-mini",
            input=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_output_tokens=2048,
            top_p=1,
            reasoning={"effort": "medium"},
        )
        columns = response.output_text
        try:
            columns = ast.literal_eval(columns)
        except:
            print("Error in parsing columns")
            columns = None
        return columns

    def extract_keywords(self, question: str, hint: str):
        with open("extract_keywords_prompt.txt") as f:
            prompt = f.read()
        prompt = prompt.format(QUESTION=question, HINT=hint)
        response = self.openai_client.responses.create(
            model="o4-mini",
            input=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_output_tokens=2048,
            top_p=1,
            reasoning={"effort": "high"},
        )
        list_of_keywords = response.output_text
        try:
            if list_of_keywords != "":
                list_of_keywords = ast.literal_eval(list_of_keywords)
            else:
                list_of_keywords = []
        except Exception as e:
            print("Error in parsing keywords", e)
            list_of_keywords = []
        return list_of_keywords
