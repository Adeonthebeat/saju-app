from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import saju

app = FastAPI(title="나 뭐하고 먹고 살지? API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 배포 시 미니앱 WebView origin으로 좁힌다
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(saju.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
