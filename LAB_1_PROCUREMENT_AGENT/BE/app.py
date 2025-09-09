from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import List, Optional
import os
from fastapi.responses import JSONResponse
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv


env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

app = FastAPI(
    title="Retail Procurement API",
    description="Retail procurement management API for submitting and viewing purchase orders, tracking price changes, and managing staff approvals. Compatible with Watsonx Orchestrate and Swagger UI.",
    version="1.0.0",
    openapi_version="3.0.0"
)

# Add servers section to OpenAPI spec
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {
            "url": "https://be-procurement-agent.1zy07nqib9k1.us-south.codeengine.appdomain.cloud",
            "description": "Production server"
        }
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Google Sheets setup
SHEET_ID = "1bnyC1w1z2VX3ZJjz6iex4oHFPK7D2F3ws3SxgKLc_XI"  # Replace with your actual spreadsheet ID
# The worksheet/tab name is 'Sheet1', not 'order_history'
SHEET_NAME = "Sheet1"

def get_gsheet():
    try:
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path or not os.path.exists(creds_path):
            raise FileNotFoundError(f"Service account credentials file not found at {creds_path}")
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        return worksheet
    except Exception as e:
        print(f"[ERROR] Google Sheets access failed: {e}")
        raise

class OrderRequest(BaseModel):
    product_name: str
    supplier: str
    price: float
    quantity: int
    purchase_date: str  # YYYY-MM-DD
    staff_in_charge: str
    approver: str

class OrderResponse(BaseModel):
    message: str
    latest_price_change: Optional[str] = "-"

class OrderHistoryItem(BaseModel):
    product_name: str
    supplier: str
    price: float
    quantity: int
    purchase_date: str
    staff_in_charge: str
    approver: str
    latest_price_change: Optional[str] = "-"

class OrderHistoryResponse(BaseModel):
    orders: List[OrderHistoryItem]

class ErrorResponse(BaseModel):
    detail: str

@app.post(
    "/orders",
    response_model=OrderResponse,
    summary="Create a new purchase order",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product. 
        User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver.
        Always ask user for every fields when creating adding a new order.
        """,
    operation_id="addOrder"
)
def add_order(order: OrderRequest):
    """
    Add a new order to the order history.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver."
    """
    latest_price_change = "-"
    try:
        sheet = get_gsheet()
        records = sheet.get_all_records()
        previous_price = None
        for row in records:
            if row.get("product_name", "").strip().lower() == order.product_name.strip().lower():
                try:
                    previous_price = float(row.get("price", 0))
                except Exception:
                    previous_price = None
        if previous_price is not None:
            price_change = order.price - previous_price
            if price_change != 0:
                latest_price_change = str(price_change)
        # Append new order
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(message="Order added successfully", latest_price_change=latest_price_change)

@app.get(
    "/orders",
    response_model=OrderHistoryResponse,
    summary="View purchase order history",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, latest_price_change information.",
    operation_id="getOrderHistory"
)
def get_order_history():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet()
        records = sheet.get_all_records()
        for row in records:
            # Ensure latest_price_change is a string
            if "latest_price_change" in row:
                row["latest_price_change"] = str(row["latest_price_change"])
            try:
                orders.append(OrderHistoryItem(**row))
            except Exception as item_error:
                print(f"[ERROR] Failed to parse row: {row}, error: {item_error}")
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch order history: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderHistoryResponse(orders=orders)
