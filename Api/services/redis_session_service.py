"""
Servicio de Redis para gestión de sesiones SII
Maneja el almacenamiento y recuperación de tokens de sesión con TTL de 2 horas
"""
from datetime import timedelta
from typing import Optional, Dict
import json
import sys
from pathlib import Path

# Agregar el directorio Api al path
current_dir = Path(__file__).resolve().parent
api_dir = current_dir.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

# Importar usando el nombre correcto del módulo
import importlib
db_redis = importlib.import_module('database.db_redis')
RedisConnection = db_redis.RedisConnection


_SESSION_TTL_SECONDS = 7200  # 2 horas


class RedisSessionService:
    """Servicio para gestionar sesiones del SII en Redis"""
    
    def __init__(self):
        self.redis_client = RedisConnection.get_connection()
    
    def _build_session_key(self, rut: str, dv: str) -> str:
        """
        Construye la clave de Redis para una sesión
        
        Args:
            rut: RUT del usuario sin puntos ni guión
            dv: Dígito verificador
        
        Returns:
            Clave de Redis en formato 'session:sii:{rut}-{dv}'
        """
        return f"session:sii:{rut}-{dv}"
    
    def _build_close_data_key(self, rut: str, dv: str) -> str:
        """
        Construye la clave auxiliar para datos de cierre de sesión
        Esta clave tiene un TTL más largo para permitir cerrar en SII incluso después de expiración
        
        Args:
            rut: RUT del usuario sin puntos ni guión
            dv: Dígito verificador
        
        Returns:
            Clave de Redis en formato 'session:sii:close:{rut}-{dv}'
        """
        return f"session:sii:close:{rut}-{dv}"
    
    def guardar_sesion(
        self, 
        rut: str, 
        dv: str, 
        token: str, 
        csessionid: str,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Guarda una sesión en Redis con TTL y datos auxiliares para cierre
        
        Args:
            rut: RUT del usuario
            dv: Dígito verificador
            token: Token de sesión del SII
            csessionid: Cookie CSESSIONID del SII
            ttl_seconds: Tiempo de vida en segundos (default: 7200 = 2 horas)
        
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            # Construir claves
            session_key = self._build_session_key(rut, dv)
            close_data_key = self._build_close_data_key(rut, dv)
            
            # Preparar datos de sesión
            session_data = {
                'token': token,
                'csessionid': csessionid,
                'rut': rut,
                'dv': dv
            }
            
            # Datos mínimos para cierre (se guardan con TTL más largo)
            close_data = {
                'token': token,
                'csessionid': csessionid,
                'rut': rut,
                'dv': dv
            }
            
            # Guardar en Redis con TTL
            ttl = ttl_seconds or _SESSION_TTL_SECONDS
            self.redis_client.setex(
                session_key,
                ttl,
                json.dumps(session_data)
            )
            
            # Guardar datos de cierre con TTL + 60 segundos adicionales
            # Esto permite cerrar en SII incluso después de la expiración
            self.redis_client.setex(
                close_data_key,
                ttl + 60,
                json.dumps(close_data)
            )
            
            print(f"✅ Sesión guardada en Redis para {rut}-{dv} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            print(f"❌ Error al guardar sesión en Redis: {e}")
            return False
    
    def obtener_sesion(self, rut: str, dv: str) -> Optional[Dict[str, str]]:
        """
        Obtiene una sesión de Redis si existe y no ha expirado
        
        Args:
            rut: RUT del usuario
            dv: Dígito verificador
        
        Returns:
            Diccionario con token y csessionid o None si no existe/expiró
        """
        try:
            key = self._build_session_key(rut, dv)
            session_json = self.redis_client.get(key)
            
            if not session_json:
                return None
            
            session_data = json.loads(session_json)
            
            # Retornar solo los datos de sesión
            return {
                "token": session_data.get("token"),
                "csessionid": session_data.get("csessionid")
            }
            
        except Exception as e:
            print(f"❌ Error al obtener sesión de Redis: {e}")
            return None
    
    def obtener_datos_cierre(self, rut: str, dv: str) -> Optional[Dict[str, str]]:
        """
        Obtiene los datos necesarios para cerrar sesión en SII (token y csessionid)
        Primero intenta obtener de la sesión activa, si no existe, de la clave auxiliar
        
        Args:
            rut: RUT del usuario
            dv: Dígito verificador
        
        Returns:
            Diccionario con token, csessionid, rut y dv o None si no existe
        """
        try:
            # Intentar primero desde la sesión activa
            session_data = self.obtener_sesion(rut, dv)
            if session_data:
                session_data['rut'] = rut
                session_data['dv'] = dv
                return session_data
            
            # Si no hay sesión activa, intentar desde datos de cierre
            close_data_key = self._build_close_data_key(rut, dv)
            close_data_str = self.redis_client.get(close_data_key)
            
            if close_data_str:
                return json.loads(close_data_str)
            
            return None
            
        except Exception as e:
            print(f"❌ Error al obtener datos de cierre: {e}")
            return None
    
    def eliminar_sesion(self, rut: str, dv: str) -> bool:
        """
        Elimina una sesión de Redis y su clave auxiliar de cierre
        
        Args:
            rut: RUT del usuario
            dv: Dígito verificador
        
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            session_key = self._build_session_key(rut, dv)
            close_data_key = self._build_close_data_key(rut, dv)
            
            # Verificar si existe antes de eliminar
            exists_session = self.redis_client.exists(session_key)
            exists_close = self.redis_client.exists(close_data_key)
            
            if not exists_session and not exists_close:
                print(f"⚠️ No existe sesión para {rut}-{dv}")
                return False
            
            # Eliminar ambas claves
            deleted = 0
            if exists_session:
                deleted += self.redis_client.delete(session_key)
            if exists_close:
                deleted += self.redis_client.delete(close_data_key)
            
            print(f"✅ Sesión eliminada de Redis para {rut}-{dv} ({deleted} claves)")
            return True
            
        except Exception as e:
            print(f"❌ Error al eliminar sesión: {e}")
            return False
    
    def verificar_conexion(self) -> bool:
        """
        Verifica si la conexión con Redis está activa
        
        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            return self.redis_client.ping()
        except Exception as e:
            print(f"❌ Error de conexión con Redis: {e}")
            return False
    
    def obtener_ttl(self, rut: str, dv: str) -> Optional[int]:
        """
        Obtiene el tiempo de vida restante de una sesión en segundos
        
        Args:
            rut: RUT del usuario
            dv: Dígito verificador
        
        Returns:
            Segundos restantes o None si la sesión no existe
        """
        try:
            key = self._build_session_key(rut, dv)
            ttl = self.redis_client.ttl(key)
            
            # -2 significa que la clave no existe
            # -1 significa que la clave existe pero no tiene expiración
            if ttl == -2:
                return None
            
            return ttl if ttl > 0 else 0
            
        except Exception as e:
            print(f"❌ Error al obtener TTL: {e}")
            return None
    
    def renovar_sesion(self, rut: str, dv: str, ttl_seconds: Optional[int] = None) -> bool:
        """
        Renueva el TTL de una sesión existente
        
        Args:
            rut: RUT del usuario
            dv: Dígito verificador
            ttl_seconds: Nuevo tiempo de vida en segundos (default: 7200)
        
        Returns:
            True si se renovó correctamente, False si no existe o hubo error
        """
        try:
            key = self._build_session_key(rut, dv)
            ttl = ttl_seconds if ttl_seconds is not None else _SESSION_TTL_SECONDS
            
            result = self.redis_client.expire(key, ttl)
            
            if result:
                print(f"✅ Sesión renovada: {rut}-{dv} (nuevo TTL: {ttl}s)")
                return True
            else:
                print(f"⚠️ No se pudo renovar la sesión: {rut}-{dv}")
                return False
                
        except Exception as e:
            print(f"❌ Error al renovar sesión: {e}")
            return False


# Instancia global del servicio
_redis_session_service: Optional[RedisSessionService] = None


def get_redis_session_service() -> RedisSessionService:
    """
    Obtiene la instancia global del servicio de sesiones Redis (Singleton)
    
    Returns:
        Instancia de RedisSessionService
    """
    global _redis_session_service
    
    if _redis_session_service is None:
        _redis_session_service = RedisSessionService()
    
    return _redis_session_service


# Ejemplo de uso
if __name__ == "__main__":
    service = get_redis_session_service()
    
    # Verificar conexión
    if service.verificar_conexion():
        print("✓ Conexión con Redis exitosa")
        
        # Guardar sesión de prueba
        service.guardar_sesion(
            rut="12345678",
            dv="9",
            token="test_token_123456",
            csessionid="test_csession_123456"
        )
        
        # Obtener sesión
        sesion = service.obtener_sesion("12345678", "9")
        print(f"Sesión recuperada: {sesion}")
        
        # Obtener TTL
        ttl = service.obtener_ttl("12345678", "9")
        print(f"TTL restante: {ttl} segundos")
        
        # Eliminar sesión
        service.eliminar_sesion("12345678", "9")
        
    else:
        print("✗ No se pudo conectar con Redis")
