import os
import json
import re
import sqlite3
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

# =========================
# Env & Model Initialization
# =========================
load_dotenv()

WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")
if not WATSONX_PROJECT_ID or not WATSONX_API_KEY:
    raise RuntimeError("Missing WATSONX_PROJECT_ID or WATSONX_API_KEY in environment.")

credentials = Credentials(url="https://us-south.ml.cloud.ibm.com", api_key=WATSONX_API_KEY)

model = ModelInference(
    model_id="openai/gpt-oss-120b",
    params={
        "frequency_penalty": 0,
        "max_tokens": 2000,
        "presence_penalty": 0,
        "temperature": 0,
        "top_p": 1,
    },
    credentials=credentials,
    project_id=WATSONX_PROJECT_ID,
)

# =========================
# SQLite (school.db)
# =========================
DB_PATH = os.getenv("FURNITURE_DB_PATH", "furniture.db")

def _connect_db() -> sqlite3.Connection:
    # Thread-safe for FastAPI dev; set row_factory for dict-like rows
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

db_conn = _connect_db()

def run_select(sql: str) -> Dict[str, Any]:
    """
    Execute a SELECT-only SQL statement and return rows + columns.
    """
    # Basic safety: only allow SELECT; no multiple statements
    stripped = sql.strip().rstrip(";").lstrip("(").strip()  # tolerate surrounding parens
    if not stripped.lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")
    if ";" in sql.strip().rstrip(";"):
        raise HTTPException(status_code=400, detail="Multiple statements are not allowed.")

    try:
        cur = db_conn.execute(sql)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = [dict(row) for row in cur.fetchall()]
        return {"columns": cols, "rows": rows, "row_count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {e}")

# =========================
# Prompt Templates
# =========================
SQL_GENERATION_PROMPT = """
You are a senior SQL expert. Convert the user's natural language question into a SQL query for a SQLite database with this schema:

TABLE สินค้า (
  รหัสสินค้า TEXT PRIMARY KEY,
  ชื่อสินค้า TEXT NOT NULL,
  หมวดหมู่ TEXT NOT NULL,        -- e.g., 'ห้องนั่งเล่น', 'ห้องนอน', 'ห้องทานอาหาร', 'สำนักงาน', 'จัดเก็บ'
  วัสดุ TEXT,
  ความยาว_นิ้ว INTEGER,
  ความกว้าง_นิ้ว INTEGER,
  ความสูง_นิ้ว INTEGER,
  สี TEXT,
  ราคา REAL NOT NULL,
  น้ำหนัก_ปอนด์ REAL,
  ต้องประกอบ BOOLEAN,          -- 1 = ต้องประกอบ, 0 = ไม่ต้องประกอบ
  การรับประกัน_ปี INTEGER,
  จำนวนสต็อก INTEGER NOT NULL,
  สถานะสต็อก TEXT,            -- e.g., 'มีสินค้า', 'สต็อกน้อย'
  วันที่สร้าง DATE DEFAULT CURRENT_DATE,
  อัปเดตล่าสุด TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

TABLE หมวดหมู่ (
  ชื่อหมวดหมู่ TEXT PRIMARY KEY,
  คำอธิบาย TEXT,
  วันที่สร้าง DATE DEFAULT CURRENT_DATE
);

Guidelines:
- SQLite-compatible SQL only.
- Use JOINs when needed: สินค้า.หมวดหมู่ = หมวดหมู่.ชื่อหมวดหมู่.
- For substring search (e.g., วัสดุ contains ไม้), use: วัสดุ LIKE '%ไม้%'.
- For price ranges, use appropriate comparison operators: ราคา > 500, ราคา BETWEEN 100 AND 1000.
- For assembly status: ต้องประกอบ = 1 (requires assembly), ต้องประกอบ = 0 (no assembly).
- For stock status: สถานะสต็อก = 'สต็อกน้อย' or สถานะสต็อก = 'มีสินค้า'.
- Calculate percentages using: ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM สินค้า), 2).
- For inventory value calculations: ราคา * จำนวนสต็อก.
- Common categories: 'ห้องนั่งเล่น', 'ห้องนอน', 'ห้องทานอาหาร', 'สำนักงาน', 'จัดเก็บ'.
- Common materials: 'ไม้โอ๊ค', 'หนังแท้', 'เหล็ก', 'กระจก', 'ผ้า', 'ไม้สน', 'วอลนัท'.
- If ambiguous, choose the most reasonable interpretation for furniture retail business.

Respond ONLY with a valid SQL query. No explanation, no markdown, no extra text - just the SQL query.
""".strip()

