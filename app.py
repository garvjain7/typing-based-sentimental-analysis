import random
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from backend.features import FeatureValidationError
from backend.predictor import load_model, predict
from backend.storage import append_row


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory="frontend/static"),
    name="static",
)

templates = Jinja2Templates(directory="frontend/templates")

PARAGRAPHS = [
    p.strip()
    for p in Path("paragraphs.txt").read_text().split("\n\n")
    if p.strip()
]


class FeaturesInput(BaseModel):
    wpm: float
    wpm_variance: float
    avg_key_hold_time: float
    avg_inter_key_delay: float
    backspace_rate: float
    error_rate: float
    avg_pause_time: float
    pause_variability: float
    typing_consistency_score: float
    burstiness_score: float


@app.exception_handler(FeatureValidationError)
async def validation_error_handler(request: Request, exc: FeatureValidationError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/")
def index(request: Request):
    paragraph = random.choice(PARAGRAPHS)
    return templates.TemplateResponse(
        "index.html", {"request": request, "paragraph": paragraph}
    )


@app.get("/paragraph")
def get_paragraph():
    return {"paragraph": random.choice(PARAGRAPHS)}


@app.post("/predict")
def predict_mood(data: FeaturesInput):
    features = data.model_dump()
    result = predict(features)
    append_row(features, result["mood"], result["confidence"])
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)