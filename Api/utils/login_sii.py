import sys
import os
from pathlib import Path

# Agregar el directorio Api al path para que funcione cuando se ejecuta directamente
current_dir = Path(__file__).resolve().parent
api_dir = current_dir.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from typing import Optional, Dict
import requests
from urllib.parse import quote
from utils.constants import URL_LOGIN_SII, REFERENCIA_LOGIN, REFERENCIA_CIERRE_SESION
from models.ScrapeRequest import UserSii
from utils.sesion_cache import eliminar_sesion_cacheada, obtener_sesion_cacheada, guardar_sesion_cacheada

# Desactivar warnings de SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _intentar_autenticacion(user_sii: UserSii) -> Optional[Dict[str, str]]:
    url = URL_LOGIN_SII

    rut_formateado = f"{user_sii.rut[:2]}.{user_sii.rut[2:5]}.{user_sii.rut[5:]}-{user_sii.dv}"
    referencia_encoded = quote(REFERENCIA_LOGIN, safe='')

    payload = (
        f"rut={quote(user_sii.rut, safe='')}&"
        f"dv={quote(user_sii.dv, safe='')}&"
        f"referencia={referencia_encoded}&"
        f"411=&"
        f"rutcntr={quote(rut_formateado, safe='')}&"
        f"clave={quote(user_sii.password, safe='')}"
    )

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            data=payload,
            verify=False,
            allow_redirects=False
        )

        cookies = response.cookies
        set_cookie_headers = response.headers.get('Set-Cookie', '')

        token = None
        csessionid = None

        if 'TOKEN' in cookies:
            token = cookies['TOKEN']
        if 'CSESSIONID' in cookies:
            csessionid = cookies['CSESSIONID']

        if not token or not csessionid:
            import re
            if 'TOKEN=' in set_cookie_headers:
                match = re.search(r'TOKEN=([^;\s]+)', set_cookie_headers)
                if match:
                    token = match.group(1)
            if 'CSESSIONID=' in set_cookie_headers:
                match = re.search(r'CSESSIONID=([^;\s]+)', set_cookie_headers)
                if match:
                    csessionid = match.group(1)

        if token and len(token) >= 10:
            return {
                'token': token,
                'csessionid': csessionid or token
            }

        print(f"❌ No se pudo obtener el token de sesión")
        print(f"   Status Code: {response.status_code}")
        print(f"   Cookies: {dict(cookies)}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la autenticación: {e}")
        return None


def _cerrar_sesion_sii(token: str, csessionid: str, rut: str, dv: str) -> bool:
    """
    Cierra la sesión en el SII llamando al endpoint de terminación
    
    Args:
        token: Token de sesión (cookie TOKEN)
        csessionid: Cookie CSESSIONID
        rut: RUT del usuario sin puntos ni guión
        dv: Dígito verificador
    
    Returns:
        True si la sesión se cerró correctamente, False en caso de error
    """
    url = REFERENCIA_CIERRE_SESION
    
    # Construir cookies necesarias para el cierre de sesión
    cookies = {
        'TOKEN': token,
        'CSESSIONID': csessionid,
        'RUT_NS': rut,
        'DV_NS': dv,
        'NETSCAPE_LIVEWIRE.rut': rut,
        'NETSCAPE_LIVEWIRE.dv': dv
    }
    
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,es-CL;q=0.5',
        'Connection': 'keep-alive',
        'Host': 'zeusr.sii.cl',
        'Referer': 'https://misiir.sii.cl/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="142", "Not A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }
    
    try:
        response = requests.get(
            url,
            headers=headers,
            cookies=cookies,
            verify=False,
            allow_redirects=True,
            timeout=10
        )
        
        # Verificar que la respuesta sea exitosa (200-299)
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Sesión cerrada en el SII para RUT {rut}-{dv}")
            return True
        else:
            print(f"⚠️ Respuesta del SII al cerrar sesión: {response.status_code}")
            return True  # Aún así considerarlo exitoso si el servidor responde
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al cerrar sesión en el SII: {e}")
        return False


def obtener_sesion(user_sii: UserSii) -> Optional[Dict[str, str]]:
    """
    Obtiene la sesión y token del SII mediante autenticación
    
    Args:
        user_sii: Objeto UserSii con rut, dv y clave
    
    Returns:
        Diccionario con 'token' y 'csessionid' o None si hay error
    """
    sesion_cacheada = obtener_sesion_cacheada(user_sii)
    if sesion_cacheada:
        print("\n♻️ Usando sesión en caché del SII...")
        return sesion_cacheada

    print("\n🔐 Autenticando en el SII...")

    sesion = _intentar_autenticacion(user_sii)
    if not sesion:
        print("🔁 Reintentando obtención de cookie/token...")
        sesion = _intentar_autenticacion(user_sii)

    if not sesion:
        return None

    print(f"✅ Autenticación exitosa")
    print(f"   TOKEN: {sesion['token']}")
    print(f"   CSESSIONID: {sesion['csessionid']}")

    guardar_sesion_cacheada(
        user_sii=user_sii,
        token=sesion['token'],
        csessionid=sesion['csessionid']
    )

    return sesion

def cerrar_sesion(user_sii: UserSii) -> bool:
    """
    Cierra manualmente una sesión del SII:
    1. Llama al endpoint de terminación del SII (autTermino.cgi)
    2. Elimina la sesión de Redis
    
    Args:
        user_sii: Objeto UserSii con rut y dv
    
    Returns:
        True si se cerró correctamente, False si no existía o hubo error
    """
    # Verificar si existe sesión
    sesion_data = obtener_sesion_cacheada(user_sii)
    
    if not sesion_data:
        print(f"⚠️ No se encontró sesión activa para {user_sii.rut}-{user_sii.dv}")
        return False
    
    # eliminar_sesion_cacheada ahora maneja el cierre en SII automáticamente
    return eliminar_sesion_cacheada(user_sii, cerrar_en_sii=True)


