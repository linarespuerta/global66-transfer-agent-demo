"""
RAG over the policy docs — THIS is where AI belongs.

Policy is unstructured natural language that changes often. Instead of hard-coding rules (brittle)
or fine-tuning a model (expensive, slow to update), we:
  1. split the markdown policy docs into chunks,
  2. embed them with a small LOCAL model (free, no API key),
  3. store them in a FAISS vector index,
  4. retrieve the most relevant chunks for a given question at runtime.

Update a policy? Edit the markdown and rebuild the index. No model retraining. That update story
is a big part of why RAG is the right tool for a fast-moving fintech.
"""

from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

_POLICY_DIR = Path(__file__).resolve().parent.parent / "policies"

# Small, fast, local embedding model. Downloads once (~90 MB), then runs offline and free.
_EMBEDDINGS = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

_vectorstore = None  # built lazily on first use


def _build_index() -> FAISS:
    docs = []
    for path in sorted(_POLICY_DIR.glob("*.md")):
        loaded = TextLoader(str(path), encoding="utf-8").load()
        for d in loaded:
            d.metadata["source"] = path.name  # keep the source for grounding/citations
        docs.extend(loaded)

    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
    chunks = splitter.split_documents(docs)
    return FAISS.from_documents(chunks, _EMBEDDINGS)


def _get_store() -> FAISS:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = _build_index()
    return _vectorstore


def search_policy(question: str, k: int = 3) -> str:
    """
    Retrieve the top-k most relevant policy passages for a question and return them as text,
    each tagged with its source file so the answer stays grounded and auditable.
    """
    results = _get_store().similarity_search(question, k=k)
    if not results:
        return "No relevant policy found."
    blocks = [f"[source: {r.metadata.get('source','?')}]\n{r.page_content.strip()}" for r in results]
    return "\n\n---\n\n".join(blocks)
