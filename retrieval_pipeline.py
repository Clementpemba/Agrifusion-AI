import os
import re
import json
from dotenv import load_dotenv

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI


# -------------------------------
# ENV
# -------------------------------
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("❌ OPENROUTER_API_KEY is missing.")


# -------------------------------
# LOAD VECTOR DB
# -------------------------------
def load_vector_store():
    print("Loading vector database...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    db = Chroma(
        persist_directory="chroma_db",
        embedding_function=embeddings
    )

    print("Vector DB loaded successfully!")
    return db


# -------------------------------
# CREATE RETRIEVERS
# -------------------------------
def create_retrievers(db):

    indigenous_retriever = db.as_retriever(
        search_kwargs={
            "k": 5,
            "filter": {"source_type": "indigenous"}
        }
    )

    historical_retriever = db.as_retriever(
        search_kwargs={
            "k": 5,
            "filter": {"source_type": "historical"}
        }
    )

    return indigenous_retriever, historical_retriever


# -------------------------------
# LLM
# -------------------------------
def get_llm():
    print("Using OpenRouter GPT-4o-mini 🚀")

    llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "UlimiFusion AI",
        },
    )

    print("Model connected ✅")
    return llm


# -------------------------------
# REMOVE DUPLICATES
# -------------------------------
def remove_duplicates(docs):
    if not isinstance(docs, list):
        return []

    seen = set()
    unique_docs = []

    for doc in docs:
        if hasattr(doc, "page_content"):
            if doc.page_content not in seen:
                unique_docs.append(doc)
                seen.add(doc.page_content)

    return unique_docs


# -------------------------------
# DETECT LOCATION
# -------------------------------
def detect_location(query):
    locations = ["rumphi", "lilongwe", "mzuzu", "zomba", "kasungu", "mangochi"]

    query_lower = query.lower()
    for loc in locations:
        if loc in query_lower:
            return loc

    return "malawi"


# -------------------------------
# CLEAN OUTPUT
# -------------------------------
def clean_llm_output(text):
    text = re.sub(r"(\*\*|\*|###|##|#|-)", "", text)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)

    return text


# -------------------------------
# GENERATE ANSWER
# -------------------------------
def generate_answer(query, ik_retriever, hd_retriever, llm):

    location = detect_location(query)

    enhanced_query = f"""
    Farming question in {location} Malawi:

    {query}

    Focus on:
    - local climate
    - soil
    - rainfall patterns
    - indigenous practices
    """

    # -------------------------
    # FIX: use correct LangChain method
    # -------------------------
    ik_docs = ik_retriever.get_relevant_documents(enhanced_query)
    hd_docs = hd_retriever.get_relevant_documents(enhanced_query)

    # Safety checks
    ik_docs = remove_duplicates(ik_docs)
    hd_docs = remove_duplicates(hd_docs)

    # Convert safely
    if len(ik_docs) < 2:
        ik_text = "No strong indigenous signal found"
    else:
        ik_text = "\n".join([doc.page_content for doc in ik_docs])

    hd_text = "\n".join([doc.page_content for doc in hd_docs])

    # -------------------------
    # PROMPT
    # -------------------------
    prompt = f"""
You are an agricultural advisor for Malawi.

QUESTION:
{query}

INDIGENOUS KNOWLEDGE:
{ik_text}

HISTORICAL DATA:
{hd_text}

Return ONLY JSON:

{{
  "indigenous_insight": "",
  "scientific_insight": "",
  "recommendation": "",
  "risk": ""
}}
"""

    response = llm.invoke(prompt)
    cleaned = clean_llm_output(response.content)

    return {
        "answer": cleaned,
        "ik_sources": [doc.page_content[:120] for doc in ik_docs],
        "hd_sources": [doc.page_content[:120] for doc in hd_docs],
    }


# -------------------------------
# INIT
# -------------------------------
def initialize_rag():
    db = load_vector_store()
    ik_retriever, hd_retriever = create_retrievers(db)
    llm = get_llm()

    return ik_retriever, hd_retriever, llm


# -------------------------------
# CLI TEST
# -------------------------------
def main():
    print("Starting Smart RAG Pipeline...\n")

    ik_retriever, hd_retriever, llm = initialize_rag()

    while True:
        query = input("\nYou: ")

        if query.lower() == "exit":
            break

        result = generate_answer(query, ik_retriever, hd_retriever, llm)

        print("\nANSWER:\n")
        print(result["answer"])

        print("\n--- IK SOURCES ---")
        for src in result["ik_sources"]:
            print("-", src)

        print("\n--- HD SOURCES ---")
        for src in result["hd_sources"]:
            print("-", src)

        print("\n" + "-" * 50)


if __name__ == "__main__":
    main()