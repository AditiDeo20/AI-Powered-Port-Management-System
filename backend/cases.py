from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

cases_router = APIRouter(prefix="/api/v1", tags=["Workflow Cases & Active Thread"])

try:
    from database import get_cursor
except ModuleNotFoundError:
    from backend.database import get_cursor

# ── Helper functions for PostgreSQL Database Access ─────────────────────────

def db_get_cases(workflow_state: Optional[str] = None, current_owner: Optional[str] = None):
    with get_cursor() as cur:
        query = "SELECT case_id, tenancy_id, title, workflow_state, current_owner, created_by, created_at FROM workflow_cases"
        filters = []
        params = []
        if workflow_state and workflow_state != "ALL":
            filters.append("workflow_state = %s")
            params.append(workflow_state)
        if current_owner:
            filters.append("current_owner = %s")
            params.append(current_owner)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY created_at DESC"
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        for r in rows:
            if isinstance(r.get("created_at"), (datetime.date, datetime.datetime)):
                r["created_at"] = r["created_at"].isoformat()
        return rows

def db_get_timeline(case_id: str):
    with get_cursor() as cur:
        cur.execute("SELECT case_id, tenancy_id, title, workflow_state, current_owner, created_by, created_at FROM workflow_cases WHERE case_id = %s", (case_id,))
        case_row = cur.fetchone()
        if not case_row:
            return None
        
        if isinstance(case_row.get("created_at"), (datetime.date, datetime.datetime)):
            case_row["created_at"] = case_row["created_at"].isoformat()
            
        cur.execute("SELECT sender_username, sender_role, content, created_at FROM workflow_messages WHERE case_id = %s ORDER BY id ASC", (case_id,))
        messages = cur.fetchall()
        for m in messages:
            if isinstance(m.get("created_at"), (datetime.date, datetime.datetime)):
                m["created_at"] = m["created_at"].isoformat()
        case_row["messages"] = messages

        cur.execute("SELECT version, draft_content, updated_by AS created_by, updated_at FROM workflow_artifacts WHERE case_id = %s ORDER BY version ASC", (case_id,))
        artifacts = cur.fetchall()
        for a in artifacts:
            if isinstance(a.get("updated_at"), (datetime.date, datetime.datetime)):
                a["updated_at"] = a["updated_at"].isoformat()
        case_row["artifacts"] = artifacts

        return case_row

USERS_LIST = [
    {"user_name": "rsharma", "name": "Rohit Sharma", "role": "DO"},
    {"user_name": "pdeshmukh", "name": "Pooja Deshmukh", "role": "NODAL"},
    {"user_name": "vrao", "name": "Vikram Rao", "role": "HOD"}
]

TENANTS_LIST = [
    {"tenancy_id": "TEN-2026-001", "name": "Adani Ports & SEZ Ltd", "status": "APPROVED", "tenancy_type": "Long Lease"},
    {"tenancy_id": "TEN-2026-002", "name": "DP World Logistics", "status": "APPROVED", "tenancy_type": "Short Term"},
    {"tenancy_id": "TEN-2026-003", "name": "Jindal Steel & Power Ltd", "status": "PENDING", "tenancy_type": "Long Lease"}
]

# ── Pydantic Request Models ──────────────────────────────────────────────────

class CaseCreateRequest(BaseModel):
    title: str
    tenancy_id: str
    created_by: str
    workflow_state: str = "INITIATED"

class PostMessageRequest(BaseModel):
    sender_username: str
    sender_role: str
    content: str

class TransitionRequest(BaseModel):
    action_by: str
    user_role: str
    remarks: Optional[str] = None
    draft_content: Optional[str] = None

# ── Endpoints ────────────────────────────────────────────────────────────────

@cases_router.get("/users")
async def get_users(role: Optional[str] = None):
    if role:
        return [u for u in USERS_LIST if u["role"] == role]
    return USERS_LIST

