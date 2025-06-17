import streamlit as st
from main import main
st.title("Chase SQL Chatbot")

question = st.text_input("Ask a question about the database:")

if st.button("Submit") and question:
    results, sql_query = main(question)
    st.write("Results:")
    st.dataframe(results)
    if sql_query:
        st.write("SQL Query:")
        st.code(sql_query, language='sql')