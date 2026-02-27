from pydantic import BaseModel, Field, ConfigDict
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
    model_config = ConfigDict(populate_by_name=True)

    rut: str
    dv: str
    password: str
    mes: str
    anio: str
    json_output: bool = Field(default=False, alias="json")

class UserSIIDataAnual(BaseModel):
    """Modelo para consultar datos de todo un año"""
    model_config = ConfigDict(populate_by_name=True)
    rut: str
    dv: str
    password: str
    anio: str
    token_recaptcha: Optional[str] = "1111111ww"

class SessionCache(BaseModel):
    token: str
    csessionid: str
    rut: str