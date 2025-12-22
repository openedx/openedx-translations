"""
Set the Transifex projects resources to have readable resource names and slugs:

Run via `$ make fix_transifex_resource_names`.

Transifex sets resource slug names and slugs to a long name which makes it unreadable by translators .e.g.
 - "translations..frontend-app-something..src-i18n-transifex-input--main"

This script infer the resource name in two ways:

1) From slug if it starts with "translations..frontend-app-something..src-i18n-transifex-input--main" would result
   in "frontend-app-something" as resource name.

2) If no usable slug is available, infer the resource name from the categories e.g.
 - ["github#repository:openedx/openedx-translations#branch:main#path:translations/my-xblock/openassessment/conf/locale/en/LC_MESSAGES/djangojs.po"]
   would result in "my-xblock-js" as resource name.


Slugs are even worse than random names, sometimes they're also the lengthy while other times they're just hashes e.g.
 - "b8933764bdb3063ca09d6aa20341102f"

Slug deduplication: Slugs are used by internal Transifex applications, so this script adds a random suffix to avoid
                    slug collisions across projects.

Transifex Python API docs: https://github.com/transifex/transifex-python/blob/devel/transifex/api/README.md
"""

import argparse
import configparser
import re
import sys
import random
import string
from os import getenv
from os.path import expanduser

from slugify import slugify
from transifex.api import transifex_api

# Use random suffix to avoid slug collisions across projects
# See the AI Transifex translations postmortem for more details:
#   - https://github.com/openedx/openedx-translations/issues/41695
UNIQUE_RESOURCE_SLUG_REGEXP = re.compile(r'^[a-z0-9-]*-r[0-9]{4}$')

# Slugs are just hashes (e.g. "b8933764bdb3063ca09d6aa20341102f") should be made readable
RESOURCE_SLUG_IS_JUST_HASH_REGEXP = re.compile(r'^[a-z0-9]{32}$')


def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description=f'Update Transifex resource names and slugs to be more readable. \n {__doc__}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode without making any changes'
    )
    parser.add_argument(
        '--force-suffix',
        action='store_true',
        help='Force suffix to be added to the resource Transifex slug'
    )
    parser.add_argument(
        '--release',
        dest='release',
        required=True,
        help=(
            'Release name e.g. "main", "redwood", "quince", "palm", etc. '
            'List of Open edX releases are available in the following page: '
            'https://openedx.atlassian.net/wiki/spaces/OEPM/pages/4191191044/Open+edX+Releases+Homepage'
        ),
    )
    return parser.parse_args()


def get_project_slug_from_release(release):
    """
    Convert release name to Transifex project slug.
    """
    if release == 'main':
        return 'openedx-translations'
    else:
        return f'openedx-translations-{release}'


def get_transifex_project(release):
    """
    Get the translations project object from Transifex.
    """
    transifex_api_token = getenv('TRANSIFEX_API_TOKEN')
    if not transifex_api_token:
        config = configparser.ConfigParser()
        config.read(expanduser('~/.transifexrc'))
        transifex_api_token = config['https://www.transifex.com']['password']

    if not transifex_api_token:
        raise Exception(
            'Error: No auth token found. '
            'Set transifex API token via TRANSIFEX_API_TOKEN environment variable or via the ~/.transifexrc file.'
        )

    transifex_api.setup(auth=transifex_api_token)

    openedx_org = transifex_api.Organization.get(slug='open-edx')
    project_slug = get_project_slug_from_release(release)
    return openedx_org.fetch('projects').get(slug=project_slug)


def generate_short_random_suffix(length=4):
    return ''.join(random.choice(string.digits) for i in range(length))


def get_repo_name_from_resource(resource):
    """
    Get a human-readable resource name from the resource categories and file path.
    """
    if resource.categories:
        github_repo_categories = [
            category for category in resource.categories if 'github#repository' in category
        ]
        if github_repo_categories:
            # example github_repo_info = (
            #   "github#repository:openedx/openedx-translations"
            #   "#branch:main#path:translations/my-xblock/openassessment/conf/locale/"
            #   "en/LC_MESSAGES/djangojs.po"
            # )
            github_repo_info = github_repo_categories[0]
            if '#path:translations/' in github_repo_info:
                path_name = github_repo_info.split('#path:translations/')[1]
                directory_name = path_name.split('/')[0]
                if github_repo_info.endswith('js.po'):
                    return slugify(f'{directory_name}-js')
                else:
                    return slugify(directory_name)

    if resource.slug.startswith('translations-'):
        # example resource.slug:
        # - "translations-my-xblock-conf-locale-en-lc-messages-django-po--main"
        # - "translations-frontend-app-library-authoring-src-i18n-transifex-input-json--main"
        #
        results = re.search(r'translations-(.*)-(conf-locale|src-i18n)', resource.slug)
        if results:
            if new_name := results.group(1):
                if 'djangojs-po' in resource.slug:
                    return f'{new_name}-js'
                else:
                    return new_name


