from fastapi import FastAPI

from App.api.routes import router

app = FastAPI(title="Pokemon Weakness and Counter API", version="0.1.0")
app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["Operations"])
def health() -> dict[str, str]:
    return {"status": "ok"}
