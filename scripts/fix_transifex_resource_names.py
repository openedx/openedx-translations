"""
Set the openedx-translations to readable resource names and slugs:

Run via `$ make fix_transifex_resource_names`.


Transifex sets resource slug names and slugs to a long name which makes it unreadable by translators .e.g.
 - "translations..frontend-app-something..src-i18n-transifex-input--main"

This script infer the resource name in two ways:

1) From slug if it starts with "translations..frontend-app-something..src-i18n-transifex-input--main" would result
   in "frontend-app-something" as resource name.

2) If no usable slug is available, infer the resource name from the categories e.g.
 - ["github#repository:openedx/openedx-translations#branch:main#path:translations/my-xblock/openassessment/conf/locale/en/LC_MESSAGES/djangojs.po"]
   would result in "my-xblock-js" as resource name.

Slugs are even worse, sometimes they're also the lengthy while other times they're just hashes e.g.
 - "b8933764bdb3063ca09d6aa20341102f"

This script updates slugs to be like names.
"""

import configparser
import re
import sys
from os import getenv
from os.path import expanduser

from slugify import slugify
from transifex.api import transifex_api


def is_dry_run():
    """
    Check if the script is running in debug mode.
    """
    return '--dry-run' in sys.argv


def get_transifex_project():
    """
    Get openedx-translations project from Transifex.
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
    return openedx_org.fetch('projects').get(slug='openedx-translations')


def get_repo_slug_from_resource(resource):
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


def main(argv):
    if '--help' in argv:
        # Print help document.
        print(__doc__)
        return

    print('Updating openedx-translations project resource and slug names:')

    openedx_translations_proj = get_transifex_project()
    for resource in openedx_translations_proj.fetch('resources'):
        print('------------')
        print('Updating:')
        print('Resource id:', resource.id)
        print('Resource slug:', resource.slug)
        print('Resource name:', resource.name)
        print('Resource categories:', ', '.join(resource.categories))

        new_name = get_repo_slug_from_resource(resource)
        new_slug = get_repo_slug_from_resource(resource)

        if resource.name.startswith('translations..'):
            if new_name and resource.name != new_name:
                resource.name = new_name
                if is_dry_run():
                    print(f'\n### Saving new name "{new_name}" (dry-run) ###', '\n')
                else:
                    print(f'\n### Saving new name "{new_name}" ###', '\n')
                    resource.save('name')
            else:
                print(f'Error: Unrecognized slug pattern or categories to infer resource resource name from.')

        if re.match('^[a-z0-9]{32}$', resource.slug) or resource.slug.startswith('translations-'):
            if new_slug and resource.slug != new_slug:
                resource.slug = new_slug
                if is_dry_run():
                    print(f'\n### Saving new slug "{new_slug}" (dry-run) ###', '\n')
                else:
                    print(f'\n### Saving new slug "{new_slug}" ###', '\n')
                    try:
                        resource.save('slug')
                    except Exception as e:
                        # Slug is unique, so if it already exists, we get an error.
                        print(f'Error: {e}')
            else:
                print(f'Error: Unrecognized slug pattern or categories to infer resource slug from.')

        else:
            print(f'Skipping: "{resource.name}" because it seems to have proper attributes')


if __name__ == '__main__':
    main(sys.argv[1:])
