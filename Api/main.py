from fastapi import FastAPI
from routes.ApiRoutes import router

app = FastAPI(title="Scrapper", version="1.0")

app.include_router(router)

@app.get("/")
def root():
    return {"message": "API funcionando correctamente"}
