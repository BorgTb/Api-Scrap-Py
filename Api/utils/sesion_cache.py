"""
Módulo de caché de sesiones SII usando Redis
Proporciona funciones simplificadas para guardar y obtener sesiones
que internamente utilizan el servicio de Redis
"""
from typing import Optional, Dict
from models.ScrapeRequest import UserSii
from services.redis_session_service import get_redis_session_service


def obtener_sesion_cacheada(user_sii: UserSii) -> Optional[Dict[str, str]]:
	"""
	Obtiene una sesión almacenada en Redis
	
	Args:
		user_sii: Objeto UserSii con rut y dv
	
	Returns:
		Diccionario con token y csessionid o None si no existe/expiró
	"""
	try:
		redis_service = get_redis_session_service()
		return redis_service.obtener_sesion(user_sii.rut, user_sii.dv)
	except Exception as e:
		print(f"❌ Error al obtener sesión cacheada: {e}")
		return None


def guardar_sesion_cacheada(user_sii: UserSii, token: str, csessionid: str) -> bool:
	"""
	Guarda una sesión en Redis con TTL de 2 horas
	
	Args:
		user_sii: Objeto UserSii con rut y dv
		token: Token de sesión del SII
		csessionid: Cookie CSESSIONID del SII
	
	Returns:
		True si se guardó correctamente, False en caso contrario
	"""
	try:
		redis_service = get_redis_session_service()
		return redis_service.guardar_sesion(
			rut=user_sii.rut,
			dv=user_sii.dv,
			token=token,
			csessionid=csessionid
		)
	except Exception as e:
		print(f"❌ Error al guardar sesión cacheada: {e}")
		return False


def eliminar_sesion_cacheada(user_sii: UserSii, cerrar_en_sii: bool = True) -> bool:
	"""
	Elimina manualmente una sesión de Redis y opcionalmente cierra en el SII
	
	Args:
		user_sii: Objeto UserSii con rut y dv
		cerrar_en_sii: Si es True, cierra la sesión en el SII antes de eliminar de Redis
	
	Returns:
		True si se eliminó correctamente, False en caso contrario
	"""
	try:
		redis_service = get_redis_session_service()
		
		# Si se debe cerrar en el SII, obtener primero los datos de la sesión
		if cerrar_en_sii:
			sesion_data = redis_service.obtener_datos_cierre(user_sii.rut, user_sii.dv)
			
			if sesion_data:
				# Importar la función de cierre aquí para evitar importación circular
				from utils.login_sii import _cerrar_sesion_sii
				
				_cerrar_sesion_sii(
					token=sesion_data.get('token'),
					csessionid=sesion_data.get('csessionid'),
					rut=user_sii.rut,
					dv=user_sii.dv
				)
		
		# Eliminar de Redis
		return redis_service.eliminar_sesion(user_sii.rut, user_sii.dv)
		
	except Exception as e:
		print(f"❌ Error al eliminar sesión cacheada: {e}")
		return False


def obtener_ttl_sesion(user_sii: UserSii) -> Optional[int]:
	"""
	Obtiene el tiempo de vida restante de una sesión en segundos
	
	Args:
		user_sii: Objeto UserSii con rut y dv
	
	Returns:
		Segundos restantes o None si la sesión no existe
	"""
	try:
		redis_service = get_redis_session_service()
		return redis_service.obtener_ttl(user_sii.rut, user_sii.dv)
	except Exception as e:
		print(f"❌ Error al obtener TTL de sesión: {e}")
		return None


def iniciar_listener_expiraciones():
	"""
	Inicia un listener en segundo plano que escucha eventos de expiración de Redis
	y cierra las sesiones en el SII cuando expiran automáticamente.
	
	Este listener debe ejecutarse en un thread/proceso separado.
	"""
	import threading
	from services.redis_session_service import get_redis_session_service
	
	def listener_worker():
		"""
		Worker que escucha eventos de expiración de Redis
		"""
		try:
			redis_service = get_redis_session_service()
			redis_client = redis_service.redis_client
			
			# Configurar Redis para enviar eventos de expiración
			# Esto requiere: CONFIG SET notify-keyspace-events Ex
			try:
				redis_client.config_set('notify-keyspace-events', 'Ex')
			except:
				print("⚠️ No se pudo configurar notify-keyspace-events. Ejecutar manualmente: redis-cli CONFIG SET notify-keyspace-events Ex")
			
			# Crear pubsub para escuchar expiraciones
			pubsub = redis_client.pubsub()
			pubsub.psubscribe('__keyevent@0__:expired')
			
			print("🔊 Listener de expiraciones de Redis iniciado")
			
			for message in pubsub.listen():
				if message['type'] == 'pmessage':
					expired_key = message['data'].decode('utf-8') if isinstance(message['data'], bytes) else message['data']
					
					# Verificar si es una clave de sesión SII
					if expired_key.startswith('session:sii:') and ':close:' not in expired_key:
						# Extraer rut-dv de la clave: session:sii:12345678-9
						try:
							rut_dv = expired_key.replace('session:sii:', '')
							parts = rut_dv.split('-')
							if len(parts) == 2:
								rut, dv = parts
								
								print(f"\n⏰ Sesión expirada detectada: {rut}-{dv}")
								
								# Obtener datos de cierre (de la clave auxiliar)
								sesion_data = redis_service.obtener_datos_cierre(rut, dv)
								
								if sesion_data:
									from utils.login_sii import _cerrar_sesion_sii
									
									# Cerrar sesión en el SII
									_cerrar_sesion_sii(
										token=sesion_data.get('token'),
										csessionid=sesion_data.get('csessionid'),
										rut=rut,
										dv=dv
									)
									
									# Limpiar clave auxiliar de cierre
									redis_service.eliminar_sesion(rut, dv)
									print(f"✅ Sesión expirada cerrada en SII: {rut}-{dv}")
								else:
									print(f"⚠️ No se encontraron datos para cerrar sesión expirada: {rut}-{dv}")
									
						except Exception as e:
							print(f"❌ Error procesando expiración de {expired_key}: {e}")
							
		except Exception as e:
			print(f"❌ Error en listener de expiraciones: {e}")
	
	# Iniciar listener en thread daemon
	listener_thread = threading.Thread(target=listener_worker, daemon=True)
	listener_thread.start()
	print("✅ Listener de expiraciones iniciado en segundo plano")
