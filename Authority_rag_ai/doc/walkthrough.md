# Walkthrough - Input Guardrail System

Implemented an Input Guardrail service to detect, filter, and reject queries containing vulgar, filthy, or cuss words (including obfuscated/leetspeak variations like `f*ck`, `sh1t`, etc.) before RAG processing.

## Changes Made

### Core Services
- **[NEW] [guardrail_service.py](file:///d:/AI-PMS/RAG/RAG_SYSTEM/app/services/guardrail_service.py)**: Implemented `GuardrailService` utilizing `better-profanity` and regex pattern detection. Includes support for domain-specific whitelisting (e.g. `PMS`, `ai-pms`) to prevent false positives on project acronyms.
- **[MODIFY] [requirements.txt](file:///d:/AI-PMS/RAG/RAG_SYSTEM/requirements.txt)**: Added `better-profanity` dependency.

### Pipeline Integration
- **[MODIFY] [rag_system_chatbot.py](file:///d:/AI-PMS/RAG/RAG_SYSTEM/scripts/rag_system_chatbot.py)**: Added `STEP 0: INPUT GUARDRAIL` at the start of the chatbot query loop. Inappropriate inputs are intercepted in <1ms, displaying a safety warning and aborting embedding/retrieval/LLM generation.

### Tests
- **[NEW] [test_guardrail.py](file:///d:/AI-PMS/RAG/RAG_SYSTEM/scripts/tests/test_guardrail.py)**: Added unit test suite covering clean queries, profane inputs, obfuscated inputs, and domain whitelisted terms.

---

## Verification Results

### Automated Unit Tests
Executed `python scripts/tests/test_guardrail.py`:
```text
All guardrail tests passed successfully!
```

### End-to-End Chatbot Test

#### 1. Inappropriate / Vulgar Query Interception
```text
Enter your question: What the fuck is this?

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
⚠️ INPUT GUARDRAIL REJECTION
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Message: Input contains inappropriate, vulgar, or profanity language.
Filtered: What the **** is this?
Query aborted to uphold content safety guidelines.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

#### 2. Clean Domain Query Execution
```text
Enter your question: What is PMS?

======================================================================
STEP 1 : EMBEDDING QUERY
======================================================================
Embedding Generated in 0.61s

======================================================================
STEP 2 : RETRIEVAL
======================================================================
Retrieved 3 chunks in 0.26s

======================================================================
STEP 3 : BUILD PROMPT
======================================================================
Prompt Created in 0.0000s

======================================================================
STEP 4 : LLM GENERATION
======================================================================
```
