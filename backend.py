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
        # 1. Setup Embeddings
        self.embedder = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")

        # 2. Setup LLM
        self.llm = ChatGroq(
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2,
        )

        # 3. Define Prompt
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

        # 4. Chain prompt into LLM
        self.llm_chain = self.prompt_template | self.llm

    def load_and_embed(self, file_path):
        """Step 1: Load PDF and split into chunks"""
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            texts = [doc.page_content.strip() for doc in docs]
            splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
            text_chunks = splitter.split_text(" ".join(texts))
            return text_chunks
        except Exception as e:
            raise RuntimeError(f"PDF loading failed: {str(e)}")

    def create_vector_store(self, texts):
        """Step 2: Create in-memory ChromaDB vector store"""
        try:
            vectorstore = Chroma.from_texts(
                texts=texts,
                embedding=self.embedder,
                collection_name="legal_contract"
            )
            return vectorstore
        except Exception as e:
            raise RuntimeError(f"Vector store creation failed: {str(e)}")

    def analyze_risk(self, file_path):
        """Step 3: Run RAG + LLM analysis"""
        try:
            texts = self.load_and_embed(file_path)
        except Exception as e:
            raise RuntimeError(f"PDF loading failed: {str(e)}")

        try:
            vectorstore = self.create_vector_store(texts)
            retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
            context = "\n\n".join([doc.page_content for doc in retriever.invoke("Risk Analysis")])
        except Exception as e:
            raise RuntimeError(f"Vector store failed: {str(e)}")

        try:
            response = self.llm_chain.invoke({"context": context})
        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {str(e)}")

        try:
            result = json.loads(response.content)
            return result
        except json.JSONDecodeError:
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

    def calculate_risk_score(self, results):
        """Calculate overall risk score from analysis results"""
        if not results:
            return {
                "score": 0,
                "label": "🟢 LOW RISK",
                "color": "green",
                "breakdown": {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
            }

        scores = {"HIGH": 10, "MEDIUM": 5, "LOW": 1}
        breakdown = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for r in results:
            level = r.get("risk_level", "LOW")
            if level in breakdown:
                breakdown[level] += 1

        total = sum(scores[level] * count for level, count in breakdown.items())
        max_score = len(results) * 10
        percentage = int((total / max_score) * 100) if max_score > 0 else 0

        if percentage >= 60:
            label, color = "🔴 HIGH RISK", "red"
        elif percentage >= 30:
            label, color = "🟠 MEDIUM RISK", "orange"
        else:
            label, color = "🟢 LOW RISK", "green"

        return {
            "score": percentage,
            "label": label,
            "color": color,
            "breakdown": breakdown
        }

    def process_file(self, uploaded_file):
        """Accepts a Streamlit UploadedFile, saves to temp file, runs analysis"""
        if uploaded_file is None:
            raise ValueError("No file provided. Please upload a PDF.")

        tmp_path = None
        try:
            uploaded_file.seek(0)
            file_bytes = uploaded_file.read()

            if len(file_bytes) == 0:
                raise ValueError("Uploaded file is empty. Please upload a valid PDF.")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            result = self.analyze_risk(tmp_path)
            return result

        except Exception as e:
            raise RuntimeError(f"Error during analysis: {str(e)}")

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)


analyzer = LegalAnalyzer()
