from pydantic import BaseModel

class ScrapeRequest(BaseModel):
    rut: str
    password: str
    mes: str
    anio: str
