import os
import json
import tempfile
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

class LegalAnalyzer:
    def __init__(self, model_name="llama-3.1-8b-instant"):
        # 1. Setup Embeddings (For Vector Search)
        self.embedder = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")
        
        # 2. Setup the LLM
        self.llm = ChatGroq(
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2,
        )
        
        # 3. Define the Legal Analysis Prompt
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a senior legal expert specializing in contract risk analysis. 
            Your task is to analyze the provided text chunks from a contract and identify "Red Flags".
            
            Focus on these specific high-risk clauses:
            1. Non-Compete / Restricted Activity
            2. Indefinite Term (Auto-Renewal)
            3. Broad Liability Caps / Unlimited Liability
            4. Arbitration Clauses (Waiving Court Rights)
            5. Data Privacy / GDPR Compliance
            
            Return ONLY valid JSON, no extra commentary, in this exact format:
            [
                {{
                    "clause_type": "string", 
                    "risk_level": "HIGH/MEDIUM/LOW", 
                    "explanation": "string",
                    "text_snippet": "string"
                }}
            ]"""),
            ("human", "{context}")
        ])
        
        # 4. Chain the prompt into the LLM
        self.llm_chain = self.prompt_template | self.llm

    def load_and_embed(self, file_path):
        """Step 1: Load PDF and split into chunks"""
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        texts = [doc.page_content.strip() for doc in docs]
        splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        text_chunks = splitter.split_text(" ".join(texts))
        return text_chunks

    def create_vector_store(self, texts):
        """Step 2: Create in-memory ChromaDB vector store"""
        vectorstore = Chroma.from_texts(
            texts=texts,
            embedding=self.embedder,
            collection_name="legal_contract"
        )
        return vectorstore

    def analyze_risk(self, file_path):
        """Step 3: Run RAG + LLM analysis"""
        texts = self.load_and_embed(file_path)
        vectorstore = self.create_vector_store(texts)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        context = "\n\n".join([doc.page_content for doc in retriever.invoke("Risk Analysis")])
        response = self.llm_chain.invoke({"context": context})
        
        try:
            result = json.loads(response.content)
            return result
        except json.JSONDecodeError:
            # Try to extract JSON from response if there's extra text
            try:
                start = response.content.index("[")
                end = response.content.rindex("]") + 1
                result = json.loads(response.content[start:end])
                return result
            except (ValueError, json.JSONDecodeError):
                return [{
                    "clause_type": "General",
                    "risk_level": "MEDIUM",
                    "explanation": response.content,
                    "text_snippet": ""
                }]

    def process_file(self, uploaded_file):
        """Accepts a Streamlit UploadedFile, saves to temp file, runs analysis"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            
            result = self.analyze_risk(tmp_path)
            return result
        
        except Exception as e:
            raise RuntimeError(f"Error during analysis: {str(e)}")
        
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


analyzer = LegalAnalyzer()
