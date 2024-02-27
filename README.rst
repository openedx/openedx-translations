openedx-translations
####################

The openedx-translations repository contains translation files from Open edX repositories
to be kept in sync with Transifex. To accomplish this task, a GitHub Action in
``.github/workflows/`` named ``extract-translation-source-files.yml`` regularly extracts
English translation source files form Open edX repositories containing code and adds them
to this repository. A GitHub Transifex app allows for the automatic upload of these
translation files and after being translated on Transifex, the automatic download back
into this repository. The translation files in this repository can then be accessed by
using the `openedx-atlas`_ CLI tool to download specific directories of translation files
from openedx-translations.

Current State
*************

This repository is currently under active development with limited use.
The GitHub Action
``extract-translation-source-files.yml`` generates English translation source
files for the configured repositories. These translation source files are the only
ones uploaded to the Transifex project openedx-translations. The English translation
source files have only been translated into one language: French Canadian (fr_CA). The
`openedx-atlas`_ CLI tool can only be used to pull translation files from the credentials
directory in openedx-translations.

Translation validation
**********************

This repository validates translations with the GNU gettext ``msgfmt`` tool.

The validation can be run locally with the following command:

.. code-block:: bash

    make validate_translations


The validation errors is also posted as a comment on the update translation
pull requests.

If GitHub Actions has an outage or any other issues there will be a backlog
of stale unmerged Transifex bot pull requests. To re-run tests and merge the
pull requests, run the following command:

.. code-block:: bash

    make retry_merge_transifex_bot_pull_requests


Translations sync from old Transifex projects
*********************************************

This repository allows for syncing translations old
`open-edx/edx-platform`_ and `open-edx/xblocks`_ Transifex projects into
the new `open-edx/openedx-translations`_ Transifex project. This is done by
trigger the `sync_translations.yml workflow on GitHub`_.

Alternatively, you can run the following command to trigger the workflow:

.. code-block:: bash

    # Run with parameters from .github/workflows/sync-translations.yml
    make sync_translations_github_workflow


For more information, please see the pull request for `OEP-58`_.


.. _OEP-58: https://github.com/openedx/open-edx-proposals/pull/367
.. _openedx-atlas: https://github.com/openedx/openedx-atlas

.. _sync_translations.yml workflow on GitHub: https://github.com/openedx/openedx-translations/actions/workflows/sync-translations.yml

.. _open-edx/edx-platform: https://app.transifex.com/open-edx/edx-platform/dashboard/
.. _open-edx/xblocks: https://app.transifex.com/open-edx/xblocks/dashboard/
.. _open-edx/openedx-translations: https://app.transifex.com/open-edx/openedx-translations/dashboard/
