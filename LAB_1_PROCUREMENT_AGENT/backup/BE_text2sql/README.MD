## Instructions

1. Please create an agent called `text2sql_agent`

![alt text](images/agent.png)

with the following description

```
You are a furniture inventory specialist AI agent that helps users analyze and query furniture product data. When users ask questions about furniture inventory, products, categories, pricing, stock levels, materials, or any related business analytics, use the Text2SQL tool to convert their natural language questions into SQL queries and execute them against the furniture database. The tool will return structured results including the generated SQL query, executed data, and an AI explanation. After receiving the results, provide a clear, business-focused summary that directly answers the user's question, highlights key insights, and explains what the data means for inventory management, sales decisions, or customer service. Always present findings in an accessible way that helps users understand their furniture business performance and make informed decisions.
```

2. add new tools by uploading the openapi json file that is provided called `openapi_text2sql.json` and add to tools

![alt text](images/import.png)
![alt text](images/convert.png)

You should see that the tools have been added.

![alt text](images/tool.png)


3. Please choose `virtual-model/google/gemini-2.5-flash` and test the agent with following queries:

**Testing Queries**

- สินค้าในแต่ละหมวดหมู่มีกี่ชิ้น
- สินค้าที่ราคาสูงกว่า 1000 บาทมีอะไรบ้าง
- สินค้าที่ต้องประกอบและไม่ต้องประกอบมีกี่ชิ้น
- สินค้าในหมวดห้องนั่งเล่นทั้งหมด
- วัสดุที่ใช้ทำเฟอร์นิเจอร์มีอะไรบ้างและใช้กี่ชิ้น
- สินค้าที่มีสถานะสต็อกน้อยคืออะไร
- ราคาเฉลี่ยของสินค้าในแต่ละหมวดหมู่
- สินค้าที่มีการรับประกันมากกว่า 3 ปี
- สินค้าที่น้ำหนักมากกว่า 100 ปอนด์
- มูลค่าสต็อกรวมของสินค้าทั้งหมด




## How to add `AI gateway`. 
Read more later at: https://developer.watson-orchestrate.ibm.com/llm/managing_llm


4. Our goal is to add `google/gemini-2.5-flash` to watsonx Orchestrate. Rename `env-template` to `.env` and add in your `GOOGLE_API_KEY`.Please visit https://aistudio.google.com and click generate an API key to get your API key.

![alt text](images/getapikey.png)
![alt text](images/success.png)

NOTE:
If you are unable to create api key, it means you haven't enabled Gemini API in Google cloud console and created a project. Hence please, enable gemini API and create a project.

![alt text](images/unabletocreatekey.png)
Enabling Gemini API
![alt text](images/enablegemini.png)
Creating Project
![alt text](images/create-gcpproject.png)

5. Ensure you have completed the instructions in `00_SETUP`. Now that you have all credentials, please run `set_connections.sh` followed by `add_models.sh` in `AI_gateway/` folder. You should see the model being added.

![alt text](images/added_gemini.png)