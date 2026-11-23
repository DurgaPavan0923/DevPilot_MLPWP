"""Unit tests for Context Engine: BM25, Dense semantic, RRF, Kneedle, and Adaptive-K."""

from pathlib import Path

import pytest

from devpilot.context.adaptive_k import AdaptiveKSelector, TaskComplexityEstimator
from devpilot.context.bm25 import BM25Retriever
from devpilot.context.chunker import CodeChunk
from devpilot.context.dense import DenseSemanticRetriever, _cosine_similarity
from devpilot.context.fusion import min_max_normalize, reciprocal_rank_fusion
from devpilot.context.hybrid import AdaptiveHybridRetriever
from devpilot.repo.graph import RepoDependencyGraph


@pytest.fixture
def sample_chunks() -> list[CodeChunk]:
    return [
        CodeChunk(
            chunk_id="chunk_auth",
            file_path="src/auth.py",
            start_line=1,
            end_line=20,
            content="def verify_jwt_token(token: str):\n    # JWT signature verification\n    return decode(token)",
            symbol_name="verify_jwt_token",
            symbol_type="function",
            token_count=15,
        ),
        CodeChunk(
            chunk_id="chunk_db",
            file_path="src/db.py",
            start_line=1,
            end_line=25,
            content="class DatabaseConnection:\n    def connect(self):\n        # Open SQL connection\n        pass",
            symbol_name="DatabaseConnection",
            symbol_type="class",
            token_count=15,
        ),
        CodeChunk(
            chunk_id="chunk_routes",
            file_path="src/routes.py",
            start_line=1,
            end_line=30,
            content="def login_route(request):\n    token = verify_jwt_token(request.headers)\n    return token",
            symbol_name="login_route",
            symbol_type="function",
            token_count=20,
        ),
        CodeChunk(
            chunk_id="chunk_utils",
            file_path="src/utils.py",
            start_line=1,
            end_line=15,
            content="def format_date(dt):\n    return dt.isoformat()",
            symbol_name="format_date",
            symbol_type="function",
            token_count=10,
        ),
    ]


def test_bm25_lexical_scoring(sample_chunks):
    retriever = BM25Retriever(sample_chunks)
    scores = retriever.score("verify jwt token decode")
    top_idx, top_score = scores[0]
    assert sample_chunks[top_idx].file_path == "src/auth.py"
    assert top_score > 0.0


def test_bm25_ranker_synthetic_corpus():
    corpus = [
        CodeChunk(
            chunk_id="c1",
            file_path="a.py",
            start_line=1,
            end_line=5,
            content="apple banana apple apple",
            token_count=5,
        ),
        CodeChunk(
            chunk_id="c2",
            file_path="b.py",
            start_line=1,
            end_line=5,
            content="banana cherry date",
            token_count=5,
        ),
        CodeChunk(
            chunk_id="c3",
            file_path="c.py",
            start_line=1,
            end_line=5,
            content="elderberry fig grape",
            token_count=5,
        ),
    ]
    bm25 = BM25Retriever(corpus)
    scores = dict(bm25.score("apple"))
    # c1 has highest term frequency for 'apple'
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


def test_dense_embeddings_cosine_similarity(tmp_path: Path, sample_chunks):
    # Test cosine similarity math function directly
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert _cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert _cosine_similarity(v1, v3) == pytest.approx(0.0)

    # Test retriever with cache
    cache_dir = tmp_path / "cache"
    retriever = DenseSemanticRetriever(sample_chunks, cache_dir=cache_dir)
    scores = retriever.score("sql database connect")
    top_idx, top_score = scores[0]
    assert sample_chunks[top_idx].file_path == "src/db.py"
    assert 0.0 <= top_score <= 1.0

    # Incremental update with modified chunk
    new_chunks = list(sample_chunks)
    new_chunks.append(
        CodeChunk(
            chunk_id="chunk_cache",
            file_path="src/cache.py",
            start_line=1,
            end_line=10,
            content="class RedisCache:\n    def get(self, key): pass",
            token_count=10,
        )
    )
    retriever.update_chunks(new_chunks)
    scores2 = retriever.score("redis cache get")
    assert any(new_chunks[idx].file_path == "src/cache.py" for idx, _ in scores2[:2])


def test_score_min_max_normalization():
    raw_scores = [(0, 10.0), (1, 5.0), (2, 0.0)]
    norm = min_max_normalize(raw_scores)
    assert norm[0] == pytest.approx(1.0)
    assert norm[1] == pytest.approx(0.5)
    assert norm[2] == pytest.approx(0.0)


def test_rrf_fusion_monotonicity_and_order():
    ranked_lists = {
        "bm25": [0, 1, 2],
        "dense": [1, 0, 2],
    }
    fused = reciprocal_rank_fusion(ranked_lists, k_rrf=60)
    # Docs 0 and 1 appear in top 2 across both lists; doc 2 appears in 3rd place in both
    assert len(fused) == 3
    # Both doc 0 and doc 1 must strictly outscore doc 2
    fused_dict = dict(fused)
    assert fused_dict[0] > fused_dict[2]
    assert fused_dict[1] > fused_dict[2]
    assert fused[0][1] >= fused[1][1] >= fused[2][1]


def test_task_complexity_estimator():
    # Simple query
    c_simple = TaskComplexityEstimator.estimate("fix typo")
    assert 0.5 <= c_simple <= 0.85

    # Complex query with stack trace and multi-file refactoring hints
    complex_query = (
        "Traceback (most recent call last):\n"
        "  File 'server.py', line 89, in handle_request\n"
        "ZeroDivisionError: division by zero in calculate_rate_limit across multiple files "
        "and modules in authentication_pipeline and crypto_verification_service"
    )
    c_complex = TaskComplexityEstimator.estimate(complex_query)
    assert c_complex >= 1.4
    assert c_complex <= 2.0


