from openai import OpenAI
import ast

class LLM:
    def __init__(self):
        self.openai_client = OpenAI(
            api_key="api_key_placeholder"  # Replace with your actual OpenAI API key
        )
    def write_sql_query(self, question: str, dimensions: list, kpis: list, table_metadata: dict):
        prompt = f"""You are a data analyst agent. Your client is a human who is asking a question about the data. \
Your job is to read the question and write a SQL query that can be used to answer the user's question. 
You will be given a list of dimensions that can be used in the format of "[Table Name | Column Name |  Column Value]" \
and a list of kpis that can be used, in the format of "[Table Name | Column Name]". \
You will also be given the PRAGMA table_info metadata for the tables that can be used to answer the user's question. \

For example, if the user asks "What is the total sales in 2023 by country?" and the list of dimensions is \
["sales | sale_year | 2023", "revenue | revenue_year | 2023", "countries | country_name | USA], \
and the list of kpis is ["sales | sales_amount"], \
and the PRAGMA table_info metadata for sales table is \
[(0, 'SalesID', 'INTEGER', 1, None, 1), (1, 'sale_year', 'INTEGER', 1, None, 0), (2, 'sales_amount', 'INTEGER', 1, None, 0), (3, 'CountryID', 'INTEGER', 1, None, 0)] \
and the PRAGMA table_info metadata for revenue table is \
[(0, 'RevenueID', 'INTEGER', 1, None, 1), (1, 'revenue_year', 'INTEGER', 1, None, 0), (2, 'revenue_amount', 'INTEGER', 1, None, 0)], \
and the PRAGMA table_info metadata for countries table is \
[(0, 'CountryID', 'INTEGER', 1, None, 1), (1, 'country_name', 'TEXT', 1, None, 0)], \
you should return 

SELECT country_name, SUM(sales_amount) 
FROM sales as a
left join countries as b 
on a.CountryID = b.CountryID
WHERE sale_year = 2023
group by country_name

Always return only the SQL query and don't include any other text or formatting, since I will directly run this query in the database.
The user is asking:
{question}
The list of dimensions is:
{str(dimensions)}
The list of kpis is:
{str(kpis)}
"""
        for table in table_metadata:
            prompt += f"\nThe PRAGMA table_info metadata for {table} is:\n{str(table_metadata[table])}\n"
        prompt += ("Write the SQL query that can be used to answer the user's question. You don't always need to use all "
                   "the dimensions and kpis, do not apply any filters if the user's question doesn't require it. ")
        response = self.openai_client.responses.create(
            model="o4-mini",
            input=prompt,
            max_output_tokens=2048,
            top_p=1,
            reasoning={"effort": "high"},
        )
        return response.output_text

    def extract_dimensions_and_kpis(self, question: str, dimension_list: list, kpi_list: list):
        dimensions_prompt = f"""You are a data Analyst agent. Your client is a human who is asking an analytical question. \ 
Your job is to read the question and pick all the columns that can be used to answer the user's question from a list. \
You will be given a short listed list of available columns in the format of "[Table Name | Column Name |  Column Value]" \
For example, if the user asks "What is the total sales in 2023?" and the list of columns is \
["sales | sale_year | 2023", "revenue | revenue_year | 2023", "orders | year | 2023"], \
, you should return ["sales | sale_year | 2023"]\
If the user asks "revenue in 2023 by country?", and the list of columns is \
["revenue | revenue_year | 2023", "orders | year | 2023", "country | country_name | USA"], \
you should return ["revenue | revenue_year | 2023", "country | country_name | USA"]. \
Always return a well formatted list of strings and don't include any other text. \
If you don't find any columns, return None.
The user is asking:
{question}
The list of columns is:
{str(dimension_list)}
Pick all the columns that can be used to answer the user's question, read each column carefully and pick the ones that are relevant.
"""
        dimensions_response = self.openai_client.responses.create(
            model="o4-mini",
            input=[
                {
                    "role": "user",
                    "content": dimensions_prompt,
                }
            ],
            max_output_tokens=2048,
            top_p=1,
            reasoning={"effort": "high"},

        )
        dimensions = dimensions_response.output_text
        if not dimensions == "None":
            try:
                dimensions = ast.literal_eval(dimensions)
            except:
                print('Error in parsing dimensions')
                dimensions = dimension_list
        else:
            dimensions = dimension_list
        kpis_prompt = f"""You are a data Analyst agent. Your client is a human who is asking a question about the data. \ 
Your job is to read the question and pick all the columns that can be used to answer the user's question from a list. \
You will be given a list of columns in the format of "[Table Name | Column Name" \
For example, if the user asks "What is the total sales in 2023?" and the list of columns is \
["invoice | sales", "orders | cost", "invoice | revenue"], \
, you should return ["invoice | sales"]\
If the user asks "revenue and sales in 2023 by country?", and the list of columns is \
["invoice | sales", "orders | cost", "invoice | revenue"], \
you should return ["invoice | revenue", "invoice | sales"]. \
Always return a well formatted list of strings and don't include any other text. \
If you don't find any columns, return None.
The user is asking:
{question}
The list of columns is:
{str(kpi_list)}
Pick all the columns that can be used to answer the user's question, read each column carefully and pick the ones that are relevant.
"""
        kpi_response = self.openai_client.responses.create(
            model="o4-mini",
            input=[
                {
                    "role": "user",
                    "content": kpis_prompt
                }
            ],
            max_output_tokens=2048,
            top_p=1,
            reasoning={"effort": "high"},

        )
        kpis = kpi_response.output_text
        if not kpis == "None":
            try:
                kpis = ast.literal_eval(kpis)
            except:
                print('Error in parsing kpis')
                kpis = kpi_list
        else:
            kpis = kpi_list
        return dimensions, kpis


# llm = LLM()
# print(llm.extract_dimensions_and_kpis("Obama is a great president"))
