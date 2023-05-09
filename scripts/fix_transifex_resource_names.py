"""
Set the openedx-translations to readable resource names:

Run via `$ make fix_transifex_resource_names`.


Transifex sets resource slug names to a long name which makes it unreadable by translators .e.g.
 - "translations..frontend-app-something..src-i18n-transifex-input--main"

This script infer the resource name in two ways:

1) From slug if it starts with "translations..frontend-app-something..src-i18n-transifex-input--main" would result
   in "frontend-app-something" as resource name.

2) If no usable slug is available, infer the resource name from the categories e.g.
 - ["github#repository:openedx/openedx-translations#branch:main#path:translations/my-xblock/openassessment/conf/locale/en/LC_MESSAGES/djangojs.po"]
   would result in "my-xblock" as resource name.
"""

import configparser
import re
import sys
from os import getenv
from os.path import expanduser

from transifex.api import transifex_api


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


def get_repo_name_from_resource(resource):
    if resource.slug.startswith('translations-'):
        # example resource.slug = (
        #     "translations-my-xblock-conf-locale-en-lc-messages-django-po--main"
        # )
        new_name = re.sub(r'(^translations-|-src-i18n-.*--main$|-conf-locale-.*--main)', '', resource.slug)
        return new_name

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
                return directory_name


def main(argv):
    if '--help' in argv:
        # Print help document.
        print(__doc__)
        return

    print('Updating openedx-translations project resource names:')

    openedx_translations_proj = get_transifex_project()
    for resource in openedx_translations_proj.fetch('resources'):
        if resource.name.startswith('translations..'):
            print('------------')
            print('Updating:')
            print('Resource id:', resource.id)
            print('Resource slug:', resource.slug)
            print('Resource name:', resource.name)
            print('Resource categories:', ', '.join(resource.categories))

            new_name = get_repo_name_from_resource(resource)
            if new_name:
                if '--dry-run' in argv:
                    print('Saving new name (dry run):', new_name, '\n')
                else:
                    print('Saving new name:', new_name, '\n')
                    resource.name = new_name
                    resource.save('name')
            else:
                print(f'Error: Unrecognized slug pattern "{resource.slug}" or categories "{resource.categories}" '
                      f'to infer resource name from.')
        else:
            print(f'Skipping: "{resource.name}" because it seems to have a proper name (id={resource.id})')


if __name__ == '__main__':
    main(sys.argv[1:])