EXPLANATION_PROMPT = """
You are a furniture retail data analyst explaining query results to users. Given:
1. Original question: {question}
2. SQL query executed: {sql_query}
3. Query results: {results_summary}

Provide a clear, concise explanation of what the results show in relation to the original question. Focus on:
- What the furniture data reveals
- Key business insights or patterns
- Direct answer to the user's question
- Practical implications for inventory management, sales, or customer service

Use Thai language when appropriate and keep the explanation conversational and accessible to retail managers and non-technical users.
""".strip()

# # Example usage patterns for common furniture queries:

# EXAMPLE_QUERIES = {
#     "category_analysis": """
#     -- สินค้าในแต่ละหมวดหมู่มีกี่ชิ้น
#     SELECT หมวดหมู่, COUNT(*) as จำนวนสินค้า, 
#            ROUND(AVG(ราคา), 2) as ราคาเฉลี่ย
#     FROM สินค้า 
#     GROUP BY หมวดหมู่ 
#     ORDER BY จำนวนสินค้า DESC;
#     """,
    
#     "assembly_analysis": """
#     -- สินค้าที่ต้องประกอบ vs ไม่ต้องประกอบ
#     SELECT 
#         CASE WHEN ต้องประกอบ = 1 THEN 'ต้องประกอบ' ELSE 'ไม่ต้องประกอบ' END as การประกอบ,
#         COUNT(*) as จำนวน,
#         ROUND(AVG(ราคา), 2) as ราคาเฉลี่ย
#     FROM สินค้า 
#     GROUP BY ต้องประกอบ;
#     """,
    
#     "premium_products": """
#     -- สินค้าราคาสูงและการรับประกันยาว
#     SELECT ชื่อสินค้า, หมวดหมู่, ราคา, การรับประกัน_ปี
#     FROM สินค้า 
#     WHERE ราคา > 500 AND การรับประกัน_ปี > 2
#     ORDER BY ราคา DESC;
#     """,
    
#     "stock_status": """
#     -- การวิเคราะห์สถานะสต็อก
#     SELECT สถานะสต็อก, 
#            COUNT(*) as จำนวนรายการ,
#            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM สินค้า), 2) as เปอร์เซ็นต์
#     FROM สินค้า 
#     GROUP BY สถานะสต็อก;
#     """,
    
#     "inventory_value": """
#     -- มูลค่าสต็อกรวม
#     SELECT 
#         หมวดหมู่,
#         SUM(ราคา * จำนวนสต็อก) as มูลค่าสต็อกรวม,
#         AVG(ราคา) as ราคาเฉลี่ย
#     FROM สินค้า 
#     GROUP BY หมวดหมู่ 
#     ORDER BY มูลค่าสต็อกรวม DESC;
#     """
# }

# =========================
# Pydantic Schemas
# =========================
class Text2SQLRequest(BaseModel):
    question: str = Field(..., description="Natural language question")
    assumptions: Optional[str] = Field(None, description="Optional clarifications/assumptions")
    # Optional: cap result size
    limit: Optional[int] = Field(200, ge=1, le=10000, description="Max rows to return")

class Text2SQLResponse(BaseModel):
    sql_query: str
    explanation: str
    results: Dict[str, Any]      # {columns: [...], rows: [...], row_count: n}

# =========================
# Utilities
# =========================
def extract_sql_query(model_output: str) -> str:
    """
    Clean extraction of SQL query from model output.
    Handles various response formats and cleans the SQL.
    """
    content = model_output.strip()
    
    # Remove markdown code blocks if present
    if content.startswith("```"):
        lines = content.split('\n')
        # Find first line after opening ```
        start_idx = 1
        if len(lines) > 1 and lines[1].strip().lower() in ['sql', 'sqlite']:
            start_idx = 2
        
        # Find closing ```
        end_idx = len(lines)
        for i in range(start_idx, len(lines)):
            if lines[i].strip() == "```":
                end_idx = i
                break
        
        content = '\n'.join(lines[start_idx:end_idx]).strip()
    
    # Try to parse as JSON (legacy support)
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "sql_query" in parsed:
            return str(parsed["sql_query"]).strip()
    except (json.JSONDecodeError, KeyError):
        pass
    
    # Clean up common prefixes/suffixes
    prefixes_to_remove = [
        "sql query:", "query:", "sql:", "answer:", "result:",
        "here's the sql:", "here is the sql:", "the sql query is:"
    ]
    
    content_lower = content.lower()
    for prefix in prefixes_to_remove:
        if content_lower.startswith(prefix):
            content = content[len(prefix):].strip()
            break
    
    # Remove trailing explanations (look for common patterns)
    lines = content.split('\n')
    sql_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Stop at explanation-like content
        if any(line.lower().startswith(phrase) for phrase in [
            "this query", "explanation:", "this will", "note:", 
            "the above", "this sql", "//", "--", "#"
        ]):
            break
            
        sql_lines.append(line)
    
    result = ' '.join(sql_lines).strip()
    
    # Final cleanup
    result = result.rstrip(';').strip() + ';'
    
    if not result or result == ';':
        raise ValueError("No valid SQL query found in model output")
    
    return result

