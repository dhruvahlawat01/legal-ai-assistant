import os
import json
import tempfile
import io
from datetime import datetime
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

        # 3. Define Risk Analysis Prompt
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

    def get_vectorstore(self, file_path):
        """Load PDF and return vectorstore for chat"""
        texts = self.load_and_embed(file_path)
        vectorstore = self.create_vector_store(texts)
        return vectorstore

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

    def rewrite_clause(self, clause_type, explanation, text_snippet):
        """Suggest a safer rewrite for a risky clause"""
        rewrite_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior legal expert specializing in contract drafting.
            Your task is to rewrite risky contract clauses into fair, balanced alternatives.
            
            Guidelines for rewriting:
            - Make the clause fair for both parties
            - Use clear, plain English
            - Remove or limit overly broad restrictions
            - Add reasonable time limits where missing
            - Add geographical limits where missing
            - Ensure GDPR compliance where relevant
            - Keep it professional and legally sound
            
            Return ONLY valid JSON in this exact format, no extra commentary:
            {{
                "original_issue": "string - what makes the original clause risky",
                "rewritten_clause": "string - the full rewritten clause text",
                "key_changes": ["change 1", "change 2", "change 3"],
                "risk_reduction": "HIGH/MEDIUM/LOW - how much risk this rewrite reduces"
            }}
            """),
            ("human", """Please rewrite this risky contract clause:
            
            Clause Type: {clause_type}
            Risk Explanation: {explanation}
            Original Text: {text_snippet}
            
            Provide a safer, fairer alternative.""")
        ])

        rewrite_chain = rewrite_prompt | self.llm

        try:
            response = rewrite_chain.invoke({
                "clause_type": clause_type,
                "explanation": explanation,
                "text_snippet": text_snippet if text_snippet else "No specific text provided"
            })

            try:
                result = json.loads(response.content)
                return result
            except json.JSONDecodeError:
                try:
                    start = response.content.index("{")
                    end = response.content.rindex("}") + 1
                    result = json.loads(response.content[start:end])
                    return result
                except (ValueError, json.JSONDecodeError):
                    return {
                        "original_issue": explanation,
                        "rewritten_clause": response.content,
                        "key_changes": ["See rewritten clause above"],
                        "risk_reduction": "MEDIUM"
                    }
        except Exception as e:
            raise RuntimeError(f"Clause rewriting failed: {str(e)}")

    def chat_with_contract(self, question, vectorstore):
        """Answer questions about the contract using RAG"""
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful legal assistant. You have been given relevant 
            sections from a contract. Answer the user's question based ONLY on the contract 
            content provided. 
            
            Rules:
            - Answer in plain, simple English
            - If the answer is not in the contract, say "I couldn't find this in the contract"
            - Be concise but complete
            - Quote relevant parts of the contract when helpful
            - Do not make up information
            """),
            ("human", """Contract sections:
            {context}
            
            Question: {question}
            
            Please answer based on the contract content above.""")
        ])

        chat_chain = chat_prompt | self.llm

        try:
            retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
            relevant_docs = retriever.invoke(question)
            context = "\n\n".join([doc.page_content for doc in relevant_docs])

            response = chat_chain.invoke({
                "context": context,
                "question": question
            })
            return response.content
        except Exception as e:
            raise RuntimeError(f"Chat failed: {str(e)}")

    def generate_pdf_report(self, results, risk_data, filename="contract_analysis"):
        """Generate a PDF report of the analysis"""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.enums import TA_CENTER

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#1a1a2e"),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold"
        )
        subtitle_style = ParagraphStyle(
            "SubtitleStyle",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#555555"),
            spaceAfter=4,
            alignment=TA_CENTER
        )
        section_header_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#1a1a2e"),
            spaceBefore=16,
            spaceAfter=8,
            fontName="Helvetica-Bold"
        )
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#333333"),
            spaceAfter=4,
            leading=14
        )
        snippet_style = ParagraphStyle(
            "SnippetStyle",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#666666"),
            spaceAfter=4,
            leading=13,
            leftIndent=10,
            fontName="Helvetica-Oblique"
        )

        story = []

        # Header
        story.append(Paragraph("ContractSentry AI", title_style))
        story.append(Paragraph("Legal Contract Risk Analysis Report", subtitle_style))
        story.append(Paragraph(
            f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            subtitle_style
        ))
        story.append(Spacer(1, 0.2 * inch))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
        story.append(Spacer(1, 0.2 * inch))

        # Risk Score Summary
        story.append(Paragraph("Overall Risk Assessment", section_header_style))

        risk_color_map = {
            "red": colors.HexColor("#dc3545"),
            "orange": colors.HexColor("#fd7e14"),
            "green": colors.HexColor("#28a745")
        }
        risk_color = risk_color_map.get(risk_data["color"], colors.grey)

        summary_data = [
            ["Overall Risk Score", "High Risk Clauses", "Medium Risk Clauses", "Low Risk Clauses"],
            [
                f"{risk_data['score']}%",
                str(risk_data["breakdown"].get("HIGH", 0)),
                str(risk_data["breakdown"].get("MEDIUM", 0)),
                str(risk_data["breakdown"].get("LOW", 0))
            ]
        ]

        summary_table = Table(summary_data, colWidths=[1.7 * inch] * 4)
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8f9fa")),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, 1), 16),
            ("TEXTCOLOR", (0, 1), (0, 1), risk_color),
            ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor("#dc3545")),
            ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#fd7e14")),
            ("TEXTCOLOR", (3, 1), (3, 1), colors.HexColor("#28a745")),
            ("ROWHEIGHT", (0, 0), (-1, -1), 35),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.1 * inch))

        risk_label_style = ParagraphStyle(
            "RiskLabel",
            parent=styles["Normal"],
            fontSize=16,
            textColor=risk_color,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            spaceBefore=8,
            spaceAfter=8
        )
        story.append(Paragraph(risk_data["label"], risk_label_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dee2e6")))

        # Detailed Findings
        story.append(Paragraph("Detailed Risk Findings", section_header_style))

        risk_colors_map = {
            "HIGH": colors.HexColor("#dc3545"),
            "MEDIUM": colors.HexColor("#fd7e14"),
            "LOW": colors.HexColor("#28a745")
        }
        risk_bg_map = {
            "HIGH": colors.HexColor("#fff5f5"),
            "MEDIUM": colors.HexColor("#fff8f0"),
            "LOW": colors.HexColor("#f0fff4")
        }

        for i, item in enumerate(results, 1):
            risk_level = item.get("risk_level", "UNKNOWN")
            clause_type = item.get("clause_type", "General")
            explanation = item.get("explanation", "")
            text_snippet = item.get("text_snippet", "")

            item_color = risk_colors_map.get(risk_level, colors.grey)
            item_bg = risk_bg_map.get(risk_level, colors.white)

            clause_data = [[f"{i}. {clause_type}", risk_level]]
            clause_table = Table(clause_data, colWidths=[5.5 * inch, 1.2 * inch])
            clause_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), item_bg),
                ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (1, 0), (1, 0), item_color),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (0, 0), 11),
                ("FONTSIZE", (1, 0), (1, 0), 10),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWHEIGHT", (0, 0), (-1, -1), 28),
                ("LEFTPADDING", (0, 0), (0, 0), 10),
                ("LINEBELOW", (0, 0), (-1, -1), 2, item_color),
            ]))
            story.append(clause_table)
            story.append(Spacer(1, 0.05 * inch))
            story.append(Paragraph(f"<b>Explanation:</b> {explanation}", body_style))

            if text_snippet:
                story.append(Paragraph("<b>Contract Text:</b>", body_style))
                story.append(Paragraph(f'"{text_snippet}"', snippet_style))

            story.append(Spacer(1, 0.15 * inch))

        # Footer
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dee2e6")))
        story.append(Spacer(1, 0.1 * inch))
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#999999"),
            alignment=TA_CENTER
        )
        story.append(Paragraph(
            "This report is generated by AI and is for informational purposes only.",
            footer_style
        ))
        story.append(Paragraph(
            "It does not constitute legal advice. Please consult a qualified lawyer for legal guidance.",
            footer_style
        ))
        story.append(Paragraph(
            "Generated by ContractSentry AI | Powered by Groq LLaMA 3.1",
            footer_style
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def extract_obligations(self, file_path):
        """Extract all obligations, milestones, and deadlines from the contract"""
        try:
            texts = self.load_and_embed(file_path)
            vectorstore = self.create_vector_store(texts)
            retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
            context = "\n\n".join([doc.page_content for doc in retriever.invoke("obligations milestones deadlines deliverables timeline payment schedule")])
        except Exception as e:
            raise RuntimeError(f"Failed to extract obligations: {str(e)}")

        obligations_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior legal expert. Extract all contractual obligations, milestones, deadlines, and dependencies from the contract text.

            Return ONLY valid JSON in this exact format, no extra commentary:
            [
                {{
                    "obligation": "string - what must be done",
                    "deadline": "string - timeframe or deadline (e.g. '5 business days', 'within 30 days of signing')",
                    "party_responsible": "string - who is responsible",
                    "dependency": "string or null - what this depends on",
                    "clause_reference": "string - clause number or section if mentioned"
                }}
            ]
            
            If no clear obligations are found, return an empty array [].
            """),
            ("human", "{context}")
        ])

        chain = obligations_prompt | self.llm
        try:
            response = chain.invoke({"context": context})
            try:
                result = json.loads(response.content)
                return result
            except json.JSONDecodeError:
                start = response.content.index("[")
                end = response.content.rindex("]") + 1
                return json.loads(response.content[start:end])
        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {str(e)}")

    def predict_breach(self, obligations, team_capacity):
        """Run breach prediction based on obligations and user's operational capacity"""
        if not obligations:
            return []

        breach_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in contract compliance and operational risk management.
            
            You will be given:
            1. A list of contractual obligations extracted from a contract
            2. The user's team operational capacity details
            
            Your job is to predict which obligations are at risk of breach based on the capacity constraints.
            
            Return ONLY valid JSON in this exact format, no extra commentary:
            [
                {{
                    "obligation": "string - the obligation at risk",
                    "deadline": "string - the deadline",
                    "breach_probability": "HIGH/MEDIUM/LOW",
                    "reason": "string - why this is at risk given the team capacity",
                    "alert_message": "string - a specific predictive alert message like 'Predictive Alert: Clause X requires...'",
                    "recommendation": "string - what the user should do to avoid breach"
                }}
            ]
            
            Only include obligations that have a MEDIUM or HIGH breach probability. 
            If all obligations seem manageable, return an empty array [].
            """),
            ("human", """Contractual Obligations:
            {obligations}
            
            Team Operational Capacity:
            {capacity}
            
            Analyze each obligation against the capacity and predict breach risks.""")
        ])

        chain = breach_prompt | self.llm
        try:
            response = chain.invoke({
                "obligations": json.dumps(obligations, indent=2),
                "capacity": team_capacity
            })
            try:
                result = json.loads(response.content)
                return result
            except json.JSONDecodeError:
                start = response.content.index("[")
                end = response.content.rindex("]") + 1
                return json.loads(response.content[start:end])
        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {str(e)}")

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
