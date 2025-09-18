$env:PYTHONUTF8=1

git lfs install

orchestrate env activate test-env

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition

orchestrate knowledge-bases import -f "$SCRIPT_DIR/knowledge_base/accounting_knowledge_base.yaml"
orchestrate agents import -f "$SCRIPT_DIR/agents/Accounting_RAG_agent.yaml"
