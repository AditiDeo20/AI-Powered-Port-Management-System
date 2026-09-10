"""
Port Land Lease MMS - Intelligent Query Router Service
=====================================================
Routes user queries to DATABASE, DOCUMENT, or MULTI_HOP retrieval engines.
Default ambiguous queries to MULTI_HOP to ensure both DB records and vector document chunks are retrieved.
"""

import json
from typing import Dict, Any

try:
    from langchain_community.llms import Ollama
    from langchain_core.prompts import PromptTemplate
    LANGCHAIN_ROUTER_AVAILABLE = True
except Exception:
    LANGCHAIN_ROUTER_AVAILABLE = False


class RouterService:
    def __init__(self, model_name="qwen2.5:3b"):
        from app.services.llm_service import resolve_ollama_model
        self.model_name = resolve_ollama_model(model_name)
        self.available = LANGCHAIN_ROUTER_AVAILABLE
        
        if LANGCHAIN_ROUTER_AVAILABLE:
            try:
                self.llm = Ollama(model=self.model_name, base_url="http://127.0.0.1:11434")
                template = """
You are an intelligent router for the Port Land Lease MMS AI assistant.
Decide which route is required for the user's question:

ROUTING OPTIONS:
1. "DOCUMENT": The query asks about policy manuals, guidelines, subletting rules, legal terms, contract clauses, acts, sections, or document text.
2. "DATABASE": The query asks strictly about structured database numbers (plot area, tenant names, due dates, memo amounts, zone rates).
3. "MULTI_HOP": The query asks for structured database records AND policy/manual guidelines or legal context.

Question: {question}

Return JSON with keys "route" ("DOCUMENT", "DATABASE", or "MULTI_HOP") and "table" (string or null).
JSON:"""
                self.prompt = PromptTemplate(template=template, input_variables=["question"])
                self.chain = self.prompt | self.llm
            except Exception as e:
                print(f"[WARN] RouterService LangChain error ({e}). Using rule-based router.")
                self.available = False

    def route_query(self, question: str) -> Dict[str, Any]:
        """
        Routes query by returning a dict with 'route' ('DOCUMENT', 'DATABASE', or 'MULTI_HOP') and 'table'.
        """
        q_lower = (question or "").lower()

        # Document/Policy/Legal keywords check
        doc_keywords = ["doc", "document", "policy", "guideline", "manual", "rule", "clause", "sublet", "subletting", "act", "section", "contract", "terms", "agreement", "lease grant", "permission", "renewal"]
        db_keywords = ["plot", "sq.m", "rate", "amount", "memo", "pmemo", "due date", "tenant", "mtenant", "customer", "zone", "bill", "table", "database"]

        has_doc = any(k in q_lower for k in doc_keywords)
        has_db = any(k in q_lower for k in db_keywords)

        if has_doc and has_db:
            return {"route": "MULTI_HOP", "table": "plot"}
        elif has_doc:
            return {"route": "DOCUMENT", "table": None}
        elif has_db:
            # Route to MULTI_HOP by default to fetch document context alongside DB records
            return {"route": "MULTI_HOP", "table": "plot"}

        if self.available and hasattr(self, 'chain'):
            try:
                res = self.chain.invoke({"question": question}).strip()
                if res.startswith("```json"):
                    res = res.split("```json")[1].split("```")[0].strip()
                elif res.startswith("```"):
                    res = res.split("```")[1].split("```")[0].strip()
                    
                data = json.loads(res)
                route = data.get("route", "MULTI_HOP").upper()
                
                if "DOCUMENT" in route:
                    return {"route": "DOCUMENT", "table": None}
                elif "DATABASE" in route:
                    return {"route": "MULTI_HOP", "table": data.get("table")}
                else:
                    return {"route": "MULTI_HOP", "table": data.get("table")}
            except Exception:
                pass

        return {"route": "MULTI_HOP", "table": "plot"}
