import json
from typing import Dict, Any, Optional, List
from openai import OpenAI
from backend.config import settings
from backend.models.schemas import ExtractedStudy, EffectMeasure
from backend.models.extraction_output import ExtractedStudyData
from backend.services.embeddings import embedding_service

# LangChain imports for RAG
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        # Fallback if langchain is not installed at all, though we're installing it now
        class RecursiveCharacterTextSplitter:
            def __init__(self, **kwargs): pass
            def split_documents(self, docs): return docs
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document


EXTRACTION_PROMPT = """You are an expert epidemiologist. Extract key epidemiologic data from the provided research study text.

CRITICAL: If the study reports MULTIPLE subgroups, stratified analyses, or meta-analyses, extract ONLY the PRIMARY/MAIN analysis result.
Use SINGLE VALUES, NOT LISTS.

ALWAYS return the COMPLETE JSON object below. Every key must be present.
For fields that are missing or not applicable:
  • Use `null` for numeric, object, or string fields (unless explicitly stated otherwise for a specific string field).
  • Use `[]` for array fields.
Do NOT omit any keys.

RETURN THIS EXACT SCHEMA:
{
  "metadata": {
    "study_id": "<string or null>",
    "title": "<FULL TITLE - REQUIRED, never null or empty>",
    "authors": "<string or null>",
    "year": <integer or null>,
    "journal": "<string or null>"
  },
  "methods": {
    "study_design": "<string or null>",
    "population": "<string or null>",
    "sample_size": <integer or null>,
    "exposure_definition": "<string or null>",
    "outcome_definition": "<string or null>"
  },
  "analysis": {
    "exposure": "<short string — empty string if study does not examine the primary relationship investigated>",
    "outcome": "<short string — empty string if study does not examine the primary relationship investigated>",
    "effect_measure": "<'OR'|'RR'|'HR'|'MD'|'SMD' or null>",
    "effect_value": <number or null>,
    "ci_lower": <number or null>,
    "ci_upper": <number or null>,
    "p_value": <number or null>,
    "group_statistics": {
      "exposed":   { "n": <integer or null>, "mean": <number or null>, "sd": <number or null> },
      "unexposed": { "n": <integer or null>, "mean": <number or null>, "sd": <number or null> }
    },
    "adjustment_variables": ["<string>", "..."]
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TITLE (metadata.title)
  • MANDATORY — never null, never empty string
  • Use the full title as written in the text

EXPOSURE / OUTCOME (analysis.exposure, analysis.outcome)
  • MANDATORY keys — always present in output
  • If the study DOES examine the primary relationship investigated: provide a short string description.
  • If the study does NOT examine the primary relationship investigated: provide an empty string "".

EFFECT MEASURE (analysis.effect_measure)
  • Use ONLY: "OR", "RR", "HR", "MD", "SMD"
  • Normalize abbreviations: "MAOR", "meta-OR" → "OR"
  • Set to null if no effect measure is reported.

NUMERIC FIELDS (effect_value, ci_lower, ci_upper, p_value, sample_size)
  • Single numbers only — NEVER arrays or lists.
  • Use the result from the PRIMARY/MAIN analysis when multiple values are reported.
  • Only populate ci_lower / ci_upper if a confidence interval is EXPLICITLY stated.
  • Set to null if not reported.

GROUP STATISTICS (analysis.group_statistics)
  • Always include the group_statistics object with both "exposed" and "unexposed" keys.
  • Within each group, include only the fields (n, mean, sd) that are explicitly reported; set others to null.
  • If no group statistics are reported at all, set both sub-objects to { "n": null, "mean": null, "sd": null }.

ADJUSTMENT VARIABLES (analysis.adjustment_variables)
  • List of strings — provide an empty array [] if none reported.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example A — Study WITH matching exposure/outcome and effect size:
{
  "metadata": { "study_id": null, "title": "Smoking and Lung Cancer Risk", "authors": "Smith J", "year": 2021, "journal": "Lancet" },
  "methods": { "study_design": "Case-control", "population": "Adults aged 40-70", "sample_size": 500, "exposure_definition": "Self-reported smoking >10 pack-years", "outcome_definition": "Histologically confirmed lung cancer" },
  "analysis": {
    "exposure": "cigarette smoking",
    "outcome": "lung cancer",
    "effect_measure": "OR",
    "effect_value": 4.5,
    "ci_lower": 3.2,
    "ci_upper": 6.3,
    "p_value": 0.001,
    "group_statistics": {
      "exposed":   { "n": 150, "mean": null, "sd": null },
      "unexposed": { "n": 350, "mean": null, "sd": null }
    },
    "adjustment_variables": ["age", "sex"]
  }
}

Example B — Study WITH matching exposure/outcome but NO effect size:
{
  "metadata": { "study_id": null, "title": "Smoking Review", "authors": null, "year": null, "journal": null },
  "methods": { "study_design": null, "population": null, "sample_size": null, "exposure_definition": null, "outcome_definition": null },
  "analysis": {
    "exposure": "smoking",
    "outcome": "lung cancer",
    "effect_measure": null,
    "effect_value": null,
    "ci_lower": null,
    "ci_upper": null,
    "p_value": null,
    "group_statistics": {
      "exposed":   { "n": null, "mean": null, "sd": null },
      "unexposed": { "n": null, "mean": null, "sd": null }
    },
    "adjustment_variables": []
  }
}

Example C — Study that does NOT examine the primary relationship investigated:
{
  "metadata": { "study_id": null, "title": "Dietary Fiber and Colorectal Health", "authors": "A. Lee", "year": 2021, "journal": null },
  "methods": { "study_design": "Cohort", "population": null, "sample_size": null, "exposure_definition": null, "outcome_definition": null },
  "analysis": {
    "exposure": "",
    "outcome": "",
    "effect_measure": null,
    "effect_value": null,
    "ci_lower": null,
    "ci_upper": null,
    "p_value": null,
    "group_statistics": {
      "exposed":   { "n": null, "mean": null, "sd": null },
      "unexposed": { "n": null, "mean": null, "sd": null }
    },
    "adjustment_variables": []
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL REMINDERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Extract ONLY the PRIMARY analysis result.
• Only extract data EXPLICITLY stated in the text — do not infer or calculate.
• Return ONLY valid JSON — no markdown, no code blocks, no commentary.
• Every key in the schema must appear in your output.

Study text:
{text}"""