def format_results_summary(results: Dict[str, Any]) -> str:
    """
    Create a concise summary of query results for explanation generation.
    """
    row_count = results.get("row_count", 0)
    columns = results.get("columns", [])
    rows = results.get("rows", [])
    
    if row_count == 0:
        return "No results found."
    
    summary = f"Found {row_count} result{'s' if row_count != 1 else ''}.\n"
    summary += f"Columns: {', '.join(columns)}\n"
    
    # Include sample data (first few rows)
    if rows:
        sample_size = min(3, len(rows))
        summary += f"Sample data (first {sample_size} row{'s' if sample_size != 1 else ''}):\n"
        for i, row in enumerate(rows[:sample_size]):
            summary += f"Row {i+1}: {dict(row)}\n"
    
    return summary

def maybe_wrap_with_limit(sql: str, limit: Optional[int]) -> str:
    """
    Add LIMIT clause if not already present and limit is specified.
    """
    if not limit:
        return sql
    # Simple LIMIT appender if none present
    low = sql.lower()
    if " limit " in low:
        return sql
    return sql.rstrip().rstrip(";") + f" LIMIT {limit};"

def generate_explanation(question: str, sql_query: str, results: Dict[str, Any]) -> str:
    """
    Generate explanation using the AI model after query execution.
    """
    try:
        results_summary = format_results_summary(results)
        
        prompt = EXPLANATION_PROMPT.format(
            question=question,
            sql_query=sql_query,
            results_summary=results_summary
        )
        
        messages = [
            {"role": "system", "content": "You are a helpful data analyst."},
            {"role": "user", "content": prompt}
        ]
        
        out = model.chat(messages=messages)
        explanation = out["choices"][0]["message"]["content"].strip()
        
        return explanation
        
    except Exception as e:
        # Fallback explanation if AI generation fails
        row_count = results.get("row_count", 0)
        return f"Query executed successfully. Found {row_count} result{'s' if row_count != 1 else ''}."

# =========================
# FastAPI App
# =========================
app = FastAPI(
    title="Text2SQL + Execute (School DB)",
    version="1.0.0",
    description="Turns NL questions into SQL with watsonx.ai gpt-oss-120b and executes on SQLite school.db."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    # Basic DB check
    try:
        db_conn.execute("SELECT 1;").fetchone()
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok", "db_connected": db_ok, "db_path": os.path.abspath(DB_PATH)}

@app.post("/text2sql", response_model=Text2SQLResponse)
def text2sql(req: Text2SQLRequest):
    """
    Generate SQL from NL question, execute it on school.db, and return results with AI-generated explanation.
    """
    try:
        # Step 1: Generate SQL query
        user_content = req.question
        if req.assumptions:
            user_content += f"\n\nAdditional assumptions/notes: {req.assumptions}"
            
        messages = [
            {"role": "system", "content": SQL_GENERATION_PROMPT},
            {"role": "user", "content": user_content}
        ]
        
        sql_out = model.chat(messages=messages)
        sql_content = sql_out["choices"][0]["message"]["content"]
        
        # Step 2: Extract and clean SQL query
        sql_query = extract_sql_query(sql_content)
        
        # Step 3: Execute query
        sql_to_run = maybe_wrap_with_limit(sql_query, req.limit)
        results = run_select(sql_to_run)
        
        # Step 4: Generate explanation based on results
        explanation = generate_explanation(req.question, sql_query, results)

        return Text2SQLResponse(
            sql_query=sql_query,
            explanation=explanation,
            results=results
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"SQL parsing error: {ve}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model/DB error: {e}")

# Local dev
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)