# Enterprise RAG - Project Inspection Report

Generated: 2026-11-26T16:50:32
Project root: `C:\Users\Partha\Desktop\Enterprise RAG`

## 1. Project Statistics

- Source/config files: 15
- Python files: 14

## 2. Project Structure

```text
Enterprise RAG/
  app/__init__.py
  app/agent.py
  app/config.py
  app/database.py
  app/guardrails.py
  app/ingestion.py
  app/main.py
  app/observability.py
  app/retrieval.py
  project_inspector.py
  requirements.txt
  scripts/init_db.py
  tests/test_api.py
  tests/test_ingestion.py
  tests/test_rag.py
```

## 3. Python File Analysis

### `app\__init__.py`
- Imports: 
- Classes: 
- Functions: 

### `app\agent.py`
- Imports: app.config, app.guardrails, app.observability, app.retrieval, langchain_aws, langchain_core.messages, langgraph.checkpoint.memory, langgraph.checkpoint.postgres, langgraph.graph, langgraph.types, psycopg, sqlalchemy.engine, typing
- Classes: RAGState
- Functions: get_last_user_query, get_conversation_history, guardrail_node, guardrail_router, blocked_node, retrieval_node, approval_node, approval_router, get_chat_model, normalize_response_content, generate_node, rejected_node, build_graph, get_checkpoint_database_url, initialize_agent, get_agent, close_agent, invoke_agent

### `app\config.py`
- Imports: functools, pathlib, pydantic, pydantic_settings
- Classes: Settings
- Functions: get_settings

### `app\database.py`
- Imports: app.config, datetime, sqlalchemy, sqlalchemy.orm, uuid
- Classes: Base, Document, Conversation, Message, Approval, AuditLog
- Functions: utc_now, get_db, check_database_connection, initialize_database

### `app\guardrails.py`
- Imports: re
- Classes: 
- Functions: validate_query, validate_response, requires_human_approval, grounding_fallback

### `app\ingestion.py`
- Imports: app.config, boto3, botocore.config, docx, fitz, functools, hashlib, io, json, logging, pathlib, pinecone, re, tenacity
- Classes: 
- Functions: get_bedrock_client, get_pinecone_client, get_pinecone_index, calculate_hash, save_local_file, delete_local_file, extract_text, chunk_text, generate_embedding, index_document, delete_document_vectors, process_document

### `app\main.py`
- Imports: app.agent, app.config, app.database, app.ingestion, app.observability, contextlib, fastapi, hashlib, pathlib, pydantic, sqlalchemy, sqlalchemy.orm, uuid
- Classes: ChatRequest, ApprovalRequest
- Functions: lifespan, create_audit, get_answer, save_message, root, health, database_health, upload_document, list_documents, get_document, delete_document, chat, chat_history, list_approvals, review_approval, application_info

### `app\observability.py`
- Imports: app.config, contextlib, logging, opentelemetry, opentelemetry.exporter.otlp.proto.http.trace_exporter, opentelemetry.sdk.resources, opentelemetry.sdk.trace, opentelemetry.sdk.trace.export, time
- Classes: 
- Functions: initialize_observability, trace_operation, shutdown_observability

### `app\retrieval.py`
- Imports: app.config, app.ingestion
- Classes: 
- Functions: retrieve_documents, prepare_context, prepare_citations

### `project_inspector.py`
- Imports: ast, datetime, json, os, pathlib
- Classes: 
- Functions: safe_read, discover_files, project_tree, inspect_python, inspect_dependencies, inspect_config_names, main

### `scripts\init_db.py`
- Imports: app.database
- Classes: 
- Functions: main

### `tests\test_api.py`
- Imports: 
- Classes: 
- Functions: 

### `tests\test_ingestion.py`
- Imports: 
- Classes: 
- Functions: 

### `tests\test_rag.py`
- Imports: 
- Classes: 
- Functions: 

## 4. Dependency Files