class LLMExtractionService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        
        # Text splitter for RAG
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Embeddings for vector store
        self.embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
        
        # LLM setup based on provider
        if self.provider == "deepseek":
            self.client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_API_URL
            )
            self.model = settings.DEEPSEEK_MODEL
            self.llm_chain = None
        else:
            # Default to OpenAI
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.3,
                api_key=settings.OPENAI_API_KEY
            )
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "gpt-3.5-turbo"
            
            # Build extraction chain with ChatPromptTemplate
            self._build_extraction_chain()
    
    def _build_extraction_chain(self):
        """Build a LangChain RAG chain using ChatPromptTemplate"""
        # Create system message for epidemiologist role
        system_message = """You are an expert epidemiologist extracting key data from research studies. 
Only extract data explicitly mentioned in the document. Return structured JSON.
Omit fields that are not found in the document."""
        
        # Create ChatPromptTemplate for extraction
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", """{extraction_instructions}

STUDY TEXT:
=====================================
{study_text}""")
        ])
        
        # Build the chain: prompt -> LLM -> parser
        self.extraction_chain = (
            self.extraction_prompt
            | self.llm
            | StrOutputParser()
        )
    
    
    def _build_rag_chain(self, documents: List[str]) -> Optional[any]:
        """Build a LangChain RAG chain for retrieval-augmented extraction"""
        try:
            # Create Document objects for LangChain
            docs = [Document(page_content=doc) for doc in documents]
            
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(docs)
            
            if not chunks:
                return None
            
            # Create FAISS vector store
            vectorstore = FAISS.from_documents(chunks, self.embeddings)
            retriever = vectorstore.as_retriever(search_type='similarity', search_kwargs={"k": 4})
            
            return retriever
        except Exception as e:
            print(f"Error building RAG chain: {e}")
            return None
    
    def _retrieve_relevant_context(
        self,
        text: str,
        outcome: Optional[str] = None,
        exposure: Optional[str] = None,
        top_k: int = 4
    ) -> str:
        """Retrieve relevant context using FAISS vector store"""
        try:
            # Build retriever on the document
            retriever = self._build_rag_chain([text])
            
            if not retriever:
                return text
            
            # Build search query from outcome and exposure
            queries = []
            if outcome:
                queries.append(outcome)
            if exposure:
                queries.append(exposure)
            queries.extend([
                "methods sample size effect measure",
                "results confidence interval p-value",
                "study design population"
            ])
            
            # Combine queries into a single search string
            combined_query = " ".join(queries)
            
            # Retrieve documents
            retrieved_docs = retriever.invoke(combined_query)
            
            if retrieved_docs:
                # Combine retrieved documents
                relevant_text = "\n\n".join([doc.page_content for doc in retrieved_docs])
                return relevant_text
            
            return text
        
        except Exception as e:
            print(f"Could not retrieve relevant context: {e}")
            return text
    
    async def extract_study_data(
        self,
        text: str,
        effect_type: EffectMeasure,
        outcome: str = None,
        exposure: str = None,
        use_semantic_search: bool = True
    ) -> Dict[str, Any]:
        """Extract structured data from study text using RAG-enhanced LLM extraction"""
        try:
            # Use RAG retrieval to get relevant context
            if use_semantic_search and (outcome or exposure):
                relevant_text = self._retrieve_relevant_context(
                    text,
                    outcome=outcome,
                    exposure=exposure,
                    top_k=4
                )
            else:
                relevant_text = text
            
            # Build extraction instructions with outcome and exposure context
            extraction_instructions = EXTRACTION_PROMPT
            
            if outcome and exposure:
                context = f"""\n\nIMPORTANT CONTEXT:\nYou are tasked with extracting data related to:\n- PRIMARY OUTCOME:
                  {outcome}\n- PRIMARY EXPOSURE: {exposure}\n\nIMPORTANT — Be flexible with terminology and partial matches:\n• 
                  The outcome '{outcome}' may appear as synonyms, variations, or related terms (e.g., 'male' and 'male gender' and 'sex' 
                  are conceptually equivalent).\n• If the requested outcome contains multiple options separated by 'or' (e.g., 
                  'Macrosomia or Large for gestational age'), 
                  a study examining ANY of those options is considered relevant. For example, if searching for 'Macrosomia or Large 
                  for gestational age' and the study only reports 'Macrosomia', that IS a match.\n• 
                  The exposure '{exposure}' may appear as synonyms, variations, or related terms
                    (e.g., 'risk factor', 'predictor', 'intervention', 'treatment', 'independent variable', 'determinant').\n• 
                    Extract data if the study examines ANY component of the requested outcome AND the requested exposure, even if not exactly named as provided.\n•
                      DO NOT extract if the study clearly does NOT address the relationship between these concepts—in that case, set `analysis.exposure` and `analysis.outcome` to empty strings (\"\").\n\n
                Use reasonable judgment: if the study is about a component of the requested concepts (e.g., searching for 'Hypertension or Blood pressure elevation' and finding 'Blood pressure'), extract the data.\n"""
                extraction_instructions = EXTRACTION_PROMPT + context
            
            # Use LangChain chain for OpenAI provider
            if self.provider == "deepseek":
                # Use raw client for DeepSeek
                response_text = self._extract_with_client(
                    extraction_instructions, relevant_text
                )
            else:
                # Use LangChain chain for OpenAI
                try:
                    response_text = await self.extraction_chain.ainvoke({
                        "extraction_instructions": extraction_instructions,
                        "study_text": relevant_text[:15000]
                    })
                except Exception as e:
                    print(f"Chain execution failed, falling back to raw client: {e}")
                    response_text = self._extract_with_client(
                        extraction_instructions, relevant_text
                    )
            
            # Parse the response
            try:
                extracted_json = json.loads(response_text)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse JSON response, attempting fallback")
                extracted_json = self._fallback_parse(response_text)
            
            # Normalize the extracted data
            extracted_json = self._normalize_extraction(extracted_json)
            
            # Validate and normalize using Pydantic model
            try:
                validated_data = ExtractedStudyData(**extracted_json)
                result = validated_data.dict(exclude_none=True)
            except Exception as e:
                print(f"Pydantic validation warning: {e}. Using raw extraction.")
                result = extracted_json
            
            # Ensure effect_measure_type is included
            result["effect_measure_type"] = effect_type.value
            
            return result
        
        except Exception as e:
            print(f"Error during extraction: {e}")
            import traceback
            traceback.print_exc()
            return self._get_empty_extraction(effect_type.value)
    
    def _extract_with_client(self, extraction_instructions: str, study_text: str) -> str:
        """Extract using raw OpenAI-compatible client (for DeepSeek)"""
        # Prepare full prompt
        full_prompt = f"{extraction_instructions}\n\n{'='*50}\nSTUDY TEXT:\n{'='*50}\n{study_text[:15000]}"
        
        # Configure response format based on provider
        if self.provider == "deepseek":
            response_format = {"type": "json_object"}
        else:
            response_format = None
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert epidemiologist extracting key data from research studies. Only extract data explicitly mentioned in the document. Return structured JSON. Omit fields that are not found in the document."
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            response_format=response_format,
            temperature=0.3,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    
    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """Try to parse response if JSON parsing fails"""
        # Try to clean up markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"Fallback parse also failed: {e}")
            return {}
    
    def _normalize_extraction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize extracted data to handle edge cases like lists and invalid effect measures"""
        if not data:
            return data
        
        # Normalize analysis section
        if "analysis" in data and isinstance(data["analysis"], dict):
            analysis = data["analysis"]
            
            # Handle exposure - convert list to string
            if "exposure" in analysis:
                if isinstance(analysis["exposure"], list):
                    analysis["exposure"] = "; ".join(str(e) for e in analysis["exposure"][:3])  # Take first 3
            
            # Handle outcome - convert list to string
            if "outcome" in analysis:
                if isinstance(analysis["outcome"], list):
                    analysis["outcome"] = "; ".join(str(o) for o in analysis["outcome"][:3])  # Take first 3
            
            # Normalize effect_measure
            if "effect_measure" in analysis:
                em = analysis["effect_measure"]
                if isinstance(em, str):
                    em_upper = em.upper().strip()
                    # Map common abbreviations to valid enum values
                    if em_upper in ["MAOR", "META-OR", "META OR"]:
                        analysis["effect_measure"] = "OR"
                    elif em_upper in ["MARR", "META-RR", "META RR"]:
                        analysis["effect_measure"] = "RR"
                    elif em_upper in ["MAHR", "META-HR", "META HR"]:
                        analysis["effect_measure"] = "HR"
                    elif em_upper not in ["OR", "RR", "HR", "MD", "SMD"]:
                        # If not a valid enum, try to map it
                        if "OR" in em_upper:
                            analysis["effect_measure"] = "OR"
                        elif "RR" in em_upper:
                            analysis["effect_measure"] = "RR"
                        elif "HR" in em_upper:
                            analysis["effect_measure"] = "HR"
                        else:
                            # Default to OR if we can't determine
                            analysis["effect_measure"] = "OR"
            
            # Handle effect_value - convert list to first value
            if "effect_value" in analysis:
                if isinstance(analysis["effect_value"], list) and analysis["effect_value"]:
                    analysis["effect_value"] = float(analysis["effect_value"][0])
                elif isinstance(analysis["effect_value"], str):
                    try:
                        analysis["effect_value"] = float(analysis["effect_value"])
                    except:
                        del analysis["effect_value"]
            
            # Handle ci_lower - convert list to first value
            if "ci_lower" in analysis:
                if isinstance(analysis["ci_lower"], list) and analysis["ci_lower"]:
                    analysis["ci_lower"] = float(analysis["ci_lower"][0])
                elif isinstance(analysis["ci_lower"], str):
                    try:
                        analysis["ci_lower"] = float(analysis["ci_lower"])
                    except:
                        del analysis["ci_lower"]
            
            # Handle ci_upper - convert list to first value
            if "ci_upper" in analysis:
                if isinstance(analysis["ci_upper"], list) and analysis["ci_upper"]:
                    analysis["ci_upper"] = float(analysis["ci_upper"][0])
                elif isinstance(analysis["ci_upper"], str):
                    try:
                        analysis["ci_upper"] = float(analysis["ci_upper"])
                    except:
                        del analysis["ci_upper"]
            
            # Handle p_value
            if "p_value" in analysis:
                if isinstance(analysis["p_value"], list) and analysis["p_value"]:
                    analysis["p_value"] = float(analysis["p_value"][0])
                elif isinstance(analysis["p_value"], str):
                    try:
                        analysis["p_value"] = float(analysis["p_value"])
                    except:
                        del analysis["p_value"]
        
        return data
    
    def _get_empty_extraction(self, effect_type: str) -> Dict[str, Any]:
        """Return minimal empty extraction structure"""
        return {
            "effect_measure_type": effect_type
        }

# Global instance
llm_extraction_service = LLMExtractionService()
