"""General utility functions for DevPilot."""


def truncate_output(
    output: str, max_chars: int = 40_000, head_ratio: float = 0.7
) -> tuple[str, bool]:
    """Truncates large outputs retaining informative head and tail segments.

    Preserves `head_ratio` of max_chars at the beginning and the remaining at the end,
    inserting an informative summary marker indicating omitted lines and characters.
    """
    if len(output) <= max_chars:
        return output, False

    head_chars = int(max_chars * head_ratio)
    tail_chars = max_chars - head_chars

    head_part = output[:head_chars]
    tail_part = output[-tail_chars:]

    omitted_chars = len(output) - (head_chars + tail_chars)
    omitted_lines = output[head_chars:-tail_chars].count("\n")

    summary_marker = f"\n\n... [{omitted_lines} lines / {omitted_chars} characters truncated for context limit] ...\n\n"
    return head_part + summary_marker + tail_part, True
