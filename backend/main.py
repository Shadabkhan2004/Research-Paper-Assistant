from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os, shutil
import uuid

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainFilter
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

from pydantic import BaseModel
from dotenv import load_dotenv
from utils import extract_text_from_pdf, clean_text, filter_docs, chunk_documents, format_docs

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
VECTOR_DIR = os.path.join(tempfile.gettempdir(), "vector_store")
LATEST_VECTOR_STORE: str | None = None

def init_vector_store(docs):
    embedding = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    vector_dir = os.path.join(tempfile.gettempdir(),f"vector_store_{uuid.uuid4()}")
    
    vector_store = Chroma.from_documents(documents=docs, embedding=embedding, persist_directory=vector_dir)
    vector_store.persist()

    return vector_store,vector_dir

llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)

prompt_template = ChatPromptTemplate.from_template("""
Use the context below to answer the question.
Cite sources using the [Source: ..., Page: ...] information when relevant.

Context:
{context}

Question: {question}
""")

class QuestionRequest(BaseModel):
    query: str


@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    global LATEST_VECTOR_STORE
    file_path = f"./{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    docs = extract_text_from_pdf(file_path)
    docs = [Document(page_content=clean_text(d.page_content), metadata=d.metadata) for d in docs]
    docs = filter_docs(docs)
    chunks = chunk_documents(docs)
    
    vector_store,vector_dir = init_vector_store(chunks)
    LATEST_VECTOR_STORE = vector_dir

    compressor = LLMChainFilter.from_llm(llm)
    compression_retriever = ContextualCompressionRetriever(base_compressor=compressor, base_retriever=vector_store.as_retriever(search_kwargs={"k":3}))
    
    return {"message": f"PDF uploaded and vector store created with {len(chunks)} chunks."}

@app.post("/ask-question/")
async def ask_question(request: QuestionRequest):
    query = request.query

    if not LATEST_VECTOR_STORE or not os.path.exists(LATEST_VECTOR_STORE):
        return {"error": "No PDF uploaded yet."}

    vector_store = Chroma(persist_directory=LATEST_VECTOR_STORE, embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL))

    retriever = vector_store.as_retriever(search_kwargs={"k":3})
    compressor = LLMChainFilter.from_llm(llm)
    compression_retriever = ContextualCompressionRetriever(base_compressor=compressor, base_retriever=retriever)
    
    rag_chain = (
        {"context": compression_retriever | RunnablePassthrough(), "question": RunnablePassthrough()}
        | prompt_template
        | llm
        | StrOutputParser()
    )
    
    answer = rag_chain.invoke(query)
    return {"answer": answer}
