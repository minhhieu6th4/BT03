import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config.settings import settings
from backend.routers import (
    auth, users, teams, submissions,
    matches, games, ranking, rooms, tournaments, bots
)

app = FastAPI(title=settings.PROJECT_NAME)

# Cấu hình Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký tập trung tất cả các Routers API
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(teams.router, prefix="/api/teams", tags=["Teams"])
app.include_router(submissions.router, prefix="/api/submissions", tags=["Submissions"])
app.include_router(matches.router, prefix="/api/matches", tags=["Matches"])
app.include_router(games.router, prefix="/api/games", tags=["Games"])
app.include_router(ranking.router, prefix="/api/ranking", tags=["Ranking"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["Rooms"])
app.include_router(tournaments.router, prefix="/api/tournaments", tags=["Tournaments"])
app.include_router(bots.router, prefix="/api/bots", tags=["Bots"])

# Mount thư mục Frontend để phục vụ giao diện trực tiếp trên cổng 5500
frontend_dir = os.path.join(settings.PROJECT_ROOT, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=5000, reload=True)

