import re
from dataclasses import dataclass, field
from typing import List, Optional, Set
from better_profanity import profanity
from better_profanity.utils import read_wordlist


@dataclass
class GuardrailResult:
    is_safe: bool
    reason: Optional[str] = None
    censored_text: str = ""
    detected_words: List[str] = field(default_factory=list)
    block_type: Optional[str] = None  # 'OUT_OF_DOMAIN', 'SQL_BLOCK', 'PROFANITY'


# Domain-specific whitelisted terms that should never be flagged as profanity or out-of-domain
DEFAULT_DOMAIN_WHITELIST: Set[str] = {
    "pms",
    "pm-s",
    "ai-pms",
    "subletting",
    "sublet",
    "sub-letting",
    "sub-lease",
    "sublease",
    "section 25",
    "clause",
    "pglm",
    "tamp",
    "mpa",
    "plot",
    "plots",
    "lease",
    "leases",
    "arrears",
    "valuation",
    "timber pond",
    "wharf",
    "berth",
    "demurrage",
    "allotment",
    "allotments",
    "penalty",
    "penalties",
    "tenancy",
    "tenant",
    "tenants",
    "port",
    "ports",
    "sor",
    "ready reckoner",
    "fmv",
    "sewree",
    "wadala",
    "dock",
    "docks",
    "estate",
    "water tax",
    "general bill",
    "tgeneralbill",
    "applicant",
    "memo",
    "pmemo",
}

OUT_OF_DOMAIN_MESSAGE = (
    "Guardrail rejection: The assistant declines and states its scope is restricted to Port Estate & Land Management.\n\n"
    "I cannot answer general-knowledge, culinary, or entertainment queries. Please submit inquiries regarding "
    "port land allotments, lease renewals, subletting permissions, billing calculations, or statutory guidelines (PGLM / TAMP / MPA Act)."
)

SQL_BLOCK_MESSAGE = (
    "SQL Guardrail block: The assistant refuses to execute destructive operations.\n\n"
    "Database operations are strictly read-only. Direct execution of DDL/DML commands is prohibited."
)


