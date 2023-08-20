"""
Tests for sync_translations.py
"""
import types

import pytest
import responses
from transifex.api import transifex_api, Project
from transifex.api.jsonapi import Resource
from transifex.api.jsonapi.auth import BearerAuthentication

from . import response_data
from ..sync_translations import Command, ORGANIZATION_SLUG

HOST = transifex_api.HOST


def sync_command():
    result = Command(
        argv=[],
        tx_api=transifex_api,
        environ={
            'TX_API_TOKEN': 'dummy-token'
        }
    )
    result.tx_api.make_auth_headers = BearerAuthentication('dummy-token')
    return result


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
