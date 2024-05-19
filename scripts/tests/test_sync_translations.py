"""
Tests for sync_translations.py
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import types
from typing import Union

import pytest
import responses

from transifex.api import transifex_api, Project
from transifex.api.jsonapi import Resource
from transifex.api.jsonapi.auth import BearerAuthentication

from . import response_data
from ..sync_translations import (
    Command,
    ORGANIZATION_SLUG,
    parse_tx_date,
)

HOST = transifex_api.HOST


def sync_command(**kwargs):
    command_args = {
        'tx_api': transifex_api,
        'dry_run': True,
        'simulate_github_workflow': False,
        'environ': {
            'TX_API_TOKEN': 'dummy-token'
        }
    }
    command_args.update(kwargs)
    result = Command(**command_args)
    result.tx_api.make_auth_headers = BearerAuthentication('dummy-token')
    return result


@dataclass
class ResourceStringMock:
    """
    String entry in Transifex.

    Mock class for the transifex.api.ResourceString class.
    """
    key: str
    context: str = ''


@dataclass
class ResourceTranslationMock:
    """
    Translation for an entry in Transifex.

    Mock class for the transifex.api.ResourceTranslation class.
    """
    resource_string: ResourceStringMock
    strings: dict
    reviewed: bool
    proofread: bool
    datetime_translated: str

    _updates: dict = None  # Last updates applied via `save()`

    def save(self, **updates):
        """
        Mock ResourceTranslation.save() method.
        """
        self._updates = updates

    @property
    def updates(self):
        """
        Return the last updates applied via `save()`.
        """
        return self._updates

    @classmethod
    def factory(
        cls,
        key='key',
        context='',
        translation: Union[str, None] = 'dummy translation',
        **kwargs
    ):
        mock_kwargs = dict(
            resource_string=ResourceStringMock(
                key=key,
                context=context
            ),
            strings={
                key: translation,
            },
            reviewed=False,
            proofread=False,
            datetime_translated='2021-01-01T00:00:00Z',
        )

        mock_kwargs.update(kwargs)
        return cls(**mock_kwargs)


@responses.activate
def test_get_transifex_organization_projects():
    """
    Verify that the get_transifex_organization_projects() method returns the correct data.
    """
    command = sync_command()

    # Mocking responses
    responses.add(
        responses.GET,
        HOST + f'/organizations?filter[slug]={ORGANIZATION_SLUG}',
        json=response_data.RESPONSE_GET_ORGANIZATION,
        status=200
    )
    responses.add(
        responses.GET,
        HOST + f'/projects?filter[organization]={response_data.RESPONSE_GET_ORGANIZATION["data"][0]["id"]}',
        json=response_data.RESPONSE_GET_PROJECTS,
        status=200
    )

    # Remove the make_auth_headers to verify later that transifex setup is called
    delattr(command.tx_api, 'make_auth_headers')

    data = command.get_transifex_organization_projects()
    assert hasattr(command.tx_api, 'make_auth_headers')
    assert isinstance(command.tx_api.make_auth_headers, BearerAuthentication)
    assert len(data) == 1
    assert isinstance(data[0], Project)
    assert data[0].id == response_data.RESPONSE_GET_PROJECTS['data'][0]['id']


@responses.activate
def test_get_translations():
    """
    Verify that the get_translations() method returns the correct data.
    """
    command = sync_command()
    resource_id = f'{response_data.RESPONSE_GET_PROJECTS["data"][0]["id"]}:r:ar'

    # Mocking responses
    responses.add(
        responses.GET,
        HOST + f'/languages?filter[code]=ar',
        json=response_data.RESPONSE_GET_LANGUAGE,
        status=200
    )
    responses.add(
        responses.GET,
        HOST + f'/resource_translations?filter[resource]={resource_id}&filter[language]=l:ar&include=resource_string',
        json=response_data.RESPONSE_GET_LANGUAGE,
        status=200
    )

    data = command.get_translations(
        language_code='ar',
        resource=Resource(id=resource_id)
    )
    assert isinstance(data, types.GeneratorType)
    items = list(data)
    assert len(items) == 1
    assert items[0].id == response_data.RESPONSE_GET_LANGUAGE['data'][0]['id']


def test_translations_entry_update_empty_translation():
    """
    Test updating an entry from old project where `current_translation` is empty.
    """
    command = sync_command(dry_run=False)

    translation_from_old_project = ResourceTranslationMock.factory(
        key='test_key',
        translation='old translation',
        reviewed=True,
        datetime_translated='2023-01-01T00:00:00Z',
    )

    # Current translation is empty
    current_translation = ResourceTranslationMock.factory(
        key='test_key',
        translation=None,
        datetime_translated=None,
    )

    status = command.sync_translation_entry(
        translation_from_old_project, current_translation
    )

    assert status == 'updated'
    assert current_translation.updates == {
        'strings': {
            'test_key': 'old translation'
        },
        'reviewed': True,
    }


@pytest.mark.parametrize(
    'old_project_date, current_translation_date, new_translation_str',
    [
        # As long as the current translation is _not_ more recent, it should be updated
        (None, '2023-01-01T00:00:00Z', None),
        (None, '2023-01-01T00:00:00Z', 'some translation'),
        ('2023-01-01T00:00:00Z', '2023-01-01T00:00:00Z', 'some translation'),  # Same date
        ('2023-01-01T00:00:00Z', '2021-01-01T00:00:00Z', 'some translation'),  # New project has newer date
        ('2023-01-01T00:00:00Z', None, 'some translation'),
        ('2023-01-01T00:00:00Z', None, None),
    ]
)
def test_translations_entry_update_translation(old_project_date, current_translation_date, new_translation_str):
    """
    Test updating an entry from old project where `current_translation` is has outdated translation.
    """
    command = sync_command(dry_run=False)

    translation_from_old_project = ResourceTranslationMock.factory(
        key='test_key',
        translation='old translation',
        reviewed=True,
        datetime_translated=old_project_date,
    )

    current_translation = ResourceTranslationMock.factory(
        key='test_key',
        translation=new_translation_str,
        datetime_translated=current_translation_date,
    )

    status = command.sync_translation_entry(
        translation_from_old_project, current_translation
    )

    assert status == 'updated'
    assert current_translation.updates == {
        'strings': {
            'test_key': 'old translation'
        },
        'reviewed': True,
    }


def test_translations_entry_more_recent_translation():
    """
    Verify that the more recent translations in the open-edx/openedx-translations project are not overridden.
    """
    command = sync_command(dry_run=False)

    translation_from_old_project = ResourceTranslationMock.factory(
        key='test_key',
        translation='one translation',
        reviewed=True,
        datetime_translated='2019-01-01T00:00:00Z',
    )

    # Current translation is empty
    current_translation = ResourceTranslationMock.factory(
        key='test_key',
        translation='more recent translation',
        datetime_translated='2023-01-01T00:00:00Z',
    )

    status = command.sync_translation_entry(
        translation_from_old_project, current_translation
    )

    assert status == 'skipped'
    assert not current_translation.updates, 'save() should not be called'


def test_translations_entry_dry_run():
    """
    Verify that --dry-run option skips the save() call.
    """
    command = sync_command(dry_run=True)

    translation_from_old_project = ResourceTranslationMock.factory(
        key='test_key',
        translation='old translation',
        reviewed=True,
        datetime_translated='2023-01-01T00:00:00Z',
    )

    current_translation = ResourceTranslationMock.factory(
        key='test_key',
        translation=None,
        datetime_translated=None,
    )

    status = command.sync_translation_entry(
        translation_from_old_project, current_translation
    )

    assert status == 'updated-dry-run'
    assert not current_translation.updates, 'save() should not be called in --dry-run mode'


@pytest.mark.parametrize(
    "date_str, parse_result, test_message",
    [
        (None, None, 'None cannot be parsed'),
        ('2023-01-01T00:00:00Z', datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc),
         'Z suffix is replaced with the explict "+00:00" timezone'),
        ('2023-01-01T00:00:00', datetime(2023, 1, 1, 0, 0),
         'If there is no Z suffix, no timezone is added'),
    ]
)
def test_parse_tx_date(date_str, parse_result, test_message):
    """
    Tests for parse_tx_date() helper function.
    """
    assert parse_tx_date(date_str) == parse_result, test_message