@cases_router.get("/tenants")
async def get_tenants(search: Optional[str] = None, status: Optional[str] = None):
    try:
        with get_cursor() as cur:
            query = """
                SELECT 
                    apm.tenancy_id,
                    apm.tenant_id,
                    COALESCE(ar.ind_org_name, mt.name_val, 'Port Tenant (' || apm.tenancy_id || ')') AS tenant_name,
                    COALESCE(apm.tenancy_type, 'Long Lease') AS tenancy_type,
                    COALESCE(NULLIF(apm.purpose, ''), 'Commercial Land Lease') AS purpose,
                    COALESCE(NULLIF(apm.duration_from, ''), '1995-01-01') AS duration_from,
                    COALESCE(apm.status, 'APPROVED') AS status
                FROM applicant_property_mapping apm
                LEFT JOIN applicant_registration ar ON apm.tenant_id = ar.applicant_id
                LEFT JOIN (SELECT "TenantID" AS tid, "Name" AS name_val FROM mtenant) mt ON apm.tenant_id = mt.tid
                WHERE apm.tenancy_id IS NOT NULL AND apm.tenancy_id != ''
            """
            filters = []
            params = []
            if search:
                filters.append("(apm.tenancy_id ILIKE %s OR ar.ind_org_name ILIKE %s OR mt.name_val ILIKE %s)")
                s_param = f"%{search}%"
                params.extend([s_param, s_param, s_param])
            if status:
                filters.append("apm.status = %s")
                params.append(status)

            if filters:
                query += " AND " + " AND ".join(filters)
            
            query += " ORDER BY apm.tenant_id DESC LIMIT 100"
            cur.execute(query, tuple(params))
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@cases_router.get("/cases")
async def get_cases(
    workflow_state: Optional[str] = None,
    current_owner: Optional[str] = None
):
    try:
        return db_get_cases(workflow_state, current_owner)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@cases_router.post("/cases")
