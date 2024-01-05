import firebase_admin
from firebase_admin import credentials, auth, firestore

from modal import Image, Stub, asgi_app, Mount
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Custom imports
from config import (
    ADMIN_COFFEE_ADD_URL,
    ADMIN_COFFEE_UPDATE_URL,
    ADMIN_COFFE_DELETE_URL,
    USER_SIGN_UP_URL,
    USER_LOGIN_URL,
    LIST_AVAILABLE_COFFEES_URL,
    ORDER_PLACE_URL,
    ORDER_GET_RECENT_URL,
    DB_CONFIG_FILE,
)

origins = ["http://localhost:3000", "http://localhost", "*"]

web_app = FastAPI()
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
image = Image.debian_slim(python_version="3.9").pip_install("firebase_admin")
stub = Stub("webhw45", image=image)

db = None


@web_app.post(USER_SIGN_UP_URL)
async def user_signup(request: Request):
    body = await request.json()

    email = body.get("email")
    password = body.get("password")
    try:
        user_record = auth.create_user(email=email, password=password)
        return {"uid": user_record.uid, "email": email}
    except Exception as e:
        return {"error": str(e)}


@web_app.post(USER_LOGIN_URL)
async def user_login(request: Request):
    body = await request.json()
    email = body.get("email")
    password = body.get("password")

    try:
        user = auth.get_user_by_email(email)
        return {"message": "User logged in successfully", "uid": user.uid}
    except Exception as e:
        return {"error": str(e)}


@web_app.post(ADMIN_COFFEE_ADD_URL)
async def add_coffee(request: Request):
    if db is None:
        raise Exception("Firestore client not initialized")

    body = await request.json()
    print(body)
    coffee_data = {
        "name": body.get("name"),
        "prices": body.get("prices"),
        "product_id": body.get("productId"),
    }

    db.collection("coffees").add(coffee_data)
    return {"message": "Coffee added successfully"}


@web_app.put(ADMIN_COFFEE_UPDATE_URL)
async def update_coffee(request: Request):
    body = await request.json()
    coffee_id = body.get("id")
    updated_data = body.get("data")
    db.collection("coffees").document(coffee_id).update(updated_data)
    return {"message": "Coffee updated successfully"}


@web_app.delete(ADMIN_COFFE_DELETE_URL)
async def delete_coffee(request: Request):
    body = await request.json()
    coffee_id = body.get("id")
    db.collection("coffees").document(coffee_id).delete()
    return {"message": "Coffee deleted successfully"}


@web_app.get(LIST_AVAILABLE_COFFEES_URL)
async def list_coffees():
    coffees = db.collection("coffees").stream()
    return [coffee.to_dict() for coffee in coffees]


@web_app.post(ORDER_PLACE_URL)
async def place_order(request: Request):
    body = await request.json()

    order_data = {
        "customer_id": body.get("customer_id"),
        "items": body.get("items"),
        "delivery_time": body.get("delivery_time"),
        "coffee_quantity": body.get("coffee_quantity"),
        "created_at": firestore.SERVER_TIMESTAMP,
    }

    db.collection("orders").add(order_data)
    return {"message": "Order placed successfully"}


@web_app.get(ORDER_GET_RECENT_URL)
async def get_recent_orders():
    orders = (
        db.collection("orders")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(10)
        .stream()
    )
    return [order.to_dict() for order in orders]


@stub.function(
    mounts=[
        Mount.from_local_file(DB_CONFIG_FILE, remote_path=f"/root/{DB_CONFIG_FILE}")
    ]
)
@asgi_app()
def app():
    global db
    cred = credentials.Certificate(f"/root/{DB_CONFIG_FILE}")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    return web_app
