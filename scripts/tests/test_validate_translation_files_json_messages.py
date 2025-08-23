"""
Tests JSON messages for the validate_translation_files.py script.
"""

import icu
import pytest

from ..validate_translation_files import (
    validate_json_translation_messages,
)

from .. import validate_translation_files as validate_translation_files_module


@pytest.fixture(autouse=True)
def raise_exceptions_during_testing(monkeypatch):
    """
    Re-raise the exception for easier debugging.

    Normally icu.ICUError are handled gracefully and printed as errors.
    During testing, it's more convenient to raise them for more readable test debugging logs.
    """
    def mock_format_exception(e):
        # Re-raise the exception for easier debugging
        raise

    monkeypatch.setattr(validate_translation_files_module, 'format_exception', mock_format_exception)


def _validate_message(key, source, translation, target_locale='es'):
    """
    Validates one message against English source.

    Args:
        key: The message key/id
        source: English source message
        translation: Spanish translated message
        target_locale: The locale to be validated for.

    Returns:
        ValidationResult: Result of validation with is_valid and output
    """
    return validate_json_translation_messages(
        en_messages={key: source},
        target_locale=target_locale,
        target_messages={key: translation},
    )


def test_valid_json_message():
    result = validate_json_translation_messages(
        en_messages={"app_name": "The New Shiny Microfrontend"},
        target_locale='es',
        target_messages={"app_name": "Le app"},
    )

    assert result.is_valid, f"No errors: {result.output}"


def test_missing_variables_in_translation():
    """Test that missing variables in translation are detected."""
    result = _validate_message(
        key="welcome",
        source="Hello {username}, welcome to {appName}!",
        translation="¡Hola, bienvenido!"  # Missing both {username} and {appName}
    )

    assert not result.is_valid, f"Should be invalid: {result.output}"
    assert "Placeholder validation failed for 'es' -> 'welcome'" in result.output
    assert "source has ['appName', 'username']" in result.output
    assert "target has []" in result.output


def test_extra_variables_in_translation():
    """Test that extra variables in translation are detected."""
    result = _validate_message(
        key="simple_message",
        source="Welcome to our app!",
        translation="¡Benvenuto {appType} app!",  # Added extra {appType}
    )

    assert not result.is_valid, f"Should be invalid: {result.output}"
    assert "Placeholder validation failed for 'es' -> 'simple_message'" in result.output
    assert "source has []" in result.output
    assert "target has ['appType']" in result.output


def test_case_sensitive_variable_names():
    """Test that variable names are case-sensitive."""
    result = _validate_message(
        key="profile",
        source="Hello {UserName}!",
        translation="¡Hola {username}!",  # Changed case: UserName → username
    )

    assert not result.is_valid, f"Should be invalid: {result.output}"
    assert "Placeholder validation failed for 'es' -> 'profile'" in result.output
    assert "source has ['UserName']" in result.output
    assert "target has ['username']" in result.output


def test_valid_variables_with_complex_message():
    """Test that correctly translated variables in complex messages are valid."""
    result = _validate_message(
        key="complex",
        source="Hi {name}, you have {count, plural, one {# message} other {# messages}} from {sender}",
        translation="¡Hola {name}, you have {count, plural, one {# message} other {# messages}} en {sender}",
    )

    assert result.is_valid, f"Should be valid: {result.output}"


def test_missing_plural_hash_sign():
    """Test that missing # are spotted as invalid."""
    result = _validate_message(
        key="complex",
        source="Hi {name}, you have {count, plural, one {# message} other {# messages}} from {sender}",
        translation="¡Hola {name}, you have {count, plural, one {one message} other {several messages}} en {sender}",
    )

    assert not result.is_valid, f"Should be invalid: {result.output}"
    assert "source has ['#', 'count', 'name', 'sender']" in result.output
    assert "target has ['count', 'name', 'sender', 'several']" in result.output


def test_mixed_invalid_subtle_translation_issues():
    """
    Throws parsing errors when using the ICU parser.
    """
    with pytest.raises(icu.ICUError, match='Syntax error in format pattern'):
        _validate_message(
            key="invalid_msg",
            source="Remove member{memberCount, plural, one {} other {s}}?",
            # Causes parsing errors
            translation="Vai noņemt dalībnieku{memberCount, daudzskaitlī, vēl vienu {} citu {s}}?"
        )


def test_valid_singular_icu_message():
    """
    Ensure valid plurals accounting for cases where `one room` is used instead of `# room`.

    This is useful in cases the number placeholder (#) is not needed.
    """
    result = _validate_message(
        key="valid_plurals",
        source="{name} took {numPhotos, plural, =0 {no photos} =1 {one photo} other {# photos}} on {takenDate, date, long}.",  # noqa
        translation="El {takenDate, date, long}, {name} {numPhotos, plural, =0 {no} other {} } sacó {numPhotos, plural, =0 {ninguna foto.} =1 {una foto.} other {# fotos.}}"  # noqa
    )
    assert result.is_valid, f"Should be valid: {result.output}"
