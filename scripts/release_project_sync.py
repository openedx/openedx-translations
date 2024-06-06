"""
Release cut script to sync the main openedx-translations Transifex project into the\
openedx-translations-<release-name> release projects.

  - Project links:
     * Main: https://app.transifex.com/open-edx/openedx-translations/
     * Release projects: https://app.transifex.com/open-edx/openedx-translations-<release-name>/

Variable names meaning:

 - main_translation: translation in the main "open-edx/openedx-translations" project
 - release_translation: translation in the release project "open-edx/openedx-translations-<release-name>"

"""

import argparse
import configparser
from datetime import datetime
import os
from os.path import expanduser
import yaml

from transifex.api import transifex_api
from transifex.api.jsonapi import exceptions

ORGANIZATION_SLUG = 'open-edx'
MAIN_PROJECT_SLUG = 'openedx-translations'
RELEASE_PROJECT_SLUG_TEMPLATE = 'openedx-translations-{release_name}'


def parse_tx_date(date_str):
    """
    Parse a date string coming from Transifex into a datetime object.
    """
    if date_str:
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')

        return datetime.fromisoformat(date_str)

    return None


class Command:

    def __init__(self, tx_api, dry_run, release_name, environ):
        self.dry_run = dry_run
        self.release_name = release_name
        self.tx_api = tx_api
        self.environ = environ

    def is_dry_run(self):
        """
        Check if the script is running in dry-run mode.
        """
        return self.dry_run
    #
    def get_resource_url(self, resource):
        resource.fetch('project')
        project = resource.project
        return f'https://www.transifex.com/{ORGANIZATION_SLUG}/{project.slug}/{resource.slug}'

    def get_release_project_slug(self):
        return RELEASE_PROJECT_SLUG_TEMPLATE.format(release_name=self.release_name)

    def get_transifex_project(self, project_slug):
        """
        Get openedx-translations projects from Transifex.
        """
        tx_api_token = self.environ.get('TX_API_TOKEN')
        if not tx_api_token:
            config = configparser.ConfigParser()
            config.read(expanduser('~/.transifexrc'))
            tx_api_token = config['https://www.transifex.com']['password']

        if not tx_api_token:
            raise Exception(
                'Error: No auth token found. '
                'Set transifex API token via TX_API_TOKEN environment variable or via the ~/.transifexrc file.'
            )

        try:
            self.tx_api.setup(auth=tx_api_token)
            projects = self.tx_api.Organization.get(slug=ORGANIZATION_SLUG).fetch('projects')
            return projects.get(slug=project_slug)
        except exceptions.DoesNotExist as error:
            print(f'Error: Project not found: {project_slug}. Error: {error}')
            raise

    def get_resource(self, project, resource_slug):
        resource_id = f'o:{ORGANIZATION_SLUG}:p:{project.slug}:r:{resource_slug}'
        print(f'Getting resource id: {resource_id}')

        try:
            return self.tx_api.Resource.get(id=resource_id)
        except exceptions.DoesNotExist as error:
            print(f'Error: Resource not found: {resource_id}. Error: {error}')
            raise
    #
    # def get_resources_pair(self, resource_slug):
    #     """
    #     Load the main and release Transifex resources pair.
    #     """
    #     release_project = self.get_transifex_project(project_slug=self.get_release_project_slug())
    #
    #     release_resource_id = f'o:{ORGANIZATION_SLUG}:p:{release_project.slug}:r:{resource_slug}'
    #     print(f'release resource id: {release_resource_id}')
    #     try:
    #         release_resource = self.tx_api.Resource.get(id=release_resource_id)
    #     except exceptions.DoesNotExist as error:
    #         print(f'Error: Release resource error: {release_resource_id}. Error: {error}')
    #         raise
    #
    #     main_resource_id = f'o:{ORGANIZATION_SLUG}:p:{MAIN_PROJECT_SLUG}:r:{resource_slug}'
    #     print(f'main resource id: {main_resource_id}')
    #     try:
    #         main_resource = self.tx_api.Resource.get(id=main_resource_id)
    #     except exceptions.JsonApiException as error:
    #         print(f'Error: Main project resource error: {release_resource_id}. Error: {error}')
    #         raise
    #
    #     return {
    #         'main_resource': main_resource,
    #         'release_resource': release_resource,
    #     }

    def get_translations(self, lang_id, resource):
        """
        Get a list of translations for a given language and resource.
        """
        language = self.tx_api.Language.get(id=lang_id)
        translations = self.tx_api.ResourceTranslation. \
            filter(resource=resource, language=language). \
            include('resource_string')

        return translations.all()

    def sync_translations(self, lang_id, main_resource, release_resource):
        """
        Sync specific language translations into the release Transifex resource.
        """
        print(' syncing', lang_id, '...')
        translations_from_main_project = {
            self.get_translation_id(translation): translation
            for translation in self.get_translations(lang_id=lang_id, resource=main_resource)
        }

        for release_translation in self.get_translations(lang_id=lang_id, resource=release_resource):
            translation_id = self.get_translation_id(release_translation)
            if translation_from_main_project := translations_from_main_project.get(translation_id):
                self.sync_translation_entry(
                    translation_from_main_project=translation_from_main_project,
                    release_translation=release_translation,
                )
        print(' finished', lang_id)

    def sync_translation_entry(self, translation_from_main_project, release_translation):
        """
        Sync translation review from the main project to the release one.

        Return:
            str: status code
               - updated: if the entry was updated
               - no-op: if the entry don't need any updates
               - updated-dry-run: if the entry was updated in dry-run mode
        """
        translation_id = self.get_translation_id(release_translation)

        updates = {}

        # Only update review status if translations are the same across projects
        if translation_from_main_project.strings == release_translation.strings:
            for attr in ['reviewed', 'proofread']:
                # Reviews won't be deleted in the release project
                if main_attr_value := getattr(translation_from_main_project, attr, None):
                    if main_attr_value != getattr(release_translation, attr, None):
                        updates[attr] = main_attr_value
        else:
            print(translation_id, 'has different translations will not update it')
            return 'no-op'

        if updates:
            print(translation_id, updates, '[Dry run]' if self.is_dry_run() else '')
            if self.is_dry_run():
                return 'updated-dry-run'
            else:
                release_translation.save(**updates)
                return 'updated'

        return 'no-op'

    def sync_tags(self, main_resource, release_resource):
        """
        Sync tags from the main Transifex resource into the release Transifex resource.

        This process is language independent.
        """
        main_resource_str = self.tx_api.ResourceString.filter(resource=main_resource)
        release_resource_str = self.tx_api.ResourceString.filter(resource=release_resource)

        main_quick_lookup = {}
        for item in main_resource_str.all():
            dict_item = item.to_dict()
            main_quick_lookup[dict_item['attributes']['string_hash']] = dict_item['attributes']['tags']

        for release_info in release_resource_str.all():
            main_tags = main_quick_lookup.get(release_info.string_hash)
            release_tags = release_info.tags

            if main_tags is None:  # in case of new changes are not synced yet
                continue
            if len(release_tags) == 0 and len(main_tags) == 0:  # nothing to compare
                continue

            if len(release_tags) != len(main_tags) or set(release_tags) != set(main_tags):
                print(f'  - found tag difference for {release_info.string_hash}. overwriting: {release_tags} with {main_tags}')

                if not self.is_dry_run():
                    release_info.save(tags=main_tags)

    def get_translation_id(self, translation):
        """
        Build a unique identifier for a translation entry.
        """
        return f'context:{translation.resource_string.context}:key:{translation.resource_string.key}'

    def get_language_ids(self, project):
        """
        Get a list of languages to sync translations for.
        """
        languages = [
            lang.id
            for lang in project.fetch('languages')
            if 'zh_CN' in lang.id  # TEMP: FOR TESTING
        ]
        print('languages', languages)
        return languages

    def sync_pair_into_release_resource(self, main_resource, release_resource, language_ids):
        """
        Sync translations from main openedx-translations project into openedx-translations-<release-name>.
        """
        print(f'Syncing {main_resource.name} --> {release_resource.name}...')
        print(f'Syncing: {language_ids}')
        print(f' - from: {self.get_resource_url(main_resource)}')
        print(f' - to:   {self.get_resource_url(release_resource)}')

        for lang_id in language_ids:
            self.sync_translations(
                lang_id=lang_id,
                main_resource=main_resource,
                release_resource=release_resource,
            )

        print('Syncing tags...')
        self.sync_tags(main_resource, release_resource)

        print('-' * 80, '\n')

    def run(self):
        """
        Run the script.
        """
        main_project = self.get_transifex_project(project_slug=MAIN_PROJECT_SLUG)
        release_project = self.get_transifex_project(project_slug=self.get_release_project_slug())

        main_project_language_ids = self.get_language_ids(main_project)
        release_project_language_ids = self.get_language_ids(release_project)
        missing_languages = set(main_project_language_ids) - set(release_project_language_ids)
        for lang_id in missing_languages:
            missing_lang = self.tx_api.Resource.create(lang_id)
            print('missing_lang', missing_lang)
            # release_project.fetch('languages').append(missing_lang)

        main_resources = main_project.fetch('resources')
        pairs_list = []
        print('Verifying sync plan...')
        for main_resource in main_resources[:3]:
            try:
                release_resource = self.get_resource(release_project, main_resource.slug)
            except exceptions.DoesNotExist as error:
                print(
                    f'WARNING: Skipping resource {main_resource.slug} because it does not exist in '
                    f'"{release_project.slug}". \nError: "{error}"'
                )
            else:
                print(f'Planning to sync "{main_resource.id}" --> "{release_resource.id}"')
                pairs_list.append(
                    [main_resource, release_resource]
                )

        for main_resource, release_resource in pairs_list:
            self.sync_pair_into_release_resource(
                main_resource=main_resource,
                release_resource=release_resource,
                language_ids=main_project_language_ids,
            )


def main():  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', dest='dry_run')
    parser.add_argument('release_name',
                        help='Open edX Release name in lower case .e.g redwood or zebrawood.')
    argparse_args = parser.parse_args()

    command = Command(
        tx_api=transifex_api,
        environ=os.environ,
        dry_run=argparse_args.dry_run,
        release_name=argparse_args.release_name.lower(),
    )
    command.run()


if __name__ == '__main__':
    main()  # pragma: no cover
