import os
import shutil
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi
import nltk
from nltk.tokenize import word_tokenize

# Download NLTK data for tokenization (run once)
nltk.download('punkt_tab', quiet=True)

class HybridRAGEngine:
    def __init__(self):
        self.persist_dir = "./chroma_db"
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = None
        self.bm25_index = None
        self.doc_chunks = []  # Store raw text for BM25
        
    def process_pdf(self, file_path: str):
        """Load, split, and index a PDF."""
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(documents)
        
        # 1. Populate Vector Store (Semantic)
        if self.vectorstore is None:
            self.vectorstore = Chroma.from_documents(
                chunks, self.embeddings, persist_directory=self.persist_dir
            )
        else:
            self.vectorstore.add_documents(chunks)
        
        # 2. Populate BM25 Index (Keyword)
        self.doc_chunks.extend([doc.page_content for doc in chunks])
        tokenized_chunks = [word_tokenize(doc.lower()) for doc in self.doc_chunks]
        self.bm25_index = BM25Okapi(tokenized_chunks)
        
        self.vectorstore.persist()
        return f"Indexed {len(chunks)} chunks."
    
    def hybrid_search(self, query: str, k: int = 4):
        """Fetch results from both Vector and BM25, return text + metadata."""
        # Check if vectorstore is None
        if self.vectorstore is None:
            return []
        
        # Check if BM25 is initialized
        if self.bm25_index is None:
            return []
        
        # 1. Vector Search (Semantic) - Chroma automatically provides metadata
        vector_results = self.vectorstore.similarity_search(query, k=k)
        
        # 2. BM25 Search (Keyword)
        tokenized_query = word_tokenize(query.lower())
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        bm25_top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:k]
        
        # 3. Combine and Deduplicate (prioritize Vector results for metadata)
        final_results = []
        seen_contents = set()
        
        # Add Vector results first (they have accurate source/page metadata)
        for doc in vector_results:
            content = doc.page_content
            if content not in seen_contents:
                seen_contents.add(content)
                final_results.append({
                    "content": content,
                    "metadata": doc.metadata  # Contains 'source' (filename) and 'page'
                })
        
        # Add BM25 results (we don't have metadata for these, so we add a fallback)
        for idx in bm25_top_indices:
            content = self.doc_chunks[idx]
            if content not in seen_contents:
                seen_contents.add(content)
                final_results.append({
                    "content": content,
                    "metadata": {"source": "BM25 Keyword Match", "page": "N/A"}
                })
        
        return final_results[:k]  # Return top k unique