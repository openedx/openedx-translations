#!/usr/bin/env bash
# Retry auto-merging the stuck Transifex bot pull requests


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

list_transifex_commits_with_failed_checks() {
    # List the Transifex bot pull requests which have failed the tests
    # Print their head-commit hashes
    gh pr list -L"${MAX_PULL_REQUESTS_TO_RESTART:-1000}" \
	     --search "is:open Updates for file translations/ Transifex Event" \
	     --json=number,headRefName,headRefOid --jq='.[].headRefOid'
}


retry_commit_workflow() {
    # Re-run the tests for all workflow runs in a given commit
    # Using the `--event=pull_request` option because we're intested only in Auto-merge related workflow runs
    echo "========================================"
    echo "Re-running tests for failed pull request commit: https://github.com/openedx/openedx-translations/commit/$1";
    gh run list --commit="$1" --event=pull_request --json=databaseId --jq='.[].databaseId' | xargs -I{} gh run rerun {}
}


for pull_request_number in $(list_transifex_commits_with_failed_checks); do
    retry_commit_workflow $pull_request_number;
done
