"""
Automated RAG Retrieval, SQL Query Fix & Workflow Accuracy Verification Suite
=============================================================================
Tests:
  1. PostgreSQL SQL Query execution against real `plot` / estate records (factual DB output).
  2. PGVector hybrid search similarity query retrieving policy chunks (parent_text retrieval).
  3. Interactive AI chat in official Agenda thread combining DB facts & RAG chunks.
  4. Workflow integrity rules: Approval lock, participant chain badges, final approved doc view.
"""

from __future__ import annotations

import sys
import asyncio
from pathlib import Path

# Add backend and Authority_rag_ai to path
backend_dir = str(Path(__file__).resolve().parent)
rag_dir = str(Path(__file__).resolve().parent.parent / "Authority_rag_ai")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if rag_dir not in sys.path:
    sys.path.insert(0, rag_dir)

from database import get_cursor
from agenda_workflow import (
    init_agenda_tables,
    get_officers,
    get_agendas,
    get_agenda_detail,
    promote_sandbox,
    handoff_agenda,
    send_agenda_message,
    PromoteSandboxRequest,
    HandoffRequest,
    SendMessageRequest,
)

from app.services.database_agent import DatabaseAgent
from app.services.postgres_service import PostgreSQLService
from app.services.embedding_service import EmbeddingService
from app.services.agent_coordinator import AgentCoordinatorService
from app.services.router_service import RouterService


def test_sql_database_agent():
    print("=== [1/4] Testing Structured SQL Database Agent Accuracy ===")
    agent = DatabaseAgent()
    
    # Query registered plots
    res = agent.query("How many registered plots are in the database and what are their details?")
    print(f"SQL Agent Output:\n{res}\n")
    assert "plot" in res.lower() or "registered" in res.lower() or "summary" in res.lower()

    # Query pmemo table
    res_memo = agent.query("Show latest payment memos and due dates")
    print(f"SQL Agent Memo Output:\n{res_memo}\n")
    assert "memo" in res_memo.lower() or "query" in res_memo.lower()
    print("[OK] SQL Database Agent Accuracy Test Passed.")


def test_pgvector_hybrid_search():
    print("\n=== [2/4] Testing PGVector Hybrid Search & Parent Text Retrieval ===")
    db_service = PostgreSQLService()
    embedder = EmbeddingService()

    query = "land use policy lease tenure breach rules"
    emb = embedder.embed_text(query)
    print(f"Generated Vector Embedding: Dim={len(emb)} (bge-m3 / 1024-dim)")
    assert len(emb) == 1024

    chunks = db_service.hybrid_search(query_embedding=emb, user_id="test_user", top_k=5)
    print(f"Retrieved Chunks Count: {len(chunks)}")
    for i, c in enumerate(chunks, 1):
        p_text = c.get("parent_text") or c.get("text") or ""
        print(f"Chunk #{i}: Table={c.get('source_table')}, Doc={c.get('doc_name')}, Dist={c.get('distance'):.4f}")
        print(f"  Snippet: {p_text[:120]}...\n")
        assert "parent_text" in c
        assert "text" in c

    db_service.close()
    print("[OK] PGVector Hybrid Search Test Passed.")


async def test_interactive_agenda_thread_ai():
    print("\n=== [3/4] Testing Interactive AI Chat in Shared Agenda Thread ===")
    offs = await get_officers()
    do_user = offs.dos[0]

    # Create Agenda
    p_res = await promote_sandbox(PromoteSandboxRequest(
        user_id=do_user.admin_id,
        user_name=do_user.name,
        user_role="DO",
        agenda_title="Commercial Terminal 12A Lease Renewal",
        tenancy_id="TNT-8890",
        initial_draft="Initial draft for Terminal 12A lease renewal."
    ))
    agenda_id = p_res["agenda_id"]

    # Send interactive message in thread
    msg_res = await send_agenda_message(SendMessageRequest(
        agenda_id=agenda_id,
        thread_type="OFFICIAL_AGENDA",
        sender_id=do_user.admin_id,
        sender_name=do_user.name,
        sender_role="DO",
        content="What are the plot details and SOR rate schedule for plot renewal?"
    ))

    print(f"Interactive AI Response:\n{msg_res['ai_response']}\n")
    assert msg_res["ai_response"] is not None
    assert "AI Policy" in msg_res["ai_response"] or "Database" in msg_res["ai_response"]
    print("[OK] Interactive AI Thread Chat Test Passed.")


async def test_workflow_integrity_rules():
    print("\n=== [4/4] Testing Workflow Integrity (Approval Lock, Badges & Final Doc) ===")
    offs = await get_officers()
    do_user = offs.dos[0]
    no_user = offs.nodal_officers[0]
    hod_user = offs.hods[0]

    # Create & Promote
    p_res = await promote_sandbox(PromoteSandboxRequest(
        user_id=do_user.admin_id,
        user_name=do_user.name,
        user_role="DO",
        agenda_title="Port Land Parcel 45B Allocation",
        tenancy_id="TNT-4500",
        initial_draft="Allocation draft for plot 45B."
    ))
    agenda_id = p_res["agenda_id"]

    # DO -> NO
    await handoff_agenda(HandoffRequest(
        agenda_id=agenda_id,
        sender_id=do_user.admin_id,
        sender_name=do_user.name,
        sender_role="DO",
        action="SUBMIT_FORWARD",
        target_officer_id=no_user.admin_id,
        target_officer_name=no_user.name,
        remarks="DO submitted."
    ))

    # NO -> HOD
    await handoff_agenda(HandoffRequest(
        agenda_id=agenda_id,
        sender_id=no_user.admin_id,
        sender_name=no_user.name,
        sender_role="NODAL",
        action="SUBMIT_FORWARD",
        target_officer_id=hod_user.admin_id,
        target_officer_name=hod_user.name,
        remarks="NO forwarded."
    ))

    # HOD APPROVES
    h_app = await handoff_agenda(HandoffRequest(
        agenda_id=agenda_id,
        sender_id=hod_user.admin_id,
        sender_name=hod_user.name,
        sender_role="HOD",
        action="APPROVE",
        remarks="HOD Approved."
    ))

    assert h_app["current_state"] == "APPROVED"

    # Verify Detail Endpoint
    detail = await get_agenda_detail(agenda_id=agenda_id, user_id=do_user.admin_id, user_role="DO")
    assert detail["is_read_only"] == True
    assert detail["assigned_do_name"] == do_user.name
    assert detail["assigned_no_name"] == no_user.name
    assert detail["assigned_hod_name"] == hod_user.name
    assert detail["final_approved_document"] is not None

    print(f"Participant Chain Flow: [DO] {detail['assigned_do_name']} -> [NODAL] {detail['assigned_no_name']} -> [HOD] {detail['assigned_hod_name']}")
    print(f"Final Approved Document Present: {bool(detail['final_approved_document'])}")
    print("[OK] Workflow Integrity & Approval Lock Test Passed.")


if __name__ == "__main__":
    init_agenda_tables()
    test_sql_database_agent()
    test_pgvector_hybrid_search()
    asyncio.run(test_interactive_agenda_thread_ai())
    asyncio.run(test_workflow_integrity_rules())