class GuardrailService:
    """
    Input Guardrail Service:
      1. Normalizes input.
      2. Detects destructive SQL operations (DROP, DELETE, TRUNCATE, ALTER, UPDATE, INSERT).
      3. Validates legitimate Port Statutory terms (Whitelist immunity).
      4. Catches out-of-domain topics (Culinary/Food, Entertainment/Sports, General tech/coding, General trivia).
      5. Sanitizes profanity/vulgarity.
    """

    def __init__(
        self,
        custom_blocked_words: Optional[List[str]] = None,
        whitelist_words: Optional[Set[str]] = None
    ):
        whitelisted = DEFAULT_DOMAIN_WHITELIST.union(whitelist_words or set())
        default_words = set(read_wordlist(profanity._default_wordlist_filename))
        clean_censor_words = list(default_words - whitelisted)

        profanity.load_censor_words(custom_words=clean_censor_words)
        if custom_blocked_words:
            profanity.add_censor_words(custom_blocked_words)

        # Destructive SQL pattern (case-insensitive)
        self.sql_destructive_pattern = re.compile(
            r'\b(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE|ALTER\s+TABLE|UPDATE\s+[\w\.\"]+\s+SET|INSERT\s+INTO)\b',
            re.IGNORECASE
        )

        # Out-of-domain patterns (case-insensitive)
        self.ood_patterns = [
            # Culinary / Food
            re.compile(r'\b(bake|cake|recipe|cook|cooking|baking|frosting|batter|oven|ingredients|dish|soup|pasta|pizza|bread|pie|muffin|dessert|snack|chocolate|pancake|kitchen)\b', re.IGNORECASE),
            # Entertainment / Sports
            re.compile(r'\b(movie|cinema|actor|actress|hollywood|bollywood|cricket|football|match|song|songs|lyrics|celebrity|album|premier league|world cup)\b', re.IGNORECASE),
            # General tech / coding
            re.compile(r'\b(write\s+(a\s+)?(python|java|c\+\+|javascript|ruby|golang|rust|html|css)\s+(code|script|program)|build\s+a\s+website|snake\s+game|tic\s+tac\s+toe)\b', re.IGNORECASE),
            # General trivia / chitchat
            re.compile(r'\b(capital\s+of|weather\s+in|who\s+is\s+(the\s+)?president\s+of|tell\s+me\s+a\s+joke|who\s+won\s+the|prime\s+minister\s+of)\b', re.IGNORECASE),
        ]

        # Additional vulgar patterns
        self.vulgar_patterns = [
            re.compile(r'\b(f+[*a-z0-9]*[u4]+[*a-z0-9]*[c|k]+[*a-z0-9]*[k|t]*)\b', re.IGNORECASE),
            re.compile(r'\b(s+[*a-z0-9]*[h1|]+[*a-z0-9]*[i1|]+[*a-z0-9]*[t7]+)\b', re.IGNORECASE),
            re.compile(r'\b(b+[*a-z0-9]*[i1|]+[*a-z0-9]*[t7]+[*a-z0-9]*[c|k]+[*a-z0-9]*h*)\b', re.IGNORECASE),
            re.compile(r'\b(a+[*a-z0-9]*[s5\$]+[*a-z0-9]*[s5\$]+[*a-z0-9]*[h0|]+[*a-z0-9]*[o0]+[*a-z0-9]*l+[*a-z0-9]*e*)\b', re.IGNORECASE),
        ]

        self.whitelist = whitelisted

    def validate_input(self, text: str) -> GuardrailResult:
        """
        Validates user input text.
        Returns GuardrailResult:
          - is_safe=True if safe and in-domain.
          - is_safe=False with authoritative reason, block_type, and refusal text.
        """
        if not text or not text.strip():
            return GuardrailResult(is_safe=True, censored_text="")

        normalized_query = text.lower().strip()

        # 1. Destructive SQL Check (Highest priority security block)
        if self.sql_destructive_pattern.search(text):
            return GuardrailResult(
                is_safe=False,
                reason=SQL_BLOCK_MESSAGE,
                censored_text=text,
                detected_words=["DESTRUCTIVE_SQL_COMMAND"],
                block_type="SQL_BLOCK"
            )

        # 2. Whitelist Immunity Check for Legitimate Port Statutory Inquiries
        has_port_context = any(term in normalized_query for term in self.whitelist)

        # 3. Out-of-Domain Detection
        # If the user query matches an OOD pattern and DOES NOT have explicit port domain grounding:
        for pat in self.ood_patterns:
            if pat.search(text):
                # If it mentions cake/recipe/movie/cricket/snake game, reject even if incidental words match
                # Only bypass if strongly grounded in port land affairs
                strict_food_or_ent = bool(re.search(r'\b(bake|cake|recipe|cook|pizza|movie|actor|cricket|snake\s+game)\b', normalized_query))
                if strict_food_or_ent or not has_port_context:
                    return GuardrailResult(
                        is_safe=False,
                        reason=OUT_OF_DOMAIN_MESSAGE,
                        censored_text=text,
                        detected_words=["OUT_OF_DOMAIN"],
                        block_type="OUT_OF_DOMAIN"
                    )

        # 4. Profanity / Vulgarity Check
        contains_profanity = profanity.contains_profanity(text)
        pattern_matches = []
        for pattern in self.vulgar_patterns:
            matches = pattern.findall(text)
            if matches:
                pattern_matches.extend(matches)

        if contains_profanity or pattern_matches:
            censored = profanity.censor(text)
            return GuardrailResult(
                is_safe=False,
                reason="Input contains inappropriate, vulgar, or profanity language.",
                censored_text=censored,
                detected_words=list(set(pattern_matches)),
                block_type="PROFANITY"
            )

        return GuardrailResult(
            is_safe=True,
            reason=None,
            censored_text=text,
            detected_words=[]
        )

    def check_sql_injection_guardrail(self, text: str) -> Optional[str]:
        """Returns refusal message if destructive SQL injection pattern is detected, otherwise None."""
        if not text:
            return None
        if self.sql_destructive_pattern.search(text):
            return SQL_BLOCK_MESSAGE
        return None

    def check_domain_scope_guardrail(self, text: str) -> Optional[str]:
        """Returns refusal message if query is strictly out-of-domain, otherwise None."""
        if not text or not text.strip():
            return None
        normalized_query = text.lower().strip()
        has_port_context = any(term in normalized_query for term in self.whitelist)
        for pat in self.ood_patterns:
            if pat.search(text):
                strict_food_or_ent = bool(re.search(r'\b(bake|cake|recipe|cook|pizza|movie|actor|cricket|snake\s+game)\b', normalized_query))
                if strict_food_or_ent or not has_port_context:
                    return OUT_OF_DOMAIN_MESSAGE
        return None

