import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import WaterSample, ScenarioSummary

app = FastAPI(title="Flames.Blue Water Quality API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Water Quality Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# ------------------------------
# Data ingestion endpoints
# ------------------------------

class IngestResponse(BaseModel):
    id: str
    status: str


@app.post("/samples", response_model=IngestResponse)
async def create_sample(sample: WaterSample):
    try:
        inserted_id = create_document("watersample", sample)
        return IngestResponse(id=inserted_id, status="created")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/samples")
async def list_samples(scenario: Optional[str] = None, limit: Optional[int] = 200):
    try:
        flt: Dict[str, Any] = {}
        if scenario:
            flt["scenario"] = scenario
        docs = get_documents("watersample", flt, limit)
        # Convert ObjectId and datetime for JSON safety
        def clean(doc):
            doc["id"] = str(doc.pop("_id")) if doc.get("_id") else None
            for k, v in list(doc.items()):
                if isinstance(v, datetime):
                    doc[k] = v.isoformat()
                if isinstance(v, dict):
                    for kk, vv in list(v.items()):
                        if isinstance(vv, datetime):
                            v[kk] = vv.isoformat()
            return doc
        cleaned = [clean(d) for d in docs]
        return {"items": cleaned, "count": len(cleaned)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Basic summaries by scenario
@app.get("/summaries", response_model=List[ScenarioSummary])
async def get_summaries():
    try:
        pipeline = [
            {"$group": {
                "_id": "$scenario",
                "count": {"$sum": 1},
                "avg_ph": {"$avg": "$ph"},
                "avg_do": {"$avg": "$dissolved_oxygen_mg_l"},
                "avg_turbidity": {"$avg": "$turbidity_ntu"}
            }},
            {"$project": {
                "_id": 0,
                "scenario": "$_id",
                "count": 1,
                "avg_ph": 1,
                "avg_do": 1,
                "avg_turbidity": 1
            }}
        ]
        cursor = db["watersample"].aggregate(pipeline)
        results = list(cursor)
        return [ScenarioSummary(**r) for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Placeholder for clustering trigger (webhook-style)
class ClusterRequest(BaseModel):
    scenario: Optional[str] = None
    k: int = 3

class ClusterResult(BaseModel):
    scenario: Optional[str] = None
    k: int
    labels: Dict[str, int]

@app.post("/cluster", response_model=ClusterResult)
async def cluster_trigger(req: ClusterRequest):
    """
    This endpoint prepares data to be sent to an external clustering engine.
    In this environment we return a stubbed structure showing how you'd send/receive.
    """
    try:
        flt: Dict[str, Any] = {}
        if req.scenario:
            flt["scenario"] = req.scenario
        docs = get_documents("watersample", flt, limit=None)
        # Build payload
        payload = []
        ids = []
        for d in docs:
            ids.append(str(d["_id"]))
            payload.append([
                d.get("ph"),
                d.get("dissolved_oxygen_mg_l"),
                d.get("turbidity_ntu")
            ])
        # Here you'd call external service with payload and req.k, then map labels back by ids
        # For demonstration, assign labels round-robin
        labels = {ids[i]: int(i % max(1, req.k)) for i in range(len(ids))}
        return ClusterResult(scenario=req.scenario, k=req.k, labels=labels)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
