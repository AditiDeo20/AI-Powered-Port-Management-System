# Port Land RAG

Multi-Tenant Hybrid RAG Architecture for a Port Land Management System.

---

## Overview


Port Land RAG is a secure, AI-powered enterprise platform designed for a single Port Authority managing multiple leaseholders, departments, documents, approvals, lease records, and land-management workflows.

Unlike a typical SaaS multi-tenant system where each organization owns a separate knowledge base, this project follows a Port Authority ownership model. The system has one protected Master Knowledge Base owned by the authority and logically isolated Tenant Knowledge Bases for leaseholder-specific documents.

The core objective is to provide accurate, citation-backed answers using hybrid retrieval over structured PostgreSQL data, vector search, tenant-filtered documents, and role-based access policies.

## Design Philosophy

The system is organized around knowledge boundaries rather than separate organizations.

There are two primary knowledge domains:

### Master Knowledge Base

The Master Knowledge Base is owned and maintained by the Port Authority.

It contains enterprise-wide and authority-controlled information such as:

- Government Acts
- Port Regulations
- Office Orders
- Circulars
- Lease Policies
- Standard Operating Procedures
- Standard Lease Templates
- Inspection Guidelines
- Common Maps
- Authority-uploaded documents
- Shared engineering drawings
- Public notifications issued by the authority
- Central lease records
- Central billing metadata
- Enterprise PostgreSQL data

This is not a public knowledge base. Every document and database row is tagged with metadata and protected by access policies.

Tenant users can retrieve only the subset of master data that belongs to them. Authority users retrieve information according to their roles, departments, and organizational permissions.

### Tenant Knowledge Base

Each tenant has a logically isolated private knowledge repository.

It may contain:

- Uploaded agreements
- Correspondence
- Supporting documents
- Certificates
- Legal replies
- Uploaded PDFs
- Uploaded images
- Uploaded Excel sheets
- Additional evidence

No tenant can access another tenant’s private repository. Authority users may access tenant documents only according to their assigned role and permission level.

## High-Level Architecture

```text
                     +----------------------+
                     | React + Vite Client  |
                     +----------+-----------+
                                |
                         JWT / OIDC Token
                                |
                                v
                     +----------------------+
                     | FastAPI API Gateway  |
                     +----------+-----------+
                                |
               +----------------+----------------+
               |                                 |
               v                                 v
        Authentication                  Tenant Context
          (Keycloak)                    Resolution Engine
               |                                 |
               +----------------+----------------+
                                |
                                v
                  Authorization & Policy Engine
                                |
                                v
                      Hybrid Retrieval Engine
                                |
          +---------------------+----------------------+
          |                                            |
          v                                            v
 Master Knowledge Retrieval                 Tenant Knowledge Retrieval
(PostgreSQL + pgvector + Docs)          (Tenant Docs + Tenant Vectors)
          |                                            |
          +---------------------+----------------------+
                                |
                                v
                     Context Fusion & Deduplication
                                |
                                v
                          BGE-M3 Reranker
                                |
                                v
                      Prompt + Context Builder
                                |
                                v
                        Local Qwen (Ollama)
                                |
                                v
                      Citation & Guardrails
                                |
                                v
                           Final Response
```

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | React + Vite |
| Backend | FastAPI |
| Authentication | Keycloak / OIDC |
| Database | PostgreSQL 17 |
| Vector Storage | pgvector |
| ORM | SQLAlchemy 2 |
| Driver | Psycopg 3 |
| Migration | Alembic |
| Object Storage | MinIO |
| Embedding Model | BGE-M3 |
| Reranker | BGE Reranker v2-m3 |
| LLM | Qwen through Ollama |
| OCR / Parsing | PaddleOCR, Docling, PyMuPDF |
| Optional Graph Layer | Neo4j |
| Deployment | Docker Compose |

## Authentication and Tenant Resolution

Every request starts with Keycloak authentication. The backend verifies the JWT and derives a retrieval context from the token claims.

Example tenant token:

```json
{
  "user_id": "...",
  "role": "TENANT",
  "tenant_id": "TENANT_45",
  "department": "...",
  "permissions": []
}
```

Example authority token:

```json
{
  "user_id": "...",
  "role": "HOD",
  "department": "...",
  "permissions": []
}
```

For a tenant user, the allowed retrieval scope is:

- Tenant Knowledge Base for that tenant
- Master Knowledge Base rows and documents belonging to that tenant
- Shared master documents allowed by policy

The tenant cannot access:

- Other tenant knowledge bases
- Other tenant rows
- Unauthorized authority-only content

For an HOD or authorized Port Authority user, the retrieval scope may include:

- Master Knowledge Base
- Tenant Knowledge Bases
- SQL records
- Department-specific and role-specific records

This retrieval context is enforced by the backend and cannot be overridden by user prompts.

## Knowledge Organization

The system uses a single PostgreSQL and pgvector deployment with strict metadata-based isolation instead of creating one vector database per tenant.

### Master Knowledge Metadata

Each document and chunk in the Master Knowledge Base carries metadata such as:

