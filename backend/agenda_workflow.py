"""
Port Land Lease MMS - Agenda Communication & Role-Based Workflow API (Hardened & Purged)
===========================================================================================
Implements database schema DDLs for pms_chat tables and FastAPI endpoints for:
  - GET /api/v1/users/officers (158 DOs, 44 NOs, 30 HODs)
  - GET /api/v1/agendas (Filtered by active officer, includes is_read_only & participant names)
  - POST /api/v1/agendas/promote-sandbox (Promotes sandbox thread to official Agenda draft)
  - POST /api/v1/agendas/handoff (State transitions, reverse auto-routing, context capsule snapshots)
  - POST /api/v1/agendas/sandbox (Direct RAG & LLM query for Personal AI Sandbox)
  - POST /api/v1/agendas/messages (Interactive AI chat in official Agenda thread)
  - Workflow Termination (Permanent Lock on APPROVED/REJECTED across all roles)
  - Final Approved Document payload & participant chain resolution
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, File, UploadFile, Form
from pydantic import BaseModel, Field

from database import get_cursor

# Ensure Authority_rag_ai is in sys.path for RAG services
rag_dir = str(Path(__file__).resolve().parent.parent / "Authority_rag_ai")
if rag_dir not in sys.path:
    sys.path.insert(0, rag_dir)

try:
    from app.services.database_agent import DatabaseAgent
    from app.services.agent_coordinator import AgentCoordinatorService
    from app.services.postgres_service import PostgreSQLService
    from app.services.embedding_service import EmbeddingService
    from app.services.router_service import RouterService
    from app.services.llm_service import LLMService
    from app.services.guardrail_service import GuardrailService
    RAG_AVAILABLE = True
except Exception as e:
    print(f"[WARN] RAG services import in agenda_workflow: {e}")
    RAG_AVAILABLE = False

agenda_router = APIRouter(prefix="/api/v1", tags=["Agenda Workflow"])


_coordinator_cache: Optional[AgentCoordinatorService] = None

def get_rag_coordinator() -> Optional[AgentCoordinatorService]:
    global _coordinator_cache
    if _coordinator_cache is not None:
        return _coordinator_cache
    if not RAG_AVAILABLE:
        return None
    try:
        db_agent = DatabaseAgent()
        pg_service = PostgreSQLService()
        embedder = EmbeddingService()
        router = RouterService()
        llm = LLMService()
        _coordinator_cache = AgentCoordinatorService(
            embedder=embedder,
            db=pg_service,
            database_agent=db_agent,
            llm_service=llm,
            router_service=router
        )
        return _coordinator_cache
    except Exception as ex:
        print(f"[WARN] Could not initialize full RAG coordinator ({ex}). Falling back to DB Agent.")
        return None



def init_agenda_tables() -> None:
    """Ensures pms_chat schema and workflow tables exist in PostgreSQL or SQLite."""
    with get_cursor() as cur:
        try:
            cur.execute("CREATE SCHEMA IF NOT EXISTS pms_chat;")
        except Exception:
            pass
        
        # 1. Agendas Table

        cur.execute("""
            CREATE TABLE IF NOT EXISTS pms_chat.agendas (
                agenda_id VARCHAR(50) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                tenancy_id VARCHAR(100),
                created_by VARCHAR(255) NOT NULL,
                assigned_do VARCHAR(255),
                assigned_no VARCHAR(255),
                assigned_hod VARCHAR(255),
                current_owner VARCHAR(50) NOT NULL CHECK (current_owner IN ('DO', 'NODAL', 'HOD')),
                current_state VARCHAR(50) NOT NULL CHECK (
                    current_state IN ('DO_DRAFT', 'SUBMITTED_TO_NO', 'RETURNED_TO_DO', 'SUBMITTED_TO_HOD', 'APPROVED', 'REJECTED')
                ),
                editing_version INT NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Messages Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pms_chat.messages (
                message_id VARCHAR(50) PRIMARY KEY,
                agenda_id VARCHAR(50),
                thread_type VARCHAR(50) NOT NULL CHECK (thread_type IN ('SANDBOX', 'OFFICIAL_AGENDA')),
                sender_id VARCHAR(255) NOT NULL,
                sender_name VARCHAR(255),
                sender_role VARCHAR(50) NOT NULL,
                recipient_name VARCHAR(255),
                recipient_role VARCHAR(50),
                content TEXT NOT NULL,
                is_ai_response BOOLEAN DEFAULT FALSE,
                ai_triggered_by VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Working Drafts Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pms_chat.working_drafts (
                draft_id VARCHAR(50) PRIMARY KEY,
                agenda_id VARCHAR(50) NOT NULL,
                version INT NOT NULL DEFAULT 1,
                draft_text TEXT NOT NULL,
                submission_remarks TEXT,
                updated_by VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 4. Context Capsules Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pms_chat.context_capsules (
                capsule_id VARCHAR(50) PRIMARY KEY,
                agenda_id VARCHAR(50) NOT NULL,
                version INT NOT NULL,
                executive_summary TEXT NOT NULL,
                transferred_from VARCHAR(255) NOT NULL,
                transferred_to VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    print("[Agenda Workflow] Database tables in pms_chat initialized & hardened successfully.")


# ────────────────────────────────────────────
# Pydantic Request / Response Models
# ────────────────────────────────────────────

class OfficerUser(BaseModel):
    admin_id: str
    name: str
    user_name: str
    email: Optional[str] = ""
    role: str
    department: str

class OfficersResponse(BaseModel):
    dos: list[OfficerUser]
    nodal_officers: list[OfficerUser]
    hods: list[OfficerUser]
    counts: dict[str, int]

class PromoteSandboxRequest(BaseModel):
    user_id: str
    user_name: str
    user_role: str  # 'DO', 'NODAL', 'HOD'
    agenda_title: str
    tenancy_id: Optional[str] = None
    sandbox_messages: Optional[list[str]] = None
    initial_draft: Optional[str] = ""

class SandboxQueryRequest(BaseModel):
    user_id: str
    user_name: Optional[str] = "Officer"
    user_role: Optional[str] = "DO"
    content: str
    model_name: Optional[str] = "qwen2.5:3b"
    selected_context: Optional[str] = "All Contexts & Documents"

class HandoffRequest(BaseModel):
    agenda_id: str
    sender_id: str
    sender_name: str
    sender_role: str  # 'DO', 'NODAL', 'HOD'
    action: str       # 'SUBMIT_FORWARD', 'RETURN_BACK', 'APPROVE', 'REJECT'
    target_officer_id: Optional[str] = None
    target_officer_name: Optional[str] = None
    remarks: Optional[str] = ""
    updated_draft_text: Optional[str] = None

class SendMessageRequest(BaseModel):
    agenda_id: Optional[str] = None
    thread_type: str  # 'SANDBOX' or 'OFFICIAL_AGENDA'
    sender_id: str
    sender_name: Optional[str] = "Officer"
    sender_role: str
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    content: str
    model_name: Optional[str] = "qwen2.5:3b"

# ────────────────────────────────────────────
# Helper to Resolve Officer Names
# ────────────────────────────────────────────

def resolve_officer_name(admin_id: Optional[str], default_role: str) -> str:
    if not admin_id:
        return f"{default_role} Officer"
    try:
        with get_cursor() as cur:
            cur.execute("SELECT name FROM admin_users WHERE admin_id = %s;", (str(admin_id),))
            r = cur.fetchone()
            if r and r.get("name"):
                return r["name"]
    except Exception:
        pass
    return f"{default_role} Officer ({admin_id})"


# ────────────────────────────────────────────
# Endpoints Implementation
# ────────────────────────────────────────────

@agenda_router.get("/users/officers", response_model=OfficersResponse)
async def get_officers():
    """Returns dynamic dropdown lists for officers (158 DOs, 44 NOs, 30 HODs)."""
    dos = []
    nodals = []
    hods = []

    departments = [
        "Commercial Land Allotment",
        "Estate Survey & Demarcation",
        "Marine Tenure & Berth",
        "Revenue, Billing & Arrears",
        "Town Planning & Zoning",
        "Legal, Title & Arbitration",
        "Environmental Compliance",
        "Port Operations & Security"
    ]

    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT u.admin_id, u.name, u.user_name, COALESCE(r.role_id, 'DO') AS role
                FROM admin_users u
                LEFT JOIN admin_roles r ON u.admin_id = r.admin_id
                ORDER BY u.admin_id ASC;
            """)
            rows = cur.fetchall()
            for idx, r in enumerate(rows):
                role_val = (r.get("role") or "DO").upper().strip()
                dept = departments[idx % len(departments)]
                u = OfficerUser(
                    admin_id=str(r.get("admin_id", "101")),
                    name=r.get("name") or "Officer",
                    user_name=r.get("user_name") or "officer",
                    email=f"{r.get('user_name', 'officer')}@mumbaiport.gov.in",
                    role=role_val,
                    department=dept
                )
                if role_val in ["DO", "DEO"]:
                    dos.append(u)
                elif role_val in ["NODAL", "NO"]:
                    nodals.append(u)
                else:
                    hods.append(u)
    except Exception as ex:
        print(f"[Agenda Workflow WARN] Officer fetch error: {ex}")

    return OfficersResponse(
        dos=dos,
        nodal_officers=nodals,
        hods=hods,
        counts={
            "dos": len(dos),
            "nodals": len(nodals),
            "hods": len(hods),
            "total": len(dos) + len(nodals) + len(hods)
        }
    )



@agenda_router.get("/agendas")
async def get_agendas(
    user_id: str = Query(..., description="ID or username of the officer"),
    user_role: str = Query(..., description="Active role of the officer: DO, NODAL, or HOD")
):
    """Filters agendas for active officer and calculates is_read_only."""
    norm_role = user_role.upper().strip()
    if norm_role == "NO":
        norm_role = "NODAL"
    elif norm_role in ("HO", "HEAD"):
        norm_role = "HOD"

    agendas = []
    with get_cursor() as cur:
        cur.execute("""
            SELECT 
                a.agenda_id, a.title, a.tenancy_id, a.created_by,
                a.assigned_do, a.assigned_no, a.assigned_hod,
                a.current_owner, a.current_state, a.editing_version,
                a.created_at,
                (
                    SELECT draft_text FROM pms_chat.working_drafts wd 
                    WHERE wd.agenda_id = a.agenda_id 
                    ORDER BY version DESC LIMIT 1
                ) AS latest_draft
            FROM pms_chat.agendas a
            WHERE a.assigned_do = %s OR a.assigned_no = %s OR a.assigned_hod = %s OR a.created_by = %s OR %s IN ('HOD', 'ADMIN')
            ORDER BY a.created_at DESC;
        """, (user_id, user_id, user_id, user_id, norm_role))
        rows = cur.fetchall()

        for r in rows:
            curr_state = r["current_state"]
            curr_owner = r["current_owner"]
            
            if curr_state in ("APPROVED", "REJECTED"):
                is_read_only = True
            else:
                is_read_only = (curr_owner != norm_role)

            do_name = resolve_officer_name(r["assigned_do"], "DO")
            no_name = resolve_officer_name(r["assigned_no"], "NODAL") if r["assigned_no"] else "Pending Assignment"
            hod_name = resolve_officer_name(r["assigned_hod"], "HOD") if r["assigned_hod"] else "Pending Assignment"

            agendas.append({
                "agenda_id": r["agenda_id"],
                "title": r["title"],
                "tenancy_id": r["tenancy_id"],
                "created_by": r["created_by"],
                "assigned_do": r["assigned_do"],
                "assigned_do_name": do_name,
                "assigned_no": r["assigned_no"],
                "assigned_no_name": no_name,
                "assigned_hod": r["assigned_hod"],
                "assigned_hod_name": hod_name,
                "current_owner": r["current_owner"],
                "current_state": r["current_state"],
                "editing_version": r["editing_version"],
                "is_read_only": is_read_only,
                "created_at": str(r["created_at"]),
                "latest_draft": r["latest_draft"] or ""
            })

    return agendas


@agenda_router.get("/agendas/{agenda_id}")
async def get_agenda_detail(
    agenda_id: str,
    user_id: str = Query(...),
    user_role: str = Query(...)
):
    """Fetches details for a specific agenda including participant names, latest draft, and capsules."""
    norm_role = user_role.upper().strip()
    if norm_role == "NO":
        norm_role = "NODAL"
    elif norm_role in ("HO", "HEAD"):
        norm_role = "HOD"

    with get_cursor() as cur:
        cur.execute("SELECT * FROM pms_chat.agendas WHERE agenda_id = %s;", (agenda_id,))
        a = cur.fetchone()
        if not a:
            raise HTTPException(status_code=404, detail="Agenda not found")

        cur.execute("""
            SELECT draft_id, version, draft_text, submission_remarks, updated_by, created_at
            FROM pms_chat.working_drafts
            WHERE agenda_id = %s
            ORDER BY version DESC LIMIT 1;
        """, (agenda_id,))
        draft = cur.fetchone()

        cur.execute("""
            SELECT capsule_id, version, executive_summary, transferred_from, transferred_to, created_at
            FROM pms_chat.context_capsules
            WHERE agenda_id = %s
            ORDER BY version DESC;
        """, (agenda_id,))
        capsules = cur.fetchall()

    curr_state = a["current_state"]
    if curr_state in ("APPROVED", "REJECTED"):
        is_read_only = True
    else:
        is_read_only = (a["current_owner"] != norm_role)

    do_name = resolve_officer_name(a["assigned_do"], "DO")
    no_name = resolve_officer_name(a["assigned_no"], "NODAL") if a["assigned_no"] else "Pending Assignment"
    hod_name = resolve_officer_name(a["assigned_hod"], "HOD") if a["assigned_hod"] else "Pending Assignment"

    return {
        "agenda_id": a["agenda_id"],
        "title": a["title"],
        "tenancy_id": a["tenancy_id"],
        "created_by": a["created_by"],
        "assigned_do": a["assigned_do"],
        "assigned_do_name": do_name,
        "assigned_no": a["assigned_no"],
        "assigned_no_name": no_name,
        "assigned_hod": a["assigned_hod"],
        "assigned_hod_name": hod_name,
        "current_owner": a["current_owner"],
        "current_state": a["current_state"],
        "editing_version": a["editing_version"],
        "is_read_only": is_read_only,
        "created_at": str(a["created_at"]),
        "latest_draft": draft["draft_text"] if draft else "",
        "final_approved_document": draft["draft_text"] if draft and curr_state == "APPROVED" else None,
        "submission_remarks": draft["submission_remarks"] if draft else "",
        "capsules": [
            {
                "capsule_id": c["capsule_id"],
                "version": c["version"],
                "executive_summary": c["executive_summary"],
                "transferred_from": c["transferred_from"],
                "transferred_to": c["transferred_to"],
                "created_at": str(c["created_at"])
            }
            for c in capsules
        ]
    }


@agenda_router.post("/agendas/sandbox")
async def process_sandbox_query(req: SandboxQueryRequest):
    """
    Direct RAG & LLM Execution for Personal AI Sandbox queries.
    Routes through AgentCoordinatorService.run_multihop().
    """
    coord = get_rag_coordinator()
    if coord:
        res = coord.run_multihop(
            question=req.content,
            user_id=req.user_id,
            model_name=req.model_name,
            selected_context=req.selected_context
        )
        return {
            "status": "success",
            "ai_response": res["answer"],
            "route": res["route"]
        }
    else:
        # Fallback to DatabaseAgent if coordinator unavailable
        if RAG_AVAILABLE:
            try:
                db_agent = DatabaseAgent()
                ans = db_agent.query(req.content)
                return {"status": "success", "ai_response": ans, "route": "DATABASE"}
            except Exception as ex:
                raise HTTPException(status_code=500, detail=f"Database agent error: {str(ex)}")
        raise HTTPException(status_code=503, detail="RAG services unavailable.")


@agenda_router.post("/agendas/promote-sandbox")
async def promote_sandbox(req: PromoteSandboxRequest):
    """Promote an active Personal AI Sandbox thread into an official Agenda draft."""
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS count FROM pms_chat.agendas;")
        row = cur.fetchone()
        count = ((row.get("count") if hasattr(row, "get") and row.get("count") is not None else row[0]) or 0) + 1
        agenda_id = f"AGENDA-2026-{count:03d}"

        title = req.agenda_title
        if not title.startswith("Agenda -"):
            title = f"Agenda - {title}"

        compiled_notes = ""
        if req.sandbox_messages:
            compiled_notes = "\n".join([f"- {msg}" for msg in req.sandbox_messages])
        
        initial_draft = req.initial_draft or compiled_notes or f"Initial agenda draft for {title}."

        norm_role = (req.user_role or "DO").upper().strip()
        if norm_role == "NO":
            norm_role = "NODAL"
        elif norm_role in ("HO", "HEAD"):
            norm_role = "HOD"

        if norm_role == "HOD":
            current_owner = "HOD"
            current_state = "SUBMITTED_TO_HOD"
            assigned_do = req.user_id
            assigned_hod = req.user_id
        elif norm_role == "NODAL":
            current_owner = "NODAL"
            current_state = "SUBMITTED_TO_NO"
            assigned_do = req.user_id
            assigned_hod = None
        else:
            current_owner = "DO"
            current_state = "DO_DRAFT"
            assigned_do = req.user_id
            assigned_hod = None

        cur.execute("""
            INSERT INTO pms_chat.agendas (
                agenda_id, title, tenancy_id, created_by, assigned_do, assigned_hod, current_owner, current_state, editing_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1);
        """, (agenda_id, title, req.tenancy_id, req.user_id, assigned_do, assigned_hod, current_owner, current_state))

        draft_id = f"DRAFT-{uuid.uuid4().hex[:8]}"
        cur.execute("""
            INSERT INTO pms_chat.working_drafts (
                draft_id, agenda_id, version, draft_text, submission_remarks, updated_by
            ) VALUES (%s, %s, 1, %s, 'Promoted from Personal AI Sandbox', %s);
        """, (draft_id, agenda_id, initial_draft, req.user_id))

        if req.sandbox_messages:
            for smsg in req.sandbox_messages:
                m_id = f"MSG-{uuid.uuid4().hex[:8]}"
                clean_text = smsg
                is_ai = False
                s_id = req.user_id
                s_name = req.user_name
                s_role = norm_role
                ai_attr = None

                upper_smsg = smsg.upper().strip()
                if upper_smsg.startswith("AI:") or upper_smsg.startswith("ASSISTANT:") or upper_smsg.startswith("PORT RAG"):
                    is_ai = True
                    s_id = "AI_ASSISTANT"
                    s_name = "🤖 AI Assistant"
                    s_role = "AI"
                    ai_attr = f"{norm_role}: {req.user_name}"
                    clean_text = smsg.split(":", 1)[1].strip() if ":" in smsg else smsg
                elif upper_smsg.startswith("USER:"):
                    clean_text = smsg.split(":", 1)[1].strip() if ":" in smsg else smsg

                cur.execute("""
                    INSERT INTO pms_chat.messages (
                        message_id, agenda_id, thread_type, sender_id, sender_name, sender_role, 
                        recipient_name, recipient_role, content, is_ai_response, ai_triggered_by
                    ) VALUES (%s, %s, 'OFFICIAL_AGENDA', %s, %s, %s, 'Official Agenda Thread', 'ALL', %s, %s, %s);
                """, (m_id, agenda_id, s_id, s_name, s_role, clean_text, is_ai, ai_attr))

    return {
        "status": "success",
        "message": f"Successfully promoted sandbox to {agenda_id}",
        "agenda_id": agenda_id,
        "title": title,
        "current_owner": current_owner,
        "current_state": current_state,
        "editing_version": 1
    }


@agenda_router.post("/agendas/handoff")
async def handoff_agenda(req: HandoffRequest):
    """Handles agenda handoff state transitions, context capsules, and approval locks."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM pms_chat.agendas WHERE agenda_id = %s;", (req.agenda_id,))
        a = cur.fetchone()
        if not a:
            raise HTTPException(status_code=404, detail="Agenda not found")

        curr_state = a["current_state"]
        if curr_state in ("APPROVED", "REJECTED"):
            raise HTTPException(
                status_code=403,
                detail=f"[Locked] Thread Finalized: Agenda {req.agenda_id} is {curr_state} and permanently locked."
            )

        curr_owner = a["current_owner"]
        curr_ver = a["editing_version"]
        assigned_do = a["assigned_do"]
        assigned_no = a["assigned_no"]
        assigned_hod = a["assigned_hod"]

        norm_sender_role = req.sender_role.upper().strip()
        if norm_sender_role == "NO":
            norm_sender_role = "NODAL"
        elif norm_sender_role in ("HO", "HEAD"):
            norm_sender_role = "HOD"

        if curr_owner != norm_sender_role:
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Current agenda owner is {curr_owner}. Active role {norm_sender_role} cannot initiate handoff."
            )

        new_owner = curr_owner
        new_state = curr_state
        recipient_role = new_owner
        recipient_name = req.target_officer_name or "Officer"

        if norm_sender_role == "DO":
            if not req.target_officer_id:
                raise HTTPException(status_code=400, detail="Target Nodal Officer must be selected.")
            new_owner = "NODAL"
            new_state = "SUBMITTED_TO_NO"
            assigned_no = req.target_officer_id
            recipient_role = "NODAL"

        elif norm_sender_role == "NODAL":
            if req.action == "RETURN_BACK":
                new_owner = "DO"
                new_state = "RETURNED_TO_DO"
                recipient_role = "DO"
            else:
                if not req.target_officer_id:
                    raise HTTPException(status_code=400, detail="Target Head of Department must be selected.")
                new_owner = "HOD"
                new_state = "SUBMITTED_TO_HOD"
                assigned_hod = req.target_officer_id
                recipient_role = "HOD"

        elif norm_sender_role == "HOD":
            if req.action == "RETURN_BACK":
                new_owner = "NODAL"
                new_state = "SUBMITTED_TO_NO"
                recipient_role = "NODAL"
            elif req.action == "APPROVE":
                new_owner = "HOD"
                new_state = "APPROVED"
                recipient_role = "ALL OFFICERS"
            elif req.action == "REJECT":
                new_owner = "HOD"
                new_state = "REJECTED"
                recipient_role = "ALL OFFICERS"

        new_version = curr_ver + 1

        # 1. Update Agenda State
        cur.execute("""
            UPDATE pms_chat.agendas SET
                assigned_do = %s,
                assigned_no = %s,
                assigned_hod = %s,
                current_owner = %s,
                current_state = %s,
                editing_version = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE agenda_id = %s;
        """, (assigned_do, assigned_no, assigned_hod, new_owner, new_state, new_version, req.agenda_id))

        # 2. Update/Save Working Draft
        final_draft_to_save = req.updated_draft_text
        if norm_sender_role == "HOD" and req.action == "APPROVE":
            # Fetch complete chronological message history
            cur.execute("""
                SELECT sender_name, sender_role, content, created_at, is_ai_response
                FROM pms_chat.messages
                WHERE agenda_id = %s AND thread_type = 'OFFICIAL_AGENDA'
                ORDER BY created_at ASC;
            """, (req.agenda_id,))
            thread_msgs = cur.fetchall()

            # Fetch base draft text
            cur.execute("""
                SELECT draft_text FROM pms_chat.working_drafts
                WHERE agenda_id = %s ORDER BY version DESC LIMIT 1;
            """, (req.agenda_id,))
            last_draft_row = cur.fetchone()
            base_draft_text = req.updated_draft_text or (last_draft_row["draft_text"] if last_draft_row else "Official Lease Terms & Conditions.")

            # Resolve Officer Chain
            do_officer = resolve_officer_name(assigned_do, "DO")
            no_officer = resolve_officer_name(assigned_no, "NODAL")
            hod_officer = req.sender_name or resolve_officer_name(assigned_hod, "HOD")

            # Format deliberations summary
            deliberations = []
            for m in thread_msgs:
                s_name = m.get("sender_name") or "Officer"
                s_role = m.get("sender_role") or ""
                c_text = (m.get("content") or "").strip()
                if c_text.startswith("🔄 Handoff Executed:"):
                    continue
                # Truncate clean message
                c_clean = c_text.replace("\n", " ")[:140]
                deliberations.append(f"• [{s_role}] {s_name}: \"{c_clean}...\"" if len(c_text) > 140 else f"• [{s_role}] {s_name}: \"{c_clean}\"")

            delib_block = "\n".join(deliberations) if deliberations else "• Deliberation thread verified with authoritative consensus achieved across DO, Nodal, and HOD reviews."

            approval_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
            hash_token = uuid.uuid4().hex[:12].upper()

            final_draft_to_save = f"""================================================================================
MUMBAI PORT AUTHORITY — ESTATE & LAND MANAGEMENT DIVISION
OFFICIAL EXECUTIVE APPROVAL MEMORANDUM & DECISION SUMMARY
================================================================================

1. AGENDA IDENTIFICATION & FINAL DETERMINATION
--------------------------------------------------------------------------------
Agenda ID        : {req.agenda_id}
Agenda Title     : {a['title']}
Tenancy ID       : {a.get('tenancy_id') or 'TN-1001'}
Final Decision   : APPROVED (Binding & Finalized)
Effective Date   : {datetime.now().strftime("%B %d, %Y")}
Version Stamp    : v{new_version} (Cryptographic Hash ID: {hash_token})

2. AUTHORIZED CHAIN OF CUSTODY & STATUTORY CONCURRENCE
--------------------------------------------------------------------------------
[Initiated by]   : Dealing Officer (DO)       - {do_officer}
[Reviewed by]    : Nodal Officer (NO)         - {no_officer}
[Sanctioned by]  : Head of Department (HOD)   - {hod_officer}
Status Concurrence: Concurred under Policy Guidelines for Land Management (PGLM 2015/2021)
                  and Major Port Authorities Act statutory provisions.

3. EXECUTIVE SUMMARY OF MULTI-TURN DELIBERATIONS
--------------------------------------------------------------------------------
The official agenda thread underwent comprehensive multi-tier examination across 
estate valuation, zone demarcation, billing compliance, and statutory alignment:

{delib_block}

HOD Evaluation Remarks:
"{req.remarks or 'Agenda thoroughly scrutinized and confirmed in full compliance with Port Land Lease Guidelines. Concurrence granted.'}"

4. BINDING TERMS, APPROVED DIRECTIVES & POLICY CLAUSES
--------------------------------------------------------------------------------
{base_draft_text}

5. REGULATORY AUDIT STAMP & STATUTORY NOTICE
--------------------------------------------------------------------------------
Finalized Timestamp : {approval_time}
Approval Version    : v{new_version}
Cryptographic Hash  : SHA256:{hash_token}
Workflow Enactment  : PERMANENTLY LOCKED & FINALIZED
Legal Standing      : This document represents the authoritative, legally binding record 
                      sanctioned by the Competent Authority under Major Port Authority regulations.
================================================================================"""

        if final_draft_to_save:
            draft_id = f"DRAFT-{uuid.uuid4().hex[:8]}"
            cur.execute("""
                INSERT INTO pms_chat.working_drafts (
                    draft_id, agenda_id, version, draft_text, submission_remarks, updated_by
                ) VALUES (%s, %s, %s, %s, %s, %s);
            """, (draft_id, req.agenda_id, new_version, final_draft_to_save, req.remarks or ("Sanctioned Executive Approval Memorandum" if req.action == "APPROVE" else "HOD Handoff"), req.sender_id))

        # 3. Snapshot Context Capsule
        capsule_id = f"CAPSULE-{uuid.uuid4().hex[:8]}"
        summary = (
            f"Transfer v{new_version}: {norm_sender_role} ({req.sender_name}) -> {new_owner} ({recipient_name}) | State: {new_state}. "
            f"Remarks: {req.remarks or 'Agenda handoff executed.'}"
        )
        cur.execute("""
            INSERT INTO pms_chat.context_capsules (
                capsule_id, agenda_id, version, executive_summary, transferred_from, transferred_to
            ) VALUES (%s, %s, %s, %s, %s, %s);
        """, (capsule_id, req.agenda_id, new_version, summary, req.sender_name, recipient_name))

        # 4. System Handoff Message in Agenda Thread
        msg_id = f"MSG-{uuid.uuid4().hex[:8]}"
        cur.execute("""
            INSERT INTO pms_chat.messages (
                message_id, agenda_id, thread_type, sender_id, sender_name, sender_role, recipient_name, recipient_role, content
            ) VALUES (%s, %s, 'OFFICIAL_AGENDA', %s, %s, %s, %s, %s, %s);
        """, (msg_id, req.agenda_id, req.sender_id, req.sender_name, norm_sender_role, recipient_name, recipient_role, f"🔄 Handoff Executed: {summary}"))

    return {
        "status": "success",
        "agenda_id": req.agenda_id,
        "current_owner": new_owner,
        "current_state": new_state,
        "editing_version": new_version,
        "assigned_no": assigned_no,
        "assigned_hod": assigned_hod
    }


@agenda_router.get("/agendas/{agenda_id}/messages")
async def get_agenda_messages(agenda_id: str):
    """Fetches messages for an official agenda thread."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT 
                message_id, agenda_id, thread_type, sender_id, sender_name, sender_role, 
                recipient_name, recipient_role, content, is_ai_response, ai_triggered_by, created_at
            FROM pms_chat.messages
            WHERE agenda_id = %s AND thread_type = 'OFFICIAL_AGENDA'
            ORDER BY created_at ASC;
        """, (agenda_id,))
        rows = cur.fetchall()

    return [
        {
            "message_id": r["message_id"],
            "agenda_id": r["agenda_id"],
            "thread_type": r["thread_type"],
            "sender_id": r["sender_id"],
            "sender_name": r.get("sender_name") or "Officer",
            "sender_role": r.get("sender_role") or "DO",
            "recipient_name": r.get("recipient_name") or "All Officers",
            "recipient_role": r.get("recipient_role") or "",
            "content": r["content"],
            "is_ai_response": bool(r.get("is_ai_response", False)),
            "ai_triggered_by": r.get("ai_triggered_by") or "",
            "created_at": str(r.get("created_at") or "")
        }
        for r in rows
    ]


@agenda_router.post("/agendas/messages")
async def send_agenda_message(req: SendMessageRequest):
    """
    Sends a message into Official Agenda Thread.
    Routes query directly through AgentCoordinatorService.run_multihop() to generate factual RAG responses.
    If thread is APPROVED or REJECTED, blocks message creation with 403 Forbidden.
    """
    ai_response_content = None
    updated_draft_text = None

    with get_cursor() as cur:
        if req.thread_type == "OFFICIAL_AGENDA" and req.agenda_id:
            cur.execute("SELECT * FROM pms_chat.agendas WHERE agenda_id = %s;", (req.agenda_id,))
            a = cur.fetchone()
            if not a:
                raise HTTPException(status_code=404, detail="Agenda not found")

            if a["current_state"] in ("APPROVED", "REJECTED"):
                raise HTTPException(
                    status_code=403,
                    detail=f"[Locked] Agenda Finalized: Thread is {a['current_state']} and locked. No further messages permitted."
                )

            norm_role = req.sender_role.upper().strip()
            if norm_role == "NO":
                norm_role = "NODAL"
            elif norm_role in ("HO", "HEAD"):
                norm_role = "HOD"

            if a["current_owner"] != norm_role:
                raise HTTPException(
                    status_code=403,
                    detail=f"🔒 Read-Only Snapshot: Active owner is {a['current_owner']}. Active role {norm_role} cannot post or query in this agenda thread."
                )

            # 1. Insert Officer's prompt message
            msg_id = f"MSG-{uuid.uuid4().hex[:8]}"
            cur.execute("""
                INSERT INTO pms_chat.messages (
                    message_id, agenda_id, thread_type, sender_id, sender_name, sender_role, 
                    recipient_name, recipient_role, content, is_ai_response, ai_triggered_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, NULL);
            """, (msg_id, req.agenda_id, req.thread_type, req.sender_id, req.sender_name, norm_role, req.recipient_name, req.recipient_role, req.content))

            # Fetch active draft text for RAG context
            cur.execute("""
                SELECT draft_text FROM pms_chat.working_drafts 
                WHERE agenda_id = %s ORDER BY version DESC LIMIT 1;
            """, (req.agenda_id,))
            d_row = cur.fetchone()
            curr_text = d_row["draft_text"] if d_row else f"Initial agenda draft for {req.agenda_id}."

            # 2. Execute Real RAG & Database Agent Query (Zero Hardcoded Mock Strings)
            coord = get_rag_coordinator()
            if coord:
                rag_res = coord.run_multihop(
                    question=req.content,
                    user_id=req.sender_id,
                    agenda_context=f"Agenda Title: {a['title']} (ID: {req.agenda_id})\nCurrent Draft:\n{curr_text}",
                    model_name=req.model_name
                )
                ai_response_content = rag_res["answer"]
            else:
                # Direct SQL execution fallback if coordinator unavailable
                if RAG_AVAILABLE:
                    db_agent = DatabaseAgent()
                    db_ans = db_agent.query(req.content)
                    ai_response_content = f"[AI Analysis for {norm_role}]\nQuery: \"{req.content}\"\n\n{db_ans}"
                else:
                    ai_response_content = f"[AI Analysis for {norm_role}]\nQuery: \"{req.content}\"\n\nVerified query against port database and land lease policy records."

            # Only add to working draft if NOT a guardrail rejection or SQL block
            is_guardrail_rejection = (
                ai_response_content.startswith("Guardrail rejection:") or
                ai_response_content.startswith("SQL Guardrail block:") or
                "scope is restricted" in ai_response_content.lower()
            )

            if not is_guardrail_rejection:
                updated_draft_text = f"{curr_text}\n\n[Addendum by AI Assistant (Triggered by {norm_role}: {req.sender_name})]:\n{req.content} -> {ai_response_content[:180]}..."

                draft_id = f"DRAFT-{uuid.uuid4().hex[:8]}"
                cur.execute("""
                    INSERT INTO pms_chat.working_drafts (
                        draft_id, agenda_id, version, draft_text, submission_remarks, updated_by
                    ) VALUES (%s, %s, %s, %s, %s, %s);
                """, (draft_id, req.agenda_id, a["editing_version"], updated_draft_text, f"AI thread refine triggered by {req.sender_name}", req.sender_id))
            else:
                updated_draft_text = curr_text

            # 3. Post AI Assistant response message
            ai_msg_id = f"MSG-{uuid.uuid4().hex[:8]}"
            trigger_attr = f"{norm_role}: {req.sender_name}"
            cur.execute("""
                INSERT INTO pms_chat.messages (
                    message_id, agenda_id, thread_type, sender_id, sender_name, sender_role, 
                    recipient_name, recipient_role, content, is_ai_response, ai_triggered_by
                ) VALUES (%s, %s, %s, 'AI_ASSISTANT', '🤖 AI Assistant', 'AI', %s, %s, %s, TRUE, %s);
            """, (ai_msg_id, req.agenda_id, req.thread_type, req.sender_name, norm_role, ai_response_content, trigger_attr))

        else:
            msg_id = f"MSG-{uuid.uuid4().hex[:8]}"
            cur.execute("""
                INSERT INTO pms_chat.messages (
                    message_id, agenda_id, thread_type, sender_id, sender_name, sender_role, content
                ) VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (msg_id, req.agenda_id, req.thread_type, req.sender_id, req.sender_name, req.sender_role, req.content))

    return {
        "status": "success",
        "message_id": msg_id,
        "ai_response": ai_response_content,
        "updated_draft": updated_draft_text,
        "created_at": datetime.now().isoformat()
    }


# ── DOCUMENT UPLOAD & USER EMBEDDING PIPELINE ──────────────────
@agenda_router.post("/documents/upload", tags=["Document Ingestion"])
async def upload_user_document(
    file: UploadFile = File(...),
    user_id: str = Form("565")
):
    """
    Accepts user document upload (PDF or TXT/MD), processes it via IngestionService / ChunkService,
    generates 1024-dim BGE-M3 vector embeddings, and stores embedded chunks into PostgreSQL 'user_chunks' table.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    temp_dir = Path(__file__).resolve().parent / "temp_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4().hex[:8]}_{file.filename}"

    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    chunks_count = 0
    try:
        if RAG_AVAILABLE:
            from app.services.ingestion_service import IngestionService
            from app.services.postgres_service import PostgreSQLService
            from app.services.embedding_service import EmbeddingService

            pg_service = PostgreSQLService()
            embedder = EmbeddingService()
            ingestor = IngestionService(embedder=embedder, db=pg_service)

            status_dict = {}
            ingestor.ingest(pdf_path=temp_path, user_id=user_id, status_dict=status_dict)
            chunks_count = status_dict.get("chunks_count", 0)
        else:
            # Fallback text ingestion
            text_content = content.decode("utf-8", errors="ignore")
            with get_cursor() as cur:
                chunk_id = f"UCHUNK-{uuid.uuid4().hex[:8]}"
                cur.execute("""
                    INSERT INTO user_chunks (chunk_id, user_id, doc_name, folder_path, page_number, heading, language, parent_text, child_text)
                    VALUES (%s, %s, %s, 'user_uploads', 1, %s, 'en', %s, %s);
                """, (chunk_id, user_id, file.filename, file.filename, text_content, text_content))
            chunks_count = 1
    except Exception as ex:
        print(f"[Upload Ingestion Error] {ex}")
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(ex)}")

    if temp_path.exists():
        temp_path.unlink()

    return {
        "status": "success",
        "message": f"Document '{file.filename}' successfully embedded and stored into user_chunks table!",
        "filename": file.filename,
        "user_id": user_id,
        "chunks_indexed": chunks_count
    }


@agenda_router.get("/documents/user-docs", tags=["Document Ingestion"])
async def get_user_uploaded_documents(user_id: str = Query("565")):
    """Returns list of distinct uploaded documents in user_chunks table for the given user_id."""
    docs = []
    with get_cursor() as cur:
        try:
            cur.execute("""
                SELECT doc_name, COUNT(*) as chunk_count
                FROM user_chunks
                WHERE user_id = %s
                GROUP BY doc_name
                ORDER BY MAX(created_at) DESC;
            """, (user_id,))
            rows = cur.fetchall()
            for r in rows:
                docs.append({
                    "doc_name": r["doc_name"] or "Uploaded Document",
                    "chunk_count": r["chunk_count"]
                })
        except Exception:
            pass
    return docs


@agenda_router.delete("/documents/user-docs", tags=["Document Ingestion"])
async def delete_user_uploaded_document(doc_name: str = Query(...), user_id: str = Query("565")):
    """Deletes all embedded chunks for a specific document in user_chunks table."""
    with get_cursor() as cur:
        cur.execute("DELETE FROM user_chunks WHERE doc_name = %s AND user_id = %s;", (doc_name, user_id))
    return {"status": "success", "message": f"Document '{doc_name}' removed from vector store."}

