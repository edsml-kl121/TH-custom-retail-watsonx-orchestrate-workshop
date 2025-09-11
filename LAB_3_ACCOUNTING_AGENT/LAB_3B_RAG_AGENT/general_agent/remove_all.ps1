$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition

orchestrate knowledge-bases remove -n general_knowledge_base
# orchestrate agents remove -n ibm_agent -k native
