import os
import json
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_engine import HybridRAGEngine
from llm_client import LLMClient
import requests

from dotenv import load_dotenv
import os

# Load .env locally (does nothing on Render if no .env file exists)
load_dotenv()

print("🔑 GROQ_API_KEY loaded:", "✅ FOUND" if os.getenv("GROQ_API_KEY") else "❌ NOT FOUND")
print("🔑 GEMINI_API_KEY loaded:", "✅ FOUND" if os.getenv("GEMINI_API_KEY") else "❌ NOT FOUND")
print("🔗 TOOL_SERVER_URL:", os.getenv("TOOL_SERVER_URL"))
app = Flask(__name__)
CORS(app, origins="*")  # Allow all origins

engine = HybridRAGEngine()
UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_pdf():
    """Upload and index a PDF."""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
    
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        message = engine.process_pdf(file_path)
        return jsonify({"status": "success", "message": message})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests with Memory + Source Citations."""
    data = request.json
    query = data.get('query')
    provider = data.get('provider', 'groq')
    history = data.get('history', [])  # Module 1: Memory

    if not query:
        return jsonify({"answer": "Please enter a question."})

    # 1. MODULE 2: Hybrid Search (now returns content + metadata)
    search_results = engine.hybrid_search(query)
    context = "\n".join([res['content'] for res in search_results])
    
    # 2. MODULE 2: Extract Sources from metadata
    sources = []
    for res in search_results:
        # Safely get source and page from metadata
        meta = res.get('metadata', {})
        source_name = meta.get('source', 'Unknown PDF')
        # Extract just the filename if it's a full path
        if '\\' in source_name:
            source_name = source_name.split('\\')[-1]
        elif '/' in source_name:
            source_name = source_name.split('/')[-1]
            
        page = meta.get('page', 'N/A')
        sources.append({"source": source_name, "page": str(page)})
    
    # Deduplicate sources (same file + same page)
    unique_sources = []
    seen = set()
    for s in sources:
        key = (s['source'], s['page'])
        if key not in seen:
            seen.add(key)
            unique_sources.append(s)

    # 3. Agentic Tool Calling (Company Data)
    tool_data = ""
    trigger_words = ["company", "invest", "valuation", "sector", "startup", "portfolio"]
    if any(word in query.lower() for word in trigger_words):
        try:
            tool_server_url = os.getenv("TOOL_SERVER_URL", "http://localhost:5001")
            resp = requests.get(f"{tool_server_url}/api/companies")
            if resp.status_code == 200:
                companies = resp.json().get('data', [])
                tool_data = json.dumps(companies, indent=2)
        except Exception as e:
            tool_data = f"Tool API Error: {str(e)}"

    # 4. Module 1: Build Conversation Memory
    conversation_context = ""
    for msg in history[-5:]:  # Keep last 5 messages
        if msg['role'] == 'user':
            conversation_context += f"User: {msg['content']}\n"
        else:
            conversation_context += f"Assistant: {msg['content']}\n"

    # 5. Build the Full System Prompt
    system_prompt = f"""
You are an AI assistant helping a student understand their documents and company data.

Previous Conversation:
{conversation_context if conversation_context else "No previous conversation."}

Context from PDF (Hybrid Search):
{context if context else "No document context found."}

External Tool Data (Companies/Investments):
{tool_data if tool_data else "No external data fetched."}

Instructions:
- Use the context to answer questions about the student or document content.
- Use the tool data specifically for company valuations and sectors.
- If you use information from the PDF, the sources will be shown separately.
- Be concise and helpful.
- If the information is not available, say "I don't have that information."

Question: {query}
"""

    # 6. Call the LLM
    try:
        llm = LLMClient(provider=provider)
        answer = llm.generate(system_prompt)
    except Exception as e:
        answer = f"Error generating response: {str(e)}"
        unique_sources = []  # Clear sources on error

    # 7. Return Answer + Sources (Module 2)
    return jsonify({
        "answer": answer,
        "sources": unique_sources  # 🆕 Frontend will display these
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)