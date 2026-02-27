from fastapi import APIRouter, Response
from models.ScrapeRequest import ScrapeRequest, UserSIIData, UserSii, SessionRequest, UserSIIDataAnual
from services import ScrapSii, f29_service, RCV_service
from utils.sesion_cache import obtener_ttl_sesion
from utils.login_sii import cerrar_sesion


router = APIRouter()

@router.post("/scrap")
async def ejecutar_scraping(data: ScrapeRequest):
    result = await ScrapSii.scrap_sii(data.rut, data.password, data.mes, data.anio)
    return result

@router.get("/scrap")
async def obtener_resultado():
    return {"message": "Scraping is currently disabled for maintenance."}

@router.post("/v2/sii/data/f29")
async def obtener_datos_f29(data: UserSIIData):
    result = await f29_service.obtener_datos_f29(data)
    if isinstance(result, dict) and "error" in result:
        return result
    if not data.json_output and isinstance(result, str):
        return Response(content=result, media_type="application/xml; charset=utf-8")
    return {"f29_data": result}


@router.post("/v2/sii/data/rcv")
async def obtener_datos_rcv(data: UserSIIData):
    result = await RCV_service.obtener_datos_rcv(data)
    if isinstance(result, dict) and "error" in result:
        return result
    return {"rcv_data": result}

@router.post("/v2/sii/data/rcv/anual")
async def obtener_datos_rcv_anual(data: UserSIIDataAnual):
    """
    Obtiene el resumen de todos los periodos de un año.
    
    Args:
        data: UserSIIDataAnual con rut, dv, password, anio
    
    Returns:
        Diccionario con todos los periodos del año y sus datos
    """
    result = await RCV_service.obtener_datos_rcv_anual(data)
    return result

@router.post("/v2/sii/session/close")
async def cerrar_sesion_endpoint(session_req: SessionRequest):
    """
    Cierra manualmente una sesión del SII:
    1. Llama al endpoint de terminación del SII (autTermino.cgi)
    2. Elimina la sesión de Redis
    
    Args:
        session_req: Objeto con rut y dv
    
    Returns:
        Mensaje de confirmación o error
    """
    # Crear UserSii temporal solo con datos necesarios
    user_sii = UserSii(rut=session_req.rut, dv=session_req.dv, password="")
    resultado = cerrar_sesion(user_sii)
    
    if resultado:
        return {
            "success": True,
            "message": f"Sesión cerrada exitosamente para RUT {session_req.rut}-{session_req.dv}"
        }
    else:
        return {
            "success": False,
            "message": f"No se encontró sesión activa para RUT {session_req.rut}-{session_req.dv}"
        }

@router.post("/v2/sii/session/status")
async def obtener_estado_sesion(session_req: SessionRequest):
    """
    Obtiene el estado y TTL de una sesión del SII
    
    Args:
        session_req: Objeto con rut y dv
    
    Returns:
        Estado de la sesión y tiempo restante
    """
    # Crear UserSii temporal solo con datos necesarios
    user_sii = UserSii(rut=session_req.rut, dv=session_req.dv, password="")
    ttl = obtener_ttl_sesion(user_sii)
    
    if ttl is None:
        return {
            "active": False,
            "message": f"No existe sesión activa para RUT {session_req.rut}-{session_req.dv}"
        }
    else:
        minutos_restantes = ttl // 60
        segundos_restantes = ttl % 60
        return {
            "active": True,
            "rut": f"{session_req.rut}-{session_req.dv}",
            "ttl_seconds": ttl,
            "ttl_formatted": f"{minutos_restantes} minutos, {segundos_restantes} segundos",
            "message": "Sesión activa"
        }