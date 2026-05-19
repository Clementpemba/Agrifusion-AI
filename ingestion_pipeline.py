import os
import pandas as pd

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings


# -------------------------------
# LOAD CSV DATA
# -------------------------------
def load_csv_data():
    base_path = "Data"

    indigenous_file = os.path.join(base_path, "indigenous_Knowledge.csv")
    historical_file = os.path.join(base_path, "maize_yield_data.csv")

    documents = []

    # ---------------- Indigenous Knowledge ----------------
    ik_df = pd.read_csv(indigenous_file)

    for _, row in ik_df.iterrows():
        text = " | ".join([f"{col}: {row[col]}" for col in ik_df.columns])

        documents.append(
            Document(
                page_content=text,
                metadata={"source_type": "indigenous"}
            )
        )

    # ---------------- Historical Data ----------------
    hd_df = pd.read_csv(historical_file)

    for _, row in hd_df.iterrows():
        text = " | ".join([f"{col}: {row[col]}" for col in hd_df.columns])

        documents.append(
            Document(
                page_content=text,
                metadata={"source_type": "historical"}
            )
        )

    print(f"Loaded {len(documents)} documents from CSVs")
    return documents


# -------------------------------
# CHUNKING
# -------------------------------
def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    chunks = splitter.split_documents(documents)

    print(f"Created {len(chunks)} chunks")
    return chunks


# -------------------------------
# VECTOR STORE (FIXED VERSION)
# -------------------------------
def create_vector_store(chunks):
    print("Creating Chroma vector database...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    db = Chroma(
        persist_directory="chroma_db",
        embedding_function=embeddings
    )

    batch_size = 500  # safe small batches

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        print(f"Adding batch {i} → {i + len(batch)}")

        db.add_documents(batch)

    db.persist()

    print("Chroma DB successfully created!")
    return db

# -------------------------------
# MAIN
# -------------------------------
def main():
    print("Starting ingestion pipeline...")

    docs = load_csv_data()
    chunks = chunk_documents(docs)
    create_vector_store(chunks)

    print("\nSample document:")
    print(chunks[0].page_content)


if __name__ == "__main__":
    main()