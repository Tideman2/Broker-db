import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.email import email_service
from app.services.redis_service import redis_client, close_redis

from app.routes.auth_routes import auth_router
from app.routes.admin_routes import admin_router
from app.routes.portfolio_routes import portfolio_router
from app.routes.wallet_routes import wallet_router
from app.routes.user_routes import user_router
from app.routes.subscription_routes import subscription_router
from app.routes.plan_routes import plan_router
from app.routes.asset_routes import asset_router


origins = os.getenv(
    "ALLOWED_ORIGINS",
    "*"
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to Redis and verify the connection
    await redis_client.ping()
    # Start email workers
    email_service.start()

    yield

    # Stop email workers
    email_service.stop()
    # Close Redis connection
    await close_redis()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(portfolio_router)
app.include_router(wallet_router)
app.include_router(user_router)
app.include_router(subscription_router)
app.include_router(admin_router)
app.include_router(plan_router)
app.include_router(asset_router)


@app.get("/")
def read_root():
    """
    check health of server
    """
    return {"Hello": "World"}
