import os
import time
import logging  
import httpx
import pandas as pd
from enum import Enum
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 1. Load environment variables
load_dotenv()

# 2. Setup Logging
# This configuration tells Python HOW to log (to the console)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ChurnGateway")

# --- Configuration ---
AZURE_ENDPOINT_URL = os.getenv("AZURE_ENDPOINT_URL")
AZURE_ENDPOINT_KEY = os.getenv("AZURE_ENDPOINT_KEY")
DEPLOYMENT_CUSTOM = os.getenv("DEPLOYMENT_NAME_CUSTOM", "custom-model")
DEPLOYMENT_AUTOML = os.getenv("DEPLOYMENT_NAME_AUTOML", "automl-model")

class ModelType(str, Enum):
    custom = "custom"
    automl = "automl"

class InferencePayload(BaseModel):
    data: List[Dict[str, Any]]

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {AZURE_ENDPOINT_KEY}"},
        timeout=30.0
    )
    yield
    await app.state.http_client.aclose()

app = FastAPI(title="Smart Churn Router", lifespan=lifespan)

# --- 3. Monitoring Middleware (Logging & Timing) ---
# Once this block is added, your 'logging' and 'time' imports will light up
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # This fulfills the monitoring requirement
    logger.info(
        f"Path: {request.url.path} | Method: {request.method} | "
        f"Status: {response.status_code} | Latency: {process_time:.4f}s"
    )
    
    return response

# --- 4. The Router Endpoint ---
@app.post("/predict/{model_type}")
async def predict(model_type: ModelType, payload: InferencePayload, request: Request):
    client: httpx.AsyncClient = request.app.state.http_client
    df = pd.DataFrame(payload.data)

    # Universal Type Enforcement
    float_cols = ['Age', 'Balance', 'EstimatedSalary', 'HasCrCard', 'IsActiveMember']
    float_cols += [col for col in df.columns if col.startswith('var_')]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)

    int_cols = ['CreditScore', 'Tenure', 'NumOfProducts']
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(int)

    bool_cols = ['Geography_Germany', 'Geography_Spain', 'Gender_Male']
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({1: True, 0: False, "1": True, "0": False, True: True, False: False}).astype(bool)

    # Routing Logic
    if model_type == ModelType.custom:
        deployment_header = DEPLOYMENT_CUSTOM
        azure_payload = {"data": df.to_dict(orient='records')}
    else:
        deployment_header = DEPLOYMENT_AUTOML
        split_data = df.to_dict(orient="split")
        split_data.pop("index", None)
        azure_payload = {"input_data": split_data, "params": {}}

    headers = {
        "azureml-model-deployment": deployment_header,
        "Content-Type": "application/json"
    }

    try:
        response = await client.post(AZURE_ENDPOINT_URL, json=azure_payload, headers=headers)
        return response.json()
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))