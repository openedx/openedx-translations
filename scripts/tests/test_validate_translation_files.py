"""
Tests for the validate_translation_files.py script.
"""

import os.path
import re
import pytest
from argparse import ArgumentParser

from ..validate_translation_files import (
    get_translation_files,
    validate_translation_files,
    parse_types_argument,
)

SCRIPT_DIR = os.path.dirname(__file__)


def test_get_translation_files():
    """
    Ensure `get_translation_files` skips the source translation files and non-po files.
    """
    mock_translations_dir = os.path.join(SCRIPT_DIR, 'mock_translations_dir')
    files_sorted = sorted(get_translation_files(mock_translations_dir))
    relative_files = [
        os.path.relpath(f, mock_translations_dir)
        for f in files_sorted
    ]

    assert relative_files == [
        'demo-microfrontend/src/i18n/messages/ar.json',
        'demo-microfrontend/src/i18n/messages/es.json',
        'demo-microfrontend/src/i18n/messages/fr.json',
        'demo-xblock/conf/locale/ar/LC_MESSAGES/django.po',
        'demo-xblock/conf/locale/de_DE/LC_MESSAGES/django.po',
        'demo-xblock/conf/locale/hi/LC_MESSAGES/django.po',
    ]


def test_main_on_invalid_files(capsys):
    """
    Integration test for the `main` function on some invalid files.
    """
    mock_translations_dir = os.path.join(SCRIPT_DIR, 'mock_translations_dir')
    exit_code = validate_translation_files(mock_translations_dir)
    out, err = capsys.readouterr()

    assert 'VALID:' in out, 'Valid files should be printed in stdout'
    assert 'de_DE/LC_MESSAGES/django.po' in out, 'German translation file should be found valid'
    assert 'ar/LC_MESSAGES/django.po' in out, 'Arabic translation file should be found valid'
    assert 'messages/ar.json' in out, 'Arabic json translation file should be found valid'
    assert 'messages/es.json' in out, 'Spanish json translation file should be found valid'
    assert 'hi/LC_MESSAGES/django.po' not in out, 'Invalid file should be printed in stderr'
    assert 'en/LC_MESSAGES/django.po' not in out, 'Source file should not be validated'

    assert re.search(r'INVALID: .*messages/fr.json', err), 'French should be found invalid'
    assert re.search(r'INVALID: .*locale/hi/LC_MESSAGES/django.po', err)
    assert '\'msgstr\' is not a valid Python brace format string, unlike \'msgid\'' in err
    assert 'welcome_message: Different number of variables: [username, count] vs []' in err, 'Catch invalid placeholders'
    assert 'FAILURE: Some translations are invalid.' in err

    assert exit_code == 1, 'Should fail due to invalid hi/LC_MESSAGES/django.po file'


def test_main_on_valid_files(capsys):
    """
    Integration test for the `main` function but only for the Arabic translations which is valid.
    """
    mock_translations_dir = os.path.join(SCRIPT_DIR, 'mock_translations_dir/demo-xblock/conf/locale/ar')
    exit_code = validate_translation_files(mock_translations_dir)
    out, err = capsys.readouterr()

    assert 'VALID:' in out, 'Valid files should be printed in stdout'
    assert 'ar/LC_MESSAGES/django.po' in out, 'Arabic translation file is valid'
    assert 'SUCCESS: All translation files are valid.' in out
    assert not err.strip(), 'The stderr should be empty'
    assert exit_code == 0, 'Should succeed due in validating the ar/LC_MESSAGES/django.po file'


class MockArgs:
    """Mock args class for testing parse_types_argument"""
    def __init__(self, types):
        self.types = types


def test_parse_types_argument_valid_types():
    """Test parse_types_argument with valid type combinations"""
    parser = ArgumentParser()

    # Test single valid type
    args = MockArgs('json')
    result = parse_types_argument(parser, args)
    assert result == ['json']

    # Test multiple valid types
    args = MockArgs('json,po')
    result = parse_types_argument(parser, args)
    assert result == ['json', 'po']

    # Test with spaces
    args = MockArgs('json, po')
    result = parse_types_argument(parser, args)
    assert result == ['json', 'po']

    # Test reversed order
    args = MockArgs('po,json')
    result = parse_types_argument(parser, args)
    assert result == ['po', 'json']


def test_parse_types_argument_invalid_types():
    """Test parse_types_argument with invalid types raises SystemExit"""
    parser = ArgumentParser()

    # Test invalid type
    args = MockArgs('invalid')
    with pytest.raises(SystemExit):
        parse_types_argument(parser, args)

    # Test mix of valid and invalid types
    args = MockArgs('json,invalid')
    with pytest.raises(SystemExit):
        parse_types_argument(parser, args)

    # Test multiple invalid types
    args = MockArgs('invalid1,invalid2')
    with pytest.raises(SystemExit):
        parse_types_argument(parser, args)


def test_parse_types_argument_empty_and_whitespace():
    """Test parse_types_argument handles empty strings and whitespace"""
    parser = ArgumentParser()

    # Test empty string
    args = MockArgs('')
    result = parse_types_argument(parser, args)
    assert result == []

    # Test whitespace only
    args = MockArgs('   ')
    result = parse_types_argument(parser, args)
    assert result == []

    # Test comma only
    args = MockArgs(',')
    result = parse_types_argument(parser, args)
    assert result == []

    # Test mixed empty elements
    args = MockArgs('json, , po')
    result = parse_types_argument(parser, args)
    assert result == ['json', 'po']
