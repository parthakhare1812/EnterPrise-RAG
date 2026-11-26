# Enterprise RAG Frontend

A local-first React interface for the existing FastAPI + LangGraph + SQLite + FAISS retrieval-only backend.

## Included screens

- Overview dashboard
- RAG chat with retrieved source citations
- Document upload, listing, and deletion
- Human approval queue
- Browser-local conversation shortcuts and backend conversation history
- Local system status

## Requirements

- Node.js 18.18+ (Node.js 20 LTS recommended)
- The Enterprise RAG FastAPI backend running at `http://127.0.0.1:8000`

No cloud AI service or model download is used by this frontend. `npm install` downloads the ordinary JavaScript packages needed to run React and Vite.

## Installation

1. Extract this folder into your existing `Enterprise RAG` project root. The result should look like:

   ```text
   Enterprise RAG/
     app/
     scripts/
     data/
     frontend/
       package.json
       vite.config.js
       index.html
       src/
   ```

2. Open a terminal in the `frontend` folder:

   ```powershell
   cd frontend
   npm install
   ```

3. Start the FastAPI backend in a separate terminal from the project root:

   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

4. Start the frontend in another terminal:

   ```powershell
   cd frontend
   npm run dev
   ```

5. Open:

   http://127.0.0.1:5173

## API connection

The Vite development server proxies `/api/*` and `/health` to `http://127.0.0.1:8000`. This avoids requiring browser CORS configuration during local development.

## Backend routes used

- `GET /health`
- `GET /api/v1/health/db`
- `GET /api/v1/info`
- `GET /api/v1/documents`
- `POST /api/v1/documents/upload`
- `DELETE /api/v1/documents/{document_id}`
- `POST /api/v1/chat`
- `GET /api/v1/chat/history/{conversation_id}`
- `GET /api/v1/approvals`
- `POST /api/v1/approvals/{approval_id}`

The conversation history screen stores conversation IDs and titles in this browser's localStorage because the current backend does not expose a conversation-list endpoint. Message history itself is loaded from the backend.

## Notes

- The interface describes responses as retrieved passages, not LLM-generated answers.
- The current backend `/api/v1/info` route may report an old architecture string. The Settings page intentionally presents the local retrieval architecture rather than trusting that legacy string.
- The frontend has not been tested against your running local backend yet. We'll verify each screen and resolve any API contract mismatches file by file.
