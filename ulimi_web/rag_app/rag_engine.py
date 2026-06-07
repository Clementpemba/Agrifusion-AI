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
    raise ValueError("Missing OPENROUTER_API_KEY")


# -------------------------------
# SYSTEM PROMPT (STRONGER)
# -------------------------------
SYSTEM_RULES = """
You are an agricultural expert AI for Malawi.

You MUST:
- Use Indigenous Knowledge FIRST if available
- Then support with scientific explanation
- Always give practical farming advice

Return ONLY valid JSON:

{
  "indigenous_insight": "",
  "scientific_insight": "",
  "recommendation": "",
  "risk": ""
}
"""


# -------------------------------
# SAFE HELPERS
# -------------------------------
def safe_join(docs):
    if not isinstance(docs, list):
        return ""

    texts = []
    for d in docs:
        if hasattr(d, "page_content"):
            texts.append(d.page_content)

    return "\n".join(texts)


# -------------------------------
# LOCATION DETECTION
# -------------------------------
def detect_location(query):
    query = query.lower()

    regions = {
        "Northern Region": ["rumphi", "mzuzu", "karonga", "chitipa", "nkhata bay"],
        "Central Region": ["lilongwe", "dowa", "ntchisi", "kasungu", "ntcheu"],
        "Southern Region": ["blantyre", "zomba", "thyolo", "mangochi", "mulanje"]
    }

    for region, words in regions.items():
        for w in words:
            if w in query:
                return region

    return "Malawi"


# -------------------------------
# INIT RAG
# -------------------------------
def initialize_rag():
    print("Initializing RAG...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    db = Chroma(
        persist_directory="chroma_db",
        embedding_function=embeddings
    )

    # 🔥 Increased recall
    retriever = db.as_retriever(search_kwargs={"k": 10})

    llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "UlimiSmart AI",
        },
    )

    print("RAG ready ✅")
    return retriever, retriever, llm


# -------------------------------
# SAFE JSON PARSER
# -------------------------------
def safe_parse(text):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None

        return json.loads(match.group(0))
    except:
        return None


# -------------------------------
# MAIN GENERATION FUNCTION
# -------------------------------
def generate_answer(query, ik_retriever, hd_retriever, llm):

    location = detect_location(query)
    enhanced_query = f"{query} (Location: {location})"

    # -----------------------
    # 🔥 RETRIEVE ONCE + FILTER
    # -----------------------
    all_docs = ik_retriever.get_relevant_documents(enhanced_query)

    ik_docs = [d for d in all_docs if d.metadata.get("source_type") == "indigenous"]
    hd_docs = [d for d in all_docs if d.metadata.get("source_type") == "historical"]

    print("IK DOC COUNT:", len(ik_docs))
    print("HD DOC COUNT:", len(hd_docs))

    ik_text = safe_join(ik_docs)
    hd_text = safe_join(hd_docs)

    # -----------------------
    # FALLBACKS (IMPORTANT)
    # -----------------------
    if not ik_text:
        ik_text = "Farmers in Malawi often use natural signs such as bird movement, insects, and rainfall patterns to guide planting decisions."

    if not hd_text:
        hd_text = "Maize grows best in warm temperatures with adequate rainfall and fertile soils."

    # -----------------------
    # PROMPT (FORCED IK USAGE)
    # -----------------------
    prompt = f"""
{SYSTEM_RULES}

QUESTION:
{query}

LOCATION:
{location}

INDIGENOUS KNOWLEDGE (PRIORITY — MUST BE USED FIRST):
{ik_text}

HISTORICAL / SCIENTIFIC DATA:
{hd_text}

Return ONLY JSON.
"""

    # -----------------------
    # LLM CALL
    # -----------------------
    try:
        response = llm.invoke(prompt)
        content = getattr(response, "content", "")
    except Exception:
        content = ""

    if not isinstance(content, str):
        content = str(content)

    parsed = safe_parse(content)

    # -----------------------
    # FINAL OUTPUT
    # -----------------------
    if parsed:
        result = parsed
    else:
        result = {
            "indigenous_insight": "Unable to extract indigenous insight",
            "scientific_insight": "Model response issue",
            "recommendation": content[:300],
            "risk": "Unknown"
        }

    return {
        "indigenous_insight": result.get("indigenous_insight", "Not available"),
        "scientific_insight": result.get("scientific_insight", "Not available"),
        "recommendation": result.get("recommendation", "Not available"),
        "risk": result.get("risk", "Not available"),
        "ik_sources": [getattr(d, "page_content", "")[:120] for d in ik_docs],
        "hd_sources": [getattr(d, "page_content", "")[:120] for d in hd_docs],
    }
