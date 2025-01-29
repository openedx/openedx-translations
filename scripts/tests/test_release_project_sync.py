"""
Tests for sync_translations.py
"""
from dataclasses import dataclass
import types
from typing import Union

import responses

from transifex.api import transifex_api, Project
from transifex.api.jsonapi import Resource
from transifex.api.jsonapi.auth import BearerAuthentication

from . import response_data
from ..release_project_sync import (
    Command,
)

HOST = transifex_api.HOST


def sync_command(**kwargs):
    command_args = {
        'tx_api': transifex_api,
        'dry_run': True,
        'language': '',
        'resource': '',
        'release_name': 'zebrawood',
        'environ': {
            'TRANSIFEX_API_TOKEN': 'dummy-token'
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
        )

        mock_kwargs.update(kwargs)
        return cls(**mock_kwargs)


@responses.activate
def test_get_transifex_organization_project():
    """
    Verify that the get_transifex_project() method returns the correct data.
    """
    command = sync_command()

    # Mocking responses
    responses.add(
        responses.GET,
        HOST + f'/projects/o:open-edx:p:openedx-translations',
        json=response_data.RESPONSE_GET_PROJECT,
        status=200
    )

    # Remove the make_auth_headers to verify later that transifex setup is called
    delattr(command.tx_api, 'make_auth_headers')

    project = command.get_transifex_project('openedx-translations')
    assert hasattr(command.tx_api, 'make_auth_headers')
    assert isinstance(command.tx_api.make_auth_headers, BearerAuthentication)
    assert isinstance(project, Project)
    assert project.id == response_data.RESPONSE_GET_PROJECT["data"]['id']


@responses.activate
def test_get_translations():
    """
    Verify that the get_translations() method returns the correct data.
    """
    command = sync_command()
    resource_id = f'{response_data.RESPONSE_GET_PROJECT["data"]["id"]}:r:ar'

    # Mocking responses
    responses.add(
        responses.GET,
        HOST + f'/languages/l:ar',
        json=response_data.RESPONSE_GET_LANGUAGE,
        status=200
    )
    responses.add(
        responses.GET,
        HOST + f'/resource_translations?filter[resource]={resource_id}&filter[language]=l:ar&include=resource_string',
        json=response_data.RESPONSE_GET_LANGUAGES,
        status=200
    )

    data = command.get_translations(
        lang_id='l:ar',
        resource=Resource(id=resource_id)
    )
    assert isinstance(data, types.GeneratorType)
    items = list(data)
    assert len(items) == 1
    assert items[0].id == response_data.RESPONSE_GET_LANGUAGE['data']['id']


def test_translations_entry_update_translation():
    """
    Test updating an entry from old project where `current_translation` is has outdated translation.
    """
    command = sync_command(dry_run=False)

    translation_from_old_project = ResourceTranslationMock.factory(
        key='test_key',
        translation='same translation',
        reviewed=True,
    )

    current_translation = ResourceTranslationMock.factory(
        key='test_key',
        translation='same translation',
    )

    status, updates = command.determine_translation_updates(
        translation_from_old_project, current_translation
    )

    assert status == 'update'
    assert updates == {
        'reviewed': True,
    }


def test_translations_entry_more_recent_review():
    """
    Verify that the release project reviews aren't removed even if the main project haven't had a review.
    """
    command = sync_command(dry_run=False)

    translation_from_main_project = ResourceTranslationMock.factory(
        key='test_key',
        translation='one translation',
        reviewed=False,
    )

    # Current translation is empty
    release_translation = ResourceTranslationMock.factory(
        key='test_key',
        translation='more recent translation',
        reviewed=True,
    )

    status, updates = command.determine_translation_updates(
        translation_from_main_project, release_translation
    )

    assert status == 'no-op'
    assert not updates, 'updates should be empty'


def test_translations_entry_dry_run():
    """
    Verify that --dry-run option skips the save() call.
    """
    command = sync_command(dry_run=True)

    translation_from_old_project = ResourceTranslationMock.factory(
        key='test_key',
        translation='same translation',
        reviewed=True,
    )

    current_translation = ResourceTranslationMock.factory(
        key='test_key',
        translation='same translation',
    )

    status, updates = command.determine_translation_updates(
        translation_from_old_project, current_translation
    )

    assert status == 'update-dry-run'
    assert updates == {
        'reviewed': True,
    }, 'Planned updates but never saved because of dry-run'


def test_translations_entry_different_translation():
    """
    Verify that different translations prevents reviews sync.
    """
    command = sync_command(dry_run=False)

    translation_from_old_project = ResourceTranslationMock.factory(
        key='test_key',
        translation='some translation',
        reviewed=True,
    )

    current_translation = ResourceTranslationMock.factory(
        key='test_key',
        translation='another translation',
    )

    status, updates = command.determine_translation_updates(
        translation_from_old_project, current_translation
    )

    assert status == 'no-op'
    assert updates == {}, ''
