.PHONY: piptools upgrade fix_transifex_resource_names translations_scripts_requirements validate_translation_files \
sync_translations sync_translations_github_workflow rerun_tests_for_transifex_bot_pull_requests


# Default languages for the sync_translations.py file
# This list represents the supported languages by the Open edX community as stated by the Translators Working Group:
#   - https://openedx.atlassian.net/wiki/spaces/COMM/pages/3157524644/Translation+Working+Group#The-following-is-a-table-of-the-latest-list-of-languages-supported--by-the-Translation-Working-Group
export TX_LANGUAGES := ar,da,de_DE,el,es_419,es_ES,fr_CA,hi,he,id,it_IT,pt_BR,pt_PT,ru,th,tr_TR,uk,zh_CN


piptools:
	pip install -q -r requirements/pip_tools.txt

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: piptools  ## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	pip-compile --allow-unsafe --rebuild --upgrade -o requirements/pip.txt requirements/pip.in
	pip-compile --rebuild --upgrade -o requirements/pip_tools.txt requirements/pip_tools.in
	pip install -qr requirements/pip.txt
	pip install -qr requirements/pip_tools.txt
	pip-compile --rebuild --upgrade -o requirements/translations.txt requirements/translations.in
	pip-compile --rebuild --upgrade -o requirements/test.txt requirements/test.in


translations_scripts_requirements:  ## Installs the requirements file
	pip install -q -r requirements/translations.txt

fix_transifex_resource_names:  ## Runs the script
	python scripts/fix_transifex_resource_names.py

fix_transifex_resource_names_dry_run:  ## Runs the script in --dry-run mode
	python scripts/fix_transifex_resource_names.py --dry-run


test_requirements:  ## Installs test.txt requirements
	pip install -q -r requirements/test.txt

test:  ## Run scripts tests
	 pytest -v -s --cov=. --cov-report=term-missing --cov-report=html scripts/tests

validate_translation_files:  ## Run basic validation to ensure files are compilable
	python scripts/validate_translation_files.py

sync_translations:  ## Syncs from the old projects to the new openedx-translations project
	python scripts/sync_translations.py $(SYNC_ARGS)

sync_translations_github_workflow:  ## Run with parameters from .github/workflows/sync-translations.yml
	make SYNC_ARGS="--simulate-github-workflow $(SYNC_ARGS)" sync_translations

export MAX_PULL_REQUESTS_TO_RESTART := 1000
retry_merge_transifex_bot_pull_requests:  ## Fix Transifex bot stuck and unmerged pull requests.
	bash scripts/retry_merge_transifex_bot_pull_requests.sh
