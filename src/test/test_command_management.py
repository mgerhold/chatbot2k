"""Regression tests for command management overlap detection."""

from typing import Final
from typing import cast
from typing import final
from unittest.mock import MagicMock

import pytest

from chatbot2k.app_state import AppState
from chatbot2k.chats.chat import Chat
from chatbot2k.command_handlers.command_management_command import CommandManagementCommand
from chatbot2k.database.tables import StaticCommand
from chatbot2k.translation_key import TranslationKey
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.utils.regular_expressions import is_regex_pattern
from chatbot2k.utils.regular_expressions import parse_regular_expression

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chat_command(*arguments: str) -> ChatCommand:
    """Build a ChatCommand with the given arguments (source message/chat are unused by the tested logic)."""
    return ChatCommand(
        name="command",
        arguments=list(arguments),
        source_message=cast(ChatMessage, None),
        source_chat=cast(Chat, None),
    )


def _make_handler_mock(name: str) -> MagicMock:
    """Create a minimal CommandHandler mock that exposes name and regular_expression."""
    handler: Final = MagicMock()
    handler.name = name
    pattern: Final = parse_regular_expression(name)
    handler.regular_expression = pattern
    handler.is_regular_expression = is_regex_pattern(pattern)
    return handler


def _make_soundboard_mock(name: str) -> MagicMock:
    """Create a minimal soundboard command mock that exposes regular_expression."""
    cmd: Final = MagicMock()
    cmd.regular_expression = parse_regular_expression(name)
    return cmd


def _make_script_mock(name: str) -> MagicMock:
    """Create a minimal script mock that exposes regular_expression."""
    script: Final = MagicMock()
    script.regular_expression = parse_regular_expression(name)
    return script


@final
class _MockAppState:
    """Minimal AppState stub for testing _add_or_update_command."""

    def __init__(
        self,
        *,
        static_commands: list[StaticCommand] | None = None,
        parameterized_commands: list[MagicMock] | None = None,
        soundboard_commands: list[MagicMock] | None = None,
        scripts: list[MagicMock] | None = None,
        command_handlers: list[MagicMock] | None = None,
    ) -> None:
        self._static_commands: Final = static_commands or []
        self._parameterized_commands: Final = parameterized_commands or []
        self._soundboard_commands: Final = soundboard_commands or []
        self._scripts: Final = scripts or []
        self.command_handlers: Final = command_handlers or []  # type: ignore[assignment]

        mock_db = MagicMock()
        mock_db.get_static_commands.return_value = self._static_commands
        mock_db.get_parameterized_commands.return_value = self._parameterized_commands
        mock_db.get_soundboard_commands.return_value = self._soundboard_commands
        mock_db.get_scripts.return_value = self._scripts
        mock_db.add_static_command.return_value = None
        mock_db.remove_command_case_insensitive.return_value = True
        self.database: Final = mock_db

        mock_translations = MagicMock()
        mock_translations.get_translation.side_effect = str
        self.translations_manager: Final = mock_translations


def _add(app_state: _MockAppState, name: str, response: str = "ok") -> tuple[bool, str]:
    """Call _add_or_update_command with is_update=False."""
    return CommandManagementCommand._add_or_update_command(  # type: ignore[arg-type]
        cast(AppState, app_state),
        _make_chat_command("add", name, response),
        is_update=False,
    )


def _update(app_state: _MockAppState, name: str, response: str = "ok") -> tuple[bool, str]:
    """Call _add_or_update_command with is_update=True."""
    return CommandManagementCommand._add_or_update_command(  # type: ignore[arg-type]
        cast(AppState, app_state),
        _make_chat_command("update", name, response),
        is_update=True,
    )


# ---------------------------------------------------------------------------
# Regression tests for _add_or_update_command overlap detection
# ---------------------------------------------------------------------------


