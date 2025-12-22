openedx-translations
####################

This openedx-translations repository contains translation files from Open edX repositories
to be kept in sync with Transifex. To accomplish this task, a GitHub Action in
``.github/workflows/`` named ``extract-translation-source-files.yml`` regularly extracts
English translation source files form Open edX repositories containing code and adds them
to this repository. A GitHub Transifex app allows for the automatic upload of these
translation files and after being translated on Transifex, the automatic download back
into this repository. The translation files in this repository can then be accessed by
using the `openedx-atlas`_ CLI tool to download specific directories of translation files
from openedx-translations.

This repository implements the `OEP-58`_ proposal.

Main and Release branches
*************************

This repository has a main branch in addition to a dedicated branch for every
release. As of May 10th, 2024 the following are the release branches:

``main`` branch
===============

This branch is used for the latest version of Open edX such as
`Tutor nightly`_, `edx-platform "master" branch`_ and others.

To translate the latest versions the `open-edx/openedx-translations`_ Transifex
project should be used.


``open-release/<release-name>.master`` branch
=============================================

This branch is used for the latest version of the Open edX Release, which will
be a version of Tutor and corresponding branches in tagged repos. For example,
for the Redwood release (June 2024), the branches were:
`Tutor Redwood v18`_, `edx-platform "open-release/redwood.master" branch`_
and others.

To update translations for a named release, find the corresponding named release project in the `Open edX Transifex project <https://app.transifex.com/open-edx/>`_  by searching for the release name (for example, Redwood) in the search box. 

Tools for repository maintainers
********************************

This repository contains both `GitHub Actions workflows`_ and
`Makefile programs`_ to automate and assist maintainers chores including:

Fix resource names in Transifex
===============================

The GitHub Transifex App integeration puts an inconvenient names for resources like ``translations..frontend-app-something..src-i18n-transifex-input--main``
instead of ``frontend-app-something``.

Running this command should be safe and can be ran multiple times on
both the main ``openedx-translations`` project or on release projects
by setting the ``TRANSIFEX_PROJECT_SLUG`` make variable as shown below::

    # Dry run the name fix
    make TRANSIFEX_PROJECT_SLUG='openedx-translations-zebrawood' fix_transifex_resource_names_dry_run
    # If runs without errors, run the actual command:
    make TRANSIFEX_PROJECT_SLUG='openedx-translations-zebrawood' fix_transifex_resource_names

Translation validation
======================

This repository validates translations with the GNU gettext ``msgfmt`` tool.

The validation can be run locally with the following command:

.. code-block:: bash

    make validate_translations


The validation errors is also posted as a comment on the update translation
pull requests.

Retry merging Transifex pull requests
=====================================

If GitHub Actions has an outage or any other issues there will be a backlog
of stale unmerged Transifex bot pull requests. To re-run tests and merge the
pull requests, run the following command:

.. code-block:: bash

    make retry_merge_transifex_bot_pull_requests

.. _OEP-58: https://github.com/openedx/open-edx-proposals/pull/367
.. _openedx-atlas: https://github.com/openedx/openedx-atlas

.. _sync_translations.yml workflow on GitHub: https://github.com/openedx/openedx-translations/actions/workflows/sync-translations.yml

.. _open-edx/openedx-translations: https://app.transifex.com/open-edx/openedx-translations/dashboard/
.. _open-edx/openedx-translations-redwood: https://app.transifex.com/open-edx/openedx-translations-redwood/dashboard/


.. _Tutor nightly: https://docs.tutor.edly.io/tutorials/nightly.html
.. _edx-platform "master" branch: https://github.com/openedx/edx-platform
.. _Tutor Redwood v18: https://docs.tutor.edly.io/
.. _edx-platform "open-release/redwood.master" branch: https://github.com/openedx/edx-platform/tree/open-release/redwood.master

.. _GitHub Actions workflows: https://github.com/openedx/openedx-translations/tree/main/.github/workflows
.. _Makefile programs: https://github.com/openedx/openedx-translations/blob/main/Makefile
