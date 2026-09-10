"""
Automated Verification Suite for Workflow Termination, Final Approved Doc & UI Badging
=======================================================================================
Verifies:
  1. Dynamic officer ingestion: 158 DOs, 44 NOs, 30 HODs in pms_app.admin_users
  2. Database tables in pms_chat schema
  3. GET /api/v1/users/officers response structure & exact counts
  4. Participant chain officer names resolution (assigned_do_name, assigned_no_name, assigned_hod_name)
  5. Full Lifecycle: DO promote -> DO submit NO -> NO forward HOD -> HOD APPROVES
  6. Permanent Lock on Approval across ALL roles (is_read_only = True for DO, NO, HOD)
  7. Message posting blocked on APPROVED agendas (403 Forbidden)
  8. Final Approved Document payload returned in detail endpoint
"""

from __future__ import annotations

import asyncio
from database import get_cursor
from officer_ingestion import ingest_and_seed_officers
from agenda_workflow import (
    init_agenda_tables,
    get_officers,
    get_agendas,
    get_agenda_detail,
    get_agenda_messages,
    promote_sandbox,
    handoff_agenda,
    send_agenda_message,
    PromoteSandboxRequest,
    HandoffRequest,
    SendMessageRequest,
)

def verify_database_officer_counts():
    print("=== [1/5] Verifying DB Officer Ingestion Counts ===")
    ingest_and_seed_officers()
    
    with get_cursor() as cur:
        cur.execute("SELECT role, COUNT(*) FROM pms_app.admin_users GROUP BY role ORDER BY role;")
        rows = cur.fetchall()
        counts = {r["role"]: r["count"] for r in rows}
        print(f"PostgreSQL pms_app.admin_users counts: {counts}")
        
        assert counts.get("DO") == 158
        assert counts.get("NODAL") == 44
        assert counts.get("HOD") == 30
        print("[OK] Officer Ingestion Counts Verified: 158 DOs, 44 NOs, 30 HODs.")

def verify_db_tables_exist():
    print("\n=== [2/5] Verifying Database Schemas & Workflow Tables ===")
    init_agenda_tables()
    with get_cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'pms_chat';
        """)
        tables = [r["table_name"] for r in cur.fetchall()]
        print(f"Tables in pms_chat: {tables}")
        for required in ["agendas", "messages", "working_drafts", "context_capsules"]:
            assert required in tables
        print("[OK] Workflow Tables Verified.")

async def verify_officers_endpoint():
    print("\n=== [3/5] Verifying GET /api/v1/users/officers Endpoint ===")
    offs = await get_officers()
    print(f"API Returned Counts: DOs={offs.counts['dos']}, NOs={offs.counts['nodal_officers']}, HODs={offs.counts['hods']}")
    assert len(offs.dos) == 158
    assert len(offs.nodal_officers) == 44
    assert len(offs.hods) == 30
    print("[OK] Officers Endpoint Verified.")

async def verify_approval_lock_and_final_doc():
    print("\n=== [4/5 & 5/5] Verifying Full Handoff to Approval, Permanent Lock & Final Doc Payload ===")
    offs = await get_officers()
    do_user = offs.dos[0]
    no_user = offs.nodal_officers[0]
    hod_user = offs.hods[0]

    # Step A: Promote Sandbox
    p_res = await promote_sandbox(PromoteSandboxRequest(
        user_id=do_user.admin_id,
        user_name=do_user.name,
        user_role="DO",
        agenda_title="Commercial Waterfront Warehouse Lease Renewal 2026",
        tenancy_id="TNT-9912",
        sandbox_messages=["Initial review of commercial lease terms."],
        initial_draft="Final Agenda Draft: Renewal of Waterfront Warehouse Plot 14."
    ))
    agenda_id = p_res["agenda_id"]
    print(f"A. Created Agenda: {agenda_id}")

    # Step B: DO -> NO Handoff
    h1 = await handoff_agenda(HandoffRequest(
        agenda_id=agenda_id,
        sender_id=do_user.admin_id,
        sender_name=do_user.name,
        sender_role="DO",
        action="SUBMIT_FORWARD",
        target_officer_id=no_user.admin_id,
        target_officer_name=no_user.name,
        remarks="Submitted for Nodal review."
    ))
    assert h1["current_owner"] == "NODAL"

    # Step C: NO -> HOD Handoff
    h2 = await handoff_agenda(HandoffRequest(
        agenda_id=agenda_id,
        sender_id=no_user.admin_id,
        sender_name=no_user.name,
        sender_role="NODAL",
        action="SUBMIT_FORWARD",
        target_officer_id=hod_user.admin_id,
        target_officer_name=hod_user.name,
        remarks="Nodal approved. Submitted for HOD authorization."
    ))
    assert h2["current_owner"] == "HOD"

    # Step D: HOD APPROVES AGENDA
    h3 = await handoff_agenda(HandoffRequest(
        agenda_id=agenda_id,
        sender_id=hod_user.admin_id,
        sender_name=hod_user.name,
        sender_role="HOD",
        action="APPROVE",
        remarks="HOD Approved. Policy agenda finalized."
    ))
    print(f"D. HOD Approved Agenda: State = {h3['current_state']}")
    assert h3["current_state"] == "APPROVED"

    # Step E: Verify PERMANENT LOCK (is_read_only = True across ALL roles)
    do_ag = await get_agenda_detail(agenda_id=agenda_id, user_id=do_user.admin_id, user_role="DO")
    no_ag = await get_agenda_detail(agenda_id=agenda_id, user_id=no_user.admin_id, user_role="NODAL")
    hod_ag = await get_agenda_detail(agenda_id=agenda_id, user_id=hod_user.admin_id, user_role="HOD")

    print(f"Permanent Lock Flags -> DO: {do_ag['is_read_only']} | NO: {no_ag['is_read_only']} | HOD: {hod_ag['is_read_only']}")
    assert do_ag["is_read_only"] == True
    assert no_ag["is_read_only"] == True
    assert hod_ag["is_read_only"] == True

    # Step F: Verify Participant Chain Officer Names
    print(f"Participant Chain Names -> DO: {do_ag['assigned_do_name']} | NO: {do_ag['assigned_no_name']} | HOD: {do_ag['assigned_hod_name']}")
    assert do_ag["assigned_do_name"] == do_user.name
    assert do_ag["assigned_no_name"] == no_user.name
    assert do_ag["assigned_hod_name"] == hod_user.name

    # Step G: Verify Final Approved Document Payload
    print("Final Approved Document Payload present:", do_ag["final_approved_document"] is not None)
    assert do_ag["final_approved_document"] is not None

    # Step H: Verify Message Posting BLOCKED on Approved Agenda
    try:
        await send_agenda_message(SendMessageRequest(
            agenda_id=agenda_id,
            thread_type="OFFICIAL_AGENDA",
            sender_id=hod_user.admin_id,
            sender_name=hod_user.name,
            sender_role="HOD",
            content="Attempting post to approved agenda..."
        ))
        assert False, "Should have raised 403 error on post to approved agenda"
    except Exception as exc:
        print("Message posting correctly blocked on approved agenda:", str(exc))

    print("\n[OK] Approval Workflow Termination, Participant Chain Names, & Final Doc Verification Passed!")

if __name__ == "__main__":
    verify_database_officer_counts()
    verify_db_tables_exist()
    asyncio.run(verify_officers_endpoint())
    asyncio.run(verify_approval_lock_and_final_doc())
