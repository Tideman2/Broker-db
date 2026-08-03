from fastapi import FastAPI
from app.routes.auth_routes import auth_router
from app.routes.admin_routes import admin_router
from app.routes.portfolio_routes import portfolio_router
from app.routes.wallet_routes import wallet_router
from app.routes.user_routes import user_router
from app.routes.subscription_routes import subscription_router
from app.routes.plan_routes import plan_router


app = FastAPI()
app.include_router(auth_router)
app.include_router(portfolio_router)
app.include_router(wallet_router)
app.include_router(user_router)
app.include_router(subscription_router)
app.include_router(admin_router)
app.include_router(plan_router)


@app.get("/")
def read_root():
    """
    check health of server
    """
    return {"Hello": "World"}
