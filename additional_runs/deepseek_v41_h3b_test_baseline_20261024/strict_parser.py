from dataclasses import dataclass

@dataclass(frozen=True)
class ParseResult:
    prediction: int | None
    parse_status: str
    parse_method: str

def parse_prediction(response_text: str) -> ParseResult:
    if not isinstance(response_text, str) or not response_text.strip():
        return ParseResult(None, 'invalid', 'empty_response')
    last_line = next((line.strip() for line in reversed(response_text.splitlines()) if line.strip()), '')
    if last_line == '0': return ParseResult(0, 'valid', 'exact_last_line_binary')
    if last_line == '1': return ParseResult(1, 'valid', 'exact_last_line_binary')
    return ParseResult(None, 'invalid', 'last_line_not_exact_binary')
