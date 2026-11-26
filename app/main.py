
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    UploadFile,
    File
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import (
    engine,
    get_db,
    Document,
    Conversation,
    Message,
    Approval,
    AuditLog,
    check_database_connection,
    initialize_database
)
from app.ingestion import (
    calculate_hash,
    save_local_file,
    delete_local_file,
    process_document,
    delete_document_vectors
)
from app.agent import (
    initialize_agent,
    close_agent,
    invoke_agent
)
from app.observability import (
    initialize_observability,
    shutdown_observability
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_observability()
    initialize_database()
    initialize_agent()

    yield

    close_agent()
    shutdown_observability()
    engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local Enterprise RAG application",
    lifespan=lifespan
)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)
    conversation_id: str | None = None
    user_id: str = "default"


class ApprovalRequest(BaseModel):
    approved: bool
    reviewer: str = "local-reviewer"
    comment: str | None = None


def create_audit(
    db: Session,
    event_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
    success: bool = True
):
    db.add(
        AuditLog(
            event_type=event_type,
            resource_id=resource_id,
            details=details,
            success=success
        )
    )


def get_answer(result: dict) -> str:
    messages = result.get("messages", [])

    for message in reversed(messages):
        if getattr(message, "type", "") == "ai":
            return str(message.content)

    return result.get("answer", "No response generated.")


def save_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    sources: list | None = None
):
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources
    )

    db.add(message)
    return message


@app.get("/")
def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "execution": "local"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "execution": "local"
    }


@app.get(f"{settings.API_PREFIX}/health/db")
def database_health():
    if not check_database_connection():
        raise HTTPException(
            status_code=503,
            detail="Local SQLite database connection failed"
        )

    return {
        "status": "connected",
        "database": "Local SQLite"
    }


@app.post(
    f"{settings.API_PREFIX}/documents/upload",
    status_code=201
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    filename = Path(file.filename).name
    extension = Path(filename).suffix.lower()

    if extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported document format"
        )

    file_bytes = file.file.read(
        settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1
    )

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty document"
        )

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File size limit exceeded"
        )

    file_hash = calculate_hash(file_bytes)

    existing = db.scalar(
        select(Document).where(
            Document.file_hash == file_hash
        )
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Document already exists: {existing.id}"
        )

    document_id = str(uuid.uuid4())

    storage_path = save_local_file(
        file_bytes,
        filename,
        document_id
    )

    document = Document(
        id=document_id,
        filename=filename,
        storage_path=storage_path,
        content_type=file.content_type or "application/octet-stream",
        file_hash=file_hash,
        file_size=len(file_bytes),
        status="processing"
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

    except Exception as error:
        db.rollback()
        delete_local_file(storage_path)

        raise HTTPException(
            status_code=500,
            detail="Document record creation failed"
        ) from error

    try:
        chunk_count = process_document(
            file_bytes,
            filename,
            document_id
        )

        document.status = "completed"
        document.chunk_count = chunk_count

        create_audit(
            db,
            "document.ingested",
            document_id,
            {
                "filename": filename,
                "chunks": chunk_count
            }
        )

        db.commit()

        return {
            "document_id": document_id,
            "filename": filename,
            "status": "completed",
            "chunks_created": chunk_count
        }

    except Exception as error:
        db.rollback()

        try:
            delete_document_vectors(document_id)
        except Exception:
            pass

        document = db.get(Document, document_id)

        if document:
            document.status = "failed"
            document.error_message = str(error)[:2000]
            db.commit()

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Document ingestion failed",
                "document_id": document_id,
                "error": str(error)
            }
        ) from error


@app.get(f"{settings.API_PREFIX}/documents")
def list_documents(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination"
        )

    documents = db.scalars(
        select(Document)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
            "file_size": doc.file_size,
            "created_at": doc.created_at
        }
        for doc in documents
    ]


@app.get(f"{settings.API_PREFIX}/documents/{{document_id}}")
def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    document = db.get(Document, document_id)

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "chunk_count": document.chunk_count,
        "error_message": document.error_message,
        "created_at": document.created_at
    }


