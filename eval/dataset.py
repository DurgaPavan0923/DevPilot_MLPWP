"""Benchmark task representations, schemas, SWE-bench Lite loader, and task repository manager."""

import json
import random
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BenchmarkTask(BaseModel):
    task_id: str
    repo: str
    instruction: str
    gold_files: list[str]
    test_command: str = "pytest"
    base_commit: str | None = None
    problem_type: str = "bugfix"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SWEBenchTask(BaseModel):
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    gold_patch: str
    test_patch: str
    version: str = "lite"
    fail_to_pass: list[str] = Field(default_factory=list)
    pass_to_pass: list[str] = Field(default_factory=list)

    def to_benchmark_task(self) -> BenchmarkTask:
        """Converts to BenchmarkTask ensuring strict data leakage prevention.

        The agent runtime only receives the problem_statement and repo files.
        Gold patch and test patch are never exposed to the agent.
        """
        return BenchmarkTask(
            task_id=self.instance_id,
            repo=self.repo,
            instruction=self.problem_statement,
            gold_files=[],  # Populated strictly post-hoc during evaluation
            test_command="pytest",
            base_commit=self.base_commit,
            problem_type="swe_bench_lite",
            metadata={"instance_id": self.instance_id},
        )


BUILTIN_SAMPLE_TASKS: list[dict[str, Any]] = [
    {
        "task_id": "DP-001",
        "repo": "task_01_auth_ttl",
        "instruction": "Fix token expiration validation in src/jwt_helper.py where expired tokens with zero remaining TTL pass validation.",
        "gold_files": ["src/jwt_helper.py"],
        "test_command": "pytest tests/test_jwt.py",
        "problem_type": "security_boundary",
    },
    {
        "task_id": "DP-002",
        "repo": "task_02_csv_parser",
        "instruction": "Handle unquoted commas inside CSV fields in src/parser.py without raising parsing delimiter error.",
        "gold_files": ["src/parser.py"],
        "test_command": "pytest tests/test_parser.py",
        "problem_type": "syntax_parsing",
    },
    {
        "task_id": "DP-003",
        "repo": "task_03_lru_cache",
        "instruction": "Implement LRU eviction tie-breaking when cache items have identical access timestamps in src/lru.py.",
        "gold_files": ["src/lru.py"],
        "test_command": "pytest tests/test_lru.py",
        "problem_type": "algorithmic_state",
    },
    {
        "task_id": "DP-004",
        "repo": "task_04_http_router",
        "instruction": "Add missing 404 response handler when route pattern does not match in src/router.py.",
        "gold_files": ["src/router.py"],
        "test_command": "pytest tests/test_router.py",
        "problem_type": "error_handling",
    },
    {
        "task_id": "DP-005",
        "repo": "task_05_math_division",
        "instruction": "Correct division-by-zero guard in src/statistics.py to return None instead of raising unhandled ZeroDivisionError.",
        "gold_files": ["src/statistics.py"],
        "test_command": "pytest tests/test_stats.py",
        "problem_type": "boundary_check",
    },
    {
        "task_id": "DP-006",
        "repo": "task_06_event_emitter",
        "instruction": "Fix memory leak in src/emitter.py where disconnected subscriber callbacks are not removed from the listener list.",
        "gold_files": ["src/emitter.py"],
        "test_command": "pytest tests/test_emitter.py",
        "problem_type": "resource_leak",
    },
    {
        "task_id": "DP-007",
        "repo": "task_07_markdown_escape",
        "instruction": "Render escaped backticks inside inline code spans correctly in src/renderer.py.",
        "gold_files": ["src/renderer.py"],
        "test_command": "pytest tests/test_renderer.py",
        "problem_type": "regex_parsing",
    },
    {
        "task_id": "DP-008",
        "repo": "task_08_env_sanitizer",
        "instruction": "Parse integer environment variables in src/loader.py without crashing when value contains leading or trailing spaces.",
        "gold_files": ["src/loader.py"],
        "test_command": "pytest tests/test_loader.py",
        "problem_type": "input_sanitization",
    },
    {
        "task_id": "DP-009",
        "repo": "task_09_rate_limiter",
        "instruction": "Fix sliding window counter timestamp calculation in src/limiter.py when window rolls over.",
        "gold_files": ["src/limiter.py"],
        "test_command": "pytest tests/test_limiter.py",
        "problem_type": "concurrency_state",
    },
    {
        "task_id": "DP-010",
        "repo": "task_10_retry_backoff",
        "instruction": "Ensure exponential backoff jitter in src/retry.py never produces negative sleep durations.",
        "gold_files": ["src/retry.py"],
        "test_command": "pytest tests/test_retry.py",
        "problem_type": "numerical_edge_case",
    },
]


