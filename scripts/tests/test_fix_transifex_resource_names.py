"""
Tests for fix_transifex_resource_names.py.
"""

from dataclasses import dataclass
import pytest
from typing import List

from ..fix_transifex_resource_names import (
    get_repo_name_from_resource,
    get_repo_slug_from_resource,
    parse_arguments,
)


@dataclass
class ParsedArgumentsMock:
    force_suffix: bool = False
    dry_run: bool = False
    release: str = 'main'


@dataclass
class Resource:
    slug: str
    name: str
    categories: List[str]


@pytest.fixture(autouse=True)
def mock_random_choice(monkeypatch):
    monkeypatch.setattr('random.choice', lambda x: '9')


def test_get_repo_slug_from_resource_with_no_categories():
    resource = Resource(
        slug='translations-my-xblock-conf-locale-en-lc-messages-django-po--main',
        name='',
        categories=[]
    )
    assert get_repo_slug_from_resource(resource, 'main') == 'my-xblock-main-r9999'


def test_get_repo_slug_from_resource_slug_js_with_no_categories():
    resource = Resource(
        slug='translations-my-xblock-conf-locale-en-lc-messages-djangojs-po--main',
        name='',
        categories=[]
    )
    assert get_repo_slug_from_resource(resource, 'main') == 'my-xblock-js-main-r9999'


def test_get_repo_name_from_invalid_slug():
    resource = Resource(
        slug='some-gibberish-slug',
        name='',
        categories=[]
    )
    assert get_repo_name_from_resource(resource) == None


def test_get_repo_name_from_slug_and_categories():
    """
    Categories takes precedence over slug.
    """
    resource = Resource(
        slug='translations-my-xblock1-conf-locale-en-lc-messages-django-po--main',
        name='',
        categories=[
            'github#repository:openedx/openedx-translations#branch:main#path:translations/my-xblock2/openassessment/conf/locale/en/LC_MESSAGES/django.po', # noqa
        ]
    )
    assert get_repo_name_from_resource(resource) == 'my-xblock2'


def test_get_repo_name_from_categories():
    resource = Resource(
        slug='some-gibberish-slug',
        name='',
        categories=[
            'github#repository:openedx/openedx-translations#branch:main#path:translations/my-xblock2/openassessment/conf/locale/en/LC_MESSAGES/django.po', # noqa
        ]
    )
    assert get_repo_name_from_resource(resource) == 'my-xblock2'


def test_get_repo_name_from_categories_with_js():
    resource = Resource(
        slug='some-gibberish-slug',
        name='',
        categories=[
            'github#repository:openedx/openedx-translations#branch:main#path:translations/my-xblock2/openassessment/conf/locale/en/LC_MESSAGES/djangojs.po', # noqa
        ]
    )
    assert get_repo_name_from_resource(resource) == 'my-xblock2-js'


def test_get_repo_slug_from_resource_with_existing_suffix():
    resource = Resource(
        slug='my-resource-r1234',
        name='my-resource-r1234',
        categories=[]
    )
    # Should keep the existing suffix without adding a new one
    assert get_repo_slug_from_resource(resource, 'main') == 'my-resource-r1234'


def test_get_repo_slug_from_resource_with_clean_name():
    resource = Resource(
        slug='clean-name',
        name='clean-name',
        categories=[]
    )
    result = get_repo_slug_from_resource(resource, 'main')
    # Should add unique suffix to clean names
    assert result == 'clean-name-main-r9999'


def test_parse_arguments(monkeypatch):
    test_args = [
        '--release', 'redwood',
        '--dry-run',
        '--force-suffix'
    ]
    monkeypatch.setattr('sys.argv', ['test_script.py'] + test_args)
    args = parse_arguments()
    assert args.release == 'redwood'
    assert args.dry_run is True
    assert args.force_suffix is True


def test_parse_arguments_minimal(monkeypatch):
    test_args = ['--release', 'main']
    monkeypatch.setattr('sys.argv', ['test_script.py'] + test_args)
    args = parse_arguments()
    assert args.release == 'main'
    assert args.dry_run is False
    assert args.force_suffix is False