@app.delete(f"{settings.API_PREFIX}/documents/{{document_id}}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    document = db.get(Document, document_id)

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    if document.status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Document is processing"
        )

    try:
        delete_document_vectors(document_id)
        delete_local_file(document.storage_path)

        db.delete(document)

        create_audit(
            db,
            "document.deleted",
            document_id
        )

        db.commit()

        return {
            "message": "Document deleted successfully",
            "document_id": document_id
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Document deletion failed"
        ) from error


@app.post(f"{settings.API_PREFIX}/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    if request.conversation_id:
        conversation = db.get(
            Conversation,
            request.conversation_id
        )

        if (
            not conversation
            or conversation.user_id != request.user_id
        ):
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

    else:
        conversation = Conversation(
            user_id=request.user_id,
            title=request.query[:100]
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    conversation_id = conversation.id

    save_message(
        db,
        conversation_id,
        "user",
        request.query
    )

    db.commit()

    try:
        result = invoke_agent(
            query=request.query,
            thread_id=conversation_id
        )

        interruptions = result.get("__interrupt__", [])

        if interruptions:
            interrupt_data = interruptions[0].value

            approval = Approval(
                conversation_id=conversation_id,
                thread_id=conversation_id,
                action="review_rag_request",
                details=interrupt_data,
                status="pending"
            )

            db.add(approval)

            create_audit(
                db,
                "approval.requested",
                conversation_id,
                interrupt_data
            )

            db.commit()
            db.refresh(approval)

            return {
                "status": "pending_approval",
                "conversation_id": conversation_id,
                "approval_id": approval.id,
                "message": interrupt_data["message"]
            }

        answer = get_answer(result)
        citations = result.get("citations", [])

        save_message(
            db,
            conversation_id,
            "assistant",
            answer,
            citations
        )

        create_audit(
            db,
            "chat.completed",
            conversation_id
        )

        db.commit()

        return {
            "status": "completed",
            "conversation_id": conversation_id,
            "answer": answer,
            "citations": citations
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to process the question"
        ) from error


@app.get(
    f"{settings.API_PREFIX}/chat/history/{{conversation_id}}"
)
def chat_history(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    conversation = db.get(
        Conversation,
        conversation_id
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "role": message.role,
                "content": message.content,
                "sources": message.sources,
                "created_at": message.created_at
            }
            for message in sorted(
                conversation.messages,
                key=lambda item: item.created_at
            )
        ]
    }


@app.get(f"{settings.API_PREFIX}/approvals")
def list_approvals(
    db: Session = Depends(get_db)
):
    approvals = db.scalars(
        select(Approval)
        .where(Approval.status == "pending")
        .order_by(Approval.created_at.desc())
    ).all()

    return [
        {
            "id": item.id,
            "thread_id": item.thread_id,
            "action": item.action,
            "details": item.details,
            "created_at": item.created_at
        }
        for item in approvals
    ]


@app.post(
    f"{settings.API_PREFIX}/approvals/{{approval_id}}"
)
def review_approval(
    approval_id: str,
    request: ApprovalRequest,
    db: Session = Depends(get_db)
):
    approval = db.get(
        Approval,
        approval_id
    )

    if not approval:
        raise HTTPException(
            status_code=404,
            detail="Approval not found"
        )

    if approval.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Approval already processed"
        )

    decision = {
        "approved": request.approved,
        "reviewer": request.reviewer,
        "comment": request.comment
    }

    try:
        result = invoke_agent(
            query="",
            thread_id=approval.thread_id,
            resume=decision
        )

        approval.status = (
            "approved" if request.approved else "rejected"
        )

        approval.reviewer = request.reviewer
        approval.review_comment = request.comment

        answer = get_answer(result)

        save_message(
            db,
            approval.conversation_id,
            "assistant",
            answer,
            result.get("citations", [])
        )

        create_audit(
            db,
            "approval.reviewed",
            approval_id,
            decision
        )

        db.commit()

        return {
            "status": approval.status,
            "conversation_id": approval.conversation_id,
            "answer": answer
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Approval processing failed"
        ) from error


@app.get(f"{settings.API_PREFIX}/info")
def application_info():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "architecture": (
            "FastAPI + LangGraph + Ollama + "
            "Sentence Transformers + FAISS + SQLite"
        ),
        "execution": "100% local"
    }