### requirements.txt
```text

fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.12

pydantic>=2.9.0
pydantic-settings>=2.5.0
python-dotenv>=1.0.1

sqlalchemy>=2.0.35
psycopg[binary,pool]>=3.2.3
langgraph-checkpoint-postgres>=2.0.0

langgraph>=0.2.50
langchain-core>=0.3.0
langchain-aws>=0.2.0
boto3>=1.35.0

pinecone>=5.0.0,<8.0.0

pymupdf>=1.24.0
python-docx>=1.1.2

pydantic-ai-slim>=0.0.14

opentelemetry-api>=1.28.0
opentelemetry-sdk>=1.28.0
opentelemetry-exporter-otlp-proto-http>=1.28.0

httpx>=0.27.0
tenacity>=9.0.0
langchain-aws>=0.2.0
langgraph-checkpoint-postgres>=2.0.0
psycopg[binary,pool]>=3.2.3
opentelemetry-instrumentati
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.12

pydantic>=2.9.0
pydantic-settings>=2.5.0
python-dotenv>=1.0.1

sqlalchemy>=2.0.35
psycopg[binary,pool]>=3.2.3

langgraph>=0.2.50
langgraph-checkpoint-postgres>=2.0.0
langchain-core>=0.3.0
langchain-aws>=0.2.0

boto3>=1.35.0
pinecone>=5.0.0,<8.0.0

pymupdf>=1.24.0
python-docx>=1.1.2

opentelemetry-api>=1.28.0
opentelemetry-sdk>=1.28.0
opentelemetry-exporter-otlp-proto-http>=1.28.0
opentelemetry-instrumentation-fastapi>=0.49b0

httpx>=0.27.0
tenacity>=9.0.0
on-fastapi>=0.49b0
```

## 5. External Service and Configuration References

