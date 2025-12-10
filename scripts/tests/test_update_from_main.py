"""
Tests for update_from_main.py
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from ..update_from_main import (
    merge_translations,
    find_translation_files,
    process_json_file,
    process_po_file,
    fetch_upstream_file,
)


class TestMergeTranslations:
    """Tests for merge_translations function."""

    def test_merge_adds_new_keys(self):
        """Test that new keys from upstream are added to current."""
        current = {"key1": "value1", "key2": "value2"}
        upstream = {"key2": "different_value", "key3": "value3", "key4": "value4"}
        
        result = merge_translations(current, upstream)
        
        assert "key1" in result
        assert "key2" in result
        assert "key3" in result
        assert "key4" in result
        assert result["key1"] == "value1"
        assert result["key2"] == "value2"  # Preserves current value
        assert result["key3"] == "value3"  # Adds new key
        assert result["key4"] == "value4"  # Adds new key

    def test_merge_preserves_existing_translations(self):
        """Test that existing translations are not overridden."""
        current = {"greeting": "Olá"}
        upstream = {"greeting": "Hello", "farewell": "Goodbye"}
        
        result = merge_translations(current, upstream)
        
        assert result["greeting"] == "Olá"  # Not overridden
        assert result["farewell"] == "Goodbye"  # Added

    def test_merge_with_empty_current(self):
        """Test merging when current dictionary is empty."""
        current = {}
        upstream = {"key1": "value1", "key2": "value2"}
        
        result = merge_translations(current, upstream)
        
        assert result == upstream

    def test_merge_with_empty_upstream(self):
        """Test merging when upstream dictionary is empty."""
        current = {"key1": "value1", "key2": "value2"}
        upstream = {}
        
        result = merge_translations(current, upstream)
        
        assert result == current

    def test_merge_sorts_keys(self):
        """Test that result keys are sorted alphabetically."""
        current = {"z_key": "value", "a_key": "value"}
        upstream = {"m_key": "value"}
        
        result = merge_translations(current, upstream)
        
        keys = list(result.keys())
        assert keys == sorted(keys)
        assert keys == ["a_key", "m_key", "z_key"]


class TestFindTranslationFiles:
    """Tests for find_translation_files function."""

    def test_find_json_files_specific_language(self, tmp_path):
        """Test finding JSON files for a specific language."""
        # Create test structure
        (tmp_path / "app1" / "i18n").mkdir(parents=True)
        (tmp_path / "app2" / "messages").mkdir(parents=True)
        (tmp_path / "app1" / "i18n" / "pt_PT.json").touch()
        (tmp_path / "app2" / "messages" / "pt_PT.json").touch()
        (tmp_path / "app2" / "messages" / "es_419.json").touch()
        
        files = find_translation_files(tmp_path, ["pt_PT"], file_type="json")
        
        assert len(files) == 2
        assert all(f.name == "pt_PT.json" for f in files)

    def test_find_po_files_specific_language(self, tmp_path):
        """Test finding PO files for a specific language."""
        # Create test structure
        po_dir = tmp_path / "app1" / "locale" / "pt_PT" / "LC_MESSAGES"
        po_dir.mkdir(parents=True)
        (po_dir / "django.po").touch()
        (po_dir / "djangojs.po").touch()
        
        es_dir = tmp_path / "app1" / "locale" / "es_419" / "LC_MESSAGES"
        es_dir.mkdir(parents=True)
        (es_dir / "django.po").touch()
        
        files = find_translation_files(tmp_path, ["pt_PT"], file_type="po")
        
        assert len(files) == 2
        assert all("pt_PT" in str(f) for f in files)

    def test_find_all_json_files(self, tmp_path):
        """Test finding all JSON files when no language specified."""
        (tmp_path / "app1").mkdir()
        (tmp_path / "app1" / "pt_PT.json").touch()
        (tmp_path / "app1" / "es_419.json").touch()
        (tmp_path / "app1" / "fr_CA.json").touch()
        
        files = find_translation_files(tmp_path, None, file_type="json")
        
        assert len(files) == 3

    def test_find_both_file_types(self, tmp_path):
        """Test finding both JSON and PO files."""
        (tmp_path / "app1").mkdir()
        (tmp_path / "app1" / "pt_PT.json").touch()
        
        po_dir = tmp_path / "app1" / "locale" / "pt_PT" / "LC_MESSAGES"
        po_dir.mkdir(parents=True)
        (po_dir / "django.po").touch()
        
        files = find_translation_files(tmp_path, ["pt_PT"], file_type="both")
        
        assert len(files) == 2
        json_files = [f for f in files if f.suffix == ".json"]
        po_files = [f for f in files if f.suffix == ".po"]
        assert len(json_files) == 1
        assert len(po_files) == 1

    def test_find_multiple_languages(self, tmp_path):
        """Test finding files for multiple languages."""
        (tmp_path / "app1").mkdir()
        (tmp_path / "app1" / "pt_PT.json").touch()
        (tmp_path / "app1" / "es_419.json").touch()
        (tmp_path / "app1" / "fr_CA.json").touch()
        
        files = find_translation_files(tmp_path, ["pt_PT", "es_419"], file_type="json")
        
        assert len(files) == 2
        file_names = {f.name for f in files}
        assert file_names == {"pt_PT.json", "es_419.json"}

    def test_find_returns_sorted_list(self, tmp_path):
        """Test that results are sorted."""
        (tmp_path / "z_app").mkdir()
        (tmp_path / "a_app").mkdir()
        (tmp_path / "z_app" / "pt_PT.json").touch()
        (tmp_path / "a_app" / "pt_PT.json").touch()
        
        files = find_translation_files(tmp_path, ["pt_PT"], file_type="json")
        
        assert len(files) == 2
        assert str(files[0]) < str(files[1])  # Verify sorted order


class TestProcessJsonFile:
    """Tests for process_json_file function."""

    @patch('scripts.update_from_main.fetch_upstream_file')
    def test_process_json_adds_new_keys(self, mock_fetch, tmp_path):
        """Test that processing adds new keys from upstream."""
        # Setup local file
        local_file = tmp_path / "translations" / "app" / "pt_PT.json"
        local_file.parent.mkdir(parents=True)
        local_data = {"existing": "translation"}
        local_file.write_text(json.dumps(local_data, indent=2))
        
        # Setup upstream content
        upstream_data = {"existing": "different", "new_key": "new translation"}
        mock_fetch.return_value = json.dumps(upstream_data)
        
        # Process file
        result = process_json_file(
            local_file=local_file,
            upstream_repo=Path("/fake/repo"),
            branch="main",
            root_dir=tmp_path,
            dry_run=False
        )
        
        assert result is True
        
        # Verify merged content
        with open(local_file, 'r') as f:
            merged = json.load(f)
        
        assert merged["existing"] == "translation"  # Preserved
        assert merged["new_key"] == "new translation"  # Added

    @patch('scripts.update_from_main.fetch_upstream_file')
    def test_process_json_dry_run(self, mock_fetch, tmp_path):
        """Test that dry run doesn't modify files."""
        local_file = tmp_path / "translations" / "app" / "pt_PT.json"
        local_file.parent.mkdir(parents=True)
        local_data = {"existing": "translation"}
        local_file.write_text(json.dumps(local_data, indent=2))
        
        upstream_data = {"existing": "different", "new_key": "new translation"}
        mock_fetch.return_value = json.dumps(upstream_data)
        
        result = process_json_file(
            local_file=local_file,
            upstream_repo=Path("/fake/repo"),
            branch="main",
            root_dir=tmp_path,
            dry_run=True
        )
        
        assert result is True
        
        # Verify file was not modified
        with open(local_file, 'r') as f:
            content = json.load(f)
        
        assert content == local_data

    @patch('scripts.update_from_main.fetch_upstream_file')
    def test_process_json_no_changes(self, mock_fetch, tmp_path):
        """Test that no changes returns False."""
        local_file = tmp_path / "translations" / "app" / "pt_PT.json"
        local_file.parent.mkdir(parents=True)
        local_data = {"key": "value"}
        local_file.write_text(json.dumps(local_data, indent=2))
        
        # Upstream has same content
        mock_fetch.return_value = json.dumps(local_data)
        
        result = process_json_file(
            local_file=local_file,
            upstream_repo=Path("/fake/repo"),
            branch="main",
            root_dir=tmp_path,
            dry_run=False
        )
        
        assert result is False

    @patch('scripts.update_from_main.fetch_upstream_file')
    def test_process_json_missing_upstream(self, mock_fetch, tmp_path):
        """Test handling of missing upstream file."""
        local_file = tmp_path / "translations" / "app" / "pt_PT.json"
        local_file.parent.mkdir(parents=True)
        local_file.write_text(json.dumps({"key": "value"}))
        
        mock_fetch.return_value = None
        
        result = process_json_file(
            local_file=local_file,
            upstream_repo=Path("/fake/repo"),
            branch="main",
            root_dir=tmp_path,
            dry_run=False
        )
        
        assert result is False

    @patch('scripts.update_from_main.fetch_upstream_file')
    def test_process_json_invalid_local_json(self, mock_fetch, tmp_path):
        """Test handling of invalid local JSON."""
        local_file = tmp_path / "translations" / "app" / "pt_PT.json"
        local_file.parent.mkdir(parents=True)
        local_file.write_text("invalid json{")
        
        result = process_json_file(
            local_file=local_file,
            upstream_repo=Path("/fake/repo"),
            branch="main",
            root_dir=tmp_path,
            dry_run=False
        )
        
        assert result is False


