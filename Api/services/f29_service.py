import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))




from utils.login_sii import obtener_sesion
from models.ScrapeRequest import UserSii, UserSIIData
import requests
from utils.constants import TOKEN_SESION

def consultar_declaraciones_f29(token: str, token_sesion: str, rut: str, anio: int, mes: int):
    """
    Realiza una consulta de declaraciones del Formulario 29 al SII.
    
    Args:
        token: Token de autenticación para la cookie
        token_sesion: ID de sesión (X-GWT Strong Name)
        rut: RUT sin dígito verificador
        anio: Año de la consulta
        mes: Mes de la consulta (1-12)
    
    Returns:
        Response object con la respuesta del servidor
    """
    url = "https://www4.sii.cl/rfiInternet/formularioFacade"
    
    headers = {
        "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
        "X-GWT-Module-Base": "https://www4.sii.cl/rfiInternet/",
        "X-GWT-Permutation": "",
        "Referer": "https://www4.sii.cl/rfiInternet/consulta/index.html",
        "Cookie": f"TOKEN={token}"
    }
    
    # Construir el body con los parámetros
    body = f"7|0|17|https://www4.sii.cl/rfiInternet/|{token_sesion}|cl.sii.sdi.dim.rfi.web.client.service.FormularioFacade|findDeclaraciones|java.lang.String/2004016611|cl.sii.sdi.dim.rfi.to.Formulario/1008995664|cl.sii.sdi.dim.rfi.to.Periodo/4231800438|{rut}|java.lang.Boolean/476441737|0|029|Formulario 29 - Banco en Línea|java.lang.Integer/3438268394|java.sql.Timestamp/3040052672|Formulario 29|M|7761892\!77777777|1|2|3|4|3|5|6|7|8|6|9|0|-2|-2|-2|-2|-2|-2|-2|9|1|10|11|12|0|13|2|14|F$EFxuA|0|15|16|14|TTYdDqY|0|-3|-2|-3|-3|-3|10|-3|17|0|1|7|13|{anio}|13|{mes}|"
    
    try:
        response = requests.post(url, headers=headers, data=body)
        return response
    except Exception as e:
        print(f"Error al realizar la petición: {e}")
        return None



def limpiar_respuesta_sii_ultra(raw_string):
    # 1. Normalizar: eliminamos espacios raros y convertimos escapes básicos
    # para que la búsqueda sea más sencilla
    raw_string = raw_string.replace('\\x3C', '<').replace('\\x3E', '>').replace('\\x3D', '=')
    
    # 2. Buscar el bloque que empieza con <?xml y termina con </FormularioRfi>
    import re
    match = re.search(r'<\?xml.*?</FormularioRfi>', raw_string, re.DOTALL)
    
    if not match:
        return "No se encontró el XML. Verifica que el string incluya '<?xml' y '</FormularioRfi>'"

    xml_content = match.group(0)

    # 3. Limpieza final de escapes residuales (saltos de línea y comillas)
    remplazos = {
        '\\n': '\n',
        '\\"': '"',
        '\\': '' # Elimina cualquier barra invertida suelta
    }

    for escape, real in remplazos.items():
        xml_content = xml_content.replace(escape, real)

    return xml_content.strip()


def xml_a_json(xml_content: str):
    import xmltodict
    return xmltodict.parse(xml_content)


async def obtener_datos_f29(data: UserSIIData):
    datosSesion = obtener_sesion(UserSii(
        rut=data.rut,
        dv=data.dv,
        password=data.password
    ))

    f29Response = consultar_declaraciones_f29(
        token=datosSesion['token'],
        token_sesion=TOKEN_SESION, # Esto es un placeholder, idealmente se debería obtener dinámicamente
        rut=data.rut,
        anio=int(data.anio),
        mes=int(data.mes)
    )
    
    if f29Response is None:
        return {"error": "Error al realizar la consulta del F29."}
    
    clean_xml = limpiar_respuesta_sii_ultra(f29Response.text)

    if data.json:
        try:
            xml_dict = xml_a_json(clean_xml)
            return xml_dict['FormularioRfi']  # Retornar solo el bloque relevante
        except Exception as e:
            return {"error": f"Error al convertir XML a JSON: {e}", "raw_xml": clean_xml}
        

    return clean_xml




if __name__ == "__main__":
    test = UserSIIData(
        rut='76011662',
        dv='9',
        password='teleme662',
        mes='1',
        anio='2026',
        json=False
    )
    result = obtener_datos_f29(test)
    print(result)



