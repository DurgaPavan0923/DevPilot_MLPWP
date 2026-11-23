"""Multi-language AST symbol extractor (classes, functions, methods, imports)."""

import ast
import re
from enum import StrEnum

from pydantic import BaseModel, Field


class SymbolType(StrEnum):
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    IMPORT = "import"


class Symbol(BaseModel):
    name: str = Field(..., description="Symbol identifier name")
    symbol_type: SymbolType = Field(...)
    file_path: str = Field(..., description="Relative file path")
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    docstring: str | None = Field(None)
    signature: str | None = Field(None)
    parent_name: str | None = Field(None)


class SymbolParser:
    """Extracts symbols and code structures across supported programming languages."""

    @classmethod
    def parse_file(cls, file_path: str, content: str, language: str | None = None) -> list[Symbol]:
        if not language:
            if file_path.endswith(".py"):
                language = "python"
            elif file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
                language = "javascript"
            elif file_path.endswith(".java"):
                language = "java"
            elif file_path.endswith(".go"):
                language = "go"
            else:
                return []

        if language == "python":
            return cls._parse_python(file_path, content)
        elif language in ("javascript", "typescript"):
            return cls._parse_javascript(file_path, content)
        elif language == "java":
            return cls._parse_java(file_path, content)
        elif language == "go":
            return cls._parse_go(file_path, content)
        return []

    @classmethod
    def _parse_python(cls, file_path: str, content: str) -> list[Symbol]:
        symbols: list[Symbol] = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return cls._regex_fallback(file_path, content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                end = getattr(node, "end_lineno", node.lineno)
                symbols.append(
                    Symbol(
                        name=node.name,
                        symbol_type=SymbolType.CLASS,
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=end,
                        docstring=doc,
                    )
                )
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        m_doc = ast.get_docstring(item)
                        m_end = getattr(item, "end_lineno", item.lineno)
                        symbols.append(
                            Symbol(
                                name=item.name,
                                symbol_type=SymbolType.METHOD,
                                file_path=file_path,
                                start_line=item.lineno,
                                end_line=m_end,
                                docstring=m_doc,
                                parent_name=node.name,
                            )
                        )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Ensure it's a top-level function, not inner method
                if not any(
                    isinstance(parent, ast.ClassDef)
                    for parent in ast.walk(tree)
                    if node in getattr(parent, "body", [])
                ):
                    doc = ast.get_docstring(node)
                    end = getattr(node, "end_lineno", node.lineno)
                    symbols.append(
                        Symbol(
                            name=node.name,
                            symbol_type=SymbolType.FUNCTION,
                            file_path=file_path,
                            start_line=node.lineno,
                            end_line=end,
                            docstring=doc,
                        )
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    symbols.append(
                        Symbol(
                            name=alias.name,
                            symbol_type=SymbolType.IMPORT,
                            file_path=file_path,
                            start_line=node.lineno,
                            end_line=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    symbols.append(
                        Symbol(
                            name=f"{mod}.{alias.name}" if mod else alias.name,
                            symbol_type=SymbolType.IMPORT,
                            file_path=file_path,
                            start_line=node.lineno,
                            end_line=node.lineno,
                        )
                    )

        return sorted(symbols, key=lambda s: s.start_line)

    @classmethod
    def _parse_javascript(cls, file_path: str, content: str) -> list[Symbol]:
        symbols: list[Symbol] = []
        lines = content.splitlines()

        # Class matching
        class_pattern = re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z0-9_$]+)")
        # Function matching
        fn_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)")
        # Arrow function or method matching
        const_fn_pattern = re.compile(
            r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"
        )
        # Import matching
        import_pattern = re.compile(r"^\s*import\s+.*?from\s+['\"](.*?)['\"]")

        for idx, line in enumerate(lines, start=1):
            c_match = class_pattern.match(line)
            if c_match:
                symbols.append(
                    Symbol(
                        name=c_match.group(1),
                        symbol_type=SymbolType.CLASS,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 10,
                    )
                )
                continue

            f_match = fn_pattern.match(line) or const_fn_pattern.match(line)
            if f_match:
                symbols.append(
                    Symbol(
                        name=f_match.group(1),
                        symbol_type=SymbolType.FUNCTION,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 10,
                    )
                )
                continue

            i_match = import_pattern.match(line)
            if i_match:
                symbols.append(
                    Symbol(
                        name=i_match.group(1),
                        symbol_type=SymbolType.IMPORT,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                    )
                )

        return symbols

    @classmethod
    def _parse_java(cls, file_path: str, content: str) -> list[Symbol]:
        symbols: list[Symbol] = []
        lines = content.splitlines()
        class_pattern = re.compile(
            r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:class|interface|enum)\s+([A-Za-z0-9_]+)"
        )
        method_pattern = re.compile(
            r"^\s*(?:public|private|protected)?\s*(?:static\s+)?[\w<>[\]]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{"
        )
        import_pattern = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+);")

        for idx, line in enumerate(lines, start=1):
            c_m = class_pattern.match(line)
            if c_m:
                symbols.append(
                    Symbol(
                        name=c_m.group(1),
                        symbol_type=SymbolType.CLASS,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 15,
                    )
                )
                continue
            m_m = method_pattern.match(line)
            if m_m:
                symbols.append(
                    Symbol(
                        name=m_m.group(1),
                        symbol_type=SymbolType.METHOD,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 10,
                    )
                )
                continue
            i_m = import_pattern.match(line)
            if i_m:
                symbols.append(
                    Symbol(
                        name=i_m.group(1),
                        symbol_type=SymbolType.IMPORT,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                    )
                )
        return symbols

    @classmethod
    def _parse_go(cls, file_path: str, content: str) -> list[Symbol]:
        symbols: list[Symbol] = []
        lines = content.splitlines()
        fn_pattern = re.compile(r"^\s*func\s+([A-Za-z0-9_]+)\s*\(")
        method_pattern = re.compile(r"^\s*func\s*\([^)]+\)\s*([A-Za-z0-9_]+)\s*\(")
        type_pattern = re.compile(r"^\s*type\s+([A-Za-z0-9_]+)\s+(?:struct|interface)")

        for idx, line in enumerate(lines, start=1):
            t_m = type_pattern.match(line)
            if t_m:
                symbols.append(
                    Symbol(
                        name=t_m.group(1),
                        symbol_type=SymbolType.CLASS,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 10,
                    )
                )
                continue
            m_m = method_pattern.match(line)
            if m_m:
                symbols.append(
                    Symbol(
                        name=m_m.group(1),
                        symbol_type=SymbolType.METHOD,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 10,
                    )
                )
                continue
            f_m = fn_pattern.match(line)
            if f_m:
                symbols.append(
                    Symbol(
                        name=f_m.group(1),
                        symbol_type=SymbolType.FUNCTION,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 10,
                    )
                )

        return symbols

    @classmethod
    def _regex_fallback(cls, file_path: str, content: str) -> list[Symbol]:
        symbols = []
        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            if line.strip().startswith("def "):
                fn_name = line.strip().split()[1].split("(")[0]
                symbols.append(
                    Symbol(
                        name=fn_name,
                        symbol_type=SymbolType.FUNCTION,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 5,
                    )
                )
            elif line.strip().startswith("class "):
                cls_name = line.strip().split()[1].split("(")[0].split(":")[0]
                symbols.append(
                    Symbol(
                        name=cls_name,
                        symbol_type=SymbolType.CLASS,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 10,
                    )
                )
        return symbols
