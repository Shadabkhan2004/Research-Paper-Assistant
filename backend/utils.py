from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
import fitz

def extract_text_from_pdf(file_path):
  """Extract text from PDF pages and return list of Documents with metadata"""
  docs = []
  pdf = fitz.open(file_path)
  for i,page in enumerate(pdf):
    text = page.get_text()
    if text.strip():
      docs.append(Document(page_content=text,metadata={"page":i+1,"source": file_path}))
  return docs

def clean_text(text):
  return " ".join(text.split())


def filter_docs(docs):
  """Remove very short or artifact-heavy chunks"""
  filtered = []
  for d in docs:
    t = d.page_content
    if len(t.strip()) < 50:
      continue
    if t.count('<pad>') > 3 or t.count('<EOS>') > 3:
      continue
    if re.search(r'[0-9]{4,}',t):
      continue
    filtered.append(d)
  
  return filtered

def chunk_documents(docs,chunk_size=600,chunk_overlap=120):
  """Split docs into chunks for embeddings"""
  text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap,
    separators=["\n\n","\n","."," "]
  )

  return text_splitter.split_documents(docs)

def format_docs(docs):
  """Format docs for RAG with citation"""
  formatted = []
  for d in docs:
    src = d.metadata.get("source","Unknown source")
    page = d.metadata.get("page","Unknown page")
    formatted.append(f"[Source: {src}, Page: {page}]\n{d.page_content}")
  return "\n\n".join(formatted)