def get_repo_slug_from_resource(resource, release):
    """
    Get a unique human-readable resource slug from the resource name and categories.
    """
    # If the current slug already has a unique suffix, keep it
    if UNIQUE_RESOURCE_SLUG_REGEXP.match(resource.slug):
        return resource.slug

    clean_non_unique_current_name = None
    if resource.slug == resource.name.lower():
        # Resource has a clean name, but not unique
        clean_non_unique_current_name = resource.slug

    new_name = get_repo_name_from_resource(resource)
    if new_name:
        if UNIQUE_RESOURCE_SLUG_REGEXP.match(new_name):
            return new_name
        else:
            return f'{new_name}-{release}-r{generate_short_random_suffix()}'
    elif clean_non_unique_current_name:
        return f'{clean_non_unique_current_name}-{release}-r{generate_short_random_suffix()}'


def main():
    args = parse_arguments()

    try:
        release = args.release
        project_slug = get_project_slug_from_release(release)
        print(f'Updating "{project_slug}" project resource and slug names:')
        if args.dry_run:
            print('Running in dry-run mode. No changes will be made.')
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1

    openedx_translations_proj = get_transifex_project(release)

    # Track changes for summary
    name_changes = 0
    slug_changes = 0
    skipped_resources = 0

    for resource in openedx_translations_proj.fetch('resources'):
        print('------------')
        print('Updating:')
        print('Resource id:', resource.id)
        print('Resource slug:', resource.slug)
        print('Resource name:', resource.name)
        print('Resource categories:', ', '.join(resource.categories))

        new_name = get_repo_name_from_resource(resource)
        new_slug = get_repo_slug_from_resource(resource, release)

        if resource.name.startswith('translations..'):
            if new_name and resource.name != new_name:
                resource.name = new_name
                name_changes += 1
                if args.dry_run:
                    print(f'\n### Would save new name "{new_name}" (dry-run) ###', '\n')
                else:
                    print(f'\n### Saving new name "{new_name}" ###', '\n')
                    resource.save('name')
            else:
                print(f'Error: Unrecognized slug pattern or categories to infer resource resource name from.')

        force_slug = not UNIQUE_RESOURCE_SLUG_REGEXP.match(resource.slug) and args.force_suffix
        if (
            RESOURCE_SLUG_IS_JUST_HASH_REGEXP.match(resource.slug)
            or resource.slug.startswith('translations-')
            or force_slug
        ):
            if new_slug:
                force_slug_note = ' (force suffix)' if force_slug else ''
                if resource.slug != new_slug:
                    resource.slug = new_slug
                    slug_changes += 1
                    if args.dry_run:
                        print(f'\n### Would save new slug "{new_slug}"{force_slug_note} (dry-run) ###', '\n')
                    else:
                        print(f'\n### Saving new slug "{new_slug}"{force_slug_note} ###', '\n')
                        try:
                            resource.save('slug')
                        except Exception as e:
                            # Slug is unique, so if it already exists, we get an error.
                            print(f'Error: {e}')
            else:
                print(f'Error: Unrecognized slug pattern or categories to infer resource slug from.')

        else:
            skipped_resources += 1
            print(f'Skipping: "{resource.name}" because it seems to have proper attributes')

    # Print summary
    print('\n' + '=' * 50)
    print('SUMMARY')
    print('=' * 50)
    print(f'Release: {release}')
    print(f'Project: {project_slug}')
    print(f'Mode: {"Dry-run" if args.dry_run else "Live changes"}')
    print(f'Name changes: {name_changes}')
    print(f'Slug changes: {slug_changes}')
    print(f'Skipped resources: {skipped_resources}')
    print(f'Total resources processed: {name_changes + slug_changes + skipped_resources}')


if __name__ == '__main__':
    main()
