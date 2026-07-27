from fastapi import FastAPI
from app.routes.user_routes import auth_router
from app.routes.portfolio_routes import portfolio_router
from app.routes.wallet_routes import wallet_router

app = FastAPI()
app.include_router(auth_router)
app.include_router(portfolio_router)
app.include_router(wallet_router)


@app.get("/")
def read_root():
    """
    check health of server
    """
    return {"Hello": "World"}
