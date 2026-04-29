import asyncio
import json
from typing import Dict, Any, Optional, List, Any as AnyType
from openai import OpenAI
from backend.config import settings
from backend.models.schemas import EffectMeasure
from backend.models.extraction_output import ExtractedStudyData
from backend.services.prompts import (
    METADATA_EXTRACTION_PROMPT,
    METADATA_SYSTEM_MESSAGE,
    METHODS_EXTRACTION_PROMPT,
    METHODS_SYSTEM_MESSAGE,
    ANALYSIS_EXTRACTION_PROMPT,
    ANALYSIS_SYSTEM_MESSAGE,
    get_effect_prompt,
)

# LangChain imports for RAG
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        class RecursiveCharacterTextSplitter:
            def __init__(self, **kwargs): pass
            def split_documents(self, docs): return docs
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document


# Section-specific RAG queries
SECTION_QUERIES = {
    "metadata": [
        "title authors journal year doi",
        "publication date affiliation",
        "study identifier pmid",
    ],
    "methods": [
        "study design population sample size",
        "inclusion exclusion criteria",
        "exposure definition outcome definition",
        "methods participants recruitment",
    ],
    "analysis": [
        "results effect measure confidence interval",
        "odds ratio risk ratio hazard ratio",
        "mean difference standardized mean difference",
        "p-value statistical significance",
        "group statistics table",
    ],
}


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
        elif self.provider == "ollama":
            # Ollama exposes an OpenAI-compatible API.
            # For local: any non-empty string works (e.g., "ollama").
            # For Ollama Cloud: set OLLAMA_API_KEY to your actual token.
            self.client = OpenAI(
                api_key=settings.OLLAMA_API_KEY,
                base_url=settings.OLLAMA_API_URL
            )
            self.model = settings.OLLAMA_MODEL
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
        system_message = """You are an expert epidemiologist extracting key data from research studies.
Only extract data explicitly mentioned in the document. Return structured JSON.
Omit fields that are not found in the document."""

        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", """{extraction_instructions}

