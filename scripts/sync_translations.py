"""
Sync translations from the deprecated Transifex projects into the new openedx-translations project.

  - Old projects links:
     * edX Platform Core: https://app.transifex.com/open-edx/edx-platform/
     * XBlocks: https://app.transifex.com/open-edx/xblocks/

  - New project link:
     * https://app.transifex.com/open-edx/openedx-translations/


Variable names meaning:

 - current_translation: translation in the new "open-edx/openedx-translations" project
 - translation_from_old_project: translation in the old "open-edx/edx-platform" or "open-edx/xblocks" projects

"""

import argparse
import configparser
from datetime import datetime
import os
from os.path import expanduser
import yaml

from transifex.api import transifex_api
from transifex.api.jsonapi import exceptions

NEW_PROJECT_SLUG = 'openedx-translations'
ORGANIZATION_SLUG = 'open-edx'


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

    workflow_file_path = '.github/workflows/sync-translations.yml'

    def __init__(self, tx_api, dry_run, simulate_github_workflow, environ):
        self.dry_run = dry_run
        self.simulate_github_workflow = simulate_github_workflow
        self.tx_api = tx_api
        self.environ = environ

    def is_dry_run(self):
        """
        Check if the script is running in dry-run mode.
        """
        return self.dry_run

    def is_simulated_github_actions(self):
        """
        Check if the script is running in simulated GitHub Actions mode.
        """
        return self.simulate_github_workflow

    def get_resource_url(self, resource, project_slug):
        return f'https://www.transifex.com/{ORGANIZATION_SLUG}/{project_slug}/{resource.slug}'

    def get_transifex_organization_projects(self):
        """
        Get openedx-translations project from Transifex.
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

        self.tx_api.setup(auth=tx_api_token)
        return self.tx_api.Organization.get(slug=ORGANIZATION_SLUG).fetch('projects')

    def get_resources_pair(self, new_slug, old_slug, old_project_slug):
        """
        Load the old and new Transifex resources pair.
        """
        projects = self.get_transifex_organization_projects()
        new_project = projects.get(slug=NEW_PROJECT_SLUG)

        new_resource_id = f'o:{ORGANIZATION_SLUG}:p:{new_project.slug}:r:{new_slug}'
        print(f'new resource id: {new_resource_id}')
        try:
            new_resource = self.tx_api.Resource.get(id=new_resource_id)
        except exceptions.JsonApiException as error:
            print(f'Error: New resource error: {new_resource_id}. Error: {error}')
            raise

        old_resource_id = f'o:{ORGANIZATION_SLUG}:p:{old_project_slug}:r:{old_slug}'
        print(f'old resource id: {old_resource_id}')
        try:
            old_resource = self.tx_api.Resource.get(id=old_resource_id)
        except exceptions.JsonApiException as error:
            print(f'Error: Old resource error: {new_resource_id}. Error: {error}')
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
        return self.environ['TX_LANGUAGES'].split(',')

    def sync_pair_into_new_resource(self, new_slug, old_slug, old_project_slug):
        """
        Sync translations from both the edx-platform and XBlock projects into the new openedx-translations project.
        """
        languages = self.get_languages()
        resource_pair = self.get_resources_pair(new_slug, old_slug, old_project_slug)

        print(f'Syncing {resource_pair["new_resource"].name} from {resource_pair["old_resource"].name}...')
        print(f'Syncing: {languages}')
        print(f' - from: {self.get_resource_url(resource_pair["old_resource"], old_project_slug)}')
        print(f' - to:   {self.get_resource_url(resource_pair["new_resource"], NEW_PROJECT_SLUG)}')

        for lang_code in languages:
            self.sync_translations(language_code=lang_code, **resource_pair)

        print('Syncing tags...')
        self.sync_tags(**resource_pair)

        print('-' * 80, '\n')

    def run_from_workflow_yaml_file(self, workflow_configs):
        """
        Run the script from a GitHub Actions migrate-from-transifex-old-project.yml workflow file.
        """
        pairs_list = workflow_configs['jobs']['migrate-translations']['strategy']['matrix']['resource']

        print('Verifying existence of resource pairs...')
        for pair in pairs_list:
            self.get_resources_pair(
                new_slug=pair['new_slug'],
                old_slug=pair['old_slug'],
                old_project_slug=pair['old_project_slug'],
            )
            print('\n', '-' * 80, '\n')

        for pair in pairs_list:
            self.sync_pair_into_new_resource(
                new_slug=pair['new_slug'],
                old_slug=pair['old_slug'],
                old_project_slug=pair['old_project_slug'],
            )

    def run(self):
        if self.is_simulated_github_actions():
            with open(self.workflow_file_path) as workflow_file:
                self.run_from_workflow_yaml_file(
                    workflow_configs=yaml.safe_load(workflow_file.read()),
                )
        else:
            self.sync_pair_into_new_resource(
                new_slug=self.environ['TX_NEW_SLUG'],
                old_slug=self.environ['TX_OLD_SLUG'],
                old_project_slug=self.environ['TX_OLD_PROJECT_SLUG'],
            )


def main():  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulate-github-workflow', action='store_true',
                        dest='simulate_github_workflow')
    parser.add_argument('--dry-run', action='store_true', dest='dry_run')
    argparse_args = parser.parse_args()

    command = Command(
        tx_api=transifex_api,
        environ=os.environ,
        dry_run=argparse_args.dry_run,
        simulate_github_workflow=argparse_args.simulate_github_workflow,
    )
    command.run()


if __name__ == '__main__':
    main()  # pragma: no cover