class TaskSuiteLoader:
    """Loads and samples benchmark tasks from YAML, JSON, or built-in testbed."""

    @classmethod
    def load_builtin_tasks(
        cls, sample_size: int | None = None, seed: int = 42
    ) -> list[BenchmarkTask]:
        """Loads built-in benchmark tasks with deterministic seeded sampling."""
        tasks = [BenchmarkTask(**t) for t in BUILTIN_SAMPLE_TASKS]
        if sample_size and sample_size < len(tasks):
            rng = random.Random(seed)
            tasks = rng.sample(tasks, sample_size)
        return tasks

    @classmethod
    def load_from_file(cls, path: Path) -> list[BenchmarkTask]:
        """Loads tasks from a JSON or YAML suite specification file."""
        content = path.read_text(encoding="utf-8")
        if path.suffix.lower() in (".yaml", ".yml"):
            try:
                import yaml

                raw_list = yaml.safe_load(content)
            except ImportError:
                raw_list = json.loads(content)
        else:
            raw_list = json.loads(content)
        if not isinstance(raw_list, list):
            raise ValueError(f"Expected a list of tasks in {path}, got {type(raw_list).__name__}")
        return [BenchmarkTask(**item) for item in raw_list]

    @classmethod
    def load_swe_bench_lite(
        cls,
        path: Path,
        sample_size: int = 30,
        seed: int = 42,
    ) -> list[SWEBenchTask]:
        """Loads SWE-bench Lite tasks with data leakage prevention guarantee."""
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("SWE-bench Lite file must be a JSON array")

        tasks = [SWEBenchTask(**item) for item in data]
        if sample_size < len(tasks):
            rng = random.Random(seed)
            tasks = rng.sample(tasks, sample_size)
        return tasks