STUDY TEXT:
=====================================
{study_text}""")
        ])

        self.extraction_chain = (
            self.extraction_prompt
            | self.llm
            | StrOutputParser()
        )

    def _build_rag_chain(self, documents: List[str]) -> Optional[AnyType]:
        """Build a LangChain RAG chain for retrieval-augmented extraction"""
        try:
            docs = [Document(page_content=doc) for doc in documents]
            chunks = self.text_splitter.split_documents(docs)

            if not chunks:
                return None

            vectorstore = FAISS.from_documents(chunks, self.embeddings)
            retriever = vectorstore.as_retriever(search_type='similarity', search_kwargs={"k": 4})

            return retriever
        except Exception as e:
            print(f"Error building RAG chain: {e}")
            return None

    def _retrieve_relevant_context(
        self,
        text: str,
        queries: List[str],
        top_k: int = 4
    ) -> str:
        """Retrieve relevant context using FAISS vector store with section-specific queries."""
        try:
            retriever = self._build_rag_chain([text])

            if not retriever:
                return text

            combined_query = " ".join(queries)
            retrieved_docs = retriever.invoke(combined_query)

            if retrieved_docs:
                relevant_text = "\n\n".join([doc.page_content for doc in retrieved_docs])
                return relevant_text

            return text

        except Exception as e:
            print(f"Could not retrieve relevant context: {e}")
            return text

    async def _extract_section(
        self,
        text: str,
        section: str,
        outcome: Optional[str] = None,
        exposure: Optional[str] = None,
        effect_type: Optional[EffectMeasure] = None,
        pre_filled_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract a single section (metadata, methods, or analysis) from study text."""
        # Get section-specific queries
        queries = SECTION_QUERIES.get(section, [])

        # Add outcome/exposure to queries for methods/analysis
        if section in ("methods", "analysis"):
            if outcome:
                queries = [outcome] + queries
            if exposure:
                queries = [exposure] + queries

        # Retrieve relevant context
        relevant_text = self._retrieve_relevant_context(text, queries, top_k=3)

        # Limit text length to avoid token limits
        max_chars = 5000
        if len(relevant_text) > max_chars:
            relevant_text = relevant_text[:max_chars]

        # Get the appropriate prompt
        if section == "metadata":
            extraction_prompt = METADATA_EXTRACTION_PROMPT
            system_message = METADATA_SYSTEM_MESSAGE
        elif section == "methods":
            extraction_prompt = METHODS_EXTRACTION_PROMPT
            system_message = METHODS_SYSTEM_MESSAGE
        elif section == "analysis":
            if effect_type:
                extraction_prompt, system_message = get_effect_prompt(effect_type.value)
            else:
                extraction_prompt = ANALYSIS_EXTRACTION_PROMPT
                system_message = ANALYSIS_SYSTEM_MESSAGE
        else:
            extraction_prompt = ANALYSIS_EXTRACTION_PROMPT
            system_message = ANALYSIS_SYSTEM_MESSAGE

        # Add outcome/exposure context for methods/analysis
        if section in ("methods", "analysis") and outcome and exposure:
            context = f"""

IMPORTANT CONTEXT:
You are tasked with extracting data related to:
- PRIMARY OUTCOME: {outcome}
- PRIMARY EXPOSURE: {exposure}

Be flexible with terminology and partial matches.
Extract data if the study examines ANY component of the requested outcome AND the requested exposure.
"""
            extraction_prompt = extraction_prompt + context

        # Extract using the appropriate provider
        if self.provider in ("deepseek", "ollama"):
            response_text = self._extract_with_client(
                extraction_prompt, relevant_text, system_message
            )
        else:
            try:
                response_text = await self.extraction_chain.ainvoke({
                    "extraction_instructions": extraction_prompt,
                    "study_text": relevant_text
                })
            except Exception as e:
                print(f"Chain execution failed, falling back to raw client: {e}")
                response_text = self._extract_with_client(
                    extraction_prompt, relevant_text, system_message
                )

        # Parse the response
        try:
            extracted_json = json.loads(response_text)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse JSON response for {section}, attempting fallback")
            extracted_json = self._fallback_parse(response_text)

        return extracted_json

    async def extract_study_data(
        self,
        text: str,
        effect_type: EffectMeasure,
        outcome: str = None,
        exposure: str = None,
        use_semantic_search: bool = True,
        pre_filled_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract structured data from study text using parallel RAG-enhanced LLM extraction.

        This method splits extraction into 3 parallel chains:
        1. Metadata extraction (title, authors, year, journal, country)
        2. Methods extraction (design, population, sample size, definitions)
        3. Analysis extraction (effect measure, value, CI, group stats, effect-size-specific data)

        If any parallel chain fails, falls back to single-pass extraction.
        """
        try:
            # Launch 3 parallel extraction tasks
            metadata_task = self._extract_section(
                text, "metadata",
                pre_filled_metadata=pre_filled_metadata
            )
            methods_task = self._extract_section(
                text, "methods",
                outcome=outcome, exposure=exposure
            )
            analysis_task = self._extract_section(
                text, "analysis",
                outcome=outcome, exposure=exposure,
                effect_type=effect_type
            )

            metadata_result, methods_result, analysis_result = await asyncio.gather(
                metadata_task, methods_task, analysis_task,
                return_exceptions=True
            )

            # Handle exceptions
            if isinstance(metadata_result, Exception):
                print(f"Metadata extraction failed: {metadata_result}")
                metadata_result = {"metadata": {}}
            if isinstance(methods_result, Exception):
                print(f"Methods extraction failed: {methods_result}")
                methods_result = {"methods": {}}
            if isinstance(analysis_result, Exception):
                print(f"Analysis extraction failed: {analysis_result}")
                analysis_result = {"analysis": {}}

            # Merge results
            extracted_json = {}
            extracted_json.update(metadata_result)
            extracted_json.update(methods_result)
            extracted_json.update(analysis_result)

            # Normalize the extracted data
            extracted_json = self._normalize_extraction(extracted_json)

            # Merge pre-filled metadata from GROBID if available
            if pre_filled_metadata and isinstance(pre_filled_metadata, dict):
                if "metadata" not in extracted_json or not isinstance(extracted_json.get("metadata"), dict):
                    extracted_json["metadata"] = {}
                metadata = extracted_json["metadata"]
                for key, value in pre_filled_metadata.items():
                    if value and (not metadata.get(key) or key in ("title", "year", "doi")):
                        metadata[key] = value

            # Validate and normalize using Pydantic model
            try:
                validated_data = ExtractedStudyData(**extracted_json)
                result = validated_data.dict(exclude_none=True)
            except Exception as e:
                print(f"Pydantic validation warning: {e}. Using raw extraction.")
                result = extracted_json

            # Ensure effect_measure_type is included
            result["effect_measure_type"] = effect_type.value

            # Apply effect-size-specific agent for validation and computation
            from backend.services.agents import process_with_agent
            result = process_with_agent(effect_type.value, result)

            return result

        except Exception as e:
            print(f"Error during parallel extraction: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to single-pass extraction
            print("Falling back to single-pass extraction...")
            return await self._single_pass_extraction(
                text, effect_type, outcome, exposure, pre_filled_metadata
            )

    async def _single_pass_extraction(
        self,
        text: str,
        effect_type: EffectMeasure,
        outcome: Optional[str] = None,
        exposure: Optional[str] = None,
        pre_filled_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fallback single-pass extraction using the generic prompt."""
        from backend.services.prompt import EXTRACTION_PROMPT

        relevant_text = text

        extraction_instructions = EXTRACTION_PROMPT

        if outcome and exposure:
            context = f"""

IMPORTANT CONTEXT:
You are tasked with extracting data related to:
- PRIMARY OUTCOME: {outcome}
- PRIMARY EXPOSURE: {exposure}

Be flexible with terminology and partial matches.
Extract data if the study examines ANY component of the requested outcome AND the requested exposure.
"""
            extraction_instructions = EXTRACTION_PROMPT + context

        if self.provider == "deepseek":
            response_text = self._extract_with_client(extraction_instructions, relevant_text)
        else:
            try:
                response_text = await self.extraction_chain.ainvoke({
                    "extraction_instructions": extraction_instructions,
                    "study_text": relevant_text[:15000]
                })
            except Exception as e:
                print(f"Chain execution failed, falling back to raw client: {e}")
                response_text = self._extract_with_client(extraction_instructions, relevant_text)

        try:
            extracted_json = json.loads(response_text)
        except json.JSONDecodeError:
            print("Warning: Could not parse JSON response, attempting fallback")
            extracted_json = self._fallback_parse(response_text)

        extracted_json = self._normalize_extraction(extracted_json)

        if pre_filled_metadata and isinstance(pre_filled_metadata, dict):
            if "metadata" not in extracted_json or not isinstance(extracted_json.get("metadata"), dict):
                extracted_json["metadata"] = {}
            metadata = extracted_json["metadata"]
            for key, value in pre_filled_metadata.items():
                if value and (not metadata.get(key) or key in ("title", "year", "doi")):
                    metadata[key] = value

        try:
            validated_data = ExtractedStudyData(**extracted_json)
            result = validated_data.dict(exclude_none=True)
        except Exception as e:
            print(f"Pydantic validation warning: {e}. Using raw extraction.")
            result = extracted_json

        result["effect_measure_type"] = effect_type.value

        # Apply effect-size-specific agent for validation and computation
        from backend.services.agents import process_with_agent
        result = process_with_agent(effect_type.value, result)

        return result

    def _extract_with_client(
        self,
        extraction_instructions: str,
        study_text: str,
        system_message: Optional[str] = None
    ) -> str:
        """Extract using raw OpenAI-compatible client (for DeepSeek)."""
        full_prompt = f"{extraction_instructions}\n\n{'='*50}\nSTUDY TEXT:\n{'='*50}\n{study_text[:15000]}"

        if self.provider in ("deepseek", "ollama"):
            response_format = {"type": "json_object"}
        else:
            response_format = None

        system_msg = system_message or (
            "You are an expert epidemiologist extracting key data from research studies. "
            "Only extract data explicitly mentioned in the document. Return structured JSON. "
            "Omit fields that are not found in the document."
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": full_prompt}
            ],
            response_format=response_format,
            temperature=0.3,
            max_tokens=2000
        )

        return response.choices[0].message.content

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """Try to parse response if JSON parsing fails."""
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
        """Normalize extracted data to handle edge cases like lists and invalid effect measures."""
        if not data:
            return data

        # Normalize analysis section
        if "analysis" in data and isinstance(data["analysis"], dict):
            analysis = data["analysis"]

            # Handle exposure - convert list to string
            if "exposure" in analysis:
                if isinstance(analysis["exposure"], list):
                    analysis["exposure"] = "; ".join(str(e) for e in analysis["exposure"][:3])

            # Handle outcome - convert list to string
            if "outcome" in analysis:
                if isinstance(analysis["outcome"], list):
                    analysis["outcome"] = "; ".join(str(o) for o in analysis["outcome"][:3])

            # Normalize effect_measure
            if "effect_measure" in analysis:
                em = analysis["effect_measure"]
                if isinstance(em, str):
                    em_upper = em.upper().strip()
                    if em_upper in ["MAOR", "META-OR", "META OR"]:
                        analysis["effect_measure"] = "OR"
                    elif em_upper in ["MARR", "META-RR", "META RR"]:
                        analysis["effect_measure"] = "RR"
                    elif em_upper in ["MAHR", "META-HR", "META HR"]:
                        analysis["effect_measure"] = "HR"
                    elif em_upper == "PROPORTION":
                        analysis["effect_measure"] = "PROPORTION"
                    elif em_upper not in ["OR", "RR", "HR", "MD", "SMD", "PROPORTION"]:
                        if "OR" in em_upper:
                            analysis["effect_measure"] = "OR"
                        elif "RR" in em_upper:
                            analysis["effect_measure"] = "RR"
                        elif "HR" in em_upper:
                            analysis["effect_measure"] = "HR"
                        elif "PROPORTION" in em_upper or "PREVALENCE" in em_upper or "INCIDENCE" in em_upper:
                            analysis["effect_measure"] = "PROPORTION"
                        else:
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

            # Handle ci_lower
            if "ci_lower" in analysis:
                if isinstance(analysis["ci_lower"], list) and analysis["ci_lower"]:
                    analysis["ci_lower"] = float(analysis["ci_lower"][0])
                elif isinstance(analysis["ci_lower"], str):
                    try:
                        analysis["ci_lower"] = float(analysis["ci_lower"])
                    except:
                        del analysis["ci_lower"]

            # Handle ci_upper
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

            # Handle proportion_data nested fields
            if "proportion_data" in analysis and isinstance(analysis["proportion_data"], dict):
                pd = analysis["proportion_data"]
                for key in ["events", "sample_size"]:
                    if key in pd and isinstance(pd[key], str):
                        try:
                            pd[key] = int(pd[key])
                        except:
                            pd[key] = None
                for key in ["proportion", "se", "ci_lower", "ci_upper"]:
                    if key in pd and isinstance(pd[key], str):
                        try:
                            pd[key] = float(pd[key])
                        except:
                            pd[key] = None

            # Handle two_by_two_table nested fields
            if "two_by_two_table" in analysis and isinstance(analysis["two_by_two_table"], dict):
                t2 = analysis["two_by_two_table"]
                for key in ["a", "b", "c", "d"]:
                    if key in t2 and isinstance(t2[key], str):
                        try:
                            t2[key] = int(t2[key])
                        except:
                            t2[key] = None

            # Handle continuous_data nested fields
            if "continuous_data" in analysis and isinstance(analysis["continuous_data"], dict):
                cd = analysis["continuous_data"]
                for key in ["exposed_n", "control_n"]:
                    if key in cd and isinstance(cd[key], str):
                        try:
                            cd[key] = int(cd[key])
                        except:
                            cd[key] = None
                for key in ["exposed_mean", "exposed_sd", "control_mean", "control_sd"]:
                    if key in cd and isinstance(cd[key], str):
                        try:
                            cd[key] = float(cd[key])
                        except:
                            cd[key] = None

            # Handle survival_data nested fields
            if "survival_data" in analysis and isinstance(analysis["survival_data"], dict):
                sd = analysis["survival_data"]
                for key in ["events_exposed", "events_control"]:
                    if key in sd and isinstance(sd[key], str):
                        try:
                            sd[key] = int(sd[key])
                        except:
                            sd[key] = None
                for key in ["person_time_exposed", "person_time_control", "rate_exposed", "rate_control"]:
                    if key in sd and isinstance(sd[key], str):
                        try:
                            sd[key] = float(sd[key])
                        except:
                            sd[key] = None

        return data

    def _get_empty_extraction(self, effect_type: str) -> Dict[str, Any]:
        """Return minimal empty extraction structure."""
        return {
            "effect_measure_type": effect_type
        }


# Global instance
llm_extraction_service = LLMExtractionService()