async def create_case(body: CaseCreateRequest):
    try:
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM workflow_cases")
            count = cur.fetchone()["count"]
            new_id = f"CASE-2026-{(count + 1):03d}"
            
            cur.execute("""
                INSERT INTO workflow_cases (case_id, tenancy_id, title, workflow_state, current_owner, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (new_id, body.tenancy_id, body.title, body.workflow_state, body.created_by, body.created_by))

            cur.execute("""
                INSERT INTO workflow_messages (case_id, sender_username, sender_role, content)
                VALUES (%s, %s, %s, %s)
            """, (new_id, body.created_by, "DO", f"Initiated workflow case: {body.title}"))

            cur.execute("""
                INSERT INTO workflow_artifacts (case_id, version, draft_content, updated_by)
                VALUES (%s, 1, %s, %s)
            """, (new_id, f"INITIAL APPLICATION FOR {body.title.upper()}\n\n1. Details submitted.", body.created_by))

        return db_get_timeline(new_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@cases_router.get("/cases/{case_id}/timeline")
async def get_case_timeline(case_id: str):
    data = db_get_timeline(case_id)
    if not data:
        raise HTTPException(status_code=404, detail="Case not found")
    return data

@cases_router.post("/cases/{case_id}/messages", status_code=201)
async def post_case_message(case_id: str, body: PostMessageRequest):
    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO workflow_messages (case_id, sender_username, sender_role, content)
                VALUES (%s, %s, %s, %s)
                RETURNING id, created_at
            """, (case_id, body.sender_username, body.sender_role, body.content))
            row = cur.fetchone()
            created_at = row["created_at"].isoformat() if isinstance(row.get("created_at"), (datetime.date, datetime.datetime)) else str(row.get("created_at"))
            return {
                "id": row["id"],
                "case_id": case_id,
                "sender_username": body.sender_username,
                "sender_role": body.sender_role,
                "content": body.content,
                "created_at": created_at
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@cases_router.post("/cases/{case_id}/submit-to-nodal")
async def submit_to_nodal(case_id: str, body: TransitionRequest):
    try:
        with get_cursor() as cur:
            cur.execute("""
                UPDATE workflow_cases
                SET workflow_state = 'SUBMITTED_TO_NODAL', current_owner = 'NODAL', updated_at = CURRENT_TIMESTAMP
                WHERE case_id = %s
            """, (case_id,))

            if body.remarks:
                cur.execute("""
                    INSERT INTO workflow_messages (case_id, sender_username, sender_role, content)
                    VALUES (%s, %s, 'DO', %s)
                """, (case_id, body.action_by, f"Submitted / Returned to Nodal: {body.remarks}"))

            if body.draft_content:
                cur.execute("SELECT COALESCE(MAX(version), 0) AS max_v FROM workflow_artifacts WHERE case_id = %s", (case_id,))
                max_v = cur.fetchone()["max_v"]
                cur.execute("""
                    INSERT INTO workflow_artifacts (case_id, version, draft_content, updated_by)
                    VALUES (%s, %s, %s, %s)
                """, (case_id, max_v + 1, body.draft_content, body.action_by))

        return {"status": "success", "case_id": case_id, "workflow_state": "SUBMITTED_TO_NODAL"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@cases_router.post("/cases/{case_id}/return-to-do")
async def return_to_do(case_id: str, body: TransitionRequest):
    try:
        with get_cursor() as cur:
            cur.execute("""
                UPDATE workflow_cases
                SET workflow_state = 'RETURNED_TO_DO', current_owner = 'DO', updated_at = CURRENT_TIMESTAMP
                WHERE case_id = %s
            """, (case_id,))

            if body.remarks:
                cur.execute("""
                    INSERT INTO workflow_messages (case_id, sender_username, sender_role, content)
                    VALUES (%s, %s, %s, %s)
                """, (case_id, body.action_by, body.user_role, f"Returned Case to DO: {body.remarks}"))

        return {"status": "success", "case_id": case_id, "workflow_state": "RETURNED_TO_DO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@cases_router.post("/cases/{case_id}/verify-and-forward")
async def verify_and_forward(case_id: str, body: TransitionRequest):
    try:
        with get_cursor() as cur:
            cur.execute("""
                UPDATE workflow_cases
                SET workflow_state = 'VERIFIED_BY_NODAL', current_owner = 'HOD', updated_at = CURRENT_TIMESTAMP
                WHERE case_id = %s
            """, (case_id,))

            if body.remarks:
                cur.execute("""
                    INSERT INTO workflow_messages (case_id, sender_username, sender_role, content)
                    VALUES (%s, %s, 'NODAL', %s)
                """, (case_id, body.action_by, f"Verified & Forwarded to HOD: {body.remarks}"))

            if body.draft_content:
                cur.execute("SELECT COALESCE(MAX(version), 0) AS max_v FROM workflow_artifacts WHERE case_id = %s", (case_id,))
                max_v = cur.fetchone()["max_v"]
                cur.execute("""
                    INSERT INTO workflow_artifacts (case_id, version, draft_content, updated_by)
                    VALUES (%s, %s, %s, %s)
                """, (case_id, max_v + 1, body.draft_content, body.action_by))

        return {"status": "success", "case_id": case_id, "workflow_state": "VERIFIED_BY_NODAL"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@cases_router.post("/cases/{case_id}/approve")
async def approve_case(case_id: str, body: TransitionRequest):
    try:
        with get_cursor() as cur:
            cur.execute("""
                UPDATE workflow_cases
                SET workflow_state = 'APPROVED_BY_HOD', current_owner = 'HOD', updated_at = CURRENT_TIMESTAMP
                WHERE case_id = %s
            """, (case_id,))

            if body.remarks:
                cur.execute("""
                    INSERT INTO workflow_messages (case_id, sender_username, sender_role, content)
                    VALUES (%s, %s, 'HOD', %s)
                """, (case_id, body.action_by, f"FINALLY GRANTED: {body.remarks}"))

        return {"status": "success", "case_id": case_id, "workflow_state": "APPROVED_BY_HOD"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@cases_router.get("/cases/{case_id}/diff")
async def get_case_diff(case_id: str):
    data = db_get_timeline(case_id)
    if not data:
        raise HTTPException(status_code=404, detail="Case not found")
    
    artifacts = data.get("artifacts", [])
    v1_text = artifacts[0]["draft_content"] if len(artifacts) > 0 else ""
    v2_text = artifacts[-1]["draft_content"] if len(artifacts) > 1 else v1_text

    diff_lines = []
    additions = 0
    deletions = 0

    l1 = v1_text.splitlines()
    l2 = v2_text.splitlines()

    for line in l2:
        if line not in l1:
            diff_lines.append({"type": "addition", "line": line})
            additions += 1
        else:
            diff_lines.append({"type": "unchanged", "line": line})

    for line in l1:
        if line not in l2:
            diff_lines.append({"type": "deletion", "line": line})
            deletions += 1

    return {
        "case_id": case_id,
        "additions_count": additions,
        "deletions_count": deletions,
        "diff_lines": diff_lines
    }
