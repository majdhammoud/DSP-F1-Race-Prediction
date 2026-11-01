import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import Base, get_engine, get_session_local
from database.models import PredictionLog

engine = get_engine()


def get_db():
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


MODEL_PATH = os.getenv("MODEL_PATH", "artifacts/model.pkl")
ml = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # create the predictions table if missing
    ml["model"] = joblib.load(MODEL_PATH)  # load the model once at startup
    yield
    ml.clear()


app = FastAPI(title="F1 Prediction API", lifespan=lifespan)


class PredictRequest(BaseModel):
    features: list[dict]
    source: str = "webapp"


class PredictionOut(BaseModel):
    id: int
    season: int
    round: int
    circuit_id: str
    driver_id: str
    constructor_name: str
    grid: int
    prediction: bool
    probability: float | None
    source: str
    created_at: datetime


def to_dict(r):
    return {
        "id": r.id,
        "season": r.season,
        "round": r.round,
        "circuit_id": r.circuit_id,
        "driver_id": r.driver_id,
        "constructor_name": r.constructor_name,
        "grid": r.grid,
        "prediction": r.prediction,
        "probability": r.probability,
        "source": r.source,
        "created_at": r.created_at,
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/predict", response_model=list[PredictionOut])
def predict(req: PredictRequest, db: Session = Depends(get_db)):
    if not req.features:
        raise HTTPException(status_code=400, detail="features cannot be empty")
    df = pd.DataFrame(req.features)
    try:
        preds = ml["model"].predict(df)
        probas = ml["model"].predict_proba(df)[:, 1]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"prediction failed: {e}")

    rows = []
    for feat, p, prob in zip(req.features, preds, probas):
        row = PredictionLog(
            season=feat["Season"],
            round=feat["Round"],
            circuit_id=feat["CircuitID"],
            driver_id=feat["DriverID"],
            constructor_name=feat["ConstructorName"],
            grid=feat["Grid"],
            prediction=bool(p),
            probability=float(prob),
            source=req.source,
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return [to_dict(r) for r in rows]


@app.get("/past-predictions", response_model=list[PredictionOut])
def past_predictions(
    start: date | None = None,
    end: date | None = None,
    source: str = Query("all", pattern="^(webapp|scheduled|all)$"),
    db: Session = Depends(get_db),
):

    q = db.query(PredictionLog)
    if source != "all":
        q = q.filter(PredictionLog.source == source)
    if start:
        q = q.filter(PredictionLog.created_at >= start)
    if end:
        q = q.filter(PredictionLog.created_at < end + timedelta(days=1))
    return [to_dict(r) for r in q.order_by(PredictionLog.created_at.desc()).all()]


@app.get("/options")
def options():
    prep = ml["model"].named_steps["preprocessor"]
    encoder = prep.named_transformers_["cat"]
    cats = dict(zip(encoder.feature_names_in_, encoder.categories_))
    return {col: sorted(v.tolist()) for col, v in cats.items()}
