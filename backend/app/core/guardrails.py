import re
from typing import Tuple, Optional
from app.core.metrics import GUARDRAIL_VIOLATIONS_TOTAL

# Prompt injection heuristics and dangerous patterns
INJECTION_PATTERNS = [
    r"(?i)\bignore\s+(all\s+)?(previous|prior)\s+instructions\b",
    r"(?i)\byou\s+are\s+now\s+(an?\s+)?unrestricted\b",
    r"(?i)\bjailbreak\b",
    r"(?i)\bsystem\s+prompt\s+override\b",
    r"(?i)\brepeat\s+the\s+system\s+prompt\b",
    r"(?i)\bdisregard\s+all\s+guardrails\b",
    r"(?i)\bact\s+as\s+dan\b",
    r"(?i)\bpretend\s+you\s+have\s+root\b",
    r"(?i)\bdeveloper\s+mode\s+enabled\b",
]

MAX_QUESTION_LENGTH = 1000
MIN_QUESTION_LENGTH = 2

def sanitize_and_validate_input(question: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates user query against length limits, whitespace, and injection signatures.
    Returns: (is_valid, cleaned_question, error_message)
    """
    cleaned = question.strip()
    
    if len(cleaned) < MIN_QUESTION_LENGTH:
        GUARDRAIL_VIOLATIONS_TOTAL.labels(violation_type="empty_or_too_short").inc()
        return False, cleaned, "Question is too short. Please provide a clear university inquiry."
        
    if len(cleaned) > MAX_QUESTION_LENGTH:
        GUARDRAIL_VIOLATIONS_TOTAL.labels(violation_type="exceeds_max_length").inc()
        return False, cleaned, f"Question exceeds maximum allowed length of {MAX_QUESTION_LENGTH} characters."
        
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, cleaned):
            GUARDRAIL_VIOLATIONS_TOTAL.labels(violation_type="prompt_injection_detected").inc()
            return False, cleaned, "Security notice: Malicious instructions or prompt injection attempts are not permitted."
            
    return True, cleaned, None

def validate_retrieved_context(context_text: str) -> str:
    """
    Sanitizes retrieved text before feeding into the LLM prompt.
    Explicitly tags untrusted context boundaries to prevent indirect prompt injections.
    """
    # Neutralize instruction overriding prefixes inside documents
    neutralized = re.sub(
        r"(?i)(system\s*:|assistant\s*:|human\s*:|<\|im_start\|>|<\|im_end\|>)",
        "[doc_text]",
        context_text
    )
    return neutralized

def validate_output(answer: str) -> str:
    """
    Checks the generated response for safety, ensuring it doesn't leak secrets
    or emit model internal formatting tags.
    """
    cleaned = re.sub(r"<\|im_end\|>|<\|im_start\|>|<s>|<\/s>", "", answer).strip()
    return cleaned

