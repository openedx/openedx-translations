.PHONY: piptools upgrade fix_transifex_resource_names translations_scripts_requirements \
validate_translation_files test_requirements test fix_transifex_resource_names_dry_run \
retry_merge_transifex_bot_pull_requests

# Default project to work on. Override to release project e.g. `openedx-translations-redwood` when cutting a release.
export TRANSIFEX_PROJECT_SLUG := openedx-translations

# Max pull requests
export MAX_PULL_REQUESTS := 1000


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

fix_transifex_resource_names:  ## Runs the script on the TRANSIFEX_PROJECT_SLUG project
	python scripts/fix_transifex_resource_names.py

fix_transifex_resource_names_dry_run:  ## Runs the script in --dry-run mode on the TRANSIFEX_PROJECT_SLUG project
	python scripts/fix_transifex_resource_names.py --dry-run


test_requirements:  ## Installs test.txt requirements
	pip install -q -r requirements/test.txt

test:  ## Run scripts tests
	 pytest -v -s --cov=. --cov-report=term-missing --cov-report=html scripts/tests

validate_translation_files:  ## Run basic validation to ensure files are compilable
	python scripts/validate_translation_files.py

retry_merge_transifex_bot_pull_requests:  ## Fix Transifex bot stuck and unmerged pull requests via restarting tests.
	bash scripts/retry_merge_transifex_bot_pull_requests.sh

retry_merge_valid_transifex_bot_pull_requests:  ## Fix Transifex bot stuck and unmerged pull requests via `gh pr merge --auto`.
	bash scripts/retry_merge_valid_transifex_bot_pull_requests.sh