- `app\agent.py` line 7: `from langchain_aws import ChatBedrockConverse`
- `app\agent.py` line 13: `from langgraph.checkpoint.memory import MemorySaver`
- `app\agent.py` line 14: `from langgraph.checkpoint.postgres import PostgresSaver`
- `app\agent.py` line 15: `from langgraph.graph import StateGraph, START, END, MessagesState`
- `app\agent.py` line 16: `from langgraph.types import Command, interrupt`
- `app\agent.py` line 144: `if not settings.BEDROCK_CHAT_MODEL_ID:`
- `app\agent.py` line 146: `"BEDROCK_CHAT_MODEL_ID is not configured in .env"`
- `app\agent.py` line 149: `return ChatBedrockConverse(`
- `app\agent.py` line 150: `model=settings.BEDROCK_CHAT_MODEL_ID,`
- `app\agent.py` line 151: `region_name=settings.AWS_REGION,`
- `app\agent.py` line 296: `def get_checkpoint_database_url():`
- `app\agent.py` line 297: `database_url = make_url(settings.database_url)`
- `app\agent.py` line 299: `hostname = database_url.host`
- `app\agent.py` line 302: `database_url = database_url.set(`
- `app\agent.py` line 306: `return database_url.set(`
- `app\agent.py` line 317: `if settings.LANGGRAPH_CHECKPOINT_ENABLED:`
- `app\agent.py` line 318: `connection_url = get_checkpoint_database_url()`
- `app\config.py` line 18: `DATABASE_URL: str`
- `app\config.py` line 20: `AWS_REGION: str = "ap-south-1"`
- `app\config.py` line 21: `BEDROCK_MODEL_ID: str = "amazon.titan-embed-text-v2:0"`
- `app\config.py` line 22: `BEDROCK_CHAT_MODEL_ID: str = ""`
- `app\config.py` line 23: `EMBEDDING_DIMENSIONS: int = 1024`
- `app\config.py` line 25: `PINECONE_API_KEY: str`
- `app\config.py` line 26: `PINECONE_INDEX_NAME: str = "enterprise-rag"`
- `app\config.py` line 27: `PINECONE_NAMESPACE: str = "enterprise-documents"`
- `app\config.py` line 29: `UPLOAD_DIR: Path = PROJECT_ROOT / "uploads"`
- `app\config.py` line 30: `MAX_UPLOAD_SIZE_MB: int = 20`
- `app\config.py` line 39: `RIUS_ENDPOINT: str = ""`
- `app\config.py` line 40: `RIUS_API_KEY: str = ""`
- `app\config.py` line 42: `LANGGRAPH_CHECKPOINT_ENABLED: bool = True`
- `app\config.py` line 44: `model_config = SettingsConfigDict(`
- `app\config.py` line 57: `def database_url(self) -> str:`
- `app\config.py` line 58: `url = self.DATABASE_URL.strip()`
- `app\config.py` line 83: `if self.EMBEDDING_DIMENSIONS not in (256, 512, 1024):`
- `app\config.py` line 84: `raise ValueError("Unsupported Titan embedding dimension")`
- `app\config.py` line 86: `if self.MAX_UPLOAD_SIZE_MB <= 0:`
- `app\config.py` line 87: `raise ValueError("MAX_UPLOAD_SIZE_MB must be positive")`
- `app\config.py` line 99: `self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)`
- `app\database.py` line 28: `settings.database_url,`
- `app\ingestion.py` line 14: `from pinecone import Pinecone`
- `app\ingestion.py` line 24: `def get_bedrock_client():`
- `app\ingestion.py` line 26: `"bedrock-runtime",`
- `app\ingestion.py` line 27: `region_name=settings.AWS_REGION,`
- `app\ingestion.py` line 37: `def get_pinecone_client():`
- `app\ingestion.py` line 38: `return Pinecone(api_key=settings.PINECONE_API_KEY)`
- `app\ingestion.py` line 42: `def get_pinecone_index():`
- `app\ingestion.py` line 43: `client = get_pinecone_client()`
- `app\ingestion.py` line 44: `description = client.describe_index(settings.PINECONE_INDEX_NAME)`
- `app\ingestion.py` line 46: `if description.dimension != settings.EMBEDDING_DIMENSIONS:`
- `app\ingestion.py` line 48: `f"Pinecone dimension mismatch: expected "`
- `app\ingestion.py` line 49: `f"{settings.EMBEDDING_DIMENSIONS}, "`
- `app\ingestion.py` line 53: `return client.Index(settings.PINECONE_INDEX_NAME)`
- `app\ingestion.py` line 65: `directory = settings.UPLOAD_DIR / document_id`
- `app\ingestion.py` line 188: `def generate_embedding(content: str) -> list[float]:`
- `app\ingestion.py` line 189: `response = get_bedrock_client().invoke_model(`
- `app\ingestion.py` line 190: `modelId=settings.BEDROCK_MODEL_ID,`
- `app\ingestion.py` line 193: `"dimensions": settings.EMBEDDING_DIMENSIONS,`
- `app\ingestion.py` line 201: `embedding = result.get("embedding")`
- `app\ingestion.py` line 203: `if not embedding:`
- `app\ingestion.py` line 204: `raise ValueError("Bedrock returned an empty embedding")`
- `app\ingestion.py` line 206: `if len(embedding) != settings.EMBEDDING_DIMENSIONS:`
- `app\ingestion.py` line 208: `f"Invalid embedding dimensions: {len(embedding)}"`
- `app\ingestion.py` line 211: `return embedding`
- `app\ingestion.py` line 219: `index = get_pinecone_index()`
- `app\ingestion.py` line 233: `"values": generate_embedding(chunk),`
- `app\ingestion.py` line 244: `namespace=settings.PINECONE_NAMESPACE`
- `app\ingestion.py` line 272: `get_pinecone_index().delete(`
- `app\ingestion.py` line 276: `namespace=settings.PINECONE_NAMESPACE`
- `app\main.py` line 142: `"database": "Neon PostgreSQL"`
- `app\main.py` line 147: `def upload_document(`
- `app\main.py` line 161: `settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1`
- `app\main.py` line 167: `if len(file_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:`
- `app\main.py` line 560: `"architecture": "FastAPI + LangGraph + Bedrock + Pinecone + Neon"`
- `app\observability.py` line 36: `if settings.RIUS_ENDPOINT:`
- `app\observability.py` line 38: `endpoint=settings.RIUS_ENDPOINT,`
- `app\observability.py` line 40: `{"Authorization": f"Bearer {settings.RIUS_API_KEY}"}`
- `app\observability.py` line 41: `if settings.RIUS_API_KEY else {}`
- `app\retrieval.py` line 3: `from app.ingestion import generate_embedding, get_pinecone_index`
- `app\retrieval.py` line 21: `embedding = generate_embedding(query)`
- `app\retrieval.py` line 22: `index = get_pinecone_index()`
- `app\retrieval.py` line 32: `vector=embedding,`
- `app\retrieval.py` line 36: `namespace=settings.PINECONE_NAMESPACE,`
- `project_inspector.py` line 106: `"AWS_", "BEDROCK", "PINECONE", "DATABASE_URL",`
- `project_inspector.py` line 107: `"NEON", "RIUS", "UPLOAD_", "MODEL_", "OLLAMA",`
- `project_inspector.py` line 108: `"LANGGRAPH", "EMBEDDING"`
- `scripts\init_db.py` line 9: `raise SystemExit("Neon connection failed.")`

## 6. Important Notes

- This report does not contain environment variable values.
- `.env` and secret files are excluded.
- Virtual environments, caches, uploads and model directories are excluded.
- Application code is inspected as text and is not executed.
- Large binary files are not included.
