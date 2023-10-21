Mark invalid entries in po files as fuzzy
#########################################

Context
*******
As of the `OEP-58`_, the Transifex GitHub App is used to sync Translations.
These translations are validated by `LexiQA`_, built-in Transifex quality
checks, and human reviewers. During this synchronization process, the
`Transifex GitHub App`_ creates pull requests to this repository. The
translations in the pull requests are then validated by ``msgfmt`` in CI.

Problem
*******
There are times when the translations being synchronized fail ``msgfmt``
validation. This prevents the pull requests from being merged.


Design Decision
***************

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


Informing the Translators
*************************
Translators can be notified about invalid translations via Slack, Transifex
or GitHub issues depending on the community's preference.

Pros and Cons
*************

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

Rejected Alternative: Keep pull requests open
*********************************************

- **Create a Transifex issue only:** It would be possible to identify the
  faulty entries and create a Transifex issue via API to the faulty entries.
  However, this would require attention from the translators
  team, which can take a rather long time therefore creating a backlog of
  invalid entries. Additionally, Transifex issues are not understood or used
  by most of the Open edX community.

- **Post errors on Slack only:** Post the errors on Slack and ask the
  translators
  to fix them. Same as the previous option, not all translators are on Slack.
  Additionally, this option would have a slow feedback loop causing the pull
  requests backlog to build-up.

- **Mark faulty entries as unreviewed only:** Use the Transifex API to mark
  the the invalid entries as unreviewed, then pull only
  reviewed entries into this repository.
  This option would require an extensive use the of the Transifex API,
  and pull again which can be complex to implement. Additionally, this option
  would have a slow feedback loop causing the pull requests backlog to
  build-up.


.. _OEP-58: https://open-edx-proposals.readthedocs.io/en/latest/architectural-decisions/oep-0058-arch-translations-management.html
.. _LexiQA: https://help.transifex.com/en/articles/6219179-lexiqa
.. _Transifex GitHub App: https://github.com/apps/transifex-integration