- `document_id`
- `document_type`
- `department`
- `lease_id`
- `tenant_id`
- `access_scope`
- `effective_date`
- `version`
- `source`

Typical `access_scope` values include:

- `authority_only`
- `tenant_private`
- `shared_department`

Tenant queries apply filters such as:

```sql
tenant_id = 'T001'
OR (
  tenant_id IS NULL
  AND access_scope = 'shared_department'
)
```

Authority users apply filters based on role, department, and assigned permissions.

### Tenant Knowledge Metadata

Tenant-uploaded documents are stored in MinIO and indexed into PostgreSQL/pgvector with mandatory metadata:

- `tenant_id`
- `document_id`
- `document_type`
- `uploaded_by`
- `case_id`
- `upload_date`

Every tenant retrieval automatically filters by `tenant_id`, preventing cross-tenant access.

## Document Ingestion Pipeline

### Authority Upload Flow

```text
Upload
  ↓
Virus Scan
  ↓
OCR if needed
  ↓
Document Parsing
  ↓
Metadata Extraction
  ↓
Chunking
  ↓
Embedding with BGE-M3
  ↓
Store Vector
  ↓
Store Metadata
  ↓
Update Master Knowledge Base
```

Authority uploads may also update structured PostgreSQL records when appropriate.

### Tenant Upload Flow

```text
Upload
  ↓
Virus Scan
  ↓
OCR
  ↓
Chunking
  ↓
Embedding
  ↓
Store Document
  ↓
Tag tenant_id
  ↓
Update Tenant Knowledge Base
```

Authority users can later retrieve tenant-uploaded documents according to role. Other tenants cannot access them.

## Hybrid Retrieval Workflow

When a user asks a question such as:

> Show my lease renewal conditions.

The system follows this workflow:

1. Authenticate the user.
2. Resolve role, tenant ID, department, and permissions.
3. Build a retrieval policy from the user context.
4. Run parallel retrieval over:
   - Master Knowledge Base with metadata filters
   - Tenant Knowledge Base, if applicable
   - Structured PostgreSQL data
   - Optional graph retrieval for relationship queries
5. Merge, normalize, and deduplicate retrieved results.
6. Prioritize authoritative and recent versions.
7. Rerank results using BGE Reranker v2-m3.
8. Build a prompt using only approved context.
9. Generate the answer using local Qwen through Ollama.
10. Return a guarded, citation-backed response.

## Guardrails

The system uses multiple guardrail layers.

### Authentication Guardrail

- Keycloak identity validation
- JWT verification

### Authorization Guardrail

- RBAC policies
- Tenant-aware access rules
- Metadata filters
- PostgreSQL Row-Level Security where applicable

### Retrieval Guardrail

- Restrict retrieval scope before vector search
- Enforce SQL filters
- Apply metadata constraints

### Context Guardrail

- Remove prompt-injection content from retrieved documents
- Filter unauthorized context before generation

### Generation Guardrail

- Restrict answers to retrieved evidence
- Require citations for factual responses
- Avoid unsupported conclusions

### Output Guardrail

- Prevent leakage of restricted information
- Validate response format and confidence
- Route low-confidence or policy-sensitive responses for human review

## Why This Architecture Fits the Project

This architecture is suitable for a Port Land Management System because it:

- Uses PostgreSQL and pgvector as a unified data platform.
- Avoids a separate vector database.
- Reflects the Port Authority ownership model through a protected Master Knowledge Base.
- Supports tenant-specific private document repositories.
- Ensures tenant users retrieve only their own information.
- Allows authority users to access information according to RBAC and organizational permissions.
- Combines structured SQL retrieval with semantic document retrieval.
- Supports auditable DO → NO → HOD workflows.

Every retrieved document, generated draft, citation, and decision can be attached to a case and audited throughout the approval process.

## Current Project Structure

```text
port-land-rag/
├── app/
├── data/
├── models/
├── scripts/
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

## Status

- **API Server & Integrated Web UI**: Operational at `http://127.0.0.1:8000` via FastAPI + Uvicorn.
- **RAG Engine Services**: Integrated with PostgreSQL (`pgvector`), Ollama (`qwen2.5:7b`), BGE-M3 Embedder (with HuggingFace fallback), and Guardrails.

## Chat UI Enhancements

- **Copy button** – Appears beneath each AI response once the response is complete. Clicking copies the full response to the clipboard.
- **Download PDF button** – Adjacent to the copy button; generates a PDF of the response and prompts the user to download it.
- **Dynamic loading messages** – While the LLM is generating a reply, the UI cycles through a set of status strings (e.g., “Searching documents…”, “Retrieving chunks…”, “LLM generating response…”, “Combining results…”) every 3‑5 seconds.

## Persistent Chat History

Chat sessions are persisted both locally and on the server:

1. **Client‑side** – The current session is saved in `localStorage` so a page refresh instantly restores the conversation.
2. **Server‑side** – When a session is created, its ID and messages are stored in PostgreSQL via the `/api/sessions` endpoints, allowing retrieval across devices or after long periods.

On page load the app checks `localStorage` for a session ID; if found it fetches the full history from the server and populates the chat window.
