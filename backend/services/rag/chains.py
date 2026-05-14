"""LangChain RAG chains for epidemiologic study extraction.

Uses LCEL (LangChain Expression Language) with RunnablePassthrough
following the RealPython tutorial pattern.
"""

from typing import Optional, Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_openai import ChatOpenAI

from backend.config import settings
from backend.services.rag.retriever import StudyRetriever
from backend.services.rag.document_loader import StudyTextSplitter


# ---------------------------------------------------------------------------
# Prompt templates (following RealPython's modular prompt pattern)
# ---------------------------------------------------------------------------

METADATA_RAG_TEMPLATE = """You are an expert epidemiologist extracting metadata from research studies.
Use the following retrieved context to answer the question.
Be as detailed as possible, but don't make up any information that's not from the context.
If you don't know an answer, say you don't know.

Context:
{context}

Question: {question}

Provide a structured JSON response with these fields:
- study_id: Study identifier (DOI, PMID, etc.)
- title: Study title
- authors: Comma-separated author names
- year: Publication year (integer)
- journal: Journal name
"""

METHODS_RAG_TEMPLATE = """You are an expert epidemiologist extracting methods from research studies.
Use the following retrieved context to answer the question.
Be as detailed as possible, but don't make up any information that's not from the context.
If you don't know an answer, say you don't know.

Context:
{context}

Question: {question}

Provide a structured JSON response with these fields:
- study_design: Study design (e.g., Case-control, Cohort, RCT)
- population: Study population description
- sample_size: Total sample size (integer)
- exposure_definition: How exposure was defined/measured
- outcome_definition: How outcome was defined/measured
"""

ANALYSIS_RAG_TEMPLATE = """You are an expert epidemiologist extracting analysis results from research studies.
Use the following retrieved context to answer the question.
Be as detailed as possible, but don't don't make up any information that's not from the context.
If you don't know an answer, say you don't know.

Context:
{context}

Question: {question}

Effect measure type: {effect_type}

Provide a structured JSON response with these fields:
- exposure: Exposure / risk factor
- outcome: Outcome / disease
- effect_measure: Type of effect measure (OR, RR, HR, MD, SMD)
- effect_value: Point estimate (float)
- ci_lower: 95% CI lower bound (float)
- ci_upper: 95% CI upper bound (float)
- p_value: Statistical p-value (float)
"""


# ---------------------------------------------------------------------------
# Chain builders
# ---------------------------------------------------------------------------

def build_llm(temperature: float = 0.3) -> ChatOpenAI:
    """Build the LLM component."""
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL if settings.LLM_PROVIDER == "deepseek" else "gpt-3.5-turbo",
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY if settings.LLM_PROVIDER == "openai" else settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_API_URL if settings.LLM_PROVIDER == "deepseek" else None,
    )


def format_docs(docs: List[Any]) -> str:
    """Format retrieved documents into a single context string."""
    return "\n\n".join(doc.page_content for doc in docs)


def build_metadata_rag_chain(
    retriever: Optional[StudyRetriever] = None,
    llm: Optional[ChatOpenAI] = None,
) -> Any:
    """Build a RAG chain for metadata extraction.

    Follows the RealPython pattern:
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    """
    _retriever = retriever or StudyRetriever(k=5)
    _llm = llm or build_llm()

    prompt = ChatPromptTemplate.from_template(METADATA_RAG_TEMPLATE)

    # LCEL chain using RunnableParallel for context + question
    chain = (
        RunnableParallel({
            "context": _retriever | format_docs,
            "question": RunnablePassthrough(),
        })
        | prompt
        | _llm
        | StrOutputParser()
    )

    return chain


def build_methods_rag_chain(
    retriever: Optional[StudyRetriever] = None,
    llm: Optional[ChatOpenAI] = None,
) -> Any:
    """Build a RAG chain for methods extraction."""
    _retriever = retriever or StudyRetriever(k=5)
    _llm = llm or build_llm()

    prompt = ChatPromptTemplate.from_template(METHODS_RAG_TEMPLATE)

    chain = (
        RunnableParallel({
            "context": _retriever | format_docs,
            "question": RunnablePassthrough(),
        })
        | prompt
        | _llm
        | StrOutputParser()
    )

    return chain


def build_analysis_rag_chain(
    effect_type: str,
    retriever: Optional[StudyRetriever] = None,
    llm: Optional[ChatOpenAI] = None,
) -> Any:
    """Build a RAG chain for analysis extraction with effect-type awareness."""
    _retriever = retriever or StudyRetriever(k=10)
    _llm = llm or build_llm()

    # Inject effect_type into the prompt
    prompt = ChatPromptTemplate.from_template(ANALYSIS_RAG_TEMPLATE)

    chain = (
        RunnableParallel({
            "context": _retriever | format_docs,
            "question": RunnablePassthrough(),
            "effect_type": lambda x: effect_type,
        })
        | prompt
        | _llm
        | StrOutputParser()
    )

    return chain


# ---------------------------------------------------------------------------
# Unified extraction chain (parallel section extraction)
# ---------------------------------------------------------------------------

async def run_parallel_extraction(
    study_text: str,
    effect_type: str,
    outcome: Optional[str] = None,
    exposure: Optional[str] = None,
    population: Optional[str] = None,
    comparison: Optional[str] = None,
    study_design: Optional[str] = None,
) -> Dict[str, Any]:
    """Run parallel RAG extraction for metadata, methods, and analysis.

    This mirrors the RealPython agent pattern where multiple chains
    are executed in parallel and results are combined.
    """
    import asyncio

    # Build a retriever scoped to this study text
    # For in-memory RAG, we index the study text on-the-fly
    from backend.services.rag.vector_store import InMemoryStudyVectorStore

    vector_store = InMemoryStudyVectorStore()
    await vector_store.index_study_text(study_text)
    retriever = StudyRetriever(k=10)
    # Override the retriever to use our in-memory store
    retriever._get_relevant_documents = vector_store.similarity_search

    llm = build_llm()

    # Build section-specific chains
    metadata_chain = build_metadata_rag_chain(retriever=retriever, llm=llm)
    methods_chain = build_methods_rag_chain(retriever=retriever, llm=llm)
    analysis_chain = build_analysis_rag_chain(effect_type=effect_type, retriever=retriever, llm=llm)

    # Build questions with PICO context
    metadata_question = "Extract metadata: title, authors, year, journal, study ID"
    methods_question = f"Extract methods: study design, population, sample size"
    if outcome:
        methods_question += f", outcome definition for {outcome}"
    if exposure:
        methods_question += f", exposure definition for {exposure}"

    analysis_question = f"Extract analysis: effect measure for {effect_type}"
    if outcome:
        analysis_question += f", outcome: {outcome}"
    if exposure:
        analysis_question += f", exposure: {exposure}"

    # Run chains in parallel
    metadata_task = metadata_chain.ainvoke(metadata_question)
    methods_task = methods_chain.ainvoke(methods_question)
    analysis_task = analysis_chain.ainvoke(analysis_question)

    results = await asyncio.gather(
        metadata_task, methods_task, analysis_task,
        return_exceptions=True
    )

    # Parse results
    import json
    extracted = {}
    for section, result in zip(["metadata", "methods", "analysis"], results):
        if isinstance(result, Exception):
            extracted[section] = {}
        else:
            try:
                # Try to parse JSON from the response
                # The LLM may return markdown-wrapped JSON
                text = result.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                extracted[section] = json.loads(text)
            except json.JSONDecodeError:
                # Fallback: store raw text
                extracted[section] = {"raw_response": result}

    return extracted
