import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend folder
env_path = Path(__file__).parent.parent / 'backend' / '.env'
load_dotenv(env_path)

class LLMClient:
    def __init__(self, provider="groq"):
        self.provider = provider.lower()
        
        if self.provider == "groq":
            from groq import Groq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("❌ GROQ_API_KEY not found. Ensure .env is in the backend/ folder.")
            self.client = Groq(api_key=api_key)
            self.model = "llama-3.1-8b-instant"  # Current supported model
            
        elif self.provider == "gemini":
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("❌ GEMINI_API_KEY not found. Ensure .env is in the backend/ folder.")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel('gemini-1.5-flash')
            self.model = "gemini-1.5-flash"
            
        else:
            raise ValueError("Provider must be 'groq' or 'gemini'")

    def generate(self, full_prompt):
        """Generate a response using the selected LLM."""
        try:
            if self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": full_prompt}],
                    temperature=0.3,
                    max_tokens=500
                )
                return response.choices[0].message.content
                
            elif self.provider == "gemini":
                response = self.client.generate_content(full_prompt)
                return response.text
                
        except Exception as e:
            return f"[LLM Error: {str(e)}]"

    def route_query(self, query):
        """Classify the user query into 'pdf', 'tool', or 'both'."""
        prompt = f"""
        Classify the following user query into exactly one category:
        - 'pdf' if it asks about the content of a document (resume, PDF, student info, skills).
        - 'tool' if it asks about companies, investments, valuations, or portfolio data.
        - 'both' if it requires BOTH document context AND company data.
        
        Query: "{query}"
        
        Return only the single word: 'pdf', 'tool', or 'both'.
        """
        
        try:
            if self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=10
                )
                classification = response.choices[0].message.content.strip().lower()
            else:
                # Gemini fallback
                response = self.client.generate_content(prompt)
                classification = response.text.strip().lower()
            
            if classification in ['pdf', 'tool', 'both']:
                return classification
            return 'pdf'  # Default fallback
        except:
            return 'pdf'  # Safe fallback