class TestProcessPoFile:
    """Tests for process_po_file function."""

    @patch('scripts.update_from_main.fetch_upstream_file')
    @patch('scripts.update_from_main.run_command')
    def test_process_po_file_success(self, mock_run_command, mock_fetch, tmp_path):
        """Test successful PO file processing."""
        local_file = tmp_path / "translations" / "app" / "locale" / "pt_PT" / "LC_MESSAGES" / "django.po"
        local_file.parent.mkdir(parents=True)
        
        local_content = '''msgid "hello"
msgstr "olá"
'''
        local_file.write_text(local_content)
        
        upstream_content = '''msgid "hello"
msgstr "olá updated"

msgid "goodbye"
msgstr "adeus"
'''
        mock_fetch.return_value = upstream_content
        
        # Mock msgcat output
        merged_content = '''msgid "goodbye"
msgstr "adeus"

msgid "hello"
msgstr "olá updated"
'''
        mock_run_command.return_value = MagicMock(
            returncode=0,
            stdout=merged_content
        )
        
        result = process_po_file(
            local_file=local_file,
            upstream_repo=Path("/fake/repo"),
            branch="main",
            root_dir=tmp_path,
            dry_run=False
        )
        
        assert result is True
        # Verify msgcat was called with correct arguments
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "msgcat"
        assert "--use-first" in call_args
        assert "--no-wrap" in call_args
        assert "--sort-output" in call_args

    @patch('scripts.update_from_main.fetch_upstream_file')
    @patch('scripts.update_from_main.run_command')
    def test_process_po_file_dry_run(self, mock_run_command, mock_fetch, tmp_path):
        """Test PO file processing in dry run mode."""
        local_file = tmp_path / "translations" / "app" / "locale" / "pt_PT" / "LC_MESSAGES" / "django.po"
        local_file.parent.mkdir(parents=True)
        
        original_content = 'msgid "test"\nmsgstr "teste"\n'
        local_file.write_text(original_content)
        
        mock_fetch.return_value = 'msgid "test"\nmsgstr "teste updated"\n'
        
        mock_run_command.return_value = MagicMock(
            returncode=0,
            stdout='msgid "test"\nmsgstr "teste updated"\n'
        )
        
        result = process_po_file(
            local_file=local_file,
            upstream_repo=Path("/fake/repo"),
            branch="main",
            root_dir=tmp_path,
            dry_run=True
        )
        
        assert result is True
        # Verify file was not modified
        assert local_file.read_text() == original_content

    @patch('scripts.update_from_main.fetch_upstream_file')
    def test_process_po_file_missing_upstream(self, mock_fetch, tmp_path):
        """Test handling of missing upstream PO file."""
        local_file = tmp_path / "translations" / "app" / "locale" / "pt_PT" / "LC_MESSAGES" / "django.po"
        local_file.parent.mkdir(parents=True)
        local_file.write_text('msgid "test"\nmsgstr "teste"\n')
        
        mock_fetch.return_value = None
        
        result = process_po_file(
            local_file=local_file,
            upstream_repo=Path("/fake/repo"),
            branch="main",
            root_dir=tmp_path,
            dry_run=False
        )
        
        assert result is False

    @patch('scripts.update_from_main.fetch_upstream_file')
    @patch('scripts.update_from_main.run_command')
    def test_process_po_file_msgcat_failure(self, mock_run_command, mock_fetch, tmp_path):
        """Test handling of msgcat command failure."""
        local_file = tmp_path / "translations" / "app" / "locale" / "pt_PT" / "LC_MESSAGES" / "django.po"
        local_file.parent.mkdir(parents=True)
        local_file.write_text('msgid "test"\nmsgstr "teste"\n')
        
        mock_fetch.return_value = 'msgid "test"\nmsgstr "teste"\n'
        
        # Mock msgcat failure
        mock_run_command.return_value = MagicMock(
            returncode=1,
            stderr="msgcat error"
        )
        
        result = process_po_file(
            local_file=local_file,
            upstream_repo=Path("/fake/repo"),
            branch="main",
            root_dir=tmp_path,
            dry_run=False
        )
        
        assert result is False


class TestFetchUpstreamFile:
    """Tests for fetch_upstream_file function."""

    @patch('scripts.update_from_main.run_command')
    def test_fetch_existing_file(self, mock_run_command):
        """Test fetching an existing file from upstream."""
        mock_run_command.return_value = MagicMock(
            stdout='{"key": "value"}'
        )
        
        result = fetch_upstream_file(
            repo_path=Path("/fake/repo"),
            branch="main",
            file_path="translations/app/pt_PT.json"
        )
        
        assert result == '{"key": "value"}'
        mock_run_command.assert_called_once()
        call_args = mock_run_command.call_args[0][0]
        assert call_args == ["git", "show", "main:translations/app/pt_PT.json"]

    @patch('scripts.update_from_main.run_command')
    def test_fetch_nonexistent_file(self, mock_run_command):
        """Test fetching a non-existent file returns None."""
        from subprocess import CalledProcessError
        mock_run_command.side_effect = CalledProcessError(128, 'git show')
        
        result = fetch_upstream_file(
            repo_path=Path("/fake/repo"),
            branch="main",
            file_path="nonexistent.json"
        )
        
        assert result is None
