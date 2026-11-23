"""Error signature normalization and hashing."""

import hashlib
import re


class ErrorSignatureHasher:
    """Normalizes dynamic volatile strings (line numbers, memory addresses, timestamps)

    to produce a stable hash signature for loop and repetition detection.
    """

    @classmethod
    def normalize(cls, error_text: str) -> str:
        """Normalizes dynamic parts of an error string."""
        s = error_text.strip()
        # Line numbers: line 42 -> line <NUM>
        s = re.sub(r"line\s+\d+", "line <NUM>", s, flags=re.IGNORECASE)
        s = re.sub(r":\d+:\d+", ":<NUM>:<NUM>", s)
        s = re.sub(r":\d+", ":<NUM>", s)
        # Memory addresses: 0x7ffd98... -> 0x<HEX>
        s = re.sub(r"0x[0-9a-fA-F]{4,}", "0x<HEX>", s)
        # Temp paths
        s = re.sub(r"(/tmp|/var/folders|[A-Za-z]:\\[Tt]emp)[^\s:\"']+", "<TEMP_PATH>", s)
        # Timestamps / durations
        s = re.sub(r"\d+(\.\d+)?\s*(s|ms|seconds|minutes)", "<TIME>", s)
        return s

    @classmethod
    def hash_error(cls, error_text: str) -> str:
        """Generates deterministic 12-character SHA256 hash of normalized error."""
        normalized = cls.normalize(error_text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