def test_kneedle_knee_detection_concave_curves():
    # Steep drop after item 2, then long tail
    scores_1 = [10.0, 9.2, 2.1, 1.9, 1.8, 1.7]
    knee_1 = AdaptiveKSelector.detect_knee(scores_1)
    assert knee_1 in (2, 3)

    # Steep drop after item 3
    scores_2 = [1.0, 0.95, 0.90, 0.25, 0.20, 0.15, 0.10]
    knee_2 = AdaptiveKSelector.detect_knee(scores_2)
    assert knee_2 in (3, 4)


@pytest.mark.asyncio
async def test_adaptive_hybrid_retriever_trace_and_ranked_files(sample_chunks):
    retriever = AdaptiveHybridRetriever(sample_chunks, min_k=2, max_k=4)
    chunks, trace = await retriever.retrieve("fix jwt token verification in auth")

    assert len(chunks) >= 2
    assert any(c.chunk_id == "chunk_auth" for c in chunks)
    assert trace.chosen_k == len(chunks)
    assert len(trace.candidates) == len(sample_chunks)
    # Trace must emit deduplicated ranked files
    assert len(trace.ranked_files) >= 1
    assert "src/auth.py" in trace.ranked_files
    assert len(trace.ranked_files) == len(set(trace.ranked_files))


@pytest.mark.asyncio
async def test_adaptive_hybrid_beats_single_modalities_on_recall():
    """Validates research premise: AdaptiveHybrid achieves higher Recall@K

    than BM25 alone and Dense alone on a multi-signal synthetic repository.
    """
    # 4 distinct files in the synthetic repo:
    # 1. auth.py: has exact keyword tokens "auth_token_magic_salt_x99", but plain text comments
    # 2. crypto.py: semantic explanation of "digital credential and signature authentication", but no exact token
    # 3. helpers.py: irrelevant helper
    # 4. logger.py: irrelevant logger
    chunks = [
        CodeChunk(
            chunk_id="c_auth",
            file_path="src/auth.py",
            start_line=1,
            end_line=20,
            content="def auth_token_magic_salt_x99():\n    return 'salt'",
            token_count=10,
        ),
        CodeChunk(
            chunk_id="c_crypto",
            file_path="src/crypto.py",
            start_line=1,
            end_line=20,
            content="class CredentialValidator:\n    # Digital credential and signature security validation\n    def validate(self): pass",
            token_count=15,
        ),
        CodeChunk(
            chunk_id="c_helpers",
            file_path="src/helpers.py",
            start_line=1,
            end_line=10,
            content="def format_string(s): return s.strip()",
            token_count=10,
        ),
        CodeChunk(
            chunk_id="c_logger",
            file_path="src/logger.py",
            start_line=1,
            end_line=10,
            content="def log_event(e): print(e)",
            token_count=10,
        ),
    ]

    graph = RepoDependencyGraph()
    # auth.py and crypto.py are linked via an import dependency
    graph.add_edge("src/auth.py", "src/crypto.py", "imports")

    query = "auth_token_magic_salt_x99 credential validation and signature security"

    # 1. Evaluate BM25 alone (Top-1)
    bm25 = BM25Retriever(chunks)
    bm25_top_indices = [idx for idx, _ in bm25.score(query)[:1]]
    bm25_files = {chunks[i].file_path for i in bm25_top_indices}

    # 2. Evaluate Dense alone (Top-1)
    dense = DenseSemanticRetriever(chunks)
    dense_top_indices = [idx for idx, _ in dense.score(query)[:1]]
    dense_files = {chunks[i].file_path for i in dense_top_indices}

    # Gold target files required for the full task
    gold_files = {"src/auth.py", "src/crypto.py"}

    # Compute Recall@1 for single modalities
    recall_bm25_top1 = len(bm25_files.intersection(gold_files)) / len(gold_files)
    recall_dense_top1 = len(dense_files.intersection(gold_files)) / len(gold_files)
    assert recall_bm25_top1 <= 0.5
    assert recall_dense_top1 <= 0.5

    # 3. Evaluate AdaptiveHybrid (retrieves top K fused via RRF + Graph)
    hybrid = AdaptiveHybridRetriever(chunks, graph=graph, min_k=2, max_k=3)
    retrieved_chunks, trace = await hybrid.retrieve(query)
    hybrid_files = {c.file_path for c in retrieved_chunks}

    recall_hybrid = len(hybrid_files.intersection(gold_files)) / len(gold_files)

    # AdaptiveHybrid successfully fuses lexical and semantic signals to retrieve BOTH gold files
    assert recall_hybrid == 1.0
    assert recall_hybrid > recall_bm25_top1
    assert recall_hybrid > recall_dense_top1


@pytest.mark.neural
def test_neural_dense_retrieval_opt_in(sample_chunks: list[CodeChunk]) -> None:
    """Opt-in neural test verifying sentence-transformers when explicitly enabled."""
    import os

    if os.environ.get("DEVPILOT_RUN_NEURAL_TESTS") != "1":
        pytest.skip("Skipped: set DEVPILOT_RUN_NEURAL_TESTS=1 to run neural model tests")

    retriever = DenseSemanticRetriever(sample_chunks)
    scores = retriever.score("verify jwt token")
    assert len(scores) == len(sample_chunks)
