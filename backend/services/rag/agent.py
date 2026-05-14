"""LangChain agent for epidemiologic study extraction.

Follows the RealPython agent pattern where an LLM decides which
tool (extraction strategy) to use based on the query.
"""

from typing import Dict, Any, Optional, List
from langchain.agents import create_openai_functions_agent, Tool, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain import hub

from backend.config import settings
from backend.services.rag.chains import (
    build_metadata_rag_chain,
    build_methods_rag_chain,
    build_analysis_rag_chain,
)


# ---------------------------------------------------------------------------
# Tool definitions (following RealPython's Tool pattern)
# ---------------------------------------------------------------------------

def _build_tools(effect_type: str, study_text: str) -> List[Tool]:
    """Build extraction tools for the agent.

    Each tool wraps a RAG chain for a specific extraction task.
    """
    from backend.services.rag.vector_store import InMemoryStudyVectorStore
    from backend.services.rag.retriever import StudyRetriever

    # Index study text for retrieval
    vector_store = InMemoryStudyVectorStore()
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, schedule the task
            asyncio.create_task(vector_store.index_study_text(study_text))
        else:
            loop.run_until_complete(vector_store.index_study_text(study_text))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(vector_store.index_study_text(study_text))
        loop.close()

    retriever = StudyRetriever(k=10)
    # Monkey-patch retriever to use in-memory store
    retriever._get_relevant_documents = vector_store.similarity_search

    llm = ChatOpenAI(
        model=settings.DEEPSEEK_MODEL if settings.LLM_PROVIDER == "deepseek" else "gpt-3.5-turbo",
        temperature=0.3,
        api_key=settings.OPENAI_API_KEY if settings.LLM_PROVIDER == "openai" else settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_API_URL if settings.LLM_PROVIDER == "deepseek" else None,
    )

    metadata_chain = build_metadata_rag_chain(retriever=retriever, llm=llm)
    methods_chain = build_methods_rag_chain(retriever=retriever, llm=llm)
    analysis_chain = build_analysis_rag_chain(effect_type=effect_type, retriever=retriever, llm=llm)

    return [
        Tool(
            name="MetadataExtractor",
            func=lambda q: metadata_chain.invoke(q),
            description="""Useful for extracting study metadata: title, authors, year, journal, study ID.
Pass the full question as input. For example, if asked "What is the title?",
the input should be "Extract metadata: title, authors, year, journal".
""",
        ),
        Tool(
            name="MethodsExtractor",
            func=lambda q: methods_chain.invoke(q),
            description="""Useful for extracting study methods: design, population, sample size, definitions.
Pass the full question as input. For example, if asked "What was the sample size?",
the input should be "Extract methods: study design, population, sample size".
""",
        ),
        Tool(
            name="AnalysisExtractor",
            func=lambda q: analysis_chain.invoke(q),
            description=f"""Useful for extracting analysis results: effect measures, confidence intervals, p-values.
Effect measure type: {effect_type}.
Pass the full question as input. For example, if asked "What is the OR?",
the input should be "Extract analysis: effect measure, CI, p-value".
""",
        ),
    ]


# ---------------------------------------------------------------------------
# Agent builder
# ---------------------------------------------------------------------------

def build_extraction_agent(effect_type: str, study_text: str) -> AgentExecutor:
    """Build an agent that routes extraction queries to the right tool.

    Following the RealPython pattern:
    1. Define tools
    2. Pull agent prompt from hub
    3. Create agent with create_openai_functions_agent
    4. Wrap in AgentExecutor
    """
    tools = _build_tools(effect_type, study_text)

    # Use OpenAI functions agent prompt from LangChain Hub
    agent_prompt = hub.pull("hwchase17/openai-functions-agent")

    llm = ChatOpenAI(
        model=settings.DEEPSEEK_MODEL if settings.LLM_PROVIDER == "deepseek" else "gpt-3.5-turbo",
        temperature=0,
        api_key=settings.OPENAI_API_KEY if settings.LLM_PROVIDER == "openai" else settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_API_URL if settings.LLM_PROVIDER == "deepseek" else None,
    )

    agent = create_openai_functions_agent(
        llm=llm,
        prompt=agent_prompt,
        tools=tools,
    )

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        return_intermediate_steps=True,
        verbose=True,
    )

    return agent_executor


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

async def extract_with_agent(
    study_text: str,
    effect_type: str,
    query: str = "Extract all study data",
) -> Dict[str, Any]:
    """Extract study data using the agent-based approach.

    Args:
        study_text: Full text of the study
        effect_type: Type of effect measure (OR, RR, HR, MD, SMD)
        query: Natural language query about what to extract

    Returns:
        Dict with extraction results and intermediate steps
    """
    agent = build_extraction_agent(effect_type, study_text)
    result = await agent.ainvoke({"input": query})
    return result
