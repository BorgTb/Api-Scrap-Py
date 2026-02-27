from fastapi import FastAPI
from contextlib import asynccontextmanager
from routes.ApiRoutes import router
from utils.sesion_cache import iniciar_listener_expiraciones

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    iniciar_listener_expiraciones()
    print("✅ Sistema de gestión de sesiones iniciado")
    yield
    # Shutdown
    print("👋 Cerrando sistema de gestión de sesiones")

app = FastAPI(title="Scrapper", version="1.0", lifespan=lifespan)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "API funcionando correctamente"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




