"""
Release cut script to sync the main openedx-translations Transifex project into the\
openedx-translations-<release-name> release projects.

  - Project links:
     * Main: https://app.transifex.com/open-edx/openedx-translations/
     * Release projects: https://app.transifex.com/open-edx/openedx-translations-<release-name>/

Variable names meaning:

 - main_translation: translation in the main "open-edx/openedx-translations" project
 - release_translation: translation in the release project "open-edx/openedx-translations-<release-name>"

Python API docs: https://github.com/transifex/transifex-python/blob/devel/transifex/api/README.md
"""

import argparse
import configparser
import os
from os.path import expanduser
import dataclasses

from transifex.api import TransifexApi, transifex_api
from transifex.api.jsonapi.exceptions import DoesNotExist, JsonApiException

ORGANIZATION_SLUG = 'open-edx'
MAIN_PROJECT_SLUG = 'openedx-translations'
RELEASE_PROJECT_SLUG_TEMPLATE = 'openedx-translations-{release_name}'


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]



@dataclasses.dataclass
class Command:

    resource: str
    language: str
    tx_api: TransifexApi
    environ: any
    release_name: str

    dry_run: bool = True

    def is_dry_run(self):
        """
        Check if the script is running in dry-run mode.
        """
        return self.dry_run

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
        tx_api_token = self.environ.get('TRANSIFEX_API_TOKEN')
        if not tx_api_token:
            config = configparser.ConfigParser()
            config.read(expanduser('~/.transifexrc'))
            tx_api_token = config['https://www.transifex.com']['password']

        if not tx_api_token:
            raise Exception(
                'Error: No auth token found. '
                'Set transifex API token via TRANSIFEX_API_TOKEN environment variable or via the ~/.transifexrc file.'
            )

        try:
            self.tx_api.setup(auth=tx_api_token)
            project = self.tx_api.Project.get(id=f'o:{ORGANIZATION_SLUG}:p:{project_slug}')
            return project
        except (DoesNotExist, JsonApiException) as error:
            print(f'Error: Project not found: {project_slug}. Error: {error}')
            raise

    def get_resource(self, project, resource_slug):
        resource_id = f'o:{ORGANIZATION_SLUG}:p:{project.slug}:r:{resource_slug}'
        print(f'Getting resource id: {resource_id}')

        try:
            return self.tx_api.Resource.get(id=resource_id)
        except (DoesNotExist, JsonApiException) as error:
            print(f'Error: Resource not found: {resource_id}. Error: {error}')
            raise

    def get_resources_by_name(self, project):
        """
        Build a mapping of resource names to resource objects.

        This allows matching resources across projects by their stable 'name' attribute
        rather than their 'slug' which may include project-specific suffixes like '-main-r1234'.

        Uses lowercase keys for case-insensitive matching to handle cases where
        resource names differ in capitalization between projects (e.g., "AudioXBlock" vs "audioxblock").
        """
        return {r.name.lower(): r for r in project.fetch('resources')}

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

        updates_to_apply = []
        for release_translation in self.get_translations(lang_id=lang_id, resource=release_resource):
            translation_id = self.get_translation_id(release_translation)
            if translation_from_main_project := translations_from_main_project.get(translation_id):
                status, updates = self.determine_translation_updates(
                    translation_from_main_project=translation_from_main_project,
                    release_translation=release_translation,
                )
                if updates and status == 'update':
                    updates_to_apply.append({
                        'id': release_translation.id,
                        'attributes': updates,
                    })

        if updates_to_apply and not self.is_dry_run():
            for updates_chunk in chunks(updates_to_apply, 145):
                self.tx_api.ResourceTranslation.bulk_update(updates_chunk)

        print(' finished', lang_id)

    def determine_translation_updates(self, translation_from_main_project, release_translation):
        """
        Compare translations between main and release projects and determine needed updates.

        Return:
            tuple: status, updates
                - status:
                    - updated: the entry needs to be updated
                    - no-op: if the entry don't need any updates
                    - updated-dry-run: the entry needs to be updated but actually skipped due to dry-run mode
                - updates: dict of updates to be applied to the release translation
        """
        translation_id = self.get_translation_id(release_translation)

        updates = {}

        def _update_review_proofread_attrs():
            for attr in ['reviewed', 'proofread']:
                # Reviews won't be deleted in the release project
                if main_attr_value := getattr(translation_from_main_project, attr, None):
                    if main_attr_value != getattr(release_translation, attr, None):
                        updates[attr] = main_attr_value

        if (
            translation_from_main_project.strings
            and release_translation.strings
            and translation_from_main_project.strings != release_translation.strings
        ):
            # Do not override anything if translations are different
            print(translation_id, 'has different translations will not update it')
            return 'no-op', updates

        if (
            translation_from_main_project.strings
            and translation_from_main_project.strings == release_translation.strings
        ):
            # Only update review status if translations are the same across projects
            _update_review_proofread_attrs()

        if (
            translation_from_main_project.strings
            and not release_translation.strings
        ):
            # Set translations from the old project and update review status
            updates['strings'] = translation_from_main_project.strings
            _update_review_proofread_attrs()

        if updates:
            print(translation_id, updates, '[Dry run]' if self.is_dry_run() else '')
            if self.is_dry_run():
                return 'update-dry-run', updates
            else:
                return 'update', updates

        return 'no-op', updates

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

        dry_run_note = ''
        if self.is_dry_run():
            dry_run_note = ' (dry-run)'

        for release_info in release_resource_str.all():
            main_tags = main_quick_lookup.get(release_info.string_hash)
            release_tags = release_info.tags

            if main_tags is None:  # in case of new changes are not synced yet
                continue
            if len(release_tags) == 0 and len(main_tags) == 0:  # nothing to compare
                continue

            if len(release_tags) != len(main_tags) or set(release_tags) != set(main_tags):
                print(f'  - found tag difference for {release_info.string_hash}. overwriting{dry_run_note}: {release_tags} with {main_tags}')

                if not self.is_dry_run():
                    release_info.save(tags=main_tags)

    def get_translation_id(self, translation):
        """
        Build a unique identifier for a translation entry.
        """
        return f'context:{translation.resource_string.context}:key:{translation.resource_string.key}'

    def get_language_codes(self, project):
        """
        Get a list of languages codes to sync translations for as a list e.g. ['ar', 'fr_CA', 'es_419'].
        """
        languages = [
            lang.code
            for lang in self.get_languages(project)
        ]
        print('languages_codes', languages)
        return languages

    def get_languages(self, project):
        """
        Get a list of language objects to sync translations for as a list.
        """
        languages = [
            lang
            for lang in project.fetch('languages')

            # Limit to a specific language if specified
            if not self.language or (self.language == lang.code)
        ]
        print('languages', languages)
        return languages

    def get_language_ids(self, project):
        """
        Get a list of languages IDs to sync translations for as a list e.g. ['l:ar', 'l:fr_CA', 'l:es_419'].
        """
        languages = [
            f'l:{code}'
            for code in self.get_language_codes(project=project)
        ]
        print('languages_ids', languages)
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
        release_project_language_codes = set(self.get_language_codes(release_project))
        missing_languages = []
        for main_project_language in self.get_languages(main_project):
            if main_project_language.code not in release_project_language_codes:
                missing_languages.append(main_project_language)

        print('missing_languages', missing_languages)
        if missing_languages:
            release_project.add('languages', missing_languages)
            print('missing_languages', missing_languages, 'added!')
        else:
            print('no missing release project languages to add')

        main_resources = main_project.fetch('resources')
        # Build a mapping of resource names to resource objects for efficient lookup
        release_resources_by_name = self.get_resources_by_name(release_project)

        pairs_list = []
        print('Verifying sync plan...')
        for main_resource in main_resources:
            if self.resource:
                # Allow users to specify the resource name
                if self.resource.lower() != main_resource.name.lower():
                    # Limit to a specific resource if specified
                    continue

            # Match resources by name (case-insensitive)
            if main_resource.name.lower() in release_resources_by_name:
                release_resource = release_resources_by_name[main_resource.name.lower()]
                print(f'Planning to sync "{main_resource.id}" --> "{release_resource.id}"')
                pairs_list.append(
                    [main_resource, release_resource]
                )
            else:
                print(
                    f'NOTICE: Skipping resource "{main_resource.name}" (slug: {main_resource.slug}) '
                    f'because it does not exist in "{release_project.slug}".'
                )

        for main_resource, release_resource in pairs_list:
            self.sync_pair_into_release_resource(
                main_resource=main_resource,
                release_resource=release_resource,
                language_ids=main_project_language_ids,
            )


def main():  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', dest='dry_run',
                        help='Run the script without writing anything to Transifex.')

    ## TODO: Override source project
    ## TODO: Override older translations

    parser.add_argument('--resource', default='', dest='resource',
                        help='Resource name e.g. "AudioXBlock" or "frontend-app-learning". '
                             'Leave empty to sync all resources.')
    parser.add_argument('--language', default='', dest='language',
                        help='Language code e.g. "ar" or "zh_CN". Leave empty to sync all languages.')
    parser.add_argument('release_name',
                        help='Open edX Release name in lower case .e.g redwood or zebrawood.')
    argparse_args = parser.parse_args()

    print(f'release_project_sync.py args: {argparse_args}.')

    command = Command(
        tx_api=transifex_api,
        environ=os.environ,
        dry_run=argparse_args.dry_run,
        language=argparse_args.language,
        resource=argparse_args.resource,
        release_name=argparse_args.release_name.lower(),
    )
    command.run()


if __name__ == '__main__':
    main()  # pragma: no cover
