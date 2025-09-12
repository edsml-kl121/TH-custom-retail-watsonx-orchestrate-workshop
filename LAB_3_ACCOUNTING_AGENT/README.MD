
# Accounting RAG Agent Setup Guide

This lab we will use an ADK(Agent Development Kit) to create and configurate the accounting agent. This agent allows users to chat and ask question from a document which is stored in a knowledge base within watsonx orchestrate embed vector database.

---


## 1. Open up your code editor
Download the git repository as a .zip file
Open it using a code editor
Open and locate the repository for LAB_3B_RAG_AGENT
CD your terminal/command line into the LAB_3B_RAG_AGENT/general agent folder

## 2. Deploy the agent to watsonx orchestrate using command line


### Make sure the scripts executable (run this once):

#### For Linux/macOS:
```bash
chmod +x import_all.sh
```
or
```bash
bash import_all.sh
```

#### For Windows (PowerShell):
Open PowerShell and run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Unblock-File -Path .\import_all.ps1
```

Then run the script:
```powershell
./import_all.ps1
```

---

## 3. Look up for your deployed agent within watsonx orchestrate agent builder

Once you found your deployed agent, click on it to enter the agent builder page

## 4. Test your agent capability using the following questions

- `การบันทึกบัญชีต้องทำอะไรบ้าง`
- `การจัดทำรายงานทางการเงินมีกี่ประเภท`
- `นโยบายบัญชีหลักมีอะไรบ้าง`
- `วิธีการประเมินมูลค่าสินค้าคงเหลือที่ใช้มีอะไรบ้าง`
- `การควบคุมค่าใช้จ่ายของบริษัทต้องทำอย่างไร`
- `หลักการแบ่งแยกหน้าที่ (Segregation of Duties) คืออะไร`



