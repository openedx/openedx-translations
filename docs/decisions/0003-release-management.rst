Translation Releses branches and tags
#####################################

Status
******

Pending.

Context
*******
Open edX platform uses release branches and tags to make reproducible builds.
Most notably the `Named Releases`_ are used to name large releases.

Tutor uses numerical versioning for releases, but the concept is the same.

Problem
*******
With `OEP-58`_, translations are de-coupled from code and lives in its own
git repository -- this ``openedx/openedx-translations`` repository.

Therefore, translations are constantly updated even after releases are
cut e.g. ``open-release/quince.master`` and tagged ``open-release/quince.1``.

As of writing this proposal, translations live in the ``main`` branch with
no tags or branches that can be uses with the ``atlas pull --branch=BRANCH``
argument.

Proposed solution: Use release branches and daily tags
******************************************************

In order to facilitate reproducible builds, we propose to create a release
branch for each named release and tag it daily. This will allows builders
to either use the ``main`` branch or a specific release branch or tag
while building their server images.

Release branches
================

On every Open edX release cut, we propose to to create a branch in this
repository in the following format:

- ``open-release/quince.master`` for Quince release only.
- ``release/redwood`` for Redwood and other releases if the Build Test Release Working Group decides on the shorter naming.

For each new named-release a new Transifex project is created by creating a copy from the
`openedx-translations Transifex project`_ to a new one e.g.

``https://app.transifex.com/open-edx/openedx-translations-quince/content/`` to
capture a point-in-time source translations and
set up sync with the `Transifex GitHub App`_ for the
specific ``open-release/quince.master`` branch on the
https://github.com/openedx/openedx-translations repository.

Daily release tags
==================

Set up automated daily workflow to create tags for both
``main`` and release branches (e.g. ``release/redwood``) to capture
a point-in-time translations content.

The proposed naming for those branches is the following:

- ``main`` is tagged daily on the following tag format: ``release/main/2024-01-24``
- ``release/redwood`` is tagged daily with the following tag format: ``release/redwood/2024-01-24``


``open-release/quince.1`` tags won't be created because this repository doens't
contain code and it's highly compatible with previous versions from the same
named release.

Release end of life
*******************

Both of the release automated and Transifex projects are maintained for the last 5 of named releases.
After that the automated is ceased for the unsupported releases and the Transifex projects are deleted.

Operators of older releases are asked to maintain their own forks of this repository.

.. _OEP-58: https://open-edx-proposals.readthedocs.io/en/latest/architectural-decisions/oep-0058-arch-translations-management.html
.. _Transifex GitHub App: https://github.com/apps/transifex-integration
.. _openedx-translations Transifex project: https://app.transifex.com/open-edx/openedx-translations/content
.. _Named Releases: https://docs.openedx.org/en/latest/community/release_notes/named_release_branches_and_tags.html
