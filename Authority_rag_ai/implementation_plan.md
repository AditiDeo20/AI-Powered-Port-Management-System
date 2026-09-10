# Implement Unified RAG (Document + Database) using LangChain

Based on your request, we will integrate both the existing Document RAG (vector search) and the new Database RAG (Text-to-SQL) into **one unified chatbot**.

This document outlines the architecture for the unified system, how it securely handles confidential data, and the step-by-step implementation plan.

## Overview: The Unified Architecture

To combine both systems into a single chatbot, we will use a **Router Pattern**. The chatbot will first determine the intent of your question and then route it to the correct "expert" system.

### The Unified Workflow

1. **User Query**: The user asks a question in the terminal.
2. **Input Guardrail**: The existing `GuardrailService` checks the input for safety.
3. **The Router (LLM)**: An LLM analyzes the question to decide:
   - *Is this about policies, guidelines, or documents?* → **Route to Document RAG**
   - *Is this about structured data like tenancy details, zones, or billing?* → **Route to Database RAG**
4. **Execution**:
   - If routed to **Document RAG**: It uses your existing `EmbeddingService` and `PostgreSQLService` vector search.
   - If routed to **Database RAG**: It uses LangChain to generate SQL, execute it, and synthesize the result (as outlined below).
5. **Final Response**: The chosen system returns the final answer to the user.

---

## Security & Confidentiality (RESOLVED)

1. **Data Privacy (Confidential Data)**:
   - Because you are using **Ollama** locally, the LLM processes data on your own machine. **Your confidential data (both documents and database records) never leaves your server.**
   - We will configure the system to only expose the whitelisted tables (see below).

2. **Database Modifications (SQL Injection)**:
   - **Resolved**: You have provided the `llm_readonly` user creation script. We will use these credentials (`llm_readonly` / `root`) to connect to the database via LangChain, ensuring the LLM cannot execute destructive commands.

### Whitelisted Tables
The LangChain SQL Agent will be restricted to analyzing ONLY the following tables:
- `plot`
- `plot_action_status`
- `plot_dept_mapping`
- `plot_docs`
- `plot_ext_mstr_plan_zone`
- `plot_ext_reservation`
- `plot_fair_mkt_value`
- `plot_letout_mapping`
- `plot_merge_tbl`
- `plot_mstr_plan_zone`
- `plot_proposed_mstr_plan_zone`
- `plot_proposed_reservation`
- `plot_rmk`
- `plot_rr_land_value`
- `plot_sor_market_value`
- `plot_split_merge`
- `plot_test`
- `plot_zone_details`
- `pmemo`

---

## Proposed Implementation Plan

### 1. Dependencies

#### [MODIFY] `requirements.txt`
- Add `langchain`, `langchain-community`, `langchain-postgres`, and `sqlalchemy`.

### 2. Services

#### [NEW] `app/services/database_agent.py`
- Implements LangChain's `SQLDatabase` and `create_sql_agent` using Ollama.
- Configured to use the `llm_readonly` credentials.
- Configured to restrict schema access to only the whitelisted tables.

#### [NEW] `app/services/router_service.py`
- A new service that uses the LLM to classify user queries and route them to either the existing Document RAG or the new Database RAG.

### 3. Scripts

#### [MODIFY] `scripts/rag_system_chatbot.py`
- Update the main chatbot script to incorporate the `RouterService`.
- The main loop will now be: `Input -> Guardrail -> Router -> (Document RAG OR Database RAG) -> Output`.

## Verification Plan

### Automated Tests
- Test the `RouterService` with various questions to ensure it routes correctly (e.g., "What is the policy?" vs "Count the zones").

### Manual Verification
- Run `scripts/rag_system_chatbot.py`.
- Ask a document question and verify it uses the vector DB.
- Ask a data question and verify it uses the SQL agent using only the whitelisted tables.
