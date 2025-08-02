import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def summarize_text(text: str) -> str:
    llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that summarizes emails."),
        ("human", "Summarize the following email:\n\n{text}")
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"text": text})