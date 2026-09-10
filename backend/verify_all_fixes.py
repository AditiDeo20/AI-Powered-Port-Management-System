import urllib.request
import json
import sys
sys.stdout.reconfigure(encoding="utf-8")

API_BASE = "http://127.0.0.1:8000"

# TEST 1: Officer Roster
res = urllib.request.urlopen(f"{API_BASE}/api/v1/users/officers")
officers = json.loads(res.read().decode())
dos = officers.get("dos", [])
nodals = officers.get("nodal_officers", [])
hods = officers.get("hods", [])
counts = officers.get("counts", {})
print(f"[TEST 1] Officer Roster: DOs={len(dos)}, NOs={len(nodals)}, HODs={len(hods)}")
assert len(dos) == 158, f"Expected 158 DOs, got {len(dos)}"
assert len(nodals) == 44, f"Expected 44 NOs, got {len(nodals)}"
assert len(hods) == 30, f"Expected 30 HODs, got {len(hods)}"
print("  --> TEST 1 PASSED: Complete 232-Officer Roster Verified!")

# TEST 2: Promote Sandbox with Full Conversational History
promote_payload = {
    "user_id": "101",
    "user_name": "ROHIT SHARMA",
    "user_role": "DO",
    "agenda_title": "Renewal of Plot P-101 for Adani Ports",
    "tenancy_id": "P-101",
    "sandbox_messages": [
        "USER: What is the status of plot P-101?",
        "AI: Plot P-101 is currently status: OCCUPIED by Adani Ports & SEZ Ltd.",
        "USER: Draft a lease renewal recommendation clause.",
        "AI: Recommendation: Adani Ports & SEZ Ltd is eligible for lease renewal under Section 25."
    ],
    "initial_draft": "Draft proposal for lease renewal of Plot P-101."
}
req = urllib.request.Request(
    f"{API_BASE}/api/v1/agendas/promote-sandbox",
    data=json.dumps(promote_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
res = urllib.request.urlopen(req)
promote_res = json.loads(res.read().decode())
agenda_id = promote_res["agenda_id"]
print(f"[TEST 2] Promoted to: {agenda_id}, Owner={promote_res['current_owner']}, State={promote_res['current_state']}")
assert promote_res["current_owner"] == "DO"
assert promote_res["current_state"] == "DO_DRAFT"
print("  --> TEST 2 PASSED: Promote Sandbox Succeeded!")

# TEST 3: Retrieve Agenda Messages (Conversational History in Official Agenda)
res = urllib.request.urlopen(f"{API_BASE}/api/v1/agendas/{agenda_id}/messages")
messages = json.loads(res.read().decode())
print(f"[TEST 3] Messages retrieved: {len(messages)}")
for idx, m in enumerate(messages):
    print(f"   Msg {idx+1}: [{m['sender_name']} ({m['sender_role']})] (AI={m['is_ai_response']}) -> {m['content'][:60]}...")
assert len(messages) == 4, f"Expected 4 messages, got {len(messages)}"
assert messages[0]["is_ai_response"] is False
assert messages[1]["is_ai_response"] is True
assert messages[2]["is_ai_response"] is False
assert messages[3]["is_ai_response"] is True
print("  --> TEST 3 PASSED: Full Conversational History Retained & Rendered!")

# TEST 4: Single-Writer Lock Enforcement
# Non-owner (HOD) attempts to write into DO_DRAFT -> Expect HTTP 403
try:
    illegal_write = {
        "agenda_id": agenda_id,
        "thread_type": "OFFICIAL_AGENDA",
        "sender_id": "567",
        "sender_name": "SMT.AMRUTA HARSHAD VYAPARI",
        "sender_role": "HOD",
        "content": "Attempting unauthorized write into DO draft."
    }
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/agendas/messages",
        data=json.dumps(illegal_write).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)
    print("  --> ERROR: Non-owner write was not blocked!")
    assert False, "Non-owner write should have been blocked"
except urllib.error.HTTPError as e:
    print(f"[TEST 4] Single-Writer Lock Active: Non-owner write blocked with HTTP {e.code}: {e.read().decode()}")
    assert e.code == 403
    print("  --> TEST 4 PASSED: Non-owner locked with HTTP 403 Read-Only Snapshot!")

# TEST 5: Handoff State Machine DO -> NO -> HOD -> APPROVE
target_no = nodals[0]["admin_id"]
target_no_name = nodals[0]["name"]
handoff_payload = {
    "agenda_id": agenda_id,
    "sender_id": "101",
    "sender_name": "ROHIT SHARMA",
    "sender_role": "DO",
    "action": "SUBMIT_FORWARD",
    "target_officer_id": target_no,
    "target_officer_name": target_no_name,
    "remarks": "Submitted to Nodal Officer for verification."
}
req = urllib.request.Request(
    f"{API_BASE}/api/v1/agendas/handoff",
    data=json.dumps(handoff_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
res = urllib.request.urlopen(req)
h_res = json.loads(res.read().decode())
print(f"[TEST 5] DO -> NO Handoff: State={h_res['current_state']}, Owner={h_res['current_owner']}")
assert h_res["current_state"] == "SUBMITTED_TO_NO"
assert h_res["current_owner"] == "NODAL"

# Check that system handoff event was logged into messages
res = urllib.request.urlopen(f"{API_BASE}/api/v1/agendas/{agenda_id}/messages")
updated_messages = json.loads(res.read().decode())
print(f"Total messages after handoff: {len(updated_messages)}")
assert len(updated_messages) == 5
print(f"Latest message: {updated_messages[-1]['content'][:70]}...")
print("  --> TEST 5 PASSED: Handoff State Machine & Audit Trail Verified!")

print("\n======================================================")
print("  ALL 5 CRITICAL TESTS PASSED WITH 100% SUCCESS!      ")
print("======================================================")
