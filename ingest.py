"""
ingest.py - Document ingestion for Build Your Own Jarvis
Processes PDF documents and stores them in Pinecone vector database
"""

import os
import sys
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

# Load environment variables
load_dotenv()

def check_environment():
    """Check required environment variables"""
    required = ["OPENAI_API_KEY", "PINECONE_API_KEY", "PINECONE_ENVIRONMENT", "PINECONE_INDEX_NAME"]
    for var in required:
        if not os.getenv(var):
            print(f"Error: {var} not found in .env file!")
            sys.exit(1)

def extract_text_from_pdf(pdf_path):
    """Extract text content from PDF file"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return None

def ingest_documents():
    """Ingest all PDF documents from docs folder into Pinecone"""
    print("🚀 Starting document ingestion...")
    
    # Check environment
    check_environment()
    
    # Initialize embeddings
    print("📊 Initializing OpenAI embeddings...")
    embeddings = OpenAIEmbeddings()
    
    # Check docs folder
    docs_folder = "docs"
    if not os.path.exists(docs_folder):
        print(f"Error: '{docs_folder}' folder not found!")
        return False
    
    pdf_files = [f for f in os.listdir(docs_folder) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"No PDF files found in '{docs_folder}' folder!")
        print("Please add your PDF files to the 'docs' directory.")
        return False
    
    print(f"Found {len(pdf_files)} PDF files:")
    
    # Process each PDF
    documents = []
    for pdf_file in pdf_files:
        file_path = os.path.join(docs_folder, pdf_file)
        print(f"  📄 Processing: {pdf_file}")
        
        text = extract_text_from_pdf(file_path)
        if text:
            # Create metadata
            metadata = {
                "source": pdf_file,
                "type": "pdf"
            }
            
            # Create document chunks
            text_splitter = CharacterTextSplitter(
                separator="\n",
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            
            chunks = text_splitter.split_text(text)
            
            # Create Document objects
            for chunk in chunks:
                documents.append(Document(
                    page_content=chunk,
                    metadata=metadata
                ))
            
            print(f"    ✓ Extracted {len(chunks)} chunks")
        else:
            print(f"    ✗ Failed to process {pdf_file}")
    
    if not documents:
        print("No successful document processing!")
        return False
    
    print(f"🧠 Creating vector embeddings for {len(documents)} document chunks...")
    
    # Store in Pinecone
    try:
        # Initialize Pinecone
        pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
        
        # Create or connect to Pinecone index
        PineconeVectorStore.from_documents(
            documents=documents,
            embedding=embeddings,
            index_name=pinecone_index_name
        )
        
        print(f"✅ Successfully ingested {len(documents)} document chunks into Pinecone!")
        print(f"📁 Documents available in index: '{pinecone_index_name}'")
        return True
        
    except Exception as e:
        print(f"❌ Error storing documents in Pinecone: {e}")
        print("Please check your Pinecone API credentials and settings.")
        return False

if __name__ == "__main__":
    ingest_documents()