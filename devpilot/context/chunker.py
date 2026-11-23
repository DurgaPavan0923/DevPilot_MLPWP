"""Code and file chunking by symbol with sliding-window fallback."""

from pathlib import Path

from pydantic import BaseModel, Field

from devpilot.repo.index import RepoIndex
from devpilot.repo.parser import SymbolType


class CodeChunk(BaseModel):
    chunk_id: str = Field(...)
    file_path: str = Field(...)
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    content: str = Field(...)
    symbol_name: str | None = Field(None)
    symbol_type: str | None = Field(None)
    token_count: int = Field(default=0)


class SymbolChunker:
    """Partitions repository files into symbol-aligned or windowed code chunks."""

    @staticmethod
    def chunk_repository(
        index: RepoIndex, window_size_lines: int = 60, overlap_lines: int = 10
    ) -> list[CodeChunk]:
        chunks: list[CodeChunk] = []

        if not index.scan_result:
            return chunks

        for fmeta in index.scan_result.files:
            if fmeta.is_binary:
                continue

            abs_path = Path(fmeta.abs_path)
            try:
                raw_text = abs_path.read_text(encoding="utf-8", errors="ignore")
                lines = raw_text.splitlines()
            except Exception:
                continue

            if not lines:
                continue

            symbols = index.symbols_by_file.get(fmeta.rel_path, [])
            code_symbols = [
                s
                for s in symbols
                if s.symbol_type in (SymbolType.CLASS, SymbolType.FUNCTION, SymbolType.METHOD)
            ]

            if code_symbols:
                # Symbol-based chunking
                for idx, sym in enumerate(code_symbols):
                    s_line = max(1, sym.start_line)
                    e_line = min(len(lines), sym.end_line)
                    if e_line < s_line:
                        e_line = s_line

                    chunk_text = "\n".join(lines[s_line - 1 : e_line])
                    tokens = max(1, len(chunk_text) // 4)

                    chunks.append(
                        CodeChunk(
                            chunk_id=f"{fmeta.rel_path}#{sym.name}_{idx}",
                            file_path=fmeta.rel_path,
                            start_line=s_line,
                            end_line=e_line,
                            content=chunk_text,
                            symbol_name=sym.name,
                            symbol_type=sym.symbol_type.value,
                            token_count=tokens,
                        )
                    )
            else:
                # Sliding window chunking fallback
                total_lines = len(lines)
                curr = 0
                part_idx = 0
                while curr < total_lines:
                    end = min(total_lines, curr + window_size_lines)
                    chunk_text = "\n".join(lines[curr:end])
                    tokens = max(1, len(chunk_text) // 4)

                    chunks.append(
                        CodeChunk(
                            chunk_id=f"{fmeta.rel_path}#part_{part_idx}",
                            file_path=fmeta.rel_path,
                            start_line=curr + 1,
                            end_line=end,
                            content=chunk_text,
                            token_count=tokens,
                        )
                    )
                    part_idx += 1
                    if end >= total_lines:
                        break
                    curr += max(1, window_size_lines - overlap_lines)

        return chunks
