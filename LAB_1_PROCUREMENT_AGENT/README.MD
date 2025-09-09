First go to watsonx orchestarte agent builder

then create agent name "Procurement_agent"

add description
"This agent uses an API for managing retail procurement, allowing users to create and view purchase orders, track price changes, and handle approvals. Data is stored in Google Sheets and the API is compatible with Watsonx Orchestrate."

next add tools using "procurement_openapi.json"

then add both tools in 

"Yesterday I bought a laptop named ThinkPad for $1200."
"Today I bought the same laptop, ThinkPad, from SupplierA for $1300."

answer other missing fields

access "https://docs.google.com/spreadsheets/d/1bnyC1w1z2VX3ZJjz6iex4oHFPK7D2F3ws3SxgKLc_XI/edit?usp=sharing"

to see the google sheet getting updated

"Show me the history of all laptops purchased."

