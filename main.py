from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from schema import ClassificationRequest, ClassificationResponse
from classifier import classify

app = FastAPI(
    title="Mumzworld Return Reason Classifier",
    description="Classifies free-text return reasons into refund / exchange / store_credit / escalate",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("index.html")


@app.post("/classify", response_model=ClassificationResponse)
def classify_return(req: ClassificationRequest):
    """
    Accepts a free-text return reason (EN or AR, up to 2000 chars).
    Returns structured classification with confidence, reasoning, and a CS hint.

    On model or schema failure, validation_passed=False and error is populated.
    The endpoint never returns a 500 — failures are surfaced in the response body
    so the caller can decide how to handle them (e.g. route to human agent).
    """
    try:
        result = classify(req.text)
        return ClassificationResponse(
            input=req.text,
            result=result,
            validation_passed=True,
        )
    except Exception as e:
        # Explicit failure — never silently pass bad data downstream
        return ClassificationResponse(
            input=req.text,
            result=None,
            validation_passed=False,
            error=str(e),
        )
