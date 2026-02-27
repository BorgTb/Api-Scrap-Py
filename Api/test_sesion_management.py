"""
Script de prueba para el sistema de gestión de sesiones con cierre automático
Prueba tanto el cierre manual como el cierre por expiración (TTL)
"""
import time
from models.ScrapeRequest import UserSii
from utils.sesion_cache import (
    guardar_sesion_cacheada, 
    obtener_sesion_cacheada, 
    eliminar_sesion_cacheada,
    obtener_ttl_sesion,
    iniciar_listener_expiraciones
)

def prueba_cierre_manual():
    """
    Prueba el cierre manual de sesión
    """
    print("\n" + "="*60)
    print("PRUEBA 1: Cierre Manual de Sesión")
    print("="*60)
    
    # Crear usuario de prueba
    user_sii = UserSii(rut="11111111", dv="1", password="test123")
    
    # Guardar sesión
    print("\n1. Guardando sesión de prueba...")
    resultado = guardar_sesion_cacheada(
        user_sii=user_sii,
        token="TOKEN_TEST_123456",
        csessionid="CSESSIONID_TEST_789"
    )
    
    if resultado:
        print("✅ Sesión guardada")
    
    # Verificar sesión
    print("\n2. Verificando sesión guardada...")
    sesion = obtener_sesion_cacheada(user_sii)
    if sesion:
        print(f"✅ Sesión encontrada: token={sesion['token'][:20]}...")
    
    # Ver TTL
    ttl = obtener_ttl_sesion(user_sii)
    if ttl:
        print(f"⏰ TTL: {ttl} segundos ({ttl/60:.1f} minutos)")
    
    # Eliminar manualmente (esto debería cerrar en SII)
    print("\n3. Eliminando sesión manualmente (debería cerrar en SII)...")
    resultado = eliminar_sesion_cacheada(user_sii, cerrar_en_sii=True)
    
    if resultado:
        print("✅ Sesión eliminada y cerrada en SII")
    
    # Verificar que ya no existe
    print("\n4. Verificando que la sesión fue eliminada...")
    sesion = obtener_sesion_cacheada(user_sii)
    if not sesion:
        print("✅ Sesión ya no existe en Redis")
    else:
        print("❌ Error: La sesión todavía existe")

def prueba_cierre_por_expiracion():
    """
    Prueba el cierre automático cuando una sesión expira por TTL
    """
    print("\n" + "="*60)
    print("PRUEBA 2: Cierre Automático por Expiración (TTL)")
    print("="*60)
    
    # Iniciar listener
    print("\n1. Iniciando listener de expiraciones...")
    iniciar_listener_expiraciones()
    time.sleep(2)  # Dar tiempo a que el listener se inicie
    
    # Crear usuario de prueba
    user_sii = UserSii(rut="22222222", dv="2", password="test456")
    
    # Guardar sesión con TTL corto para prueba (10 segundos)
    print("\n2. Guardando sesión con TTL de 10 segundos...")
    from services.redis_session_service import get_redis_session_service
    
    redis_service = get_redis_session_service()
    resultado = redis_service.guardar_sesion(
        rut=user_sii.rut,
        dv=user_sii.dv,
        token="TOKEN_TEST_EXPIRACION_123",
        csessionid="CSESSIONID_TEST_EXPIRACION_456",
        ttl_seconds=10  # Solo 10 segundos para prueba rápida
    )
    
    if resultado:
        print("✅ Sesión guardada con TTL de 10 segundos")
    
    # Verificar sesión
    print("\n3. Verificando sesión guardada...")
    sesion = obtener_sesion_cacheada(user_sii)
    if sesion:
        print(f"✅ Sesión encontrada: token={sesion['token'][:25]}...")
    
    # Ver TTL
    ttl = obtener_ttl_sesion(user_sii)
    if ttl:
        print(f"⏰ TTL inicial: {ttl} segundos")
    
    # Esperar a que expire
    print("\n4. Esperando a que expire la sesión (10 segundos)...")
    print("   El listener debería detectar la expiración y cerrar en SII...")
    
    for i in range(10, 0, -1):
        print(f"   {i} segundos restantes...")
        time.sleep(1)
    
    # Esperar un poco más para que el listener procese
    time.sleep(3)
    
    print("\n5. Verificando que la sesión expiró...")
    sesion = obtener_sesion_cacheada(user_sii)
    if not sesion:
        print("✅ Sesión expiró correctamente")
        print("✅ El listener debería haber mostrado logs de cierre en SII")
    else:
        print("❌ Error: La sesión todavía existe")

def menu_pruebas():
    """
    Menú interactivo para elegir qué prueba ejecutar
    """
    print("\n" + "="*60)
    print("SISTEMA DE PRUEBAS - GESTIÓN DE SESIONES SII")
    print("="*60)
    print("\n1. Prueba cierre manual")
    print("2. Prueba cierre por expiración (TTL)")
    print("3. Ejecutar ambas pruebas")
    print("4. Salir")
    
    opcion = input("\nSelecciona una opción (1-4): ")
    
    if opcion == "1":
        prueba_cierre_manual()
    elif opcion == "2":
        prueba_cierre_por_expiracion()
    elif opcion == "3":
        prueba_cierre_manual()
        time.sleep(2)
        prueba_cierre_por_expiracion()
    elif opcion == "4":
        print("\n👋 Saliendo...")
        return
    else:
        print("\n❌ Opción inválida")
        menu_pruebas()

if __name__ == "__main__":
    try:
        # Verificar que Redis esté configurado
        print("\n🔧 Verificando configuración de Redis...")
        from database.db_redis import RedisConnection
        
        redis_client = RedisConnection.get_connection()
        config = redis_client.config_get('notify-keyspace-events')
        
        if 'Ex' not in str(config) and 'EA' not in str(config):
            print("\n⚠️ ADVERTENCIA: Redis no tiene habilitadas las notificaciones de expiración")
            print("   Si estás usando Docker, reinicia el contenedor: docker-compose restart redis")
            print("   Si usas Redis local, ejecuta: redis-cli CONFIG SET notify-keyspace-events Ex")
            respuesta = input("\n¿Deseas continuar de todos modos? (s/n): ")
            if respuesta.lower() != 's':
                exit()
        else:
            print("✅ Redis configurado correctamente")
        
        # Mostrar menú
        menu_pruebas()
        
    except KeyboardInterrupt:
        print("\n\n👋 Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
