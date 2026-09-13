import re

# Basic regex for common secrets
SECRET_PATTERNS = [
    (re.compile(r'(?i)(sk-[a-zA-Z0-9]{20,})'), '<REDACTED_SECRET_KEY>'),
    (re.compile(r'(?i)(AKIA[0-9A-Z]{16})'), '<REDACTED_AWS_KEY>'),
    (re.compile(r'(?i)(ghp_[a-zA-Z0-9]{36})'), '<REDACTED_GITHUB_TOKEN>'),
    (re.compile(r'-----BEGIN .*? PRIVATE KEY-----.*?-----END .*? PRIVATE KEY-----', re.DOTALL), '<REDACTED_PRIVATE_KEY>'),
    (re.compile(r'(?i)([A-Z0-9_]*(?:API_KEY|PASSWORD|TOKEN|SECRET|PRIVATE_KEY)[A-Z0-9_]*\s*=\s*)([^\r\n]+)'), r'\1<REDACTED>')
]

def redact_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted

def redact_dict(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    result = {}
    for k, v in data.items():
        # Also redact based on key names
        if isinstance(k, str) and re.search(r'(?i)(key|secret|token|password)', k):
            result[k] = '<REDACTED>'
        elif isinstance(v, str):
            result[k] = redact_text(v)
        elif isinstance(v, dict):
            result[k] = redact_dict(v)
        elif isinstance(v, list):
            result[k] = [redact_dict(i) if isinstance(i, dict) else (redact_text(i) if isinstance(i, str) else i) for i in v]
        else:
            result[k] = v
    return result
