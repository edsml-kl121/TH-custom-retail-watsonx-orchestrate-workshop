from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
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

def get_gsheet(sheet_number: int):
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
        worksheet = spreadsheet.worksheet(f"Sheet{sheet_number}")
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
    message: str = Field(..., description="Status message for the order. Only extract and present from the user's query if relevant. Make sure it is not assumed N/A or None.")
    product_name: str = Field(..., description="Name of the product. Only extract and present from the user's query if relevant. Make sure it is not assumed N/A or None.")
    supplier: str = Field(..., description="Supplier name. Only extract and present from the user's query if relevant. Make sure it is not assumed N/A or None.")
    price: float = Field(..., description="Price of the product. Only extract and present from the user's query if relevant. Make sure it is not assumed N/A or None.")
    quantity: int = Field(..., description="Quantity ordered. Only extract and present from the user's query if relevant. Make sure it is not assumed N/A or None.")
    purchase_date: str = Field(..., description="Date of purchase (YYYY-MM-DD). Only extract and present from the user's query if relevant. Make sure it is not assumed N/A or None.")
    staff_in_charge: str = Field(..., description="Staff responsible for the order. Only extract and present from the user's query if relevant. Make sure it is not assumed N/A or None.")
    approver: str = Field(..., description="Name of the approver. Only extract and present from the user's query if relevant. Make sure it is not assumed N/A or None.")
    price_category: Optional[str] = Field("No Saving", description="Price change category: 'Avoidance' (price increased), 'No Saving' (price unchanged), 'Reduction' (price decreased).")
    latest_price_change: Optional[str] = Field("0", description="Price difference from previous order (string, '0' if not applicable).")
    

class OrderHistoryItem(BaseModel):
    product_name: str
    supplier: str
    price: float
    quantity: int
    purchase_date: str
    staff_in_charge: str
    approver: str
    price_category: Optional[str] = "No Saving"
    latest_price_change: Optional[str] = "0"
    

class OrderHistoryResponse(BaseModel):
    orders: List[OrderHistoryItem]

class ErrorResponse(BaseModel):
    detail: str

@app.post(
    "/orders_1",
    response_model=OrderResponse,
    summary="Create a new purchase order 1",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 1"
)
def add_order_1(order: OrderRequest):
    """
    Add a new order to the order history.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver."
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(1)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_1",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 1",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 1"
)
def get_order_history_1():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(1)
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

@app.post(
    "/orders_2",
    response_model=OrderResponse,
    summary="Create a new purchase order 2",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 2"
)
def add_order_2(order: OrderRequest):
    """
    Add a new order to the order history.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver."
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(2)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_2",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 2",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 2"
)
def get_order_history_2():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(2)
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

@app.post(
    "/orders_3",
    response_model=OrderResponse,
    summary="Create a new purchase order 3",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 3"
)
def add_order_3(order: OrderRequest):
    """
    Add a new order to the order history.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver."
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(3)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_3",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 3",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 3"
)
def get_order_history_3():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(3)
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

@app.post(
    "/orders_4",
    response_model=OrderResponse,
    summary="Create a new purchase order 4",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 4"
)
def add_order_4(order: OrderRequest):
    """
    Add a new order to the order history.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver."
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(4)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_4",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 4",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 4"
)
def get_order_history_4():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(4)
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

@app.post(
    "/orders_5",
    response_model=OrderResponse,
    summary="Create a new purchase order 5",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 5"
)
def add_order_5(order: OrderRequest):
    """
    Add a new order to the order history.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver."
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(5)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_5",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 5",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 5"
)
def get_order_history_5():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(5)
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

@app.post(
    "/orders_6",
    response_model=OrderResponse,
    summary="Create a new purchase order 6",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 6"
)
def add_order_6(order: OrderRequest):
    """
    Add a new order to the order history.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver."
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(6)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_6",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 6",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 6"
)
def get_order_history_6():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(6)
        records = sheet.get_all_records()
        for row in records:
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

@app.post(
    "/orders_7",
    response_model=OrderResponse,
    summary="Create a new purchase order 7",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 7"
)
def add_order_7(order: OrderRequest):
    """
    Add a new order to the order history for Sheet7.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver.
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(7)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_7",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 7",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 7"
)
def get_order_history_7():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(7)
        records = sheet.get_all_records()
        for row in records:
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

@app.post(
    "/orders_8",
    response_model=OrderResponse,
    summary="Create a new purchase order 8",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 8"
)
def add_order_8(order: OrderRequest):
    """
    Add a new order to the order history for Sheet8.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver.
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(8)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_8",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 8",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 8"
)
def get_order_history_8():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(8)
        records = sheet.get_all_records()
        for row in records:
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

