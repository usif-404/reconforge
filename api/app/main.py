from fastapi import FastAPI

from app.api_routes import assets, feedback, programs, queue

app = FastAPI(
    title="ReconForge",
    description="Personal bug bounty automation platform — scope-gated recon, change detection, AI triage.",
    version="0.1.0",
)

app.include_router(programs.router, prefix="/programs", tags=["programs"])
app.include_router(assets.router, prefix="/assets", tags=["assets"])
app.include_router(queue.router, prefix="/queue", tags=["manual hunt queue"])
app.include_router(feedback.router, prefix="/feedback", tags=["hunter feedback"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
