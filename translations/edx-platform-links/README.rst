Open edX (``edx-platform``) Translations Links
==============================================

This directory contains links to the Python modules of plugins and XBlocks used in ``edx-platform``.

This directory is used to enable ``atlas`` fetch translations by module name rather than by repository name for two reasons:

1. When running ``make pull_translations`` in the edx-platform, the repository name of the installed XBlock isn't available. On the other hand XBlock's python module name is available.
2. Repo names can change but module names don't.


Example file structure of the ``edx-platform-links`` directory:

.. code-block:: bash

  edx-platform-links $ ll
  done -> ../DoneXBlock/done/
  drag_and_drop_v2 -> ../xblock-drag-and-drop-v2/drag_and_drop_v2/
  qualtricssurvey -> ../xblock-qualtrics-survey/qualtricssurvey/
  recommender -> ../RecommenderXBlock/recommender/
  submit_and_compare -> ../xblock-submit-and-compare/submit_and_compare/


The links in this directory are automatically created by the ``extract-translation-source-files.yml`` GitHub Action workflow in this repo.


Pulling ``edx-platform`` translations with Atlas
------------------------------------------------

The ``atlas`` command has been integrated in the ``edx-platform`` repository therefore there's no need to run ``atlas pull`` manually. Regardless, this section shows the manual command arguments because it's needed for some advanced usage of the edX Platform such as installing custom XBlocks that's not part of the openedx github organizaiton.

The ``atlas`` command to pull from this directory for Drag and Drop v2 XBlock can be executed in two ways:


Pull by repository name:

.. code-block:: bash

  $ atlas pull translations/xblock-drag-and-drop-v2:xblock-drag-and-drop-v2
  $ tree xblock-drag-and-drop-v2
  xblock-drag-and-drop-v2
  └── drag_and_drop_v2
      └── conf
          └── locale
              ├── ar
              │  └── LC_MESSAGES
              │      └── django.po
              ├── en
              │  └── LC_MESSAGES
              │      └── django.po
              └── fr_CA
                  └── LC_MESSAGES
                      └── django.po

Pull by python module name:

.. code-block:: bash

  $ atlas pull translations/edx-platform-links/drag_and_drop_v2:drag_and_drop_v2
  $ tree drag_and_drop_v2
  drag_and_drop_v2
  └── conf
      └── locale
          ├── ar
          │  └── LC_MESSAGES
          │      └── django.po
          ├── en
          │  └── LC_MESSAGES
          │      └── django.po
          └── fr_CA
              └── LC_MESSAGES
                  └── django.po

The second file tree has one less level of directories because ``xblock-drag-and-drop-v2`` is completely skipped.

