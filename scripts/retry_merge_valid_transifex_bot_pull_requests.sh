#!/usr/bin/env bash
# Retry merging the stuck valid Transifex bot pull requests


set -e

if ! test -d .git; then
    echo "Error: This script must be run from the root of the openedx-translations repo"
    exit 1
fi

if ! which gh; then
    echo "Error: This script requires the 'gh' command line tool."
    echo "       See https://cli.github.com/ for installation instructions."
    exit 1
fi

list_transifex_prs_with_valid_checks() {
    # List the Transifex bot pull requests which have failed the tests
    # Print their head-commit hashes
    gh pr list -L"${MAX_PULL_REQUESTS:-1000}" \
	     --search "is:open Updates for file translations/ Transifex Event 'All translation files are valid.'" \
	     --json=number,headRefName,headRefOid --jq='.[].number'
}


retry_merge() {
    # Try to merge successful commit.
    echo "========================================"
    echo "Re-trying merge for valid pull request: https://github.com/openedx/openedx-translations/pull/$1";
    gh pr merge --rebase --auto "$1"
}


for pull_request_number in $(list_transifex_prs_with_valid_checks); do
    retry_merge $pull_request_number;
    sleep 0.5;
done
