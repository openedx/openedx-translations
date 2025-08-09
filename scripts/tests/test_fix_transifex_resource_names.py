"""
Tests for fix_transifex_resource_names.py.
"""

from contextlib import contextmanager
from dataclasses import dataclass
import pytest

from unittest.mock import patch, MagicMock
from ..fix_transifex_resource_names import (
    get_repo_name_from_resource,
    get_repo_slug_from_resource,
    parse_arguments,
)


@dataclass
class ParsedArguments:
    force_suffix: bool = False
    dry_run: bool = False
    tx_project_slug: str = 'openedx-translations'


@pytest.fixture(autouse=True)
def mock_random_choice(monkeypatch):
    monkeypatch.setattr('random.choice', lambda x: '9')


def test_get_repo_slug_from_resource_with_no_categories():
    resource = MagicMock()
    resource.slug = 'translations-my-xblock-conf-locale-en-lc-messages-django-po--main'
    resource.categories = []
    assert get_repo_slug_from_resource(resource) == 'my-xblock-r999999'


def test_get_repo_slug_from_resource_slug_js_with_no_categories():
    resource = MagicMock()
    resource.slug = 'translations-my-xblock-conf-locale-en-lc-messages-djangojs-po--main'
    resource.categories = []
    assert get_repo_slug_from_resource(resource) == 'my-xblock-js-r999999'


def test_get_repo_name_from_invalid_slug():
    resource = MagicMock()
    resource.slug = 'some-gibberish-slug'
    resource.categories = []
    assert get_repo_name_from_resource(resource) == None


def test_get_repo_name_from_slug_and_categories():
    """
    Categories takes precedence over slug.
    """
    resource = MagicMock()
    resource.slug = 'translations-my-xblock1-conf-locale-en-lc-messages-django-po--main'
    resource.categories = ['github#repository:openedx/openedx-translations#branch:main#path:translations/my-xblock2/openassessment/conf/locale/en/LC_MESSAGES/django.po']  # noqa
    assert get_repo_name_from_resource(resource) == 'my-xblock2'


def test_get_repo_name_from_categories():
    resource = MagicMock()
    resource.slug = 'some-gibberish-slug'
    resource.categories = ['github#repository:openedx/openedx-translations#branch:main#path:translations/my-xblock2/openassessment/conf/locale/en/LC_MESSAGES/django.po']  # noqa
    assert get_repo_name_from_resource(resource) == 'my-xblock2'


def test_get_repo_name_from_categories_with_js():
    resource = MagicMock()
    resource.slug = 'some-gibberish-slug'
    resource.categories = ['github#repository:openedx/openedx-translations#branch:main#path:translations/my-xblock2/openassessment/conf/locale/en/LC_MESSAGES/djangojs.po']  # noqa
    assert get_repo_name_from_resource(resource) == 'my-xblock2-js'


def test_get_repo_slug_from_resource_with_existing_suffix():
    resource = MagicMock()
    resource.slug = 'my-resource-r123456'
    resource.name = 'my-resource-r123456'
    resource.categories = []
    # Should keep the existing suffix without adding a new one
    assert get_repo_slug_from_resource(resource) == 'my-resource-r123456'


def test_get_repo_slug_from_resource_with_clean_name():
    resource = MagicMock()
    resource.slug = 'clean-name'
    resource.name = 'Clean Name'  # Clean name in title case
    resource.categories = []
    result = get_repo_slug_from_resource(resource)
    # Should add unique suffix to clean names
    assert result == 'clean-name-r000000'


def test_parse_arguments(monkeypatch):
    test_args = [
        '--tx-project-slug', 'test-project',
        '--dry-run',
        '--force-suffix'
    ]
    monkeypatch.setattr('sys.argv', ['test_script.py'] + test_args)
    args = parse_arguments()
    assert args.tx_project_slug == 'test-project'
    assert args.dry_run is True
    assert args.force_suffix is True


def test_parse_arguments_minimal(monkeypatch):
    test_args = ['--tx-project-slug', 'test-project']
    monkeypatch.setattr('sys.argv', ['test_script.py'] + test_args)
    args = parse_arguments()
    assert args.tx_project_slug == 'test-project'
    assert args.dry_run is False
    assert args.force_suffix is False
