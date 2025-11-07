"""
jarvis_assistant.py - Main personal AI assistant implementation
Build Your Own Jarvis - OpenAI API + Pinecone vector database + Flask web interface
"""

import os
import sys
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

def check_environment():
    """Check required environment variables"""
    required = ["OPENAI_API_KEY", "PINECONE_API_KEY", "PINECONE_ENVIRONMENT", "PINECONE_INDEX_NAME"]
    for var in required:
        if not os.getenv(var):
            print(f"Error: {var} not found in .env file!")
            return False
    return True

def initialize_jarvis():
    """Initialize Jarvis with vector store and LLM"""
    if not check_environment():
        return None, None, None
    
    try:
        print("🤖 Initializing Jarvis...")
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings()
        
        # Connect to Pinecone
        pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
        vector_store = PineconeVectorStore(
            index_name=pinecone_index_name,
            embedding=embeddings
        )
        
        # Initialize retriever
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        
        # Initialize LLM
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        print("✅ Jarvis initialized successfully!")
        return llm, retriever, vector_store
        
    except Exception as e:
        print(f"Error initializing Jarvis: {e}")
        print("Please check your API keys and run ingest.py first!")
        return None, None, None

def format_docs(docs):
    """Format retrieved documents"""
    formatted = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get('source', 'Unknown source')
        content = doc.page_content.strip()
        formatted.append(f"[Source {i}: {source}]\\n{content}")
    return "\\n\\n".join(formatted)

def get_example_questions():
    """Generate example questions based on available documents"""
    docs_folder = "docs"
    questions = []
    
    try:
        if os.path.exists(docs_folder):
            pdf_files = [f for f in os.listdir(docs_folder) if f.endswith('.pdf')]
            
            if pdf_files:
                # Get first document for specific questions
                first_doc = pdf_files[0].replace('.pdf', '').replace('-', ' ').replace('_', ' ')
                
                questions = [
                    f"What is this document about?",
                    f"Summarize the key points",
                    f"Show me code examples from the document"
                ]
            else:
                # Fallback if no docs
                questions = [
                    "What can you help me with?",
                    "Tell me about your capabilities",
                    "How do you work?"
                ]
        else:
            questions = [
                "What can you help me with?",
                "Tell me about your capabilities",
                "How do you work?"
            ]
    except Exception as e:
        print(f"Error generating questions: {e}")
        questions = [
            "What can you help me with?",
            "Tell me about your capabilities",
            "How do you work?"
        ]
    
    return questions

def initialize_rag_chain(llm, retriever):
    """Initialize the RAG chain for question answering"""
    
    # Enhanced prompt template
    prompt_template = """You are Jarvis, a helpful personal AI assistant.
You specialize in answering questions based on the document content provided.

INSTRUCTIONS:
- Use ONLY the provided context to answer questions
- If the answer isn't in the context, say "I don't have that information in the provided documents"
- Be helpful and conversational but stick to the facts in the documents
- Cite relevant parts when helpful

Context: {context}

Question: {question}

Answer:"""

    prompt = ChatPromptTemplate.from_template(prompt_template)
    
    # Create RAG chain
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

# Initialize Jarvis in global scope
llm, retriever, vector_store = initialize_jarvis()
if llm and retriever:
    rag_chain = initialize_rag_chain(llm, retriever)
else:
    rag_chain = None

# Flask routes
@app.route('/')
def index():
    """Main chatbot interface"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for chat requests"""
    if not rag_chain:
        return jsonify({
            'error': 'Jarvis not initialized. Please check environment variables and run ingest.py first.'
        }), 500
    
    user_message = request.json.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        # Get relevant documents
        docs = retriever.invoke(user_message)
        
        # Generate response
        response = rag_chain.invoke(user_message)
        
        # Extract sources
        sources = []
        for doc in docs[:3]:  # Top 3 sources
            source = doc.metadata.get('source', 'Unknown')
            if source not in sources:
                sources.append(source)
        
        return jsonify({
            'message': response,
            'sources': sources,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Error generating response: {str(e)}'
        }), 500

@app.route('/api/status')
def status():
    """Check system status"""
    return jsonify({
        'status': 'running' if rag_chain else 'error',
        'pinecone_index': os.getenv('PINECONE_INDEX_NAME'),
        'openai_model': 'gpt-4o-mini'
    })

@app.route('/api/example-questions')
def example_questions():
    """Get dynamic example questions based on documents"""
    questions = get_example_questions()
    return jsonify({
        'questions': questions
    })

if __name__ == "__main__":
    print("🚀 Starting Build Your Own Jarvis...")
    print("🌐 Opening web interface at: http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server")
    
    # Start Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)