from pydantic import BaseModel
from typing import Optional

class ScrapeRequest(BaseModel):
    rut: str
    password: str
    mes: str
    anio: str

class UserSii(BaseModel):
    rut: str
    dv: str
    password: str

class SessionRequest(BaseModel):
    """Modelo para operaciones de sesión que no requieren password"""
    rut: str
    dv: str

class UserSIIData(BaseModel):
    rut: str
    dv: str
    password: str
    mes: str
    anio: str
    json: bool = False

class SessionCache(BaseModel):
    token: str
    csessionid: str
    rut: str