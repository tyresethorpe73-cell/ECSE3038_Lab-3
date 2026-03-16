from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Literal, Optional
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["Engineering_2026"]
collection = db["work_orders_2026"]

app = FastAPI()

class WorkOrder(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    title: str
    description: str
    assigned_to: str
    priority: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "in_progress", "completed", "cancelled"]

class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    status: Optional[Literal["open", "in_progress", "completed", "cancelled"]] = None

# sample request
@app.get("/")
def root():
    return {"Note:": "API up and running !!"}


@app.post("/work-orders", status_code=status.HTTP_201_CREATED)
async def create_work_order(order: WorkOrder):

    doc = order.model_dump()

    doc["id"] = str(doc["id"])
    doc["created_at"] = doc["created_at"].isoformat()

    try:
        await collection.insert_one(doc)
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/work-orders")
async def get_work_orders():

    orders = []

    async for doc in collection.find({}, {"_id": 0}):
        doc["id"] = str(doc["id"])
        orders.append(doc)

    return orders

@app.get("/work-orders/filter")
async def filter_work_orders(priority: Literal["low","medium","high","critical"]):

    orders = []

    async for doc in collection.find({"priority": priority}, {"_id": 0}):
        doc["id"] = str(doc["id"])
        orders.append(doc)

    return orders


@app.get("/work-orders/{order_id}")
async def get_work_order(order_id: str):

    doc = await collection.find_one({"id": order_id}, {"_id": 0})

    if not doc:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, 
        detail="Work order not found"
        )
    return doc

@app.patch("/work-orders/{order_id}")
async def update_work_order(order_id: str, partial_update: WorkOrderUpdate):

    patch_data = partial_update.model_dump(exclude_unset=True)

    if not patch_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided in patch"
        )

    result = await collection.update_one(
        {"id": order_id},
        {"$set": patch_data}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    doc = await collection.find_one({"id": order_id}, {"_id": 0})
    return doc


@app.delete("/work-orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_order(order_id: str):

    result = await collection.delete_one({"id": order_id})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

@app.put("/work-orders/{order_id}")
async def replace_work_order(order_id: str, update: WorkOrder):

    existing = await collection.find_one({"id": order_id})

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    doc = update.model_dump()

    doc["id"] = order_id
    doc["created_at"] = existing["created_at"]

    await collection.update_one(
        {"id": order_id},
        {"$set": doc}
    )

    updated_doc = await collection.find_one({"id": order_id}, {"_id": 0})
    return updated_doc