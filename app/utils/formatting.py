"""Indian numbering (lakhs/crores) for amounts: 12,34,567.89"""


def _group_integer_indian(int_part: str) -> str:
    """Group digit-only string in Indian style (last 3, then pairs)."""
    digits = int_part.lstrip("0") or "0"
    if len(digits) <= 3:
        return digits
    last_three = digits[-3:]
    head = digits[:-3]
    segments: list[str] = []
    while len(head) > 2:
        segments.insert(0, head[-2:])
        head = head[:-2]
    if head:
        segments.insert(0, head)
    segments.append(last_three)
    return ",".join(segments)


def format_indian_amount(
    value: float | int,
    *,
    decimals: int = 2,
    signed: bool = False,
) -> str:
    """Format a number with Indian thousands separators and fixed decimal places."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return str(value)

    negative = x < 0
    x = abs(x)

    if negative:
        prefix = "-"
    elif signed:
        prefix = "+"
    else:
        prefix = ""

    if decimals > 0:
        formatted = f"{x:.{decimals}f}"
        int_part, frac_part = formatted.split(".", 1)
    else:
        int_part = str(int(round(x)))
        frac_part = ""

    grouped_int = _group_integer_indian(int_part)
    if decimals > 0:
        return f"{prefix}{grouped_int}.{frac_part}"
    return f"{prefix}{grouped_int}"


def parse_amount(raw: object) -> float:
    """Parse user/API input: strips commas and spaces, then float."""
    if raw is None:
        return 0.0
    s = str(raw).strip().replace(",", "").replace(" ", "")
    if not s:
        return 0.0
    return float(s)
