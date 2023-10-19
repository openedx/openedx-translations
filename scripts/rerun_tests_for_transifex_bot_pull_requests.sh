#!/usr/bin/env bash

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

list_transifex_pull_requests() {
    gh pr list -L"${MAX_PULL_REQUESTS_TO_RESTART:-1000}" \
	     --search "is:open Updates for file translations/ Transifex Event" \
	     --json=number --jq='.[].number'
}


re_run_pull_request_tests() {
    echo "========================================"
    echo "Re-running tests for https://github.com/openedx/openedx-translations/pull/$1";
    gh pr close $1;
    gh pr reopen $1;
    gh pr merge --auto --rebase $1;
}


for pull_request_number in $(list_transifex_pull_requests); do
    re_run_pull_request_tests $pull_request_number;
done
