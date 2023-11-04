Mark invalid entries in po files as fuzzy
#########################################

Status
******

Rejected.

Context
*******
As of `OEP-58`_, the `Transifex GitHub App`_ is used to sync translations
between Transifex projects and the openedx-translations repository.
Within Transifex, translations are subjected to automated validation,
incorporating checks from both the platform itself and the `LexiQA`_ add-on,
in addition to being reviewed by human translators. During the synchronization
process, the `Transifex GitHub App`_ creates pull requests to the openedx-translations
repository. The pull requests trigger a CI workflow that runs ``msgfmt`` to
validate the translations.

Problem
*******
There are times when the translations being synchronized fail ``msgfmt``
validation. This prevents the pull requests from being automatically merged.


Default Workflow: Keep pull requests open
********************************************

By default a failing pull request will be kept open. Once translators
fix the invalid entries the `Transifex GitHub App`_ will update the
pull request and merge it automatically.

Translators do not monitor pull requests to the openedx-translations repo,
and have requested to be notified of invalid entries via slack. This will start
as a manual process. Work to automate this in the future will be tracked in
`Notify translators about invalid entries`_.

Rejected Alternative: Mark invalid entries as fuzzy
***************************************************

A GitHub Actions workflow will be implemented to mark invalid entries in
synchronized ``.po`` files as ``fuzzy``. This will update pull requests
created by the `Transifex GitHub App`_.

To ensure a safe and reliable workflow, the following workflows will be
combined into one single workflow with multiple jobs:

#. Run ``python-tests.yml`` to validate the python code
#. Then, run ``validate-translation-files.yml`` which performs the following:

   #. Validate the po-files using ``msgfmt``
   #. Notify the translators about the invalid entries via the preferred
      communication channel (Slack, Transifex, GitHub)
   #. Edit the po files to mark invalid entries as ``fuzzy``, so it's
      excluded from ``.mo`` files
   #. Revalidate the files

#. Commit the updated entries and push to the PR branch
#. Automatically merge the PR

Rejection Reasons
=================

- The workflow script edits the translations and effectively hide the
  errors, which can be confusing for the translators.
- Writing to the pull request will not trigger the GitHub Actions workflow,
  therefore the pull request cannot be merged unless the commit status
  is overridden manually via `GitHub "create a commit status" API`_.
- The solution is ``.po`` file specific. And there's no similar solution for
  ``.json``, ``.yaml``, iOS, Android or other translations files.

Please refer to the original pull request which contains the rejected
implementation: `mark invalid entries as fuzzy | FC-0012`_.


Pros and Cons
=============

**Pros**

* New valid strings would make it into the ``.mo`` files
* There's no need for manual intervention, therefore it's fast and won't
  create a backlog of pull requests.
* Rejected strings are easily identifiable by looking in the code, so it's
  easy to fix them.
* Translators can be notified about invalid translations via Slack, Transifex,
  GitHub depending on the community's preference.


**Cons**

* The workflow script runs and edits the pull request, which can be
  confusing for the reviewers.
* Previously valid entries are going to be overwritten with new ``fuzzy``
  strings which will make those entries to be shown in source language
  (English).


.. _OEP-58: https://open-edx-proposals.readthedocs.io/en/latest/architectural-decisions/oep-0058-arch-translations-management.html
.. _LexiQA: https://help.transifex.com/en/articles/6219179-lexiqa
.. _Transifex GitHub App: https://github.com/apps/transifex-integration
.. _GitHub "create a commit status" API: https://docs.github.com/en/rest/commits/statuses?apiVersion=2022-11-28#create-a-commit-status
.. _mark invalid entries as fuzzy | FC-0012: https://github.com/openedx/openedx-translations/pull/1944
.. _Notify translators about invalid entries: https://github.com/openedx/openedx-translations/issues/2130
