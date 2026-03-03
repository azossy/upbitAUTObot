"""
배짱이 v1.0 — FastAPI 백엔드
저작자: 차리 (challychoi@me.com)
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.routers import auth, bot, market, news


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.trading_tasks = {}  # user_id -> asyncio.Task (봇 시작 시 트레이딩 루프)
    await init_db()
    yield
    # 봇 정지: 모든 트레이딩 태스크 취소
    for user_id, task in list(getattr(app.state, "trading_tasks", {}).items()):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    app.state.trading_tasks.clear()


app = FastAPI(
    title="배짱이 v1.0 API",
    version="1.0.0",
    lifespan=lifespan,
)

# 4xx/5xx 시 일관된 JSON 형식 { "detail": "메시지" } 반환 (클라이언트 파싱·사용자 표시용)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail if isinstance(exc.detail, str) else str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_msg = errors[0].get("msg", "입력값을 확인해 주세요.") if errors else "입력값을 확인해 주세요."
    loc = errors[0].get("loc", []) if errors else []
    if len(loc) >= 2 and loc[0] == "body":
        field = str(loc[1]) if len(loc) > 1 else ""
        detail = f"{field}: {first_msg}" if field else first_msg
    else:
        detail = first_msg
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    if settings.DEBUG:
        detail = str(exc)
    else:
        detail = "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    return JSONResponse(status_code=500, content={"detail": detail})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(bot.router)
app.include_router(market.router)
app.include_router(news.router)

# 프로필 사진 정적 파일 (앱에서 업로드한 이미지)
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_STATIC_DIR.mkdir(exist_ok=True)
(_STATIC_DIR / "avatars").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


APP_VERSION = "1.0.0"


@app.get("/health")
async def health():
    return {"status": "ok", "version": APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
