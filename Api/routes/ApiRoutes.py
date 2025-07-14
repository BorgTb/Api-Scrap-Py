from fastapi import APIRouter
from models.ScrapeRequest import ScrapeRequest
from services import ScrapSii


router = APIRouter()

@router.post("/scrap")
async def ejecutar_scraping(data: ScrapeRequest):
    result = await ScrapSii.scrap_sii(data.rut, data.password, data.mes, data.anio)
    return result

@router.get("/scrap")
async def obtener_resultado():
    return {"message": "Scraping is currently disabled for maintenance."}