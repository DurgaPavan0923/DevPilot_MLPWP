"""Unit tests for feedback classifier, error signature hashing, and loop detection."""

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.recovery.classifier import ErrorClassifier
from devpilot.recovery.hasher import ErrorSignatureHasher
from devpilot.recovery.loop_detector import LoopDetector
from devpilot.recovery.policy import EscalationLevel, RecoveryPolicy


def test_error_classifier():
    assert ErrorClassifier.classify("SyntaxError: invalid syntax") == ErrorTypeEnum.SYNTAX
    assert (
        ErrorClassifier.classify("ModuleNotFoundError: No module named 'xyz'")
        == ErrorTypeEnum.IMPORT
    )
    assert (
        ErrorClassifier.classify("AssertionError: 1 != 2\nFAILED tests/test_a.py")
        == ErrorTypeEnum.TEST_FAILURE
    )
    assert ErrorClassifier.classify("timed out after 60.0s") == ErrorTypeEnum.TIMEOUT
    assert ErrorClassifier.classify("Path traversal detected") == ErrorTypeEnum.PERMISSION
    assert ErrorClassifier.classify("target block was not found") == ErrorTypeEnum.TOOL_MISUSE


def test_error_signature_hasher_invariance():
    # Errors differing only by volatile line numbers or addresses must produce identical signature hash!
    err1 = "File 'src/main.py', line 45, in run: 0x7ffd1234: NullPointer"
    err2 = "File 'src/main.py', line 99, in run: 0x7ffd5678: NullPointer"

    hash1 = ErrorSignatureHasher.hash_error(err1)
    hash2 = ErrorSignatureHasher.hash_error(err2)
    assert hash1 == hash2


def test_loop_detector_repeated_action():
    detector = LoopDetector(repetition_threshold=3)

    detector.record_action("read_file", {"path": "a.py"})
    detector.record_action("read_file", {"path": "a.py"})
    is_loop, _ = detector.is_action_looping()
    assert is_loop is False

    detector.record_action("read_file", {"path": "a.py"})
    is_loop, reason = detector.is_action_looping()
    assert is_loop is True
    assert "Action loop detected" in reason


def test_loop_detector_ping_pong():
    detector = LoopDetector(repetition_threshold=3)

    # Ping pong pattern: Action A -> Action B -> Action A -> Action B
    detector.record_action("read_file", {"path": "a.py"})
    detector.record_action("edit_file", {"path": "a.py"})
    detector.record_action("read_file", {"path": "a.py"})
    detector.record_action("edit_file", {"path": "a.py"})

    is_loop, reason = detector.is_action_looping()
    assert is_loop is True
    assert "Alternating cycle loop detected" in reason


def test_recovery_escalation_ladder():
    policy = RecoveryPolicy(global_retry_cap=4, per_signature_cap=2)

    # Attempt 1: Level 1 (Retry with context)
    t1 = ToolResult(
        ok=False, output="SyntaxError: invalid syntax in a_1", error_type=ErrorTypeEnum.SYNTAX
    )
    act1 = policy.handle_tool_error("edit_file", {"path": "a_1.py"}, t1)
    assert act1.level == EscalationLevel.RETRY_WITH_CONTEXT
    assert act1.should_abort is False

    # Attempt 2: Level 2 (Re-retrieve)
    t2 = ToolResult(
        ok=False, output="ImportError: cannot import name foo", error_type=ErrorTypeEnum.IMPORT
    )
    act2 = policy.handle_tool_error("edit_file", {"path": "a_2.py"}, t2)
    assert act2.level == EscalationLevel.RE_RETRIEVE_CONTEXT

    # Attempt 3: Level 3 (Switch approach)
    t3 = ToolResult(
        ok=False, output="AssertionError: 1 != 2 in test_a", error_type=ErrorTypeEnum.TEST_FAILURE
    )
    act3 = policy.handle_tool_error("edit_file", {"path": "a_3.py"}, t3)
    assert act3.level == EscalationLevel.SWITCH_APPROACH

    # Attempt 4: Level 4 (Reduce scope)
    t4 = ToolResult(
        ok=False, output="TimeoutError: command timed out", error_type=ErrorTypeEnum.TIMEOUT
    )
    act4 = policy.handle_tool_error("edit_file", {"path": "a_4.py"}, t4)
    assert act4.level == EscalationLevel.REDUCE_SCOPE

    # Attempt 5: Exceeds global cap => Level 5 (Abort)
    t5 = ToolResult(
        ok=False, output="EnvironmentError: disk full", error_type=ErrorTypeEnum.ENVIRONMENT
    )
    act5 = policy.handle_tool_error("edit_file", {"path": "a_5.py"}, t5)
    assert act5.level == EscalationLevel.ABORT
    assert act5.should_abort is True
