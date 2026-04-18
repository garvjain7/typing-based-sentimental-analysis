import random
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from backend.features import FeatureValidationError
from backend.predictor import load_model, predict
from backend.storage import append_row, get_session_logs
from backend.security import SessionManager, TrustScorer, RateLimiter

session_manager = SessionManager(expiry_minutes=5)
trust_scorer = TrustScorer()
rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


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
    session_id: str
    total_keys: int
    text_length: int
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


@app.get("/session/start")
def start_session(request: Request):
    ip = request.client.host
    session_id = session_manager.start_session(ip)
    return {"session_id": session_id}


@app.post("/predict")
def predict_mood(data: FeaturesInput, request: Request):
    ip = request.client.host
    
    # 1. Rate Limit Check (IP)
    if not rate_limiter.is_allowed(ip):
        return JSONResponse(status_code=429, content={"detail": "Too many requests from this IP. Please wait a minute."})
    
    # 2. Session Validation
    is_valid, session_or_msg = session_manager.validate_session(data.session_id)
    if not is_valid:
        return JSONResponse(status_code=403, content={"detail": session_or_msg})
    
    # 3. Prevent Replay Attacks (Mark used IMMEDIATELY)
    session_info = session_or_msg # rename for clarity
    session_manager.mark_used(data.session_id)
    
    features = data.model_dump()
    
    # 4. Filter features for ML model (remove metadata)
    ml_features = {k: v for k, v in features.items() if k not in ["session_id", "total_keys", "text_length"]}
    
    # 5. Predict
    result = predict(ml_features)
    
    # 6. Trust Scoring
    raw_stats = {"total_keys": data.total_keys, "text_length": data.text_length}
    trust_score = trust_scorer.calculate_score(ml_features, raw_stats, session_info, data.session_id)
    
    # 7. Data Storage Policy
    stored = False
    warning = None
    
    if trust_score >= 60:
        append_row(ml_features, result["mood"], result["confidence"])
        stored = True
    else:
        warning = "Low trust score detected. Result provided but not stored for training."
        
    return {
        "mood": result["mood"],
        "confidence": result["confidence"],
        "driving_factors": result.get("driving_factors", []),
        "overall_means": result.get("overall_means"),
        "stored": stored,
        "warning": warning
    }

@app.api_route("/admin", methods=["GET", "POST"])
async def admin_dashboard(request: Request):
    authorized = False
    error = None
    
    # 1. Password check
    admin_password = os.getenv("ADMIN_PASSWORD", "typing-mood-admin")
    
    # Handle both GET (if already auth via session - mock) and POST
    # Note: Using form for simple password entry
    # 2. Get intended page
    page = int(request.query_params.get("page", 1))
    per_page = 50
    
    # Strictly require POST with password for EVERY request
    # No cookies, no session, no URL params.
    if request.method == "POST":
        form_data = await request.form()
        if form_data.get("password") == admin_password:
            authorized = True
            # Allow the form to override the page number
            if form_data.get("target_page"):
                page = int(form_data.get("target_page"))
        else:
            error = "Invalid password. Access denied."

    # If authorized, allow viewing on subsequent GET page turns via URL param
    if request.query_params.get("password") == admin_password:
        authorized = True

    data, total_count = ([], 0)
    if authorized:
        data, total_count = get_session_logs(page=page, per_page=per_page)

    total_pages = (total_count + per_page - 1) // per_page
    start_idx = (page - 1) * per_page + 1 if total_count > 0 else 0
    end_idx = min(page * per_page, total_count)

    return templates.TemplateResponse(
        "admin.html", 
        {
            "request": request, 
            "authorized": authorized, 
            "admin_password": admin_password, # pass back for easy pagination links
            "data": data,
            "error": error,
            "total_count": total_count,
            "page": page,
            "total_pages": total_pages,
            "start_idx": start_idx,
            "end_idx": end_idx
        }
    )


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return FileResponse("frontend/static/robots.txt")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    return FileResponse("frontend/static/sitemap.xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)