@app.post(
    "/orders_9",
    response_model=OrderResponse,
    summary="Create a new purchase order 9",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 9"
)
def add_order_9(order: OrderRequest):
    """
    Add a new order to the order history for Sheet9.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver.
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(9)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_9",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 9",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 9"
)
def get_order_history_9():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(9)
        records = sheet.get_all_records()
        for row in records:
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

@app.post(
    "/orders_10",
    response_model=OrderResponse,
    summary="Create a new purchase order 10",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 10"
)
def add_order_10(order: OrderRequest):
    """
    Add a new order to the order history for Sheet10.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver.
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(10)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_10",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 10",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 10"
)
def get_order_history_10():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(10)
        records = sheet.get_all_records()
        for row in records:
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

@app.post(
    "/orders_11",
    response_model=OrderResponse,
    summary="Create a new purchase order 11",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 11"
)
def add_order_11(order: OrderRequest):
    """
    Add a new order to the order history for Sheetx.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver.
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(11)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_11",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 11",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 11"
)
def get_order_history_11():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(11)
        records = sheet.get_all_records()
        for row in records:
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

@app.post(
    "/orders_12",
    response_model=OrderResponse,
    summary="Create a new purchase order 12",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 12"
)
def add_order_12(order: OrderRequest):
    """
    Add a new order to the order history for Sheet12.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver.
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(12)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_12",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 12",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 12"
)
def get_order_history_12():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(12)
        records = sheet.get_all_records()
        for row in records:
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

@app.post(
    "/orders_13",
    response_model=OrderResponse,
    summary="Create a new purchase order 13",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 13"
)
def add_order_13(order: OrderRequest):
    """
    Add a new order to the order history for Sheet13.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver.
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(13)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_13",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 13",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 13"
)
def get_order_history_13():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(13)
        records = sheet.get_all_records()
        for row in records:
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

@app.post(
    "/orders_14",
    response_model=OrderResponse,
    summary="Create a new purchase order 14",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 14"
)
def add_order_14(order: OrderRequest):
    """
    Add a new order to the order history for Sheet14.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver.
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(14)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_14",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 14",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 14"
)
def get_order_history_14():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(14)
        records = sheet.get_all_records()
        for row in records:
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

@app.post(
    "/orders_15",
    response_model=OrderResponse,
    summary="Create a new purchase order 15",
    description="""Submit details to add a new purchase order, including product, supplier, quantity, and staff information. 
        Calculates price change compared to previous order for the same product.
        """,
    response_description="Returns the created order with a status message or an error message if some field are stil missing.\nFields returned:\n- message: Status message\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable) Downstream logic should extract and present only the fields relevant to the user’s query.",
    operation_id="addOrder 15"
)
def add_order_15(order: OrderRequest):
    """
    Add a new order to the order history for Sheet15.
    Calculates price change compared to previous order for the same product.
    User need to provide all fields in OrderRequest model including product_name, supplier, price, quantity, purchase_date (YYYY-MM-DD), staff_in_charge, and approver.
    """
    latest_price_change = "0"
    price_category = "No Saving"  # Default value
    try:
        sheet = get_gsheet(15)
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
            latest_price_change = str(price_change)
            # Set price_category based on price comparison
            if order.price > previous_price:
                price_category = "Avoidance"
            elif order.price < previous_price:
                price_category = "Reduction"
            else:
                price_category = "No Saving"
        else:
            price_category = "No Saving"
        # Append new order with price_category
        sheet.append_row([
            order.product_name,
            order.supplier,
            order.price,
            order.quantity,
            order.purchase_date,
            order.staff_in_charge,
            order.approver,
            price_category,
            latest_price_change
        ])
    except Exception as e:
        print(f"[ERROR] Failed to add order: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Error accessing Google Sheet: {str(e)}"})
    return OrderResponse(
        message="Order added successfully",
        product_name=order.product_name,
        supplier=order.supplier,
        price=order.price,
        quantity=order.quantity,
        purchase_date=order.purchase_date,
        staff_in_charge=order.staff_in_charge,
        approver=order.approver,
        price_category=price_category,
        latest_price_change=latest_price_change
    )

@app.get(
    "/orders_15",
    response_model=OrderHistoryResponse,
    summary="View purchase order history 15",
    description="Retrieve the complete history of purchase orders, including product_name, supplier, price, quantity, purchase_date, staff_in_charge, approver, price_category, latest_price_change information.",
    response_description="Returns a list of orders. Each order includes:\n- product_name: Name of the product\n- supplier: Supplier name\n- price: Price (float)\n- quantity: Quantity (int)\n- purchase_date: Date of purchase (YYYY-MM-DD)\n- staff_in_charge: Staff responsible\n- approver: Approver name\n- price_category: Price change category ('Avoidance', 'No Saving', 'Reduction')\n- latest_price_change: Price difference from previous order (string, '0' if not applicable)",
    operation_id="getOrderHistory 15"
)
def get_order_history_15():
    """
    Retrieve the full order history.
    Returns all recorded purchase orders.
    """
    orders = []
    try:
        sheet = get_gsheet(15)
        records = sheet.get_all_records()
        for row in records:
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
