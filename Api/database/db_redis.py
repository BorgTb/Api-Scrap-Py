import redis
from redis import Redis
from typing import Optional
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class RedisConnection:
    """Clase para manejar la conexión con Redis"""
    
    _instance: Optional[Redis] = None
    
    @classmethod
    def get_connection(cls, host: str = None, port: int = None, db: int = 0, decode_responses: bool = True) -> Redis:
        """
        Obtiene o crea una conexión con Redis (patrón Singleton)
        
        Args:
            host: Host de Redis (default: desde REDIS_HOST env o 'localhost')
            port: Puerto de Redis (default: desde REDIS_PORT env o 6379)
            db: Número de base de datos (default: 0)
            decode_responses: Si decodificar las respuestas como strings (default: True)
        
        Returns:
            Instancia de conexión Redis
        """
        if cls._instance is None:
            # Usar variables de entorno o valores por defecto
            redis_host = host or os.getenv('REDIS_HOST', 'redis')
            redis_port = port or int(os.getenv('REDIS_PORT', '6379'))
            redis_password = os.getenv('REDIS_PASSWORD', 'test')
            
            cls._instance = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=db,
                password=redis_password,
                decode_responses=decode_responses,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
                
            )
            print(f"🔗 Conectando a Redis en {redis_host}:{redis_port}")
        return cls._instance
    
    @classmethod
    def close_connection(cls):
        """Cierra la conexión con Redis"""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
    
    @classmethod
    def ping(cls) -> bool:
        """Verifica si la conexión con Redis está activa"""
        try:
            connection = cls.get_connection()
            return connection.ping()
        except redis.ConnectionError:
            return False


# Funciones auxiliares para operaciones comunes
def set_value(key: str, value: str, ex: Optional[int] = None) -> bool:
    """
    Guarda un valor en Redis
    
    Args:
        key: Clave
        value: Valor a guardar
        ex: Tiempo de expiración en segundos (opcional)
    
    Returns:
        True si se guardó correctamente
    """
    try:
        conn = RedisConnection.get_connection()
        return conn.set(key, value, ex=ex)
    except Exception as e:
        print(f"Error al guardar valor: {e}")
        return False


def get_value(key: str) -> Optional[str]:
    """
    Obtiene un valor de Redis
    
    Args:
        key: Clave a buscar
    
    Returns:
        Valor almacenado o None si no existe
    """
    try:
        conn = RedisConnection.get_connection()
        return conn.get(key)
    except Exception as e:
        print(f"Error al obtener valor: {e}")
        return None


def set_json(key: str, data: dict, ex: Optional[int] = None) -> bool:
    """
    Guarda un objeto JSON en Redis
    
    Args:
        key: Clave
        data: Diccionario a guardar
        ex: Tiempo de expiración en segundos (opcional)
    
    Returns:
        True si se guardó correctamente
    """
    try:
        json_data = json.dumps(data)
        return set_value(key, json_data, ex)
    except Exception as e:
        print(f"Error al guardar JSON: {e}")
        return False


def get_json(key: str) -> Optional[dict]:
    """
    Obtiene un objeto JSON de Redis
    
    Args:
        key: Clave a buscar
    
    Returns:
        Diccionario o None si no existe
    """
    try:
        value = get_value(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        print(f"Error al obtener JSON: {e}")
        return None


def delete_key(key: str) -> bool:
    """
    Elimina una clave de Redis
    
    Args:
        key: Clave a eliminar
    
    Returns:
        True si se eliminó correctamente
    """
    try:
        conn = RedisConnection.get_connection()
        return conn.delete(key) > 0
    except Exception as e:
        print(f"Error al eliminar clave: {e}")
        return False


# Ejemplo de uso
if __name__ == "__main__":
    # Verificar conexión
    if RedisConnection.ping():
        print("✓ Conexión con Redis exitosa")
        
        # Guardar y obtener valor
        set_value("test_key", "test_value", ex=60)
        print(f"Valor: {get_value('test_key')}")
        
        # Guardar y obtener JSON
        set_json("user:1", {"name": "John", "age": 30})
        print(f"JSON: {get_json('user:1')}")
        
        # Eliminar clave
        delete_key("test_key")
    else:
        print("✗ No se pudo conectar con Redis")