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

    def get_resource_url(self, resource):
        return f'https://www.transifex.com/{ORGANIZATION_SLUG}/{resource.project.slug}/{resource.slug}'

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

    def get_resources_pair(self, resource_slug):
        """
        Load the main and release Transifex resources pair.
        """
        main_project = self.get_transifex_project()
        release_project = self.get_transifex_project(project_slug=self.get_release_project_slug())

        release_resource_id = f'o:{ORGANIZATION_SLUG}:p:{release_project.slug}:r:{new_slug}'
        print(f'new resource id: {release_resource_id}')
        try:
            new_resource = self.tx_api.Resource.get(id=release_resource_id)
        except exceptions.DoesNotExist as error:
            print(f'Error: New resource error: {release_resource_id}. Error: {error}')
            raise

        main_resource_id = f'o:{ORGANIZATION_SLUG}:p:{old_project_slug}:r:{old_slug}'
        print(f'old resource id: {main_resource_id}')
        try:
            old_resource = self.tx_api.Resource.get(id=main_resource_id)
        except exceptions.JsonApiException as error:
            print(f'Error: Old resource error: {release_resource_id}. Error: {error}')
            raise

        return {
            'old_resource': old_resource,
            'new_resource': new_resource,
        }

    def get_translations(self, language_code, resource):
        """
        Get a list of translations for a given language and resource.
        """
        language = self.tx_api.Language.get(code=language_code)
        translations = self.tx_api.ResourceTranslation. \
            filter(resource=resource, language=language). \
            include('resource_string')

        return translations.all()

    def sync_translations(self, language_code, old_resource, new_resource):
        """
        Sync specific language translations into the new Transifex resource.
        """
        print(' syncing', language_code, '...')
        translations_from_old_project = {
            self.get_translation_id(translation): translation
            for translation in self.get_translations(language_code=language_code, resource=old_resource)
        }

        for current_translation in self.get_translations(language_code=language_code, resource=new_resource):
            translation_id = self.get_translation_id(current_translation)
            if translation_from_old_project := translations_from_old_project.get(translation_id):
                self.sync_translation_entry(
                    translation_from_old_project=translation_from_old_project,
                    current_translation=current_translation,
                )

    def sync_translation_entry(self, translation_from_old_project, current_translation):
        """
        Sync a single translation entry from the old project to the new one.

        Return:
            str: status code
               - updated: if the entry was updated
               - skipped: if the entry was skipped
               - updated-dry-run: if the entry was updated in dry-run mode
        """
        translation_id = self.get_translation_id(current_translation)

        updates = {}
        for attr in ['reviewed', 'proofread', 'strings']:
            if old_attr_value := getattr(translation_from_old_project, attr, None):
                if old_attr_value != getattr(current_translation, attr, None):
                    updates[attr] = old_attr_value

        # Avoid overwriting more recent translations in the open-edx/openedx-translations project
        newer_translation_found = False
        old_project_translation_time = parse_tx_date(translation_from_old_project.datetime_translated)
        current_translation_time = parse_tx_date(current_translation.datetime_translated)

        if old_project_translation_time and current_translation_time:
            newer_translation_found = current_translation_time > old_project_translation_time

        if updates:
            if newer_translation_found:
                print(translation_id, updates,
                    (
                      f'[Skipped: current translation "{current_translation_time}" '
                      f'is more recent than "{old_project_translation_time}"]'
                    )
                )
                return 'skipped'
            else:
                print(translation_id, updates, '[Dry run]' if self.is_dry_run() else '')
                if self.is_dry_run():
                    return 'updated-dry-run'
                else:
                    current_translation.save(**updates)
                    return 'updated'

    def sync_tags(self, old_resource, new_resource):
        """
        Sync tags from the old Transifex resource into the new Transifex resource. This process is language independent.
        """
        old_resource_str = self.tx_api.ResourceString.filter(resource=old_resource)
        new_resource_str = self.tx_api.ResourceString.filter(resource=new_resource)

        old_quick_lookup = {}
        for item in old_resource_str.all():
            dict_item = item.to_dict()
            old_quick_lookup[dict_item['attributes']['string_hash']] = dict_item['attributes']['tags']

        for new_info in new_resource_str.all():
            old_tags = old_quick_lookup.get(new_info.string_hash)
            new_tags = new_info.tags

            if old_tags is None:  # in case of new changes are not synced yet
                continue
            if len(new_tags) == 0 and len(old_tags) == 0:  # nothing to compare
                continue

            if len(new_tags) != len(old_tags) or set(new_tags) != set(old_tags):
                print(f'  - found tag difference for {new_info.string_hash}. overwriting: {new_tags} with {old_tags}')

                if not self.is_dry_run():
                    new_info.save(tags=old_tags)

    def get_translation_id(self, translation):
        """
        Build a unique identifier for a translation entry.
        """
        return f'context:{translation.resource_string.context}:key:{translation.resource_string.key}'

    def get_languages(self):
        """
        Get a list of languages to sync translations for.
        """
        return self.get_transifex_project()_

    def sync_pair_into_new_resource(self, main_resource, release_resource):
        """
        Sync translations from both the edx-platform and XBlock projects into the new openedx-translations project.
        """
        languages = self.get_languages()

        print(f'Syncing {main_resource.name} --> {release_resource.name}...')
        print(f'Syncing: {languages}')
        print(f' - from: {self.get_resource_url(main_resource)}')
        print(f' - to:   {self.get_resource_url(release_resource)}')

        for lang_code in languages:
            pass
            # self.sync_translations(language_code=lang_code, **resource_pair)

        print('Syncing tags...')
        pass
        # self.sync_tags(main_resource, release_resource)

        print('-' * 80, '\n')

    def run(self):
        """
        Run the script from a GitHub Actions migrate-from-transifex-old-project.yml workflow file.
        """
        main_project = self.get_transifex_project(project_slug=MAIN_PROJECT_SLUG)
        release_project = self.get_transifex_project(project_slug=self.get_release_project_slug())

        main_resources = main_project.fetch('resources')
        pairs_list = []
        print('Verifying sync plan...')
        for main_resource in main_resources:
            release_resource = self.get_resource(release_project, main_resource.slug)
            print(f'Planning to sync "{main_resource.id}" --> "{release_resource.id}"')
            pairs_list.append(
                [main_resource, release_resource]
            )

        for main_resource, release_resource in pairs_list:
            self.sync_pair_into_new_resource(
                main_resource=main_resource,
                release_resource=release_resource,
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