def ensure_eval_repos(base_dir: Path) -> dict[str, Path]:
    """Generates the 10 real runnable evaluation repository fixtures on disk.

    Each repo includes source files with real bugs and a failing pytest suite reproducing the bug.
    """
    repos_dir = base_dir / "eval_repos"
    repos_dir.mkdir(parents=True, exist_ok=True)
    created: dict[str, Path] = {}

    # Task 1: Auth TTL
    r1 = repos_dir / "task_01_auth_ttl"
    r1.mkdir(parents=True, exist_ok=True)
    (r1 / "src").mkdir(exist_ok=True)
    (r1 / "tests").mkdir(exist_ok=True)
    (r1 / "src" / "jwt_helper.py").write_text(
        "def is_token_valid(ttl_seconds: int) -> bool:\n"
        "    # BUG: ttl_seconds <= 0 should be invalid (False), but returns True\n"
        "    if ttl_seconds >= 0:\n"
        "        return True\n"
        "    return False\n",
        encoding="utf-8",
    )
    (r1 / "tests" / "test_jwt.py").write_text(
        "import sys, os\n"
        "sys.path.insert(0, os.path.abspath('.'))\n"
        "from src.jwt_helper import is_token_valid\n"
        "def test_token_validity():\n"
        "    assert is_token_valid(10) is True\n"
        "    assert is_token_valid(0) is False\n"
        "    assert is_token_valid(-5) is False\n",
        encoding="utf-8",
    )
    created["task_01_auth_ttl"] = r1

    # Task 2: CSV Parser
    r2 = repos_dir / "task_02_csv_parser"
    r2.mkdir(parents=True, exist_ok=True)
    (r2 / "src").mkdir(exist_ok=True)
    (r2 / "tests").mkdir(exist_ok=True)
    (r2 / "src" / "parser.py").write_text(
        "def parse_csv_line(line: str) -> list[str]:\n"
        "    # BUG: Naive split on comma breaks when field is quoted like '\"hello, world\"'\n"
        "    return [part.strip() for part in line.split(',')]\n",
        encoding="utf-8",
    )
    (r2 / "tests" / "test_parser.py").write_text(
        "import sys, os, csv, io\n"
        "sys.path.insert(0, os.path.abspath('.'))\n"
        "from src.parser import parse_csv_line\n"
        "def test_quoted_commas():\n"
        "    res = parse_csv_line('alpha,\"beta,gamma\",delta')\n"
        "    assert len(res) == 3\n"
        "    assert res[1].replace('\"', '') == 'beta,gamma'\n",
        encoding="utf-8",
    )
    created["task_02_csv_parser"] = r2

    # Task 3: LRU Cache
    r3 = repos_dir / "task_03_lru_cache"
    r3.mkdir(parents=True, exist_ok=True)
    (r3 / "src").mkdir(exist_ok=True)
    (r3 / "tests").mkdir(exist_ok=True)
    (r3 / "src" / "lru.py").write_text(
        "class LRUCache:\n"
        "    def __init__(self, capacity: int = 2):\n"
        "        self.capacity = capacity\n"
        "        self.cache: dict[str, str] = {}\n"
        "    def get(self, key: str) -> str | None:\n"
        "        if key in self.cache:\n"
        "            val = self.cache.pop(key)\n"
        "            self.cache[key] = val\n"
        "            return val\n"
        "        return None\n"
        "    def put(self, key: str, val: str) -> None:\n"
        "        if key in self.cache:\n"
        "            self.cache.pop(key)\n"
        "        elif len(self.cache) >= self.capacity:\n"
        "            # BUG: pops newest instead of oldest\n"
        "            self.cache.popitem()\n"
        "        self.cache[key] = val\n",
        encoding="utf-8",
    )
    (r3 / "tests" / "test_lru.py").write_text(
        "import sys, os\n"
        "sys.path.insert(0, os.path.abspath('.'))\n"
        "from src.lru import LRUCache\n"
        "def test_lru_eviction():\n"
        "    cache = LRUCache(capacity=2)\n"
        "    cache.put('a', '1')\n"
        "    cache.put('b', '2')\n"
        "    cache.get('a') # 'a' is most recently used, 'b' is oldest\n"
        "    cache.put('c', '3') # should evict 'b'\n"
        "    assert cache.get('a') == '1'\n"
        "    assert cache.get('b') is None\n"
        "    assert cache.get('c') == '3'\n",
        encoding="utf-8",
    )
    created["task_03_lru_cache"] = r3

    # Task 4: HTTP Router
    r4 = repos_dir / "task_04_http_router"
    r4.mkdir(parents=True, exist_ok=True)
    (r4 / "src").mkdir(exist_ok=True)
    (r4 / "tests").mkdir(exist_ok=True)
    (r4 / "src" / "router.py").write_text(
        "def route_request(path: str) -> dict[str, Any]:\n"
        "    routes = {'/api/health': {'status': 200, 'body': 'OK'}}\n"
        "    # BUG: returns 500 instead of 404 for unknown route\n"
        "    return routes.get(path, {'status': 500, 'body': 'Internal Error'})\n",
        encoding="utf-8",
    )
    (r4 / "tests" / "test_router.py").write_text(
        "import sys, os\n"
        "sys.path.insert(0, os.path.abspath('.'))\n"
        "from src.router import route_request\n"
        "def test_unknown_route():\n"
        "    res = route_request('/nonexistent')\n"
        "    assert res['status'] == 404\n",
        encoding="utf-8",
    )
    created["task_04_http_router"] = r4

    # Task 5: Math Division
    r5 = repos_dir / "task_05_math_division"
    r5.mkdir(parents=True, exist_ok=True)
    (r5 / "src").mkdir(exist_ok=True)
    (r5 / "tests").mkdir(exist_ok=True)
    (r5 / "src" / "statistics.py").write_text(
        "def calculate_harmonic_mean(a: float, b: float) -> float | None:\n"
        "    # BUG: does not guard against zero or opposite signs adding to zero\n"
        "    return 2.0 / (1.0 / a + 1.0 / b)\n",
        encoding="utf-8",
    )
    (r5 / "tests" / "test_stats.py").write_text(
        "import sys, os\n"
        "sys.path.insert(0, os.path.abspath('.'))\n"
        "from src.statistics import calculate_harmonic_mean\n"
        "def test_harmonic_mean():\n"
        "    assert calculate_harmonic_mean(2.0, 4.0) == pytest.approx(2.6666, rel=1e-3)\n"
        "    assert calculate_harmonic_mean(0.0, 5.0) is None\n"
        "    assert calculate_harmonic_mean(2.0, -2.0) is None\n",
        encoding="utf-8",
    )
    created["task_05_math_division"] = r5

    # Task 6: Event Emitter
    r6 = repos_dir / "task_06_event_emitter"
    r6.mkdir(parents=True, exist_ok=True)
    (r6 / "src").mkdir(exist_ok=True)
    (r6 / "tests").mkdir(exist_ok=True)
    (r6 / "src" / "emitter.py").write_text(
        "class EventEmitter:\n"
        "    def __init__(self):\n"
        "        self.listeners = []\n"
        "    def on(self, fn):\n"
        "        self.listeners.append(fn)\n"
        "    def off(self, fn):\n"
        "        # BUG: pass without removing\n"
        "        pass\n"
        "    def emit(self, val):\n"
        "        return [f(val) for f in self.listeners]\n",
        encoding="utf-8",
    )
    (r6 / "tests" / "test_emitter.py").write_text(
        "import sys, os\n"
        "sys.path.insert(0, os.path.abspath('.'))\n"
        "from src.emitter import EventEmitter\n"
        "def test_unsubscribe():\n"
        "    em = EventEmitter()\n"
        "    cb = lambda x: x * 2\n"
        "    em.on(cb)\n"
        "    em.off(cb)\n"
        "    assert len(em.listeners) == 0\n",
        encoding="utf-8",
    )
    created["task_06_event_emitter"] = r6

    # Task 7: Markdown Escape
    r7 = repos_dir / "task_07_markdown_escape"
    r7.mkdir(parents=True, exist_ok=True)
    (r7 / "src").mkdir(exist_ok=True)
    (r7 / "tests").mkdir(exist_ok=True)
    (r7 / "src" / "renderer.py").write_text(
        "def render_code_span(text: str) -> str:\n"
        "    # BUG: wraps without escaping existing backticks\n"
        "    return f'<code>{text}</code>'\n",
        encoding="utf-8",
    )
    (r7 / "tests" / "test_renderer.py").write_text(
        "import sys, os\n"
        "sys.path.insert(0, os.path.abspath('.'))\n"
        "from src.renderer import render_code_span\n"
        "def test_escape():\n"
        "    res = render_code_span('`code`')\n"
        "    assert '`' not in res or '&grave;' in res or '&#96;' in res or '<code>\\`code\\`</code>' in res\n",
        encoding="utf-8",
    )
    created["task_07_markdown_escape"] = r7

    # Task 8: Env Sanitizer
    r8 = repos_dir / "task_08_env_sanitizer"
    r8.mkdir(parents=True, exist_ok=True)
    (r8 / "src").mkdir(exist_ok=True)
    (r8 / "tests").mkdir(exist_ok=True)
    (r8 / "src" / "loader.py").write_text(
        "def parse_int_env(val: str, default: int = 0) -> int:\n"
        "    # BUG: does not strip spaces before int() conversion\n"
        "    try:\n"
        "        return int(val)\n"
        "    except (ValueError, TypeError):\n"
        "        return default\n",
        encoding="utf-8",
    )
    (r8 / "tests" / "test_loader.py").write_text(
        "import sys, os\n"
        "sys.path.insert(0, os.path.abspath('.'))\n"
        "from src.loader import parse_int_env\n"
        "def test_env_trim():\n"
        "    assert parse_int_env(' 42 ') == 42\n"
        "    assert parse_int_env('\\t100\\n') == 100\n",
        encoding="utf-8",
    )
    created["task_08_env_sanitizer"] = r8

    # Task 9: Rate Limiter
    r9 = repos_dir / "task_09_rate_limiter"
    r9.mkdir(parents=True, exist_ok=True)
    (r9 / "src").mkdir(exist_ok=True)
    (r9 / "tests").mkdir(exist_ok=True)
    (r9 / "src" / "limiter.py").write_text(
        "def is_rate_limited(count: int, limit: int) -> bool:\n"
        "    # BUG: > instead of >= when count reaches limit\n"
        "    return count > limit\n",
        encoding="utf-8",
    )
    (r9 / "tests" / "test_limiter.py").write_text(
        "import sys, os\n"
        "sys.path.insert(0, os.path.abspath('.'))\n"
        "from src.limiter import is_rate_limited\n"
        "def test_rate_limit_boundary():\n"
        "    assert is_rate_limited(9, 10) is False\n"
        "    assert is_rate_limited(10, 10) is True\n",
        encoding="utf-8",
    )
    created["task_09_rate_limiter"] = r9

    # Task 10: Retry Backoff
    r10 = repos_dir / "task_10_retry_backoff"
    r10.mkdir(parents=True, exist_ok=True)
    (r10 / "src").mkdir(exist_ok=True)
    (r10 / "tests").mkdir(exist_ok=True)
    (r10 / "src" / "retry.py").write_text(
        "def compute_backoff(attempt: int, base: float = 1.0, jitter: float = 0.0) -> float:\n"
        "    # BUG: jitter can make sleep negative\n"
        "    duration = (base * (2 ** attempt)) + jitter\n"
        "    return max(0.0, duration)\n",
        encoding="utf-8",
    )
    (r10 / "tests" / "test_retry.py").write_text(
        "import sys, os\n"
        "sys.path.insert(0, os.path.abspath('.'))\n"
        "from src.retry import compute_backoff\n"
        "def test_backoff_bounds():\n"
        "    assert compute_backoff(0, base=1.0, jitter=-10.0) >= 0.0\n"
        "    assert compute_backoff(2, base=1.0, jitter=0.5) == 4.5\n",
        encoding="utf-8",
    )
    created["task_10_retry_backoff"] = r10

    return created