class TestAddOrUpdateCommandOverlapDetection:
    def test_add_unique_command_succeeds(self) -> None:
        state = _MockAppState(static_commands=[StaticCommand(name="existing", response="x")])
        success, _ = _add(state, "newcmd")
        assert success

    def test_add_command_that_already_exists_fails(self) -> None:
        state = _MockAppState(static_commands=[StaticCommand(name="hello", response="x")])
        success, msg = _add(state, "hello")
        assert not success
        assert TranslationKey.COMMAND_ALREADY_EXISTS in msg

    def test_add_command_overlapping_soundboard_fails(self) -> None:
        state = _MockAppState(soundboard_commands=[_make_soundboard_mock("clap")])
        success, msg = _add(state, "clap")
        assert not success
        assert TranslationKey.CANNOT_ADD_OR_UPDATE_SOUNDBOARD_COMMAND in msg

    def test_add_command_overlapping_soundboard_via_regex_fails(self) -> None:
        # The soundboard has a pattern "clap[0-9]"; adding "clap5" should fail.
        state = _MockAppState(soundboard_commands=[_make_soundboard_mock("clap[0-9]")])
        success, msg = _add(state, "clap5")
        assert not success
        assert TranslationKey.CANNOT_ADD_OR_UPDATE_SOUNDBOARD_COMMAND in msg

    def test_add_command_not_overlapping_soundboard_succeeds(self) -> None:
        state = _MockAppState(soundboard_commands=[_make_soundboard_mock("clap")])
        success, _ = _add(state, "wave")
        assert success

    def test_add_command_overlapping_script_fails(self) -> None:
        state = _MockAppState(scripts=[_make_script_mock("mybot")])
        success, msg = _add(state, "mybot")
        assert not success
        assert TranslationKey.CANNOT_ADD_OR_UPDATE_SCRIPT_COMMAND in msg

    def test_add_command_overlapping_builtin_handler_fails(self) -> None:
        state = _MockAppState(command_handlers=[_make_handler_mock("command")])
        success, msg = _add(state, "command")
        assert not success
        assert TranslationKey.BUILTIN_COMMAND_CANNOT_BE_CHANGED in msg

    def test_add_command_not_overlapping_builtin_handler_succeeds(self) -> None:
        state = _MockAppState(command_handlers=[_make_handler_mock("command")])
        success, _ = _add(state, "mycommand")
        assert success

    def test_update_existing_command_succeeds(self) -> None:
        state = _MockAppState(static_commands=[StaticCommand(name="hello", response="x")])
        success, msg = _update(state, "hello", "new response")
        assert success
        assert TranslationKey.COMMAND_UPDATED in msg

    def test_update_nonexistent_command_fails(self) -> None:
        state = _MockAppState()
        success, msg = _update(state, "missing")
        assert not success
        assert TranslationKey.COMMAND_TO_UPDATE_NOT_FOUND in msg

    def test_update_command_that_causes_ambiguity_fails(self) -> None:
        # "hello" exists. Trying to update "hell[o]" (regex matching "hello") should fail
        # because it does NOT have the same pattern as the existing "hello" command.
        state = _MockAppState(static_commands=[StaticCommand(name="hello", response="x")])
        success, msg = _update(state, "hell[o]", "new response")
        assert not success
        assert TranslationKey.COMMAND_UPDATE_CAUSES_AMBIGUITY in msg

    def test_add_with_many_existing_commands_detects_overlap(self) -> None:
        """Ensure overlap detection still works when there are many existing commands."""
        existing = [StaticCommand(name=f"cmd{i:03d}", response="x") for i in range(50)]
        state = _MockAppState(static_commands=existing)

        # Adding a duplicate should fail.
        success, msg = _add(state, "cmd025")
        assert not success
        assert TranslationKey.COMMAND_ALREADY_EXISTS in msg

    def test_add_with_many_existing_commands_unique_succeeds(self) -> None:
        """Ensure a unique command can still be added when there are many existing commands."""
        existing = [StaticCommand(name=f"cmd{i:03d}", response="x") for i in range(50)]
        state = _MockAppState(static_commands=existing)

        success, _ = _add(state, "newcommand")
        assert success

    def test_overlap_check_covers_all_soundboard_commands(self) -> None:
        """Conflict with any soundboard command in a large list should be detected."""
        soundboard = [_make_soundboard_mock(f"sound{i}") for i in range(30)]
        state = _MockAppState(soundboard_commands=soundboard)

        success, msg = _add(state, "sound15")
        assert not success
        assert TranslationKey.CANNOT_ADD_OR_UPDATE_SOUNDBOARD_COMMAND in msg

    def test_overlap_check_covers_all_script_commands(self) -> None:
        """Conflict with any script in a large list should be detected."""
        scripts = [_make_script_mock(f"script{i}") for i in range(30)]
        state = _MockAppState(scripts=scripts)

        success, msg = _add(state, "script15")
        assert not success
        assert TranslationKey.CANNOT_ADD_OR_UPDATE_SCRIPT_COMMAND in msg


