from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.rotas import router
from app.config import config
from app.database import Base, SessionLocal, engine
from app.ia.motor import motor
from app.models import Usuario


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        banco_vazio = db.scalar(select(Usuario).limit(1)) is None
    # A sessão acima precisa estar fechada antes do seed: no PostgreSQL, o DROP TABLE
    # do seed esperaria para sempre pela transação aberta pelo SELECT.
    if banco_vazio and config.popular_banco_se_vazio:
        from app.seed import popular
        popular()  # já termina com os modelos treinados
    else:
        with SessionLocal() as db:
            motor.treinar(db)
    yield


app = FastAPI(
    title="EV ChargeOps API",
    description="Gestão de recarga compartilhada de veículos elétricos com rateio e IA",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origens.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/saude", tags=["infra"])
def saude():
    return {"status": "ok"}