async def obtener_sesion_playwright(user_sii: UserSii) -> Optional[Dict[str, str]]:
    """
    Obtiene sesión del SII usando Playwright con medidas anti-detección de bots.
    
    Características:
    - Modo headless optimizado para bypass de detección
    - Deshabilitación de features de automatización
    - Manejo correcto de CAutInicio.cgi esperando redirección del script anti-bot
    - No asume error de password falsamente
    
    Args:
        user_sii: Objeto UserSii con rut, dv y password
    
    Returns:
        Diccionario con 'token' y 'csessionid' o None si hay error
    """
    from playwright.async_api import async_playwright
    import asyncio
    
    print("\n🔐 Autenticando en el SII con Playwright (modo stealth)...")
    
    rut_formateado = f"{user_sii.rut[:2]}.{user_sii.rut[2:5]}.{user_sii.rut[5:]}-{user_sii.dv}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # ✅ Cambiar a True para usar headless moderno
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                # ✅ Agregar más argumentos stealth
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='es-CL',
            timezone_id='America/Santiago',
            # ✅ Agregar permisos y características adicionales
            permissions=['geolocation'],
            color_scheme='light'
        )
        
        # ✅ Scripts mejorados para mayor evasión
        await context.add_init_script("""
            // Ocultar webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Simular Chrome real
            window.navigator.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Plugins realistas
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Lenguajes
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-CL', 'es', 'en-US', 'en']
            });
            
            // ✅ NUEVO: Ocultar dimensiones de headless
            Object.defineProperty(screen, 'availWidth', {
                get: () => 1920
            });
            Object.defineProperty(screen, 'availHeight', {
                get: () => 1080
            });
            
            // ✅ NUEVO: Simular batería
            Object.defineProperty(navigator, 'getBattery', {
                value: () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                })
            });
        """)
        
        page = await context.new_page()
        
        try:
            # Navegar a la página de login
            await page.goto(
                "https://zeusr.sii.cl/AUT2000/InicioAutenticacion/IngresoRutClave.html?https://misiir.sii.cl/cgi_misii/siihome.cgi",
                wait_until='networkidle',
                timeout=30000
            )
            
            print(f"   📝 Ingresando credenciales para RUT: {rut_formateado}")
            
            # Llenar formulario con delays humanos
            await page.fill("#rutcntr", rut_formateado, timeout=5000)
            await asyncio.sleep(0.5)
            
            await page.fill("#clave", user_sii.password, timeout=5000)
            await asyncio.sleep(0.3)
            
            # Click en el botón de ingreso
            await page.click("#bt_ingresar")
            
            # CRÍTICO: Esperar a que CAutInicio.cgi procese el anti-bot
            # No asumir error inmediatamente, esperar redirección completa
            print("   ⏳ Esperando procesamiento anti-bot de CAutInicio.cgi...")
            
            try:
                # Esperar navegación o cambio de URL (máx 15 segundos)
                await page.wait_for_url(
                    lambda url: 'CAutInicio.cgi' not in url or 'siihome.cgi' in url,
                    timeout=15000
                )
                await asyncio.sleep(2)  # Espera adicional para estabilidad
                
            except Exception as timeout_error:
                print(f"   ⚠️ Timeout esperando redirección post-login")
            
            # Obtener URL actual para diagnóstico
            current_url = page.url
            print(f"   📍 URL actual: {current_url}")
            
            # Verificar si hay mensaje de error de credenciales
            error_element = await page.query_selector("#titulo")
            if error_element:
                contenido = await error_element.inner_text()
                # Verificar código de error 20 = credenciales incorrectas
                import re
                match = re.search(r"El código de este mensaje es ([\d.]+)", contenido)
                if match:
                    codigo = match.group(1)[-2:]
                    if codigo == "20":
                        print(f"   ❌ Credenciales incorrectas (código: {codigo})")
                        await browser.close()
                        return None
                    else:
                        print(f"   ℹ️ Mensaje del SII (código: {codigo}): {contenido[:100]}")
            
            # Extraer cookies de autenticación
            cookies = await context.cookies()
            
            token = None
            csessionid = None
            
            for cookie in cookies:
                if cookie['name'] == 'TOKEN':
                    token = cookie['value']
                if cookie['name'] == 'CSESSIONID':
                    csessionid = cookie['value']
            
            if not token:
                print("   ❌ No se pudo obtener el token de sesión")
                print(f"   Cookies disponibles: {[c['name'] for c in cookies]}")
                await browser.close()
                return None
            
            print(f"   ✅ Autenticación exitosa")
            print(f"   TOKEN: {token[:20]}...")
            print(f"   CSESSIONID: {csessionid[:20] if csessionid else 'N/A'}...")
            
            
            
            # Guardar en cache
            guardar_sesion_cacheada(
                user_sii=user_sii,
                token=token,
                csessionid=csessionid or token
            )


            # cerrar sesion y retornar datos
            await page.goto('https://zeusr.sii.cl/cgi_AUT2000/autTermino.cgi')
            #esperar a que se cierre la sesión completamente
            await page.wait_for_timeout(2000)
            await browser.close()
            return {
                'token': token,
                'csessionid': csessionid or token
            }
            
        except Exception as e:
            print(f"   ❌ Error durante la autenticación con Playwright: {e}")
            await browser.close()
            return None