@pytest.mark.parametrize(
    ("existing_names", "new_name", "should_succeed"),
    [
        (["aa", "bb", "cc"], "dd", True),
        (["aa", "bb", "cc"], "aa", False),
        (["aa", "bb", "cc"], "bb", False),
        (["aa", "bb", "cc"], "cc", False),
        ([], "anything", True),
        (["cmd[0-9]"], "cmd5", False),
        (["cmd[0-9]"], "cmd", True),
    ],
)
def test_add_parametrized_overlap(existing_names: list[str], new_name: str, should_succeed: bool) -> None:
    existing = [StaticCommand(name=n, response="x") for n in existing_names]
    state = _MockAppState(static_commands=existing)
    success, _ = _add(state, new_name)
    assert success == should_succeed


# ---------------------------------------------------------------------------
# Case-insensitivity tests
# ---------------------------------------------------------------------------
# `parse_regular_expression()` always lower-cases its input before building the
# Pattern, so `parse_regular_expression("HELLO")` and `parse_regular_expression("hello")`
# return the exact same cached object. The `==` in `_triggers_overlap()` therefore compares
# two identical objects regardless of the original casing — always `True`.


@pytest.mark.parametrize(
    ("existing_name", "new_name"),
    [
        ("hello", "HELLO"),  # uppercase new name
        ("hello", "Hello"),  # title-case new name
        ("hello", "hElLo"),  # arbitrary mixed-case new name
        ("HELLO", "hello"),  # uppercase existing, lowercase new
        ("HELLO", "Hello"),  # uppercase existing, title-case new
        ("Hello", "hElLo"),  # both mixed-case
        ("MyCommand", "mycommand"),  # realistic mixed-case
        ("mycommand", "MyCommand"),  # realistic mixed-case (reverse)
    ],
)
def test_case_insensitive_conflict(existing_name: str, new_name: str) -> None:
    """Overlap detection is case-insensitive: 'HELLO' and 'hello' describe the same trigger."""
    state: Final = _MockAppState(static_commands=[StaticCommand(name=existing_name, response="x")])
    success, msg = _add(state, new_name)
    assert not success, f"Adding '{new_name}' when '{existing_name}' exists should be rejected"
    assert TranslationKey.COMMAND_ALREADY_EXISTS in msg


# ---------------------------------------------------------------------------
# Regression tests for lookup_command with regex-escaped special characters
# ---------------------------------------------------------------------------
# Commands whose names contain regex escape sequences (e.g. `anders\+\+` for
# the literal trigger `anders++`) must still be matched when users invoke them.
# Previously, the non-regex fast-path in `lookup_command()` compared `handler.name`
# (which contains the raw escape sequences) against the normalized user input
# (which contains the literal characters), causing the lookup to always fail.


@pytest.mark.parametrize(
    ("stored_name", "trigger"),
    [
        ("anders\\+\\+", "!anders++"),  # production case: plus signs
        ("hello\\?", "!hello?"),  # question mark
        ("test\\.result", "!test.result"),  # dot
        ("cmd\\*", "!cmd*"),  # asterisk
        ("my\\(cmd\\)", "!my(cmd)"),  # parentheses
    ],
)
def test_lookup_command_with_regex_escaped_special_characters(stored_name: str, trigger: str) -> None:
    """Commands whose stored names use regex escaping for special characters must be triggerable."""
    handler: Final = _make_handler_mock(stored_name)
    mock_state: Final = MagicMock(spec=AppState)
    mock_state.command_handlers = [handler]
    result: Final = AppState.lookup_command(mock_state, trigger)
    assert result is handler, (
        f"Command stored as '{stored_name!r}' should be triggered by '{trigger}', but lookup returned None"
    )


def test_lookup_command_plain_name_still_works() -> None:
    """Plain (non-escaped) command names must still be found after the fix."""
    handler: Final = _make_handler_mock("simple")
    mock_state: Final = MagicMock(spec=AppState)
    mock_state.command_handlers = [handler]
    assert AppState.lookup_command(mock_state, "!simple") is handler
    assert AppState.lookup_command(mock_state, "!other") is None
