CUT=20090101
TOKENS=baseline/tokens.txt
TOKEN_ID=0

for d in baseline/sbl_inputs/*; do
  base=$(basename "$d")              # e.g. modelscope__agentscope
  owner="${base%%__*}"               # modelscope
  repo="${base#*__}"                 # agentscope
  full="$owner/$repo"

  python curation/swe_task_crawling/get_tasks_pipeline.py \
    --repos "$full" \
    --gh_token_file "$TOKENS" \
    --token_ids "$TOKEN_ID" \
    --path_prs "$d/prs" \
    --path_tasks "$d/tasks" \
    --cutoff_date "$CUT" 
done