from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainFilter
from pydantic import BaseModel

from utils import extract_text_from_pdf, clean_text, filter_docs, chunk_documents, format_docs
from dotenv import load_dotenv
import os,shutil

load_dotenv()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

OPENAI_MODEL = "gpt-4"
EMBEDDING_MODEL = "text-embedding-3-small"
VECTOR_DIR = "./vector_store"


def init_vector_store(docs):
  embedding = OpenAIEmbeddings(model=EMBEDDING_MODEL)
  if os.path.exists(VECTOR_DIR):
    shutil.rmtree(VECTOR_DIR)
  vector_store = Chroma.from_documents(documents=docs,embedding=embedding,persist_directory=VECTOR_DIR)
  vector_store.persist()
  return vector_store


llm = ChatOpenAI(model=OPENAI_MODEL,temperature=0)


prompt_template = ChatPromptTemplate.from_template("""
Use the context below to answer the question.
Cite sources using the [Source: ..., Page: ...] information when relevant.

Context:
{context}

Question: {question}
""")

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
  file_path = f"./{file.filename}"
  with open(file_path,"wb") as f:
    f.write(await file.read())
  
  docs = extract_text_from_pdf(file_path)
  docs = [Document(page_content=clean_text(d.page_content), metadata=d.metadata) for d in docs]
  docs = filter_docs(docs)
  chunks = chunk_documents(docs)

  vector_store = init_vector_store(chunks)

  compressor = LLMChainFilter.from_llm(llm)
  compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=vector_store.as_retriever(search_kwargs={"k":3})
  )

  return {"message": f"PDF uploaded and vector store created with {len(chunks)} chunks."}

class QuestionRequest(BaseModel):
    query: str

@app.post("/ask-question/")
async def ask_question(request: QuestionRequest):
  query = request.query
  if not os.path.exists(VECTOR_DIR):
    return {"error":"No PDF Uploaded yet."}
  
  vector_store = Chroma(persist_directory=VECTOR_DIR, embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL))
  retriever = vector_store.as_retriever(search_kwargs={"k":3})
  compressor = LLMChainFilter.from_llm(llm)
  compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=retriever
  )

  docs_text = format_docs(compression_retriever.get_relevant_documents(query))
  prompt = prompt_template.format(context=docs_text, question=query)
  answer_obj = llm.invoke(prompt)

  if hasattr(answer_obj, "content"):
    answer_text = answer_obj.content
  else:
    answer_text = str(answer_obj)

  return {"answer": answer_text}
  