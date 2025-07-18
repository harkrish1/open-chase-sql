# open-chase-sql
This repo will attempt to recreate the text to sql framework created by Google + Stanford researchers: https://arxiv.org/abs/2410.01943
# getting started
1. run docker compose up -d to setup qdrant
2. download dev-set from bird bench [https://bird-bench.github.io]
3. Change the folder paths in two places in main file
4. run main.py

# how it works
1. Loads data into a local postgres database
2. Makes a vector database of all categorical columns, ID columns, PK and FK columns
3. Makes a vector DB of the table metadata, column names and column descriptions
4. LLM takes a given user question and splits into relevant keywords, metrics and dimensions
5. Take the split keywords and search both collections for a given question
6. Retrieves the matching columns, column descriptions, categorical column values from Qdrant, passes it on to LLM to select the appropriate ones
7. LLM writes sql query based on selected columns, pragma table info, and top 3 rows for each selected table
8. First try with Openai Models, if the sql execution fails, retry mechanism with Claude models (more accurate but more expensive)
