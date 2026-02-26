gh run list --limit 3000 --status queued  --json databaseId -q '.[].databaseId' | tac  > runs-to-cancel.txt
cat runs-to-cancel.txt | xargs -n1 gh run cancel
