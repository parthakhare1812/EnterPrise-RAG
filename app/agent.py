
import logging
import sqlite3
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command, interrupt

from app.config import settings
from app.guardrails import (
    validate_query,
    validate_response,
    requires_human_approval,
    grounding_fallback,
)
from app.retrieval import (
    retrieve_documents,
    prepare_context,
    prepare_citations,
)
from app.observability import trace_operation


logger = logging.getLogger(__name__)


class RAGState(MessagesState, total=False):
    results: list[dict[str, Any]]
    context: str
    citations: list[dict[str, Any]]
    approval_required: bool
    approval_decision: dict[str, Any]
    error: str
    answer: str


def get_last_user_query(state: RAGState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)

    return ""


def guardrail_node(state: RAGState):
    query = get_last_user_query(state)
    validation = validate_query(query)

    if not validation["allowed"]:
        answer = "Your request could not be processed."

        return {
            "error": validation["reason"],
            "answer": answer,
            "messages": [AIMessage(content=answer)],
        }

    return {
        "approval_required": requires_human_approval(query),
        "error": "",
    }


def guardrail_router(state: RAGState):
    if state.get("error"):
        return "blocked"

    return "retrieve"


def blocked_node(state: RAGState):
    return {
        "answer": state.get(
            "answer",
            "Your request could not be processed.",
        )
    }


def retrieval_node(state: RAGState):
    query = get_last_user_query(state)

    with trace_operation("rag.retrieval"):
        results = retrieve_documents(query)
        context = prepare_context(results)
        citations = prepare_citations(results)

    logger.info(
        "Retrieved %s document chunks",
        len(results),
    )

    return {
        "results": results,
        "context": context,
        "citations": citations,
    }


def approval_node(state: RAGState):
    decision = interrupt({
        "type": "human_approval",
        "message": "This request requires human review.",
        "question": get_last_user_query(state),
        "sources": state.get("citations", []),
    })

    return {
        "approval_decision": decision,
    }


def approval_router(state: RAGState):
    decision = state.get("approval_decision", {})

    if decision.get("approved") is True:
        return "results"

    return "rejected"


def results_node(state: RAGState):
    results = state.get("results", [])

    if not results:
        answer = grounding_fallback(results)
    else:
        answer = prepare_context(results)

    validation = validate_response(answer)

    if not validation["valid"]:
        answer = (
            "The retrieved information could not pass "
            "response validation."
        )

    return {
        "answer": answer,
        "messages": [AIMessage(content=answer)],
    }


def rejected_node(state: RAGState):
    answer = "The request was rejected by the human reviewer."

    return {
        "answer": answer,
        "messages": [AIMessage(content=answer)],
    }


def build_graph(checkpointer=None):
    builder = StateGraph(RAGState)

    builder.add_node("guardrails", guardrail_node)
    builder.add_node("blocked", blocked_node)
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("approval", approval_node)
    builder.add_node("results", results_node)
    builder.add_node("rejected", rejected_node)

    builder.add_edge(START, "guardrails")

    builder.add_conditional_edges(
        "guardrails",
        guardrail_router,
        {
            "blocked": "blocked",
            "retrieve": "retrieval",
        },
    )

    builder.add_edge("blocked", END)

    builder.add_conditional_edges(
        "retrieval",
        lambda state: (
            "approval"
            if state.get("approval_required")
            else "results"
        ),
        {
            "approval": "approval",
            "results": "results",
        },
    )

    builder.add_conditional_edges(
        "approval",
        approval_router,
        {
            "results": "results",
            "rejected": "rejected",
        },
    )

    builder.add_edge("results", END)
    builder.add_edge("rejected", END)

    return builder.compile(checkpointer=checkpointer)


_graph = None
_checkpoint_connection = None
_checkpointer = None


def initialize_agent():
    global _graph, _checkpoint_connection, _checkpointer

    if _graph is not None:
        return _graph

    if settings.LANGGRAPH_CHECKPOINT_ENABLED:
        settings.CHECKPOINT_DB_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        _checkpoint_connection = sqlite3.connect(
            str(settings.CHECKPOINT_DB_PATH),
            check_same_thread=False,
        )

        _checkpointer = SqliteSaver(_checkpoint_connection)
        _checkpointer.setup()
    else:
        _checkpointer = None

    _graph = build_graph(_checkpointer)

    logger.info("Local retrieval-only LangGraph agent initialized")

    return _graph


def get_agent():
    if _graph is None:
        raise RuntimeError(
            "Agent has not been initialized. "
            "Call initialize_agent() first."
        )

    return _graph


def close_agent():
    global _graph, _checkpoint_connection, _checkpointer

    _graph = None
    _checkpointer = None

    if _checkpoint_connection is not None:
        _checkpoint_connection.close()
        _checkpoint_connection = None

    logger.info("Local LangGraph agent closed")


def invoke_agent(
    query: str,
    thread_id: str,
    resume: dict | None = None,
):
    graph = get_agent()

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    if resume is not None:
        return graph.invoke(
            Command(resume=resume),
            config=config,
        )

    return graph.invoke(
        {
            "messages": [
                HumanMessage(content=query),
            ]
        },
        config=config,
    )
