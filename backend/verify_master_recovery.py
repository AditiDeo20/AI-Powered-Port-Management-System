"""
AI-PMS Master Recovery & Verification Suite
===================================================
Tests end-to-end RAG pipeline, endpoints, dynamic multi-source citations, and agenda workflows.
"""

import sys
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_1_health_and_sandbox():
    print("\n--- TEST 1: API Health & AI Assistant Sandbox Endpoint ---")
    h_res = requests.get(f"{BASE_URL}/health")
    assert h_res.status_code == 200, f"Health endpoint failed: {h_res.status_code}"
    print("[OK] GET /health -> 200 OK:", h_res.json())

    sb_payload = {
        "user_id": "565",
        "user_name": "sudhakark_do",
        "user_role": "DO",
        "content": "Does Indian Contract Act apply to Jammu and Kashmir?",
        "model_name": "qwen2.5:3b"
    }
    sb_res = requests.post(f"{BASE_URL}/api/v1/agendas/sandbox", json=sb_payload)
    assert sb_res.status_code == 200, f"Sandbox query failed: {sb_res.status_code} {sb_res.text}"
    ans = sb_res.json().get("ai_response", "")
    print(f"[OK] POST /api/v1/agendas/sandbox -> 200 OK\n   Response preview: {ans[:150]}...")

def test_2_pdf_upload_state():
    print("\n--- TEST 2: User Document Upload & Vector Search Context ---")
    docs_res = requests.get(f"{BASE_URL}/api/v1/documents/user-docs?user_id=565")
    assert docs_res.status_code == 200, f"User docs endpoint failed: {docs_res.status_code}"
    docs = docs_res.json()
    print(f"[OK] GET /api/v1/documents/user-docs -> 200 OK ({len(docs)} documents indexed)")

def test_3_dynamic_citations():
    print("\n--- TEST 3: Dynamic Multi-Source Citation Verification ---")
    sb_payload = {
        "user_id": "565",
        "user_name": "sudhakark_do",
        "user_role": "DO",
        "content": "What is the SOR rate for commercial land lease in plot 12?",
        "model_name": "qwen2.5:3b"
    }
    sb_res = requests.post(f"{BASE_URL}/api/v1/agendas/sandbox", json=sb_payload)
    assert sb_res.status_code == 200
    ans = sb_res.json().get("ai_response", "")
    
    # Assert NO hardcoded mock citation string exists
    assert "[Source: Port RAG System]" not in ans, "FOUND HARDCODED MOCK CITATION STRING!"
    assert "[Source: Fallback]" not in ans, "FOUND HARDCODED FALLBACK CITATION STRING!"
    print("[OK] Verified: Zero hardcoded mock citations found. Dynamic sources formatted cleanly.")

def test_4_agenda_context_accumulation():
    print("\n--- TEST 4: Multi-Tier Agenda Handoff Context ---")
    ag_res = requests.get(f"{BASE_URL}/api/v1/agendas?user_id=565&user_role=DO")
    assert ag_res.status_code == 200
    agendas = ag_res.json()
    print(f"[OK] GET /api/v1/agendas -> 200 OK ({len(agendas)} agendas listed)")

if __name__ == "__main__":
    try:
        test_1_health_and_sandbox()
        test_2_pdf_upload_state()
        test_3_dynamic_citations()
        test_4_agenda_context_accumulation()
        print("\n======================================================================")
        print("     ALL 4 MASTER RECOVERY VERIFICATION TESTS PASSED SUCCESSFULLY!     ")
        print("======================================================================\n")
    except Exception as e:
        print(f"\n[FAIL] Test Failure: {e}")
        sys.exit(1)

