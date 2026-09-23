from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, clients, projects, tasks, comments, time_entries, files, invites, dashboard

app = FastAPI(title="AgencyDesk API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(time_entries.router)
app.include_router(files.router)
app.include_router(invites.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
