from fastapi import FastAPI
from app.api.routes import router
from app.core.config import settings
from app.db.database import Base, engine

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    

app.include_router(router, prefix="/api")
