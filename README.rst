openedx-translations
####################

The openedx-translations repository contains translation files from Open edX
repositories to be kept in sync with Transifex. To accomplish this task, a GitHub Action
in `.github/workflows/` named `extract-translation-source-files.yml` regularly extracts
English translation source files form Open edX repositories containing code and adds them
to this repository. A GitHub Transifex app allows for the automatic upload of these
translation files and after being translated on Transifex, the automatic download back
into this repository. The translation files in this repository can then be accessed by
using the openedx-atlas CLI tool to download specific directories of translation files
from openedx-translations.

Current State
*************

This repository is currently a prototype and offers limited capability. The
GitHub Action `extract-translation-source-files.yml` generates English translation source
files for only one repository `openedx/credentials`. These translation source files are
the only ones uploaded to the Transifex project openedx-translations. The English
translation source files have only been translated into one language: French Canadian
(fr_CA). The openedx-atlas CLI tool can only be used to pull translation files from the
credentials directory in openedx-translations.

For more information, please see the pull request for `OEP-58`_.

.. _OEP-58: https://github.com/openedx/open-edx-proposals/pull/367
