"""
Script para consultar el Registro de Compras y Ventas (RCV) del SII Chile
Fecha: 18 de Diciembre de 2025
"""

import sys
from pathlib import Path
import requests
import json
import csv
import uuid
from datetime import datetime
from typing import Dict, Optional
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))

from models.ScrapeRequest import UserSii, UserSIIData
from utils.login_sii import obtener_sesion

# ==================== CONSTANTES ====================

# URLs Base
BASE_URL = "https://www4.sii.cl/consdcvinternetui/services/data/facadeService/"

# Endpoints
ENDPOINT_COMPRAS = "getDetalleCompraExport"
ENDPOINT_VENTAS = "getDetalleVenta"

# Headers HTTP base
HEADERS_BASE = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Accept-Language": "es-ES,es;q=0.9",
    "User-Agent": "Mozilla/5.0 (compatible; PROG 1.0; Windows NT 5.0; YComp 5.0.2.4)"
}

# Acciones Recaptcha
ACCION_COMPRAS = "RCV_DDETC"
ACCION_VENTAS = "RCV_DETV"

# Estados contables
ESTADO_REGISTRO = "REGISTRO"
ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_NO_INCLUIR = "NO_INCLUIR"
ESTADO_RECLAMADO = "RECLAMADO"

# Tipos de operación
OPERACION_COMPRA = "COMPRA"
OPERACION_VENTA = "VENTA"

# Código tipo documento (0 = todos)
COD_TIPO_DOC_TODOS = "0"

# ==================== CONFIGURACIÓN ====================

# Valores por defecto mínimos para consumo desde endpoint
PERIODO_TRIBUTARIO_DEFAULT = datetime.now().strftime("%Y%m")
TOKEN_RECAPTCHA_DEFAULT = "1111111ww"

# ==================== VARIABLES ====================
PERIODO_TRIBUTARIO = PERIODO_TRIBUTARIO_DEFAULT

# ==================== FUNCIONES ====================


def generar_uuid() -> str:
    """Genera un UUID único para cada transacción"""
    return uuid.uuid4().hex[:13]


def construir_metadata(token: str, endpoint: str) -> Dict:
    """
    Construye el objeto metadata para la petición
    
    Args:
        token: Token de sesión
        endpoint: Nombre del endpoint (getDetalleCompraExport o getDetalleVentaExport)
    
    Returns:
        Diccionario con la metadata
    """
    return {
        "conversationId": token,
        "transactionId": generar_uuid(),
        "namespace": f"cl.sii.sdi.lob.diii.consdcv.data.api.interfaces.FacadeService/{endpoint}"
    }


def construir_data(
    rut: str,
    dv: str,
    periodo: str,
    operacion: str,
    estado_contab: str,
    token_recaptcha: str,
    cod_tipo_doc: str = COD_TIPO_DOC_TODOS
) -> Dict:
    """
    Construye el objeto data para la petición
    
    Args:
        rut: RUT del emisor sin puntos ni guión
        dv: Dígito verificador
        periodo: Periodo tributario en formato YYYYMM
        operacion: Tipo de operación (COMPRA o VENTA)
        estado_contab: Estado contable (REGISTRO, PENDIENTE, etc.)
        token_recaptcha: Token de recaptcha
        cod_tipo_doc: Código de tipo de documento (default: "0" para todos)
    
    Returns:
        Diccionario con los datos
    """
    accion = ACCION_COMPRAS if operacion == OPERACION_COMPRA else ACCION_VENTAS
    
    return {
        "accionRecaptcha": accion,
        "rutEmisor": rut,
        "dvEmisor": dv,
        "ptributario": periodo,
        "estadoContab": estado_contab,
        "codTipoDoc": cod_tipo_doc,
        "operacion": operacion,
        "tokenRecaptcha": token_recaptcha
    }


def construir_body_request(
    token: str,
    endpoint: str,
    rut: str,
    dv: str,
    periodo: str,
    operacion: str,
    estado_contab: str,
    token_recaptcha: str
) -> Dict:
    """
    Construye el body completo de la petición
    
    Returns:
        Diccionario con el body completo (metadata + data)
    """
    return {
        "metaData": construir_metadata(token, endpoint),
        "data": construir_data(rut, dv, periodo, operacion, estado_contab, token_recaptcha)
    }


def consultar_rcv(
    operacion: str,
    token: str,
    csessionid: Optional[str] = None,
    estado_contab: str = ESTADO_REGISTRO,
    rut: str = None,
    dv: str = None,
    periodo: str = None,
    token_recaptcha: str = None
) -> Optional[Dict]:
    """
    Realiza una consulta al RCV del SII
    
    Args:
        operacion: Tipo de operación (COMPRA o VENTA)
        estado_contab: Estado contable (default: REGISTRO)
        token: Token de sesión
        rut: RUT de la empresa (usa default si no se especifica)
        dv: Dígito verificador (usa default si no se especifica)
        periodo: Periodo tributario (YYYYMM) (usa default si no se especifica)
        token_recaptcha: Token de recaptcha (usa default si no se especifica)
    
    Returns:
        Respuesta JSON del servidor o None si hay error
    """
    # Usar valores por defecto mínimos
    csessionid = csessionid or token
    periodo = periodo or PERIODO_TRIBUTARIO_DEFAULT
    token_recaptcha = token_recaptcha or TOKEN_RECAPTCHA_DEFAULT

    if not rut or not dv:
        print("❌ RUT y DV son requeridos para consultar RCV")
        return None
    
    # Seleccionar endpoint según operación
    endpoint = ENDPOINT_COMPRAS if operacion == OPERACION_COMPRA else ENDPOINT_VENTAS
    url = BASE_URL + endpoint
    
    # Construir headers con cookies
    headers = HEADERS_BASE.copy()
    headers["Cookie"] = f"TOKEN={token}; CSESSIONID={csessionid}"
    
    # Construir body
    body = construir_body_request(
        token, endpoint, rut, dv, periodo, operacion, estado_contab, token_recaptcha
    )
    
    # Realizar petición
    try:
        print(f"\n🔄 Consultando {operacion} - {estado_contab}...")
        
        response = requests.post(
            url,
            headers=headers,
            json=body,
            verify=False  # SSL verify deshabilitado como en PHP
        )
        
        response.raise_for_status()
        
        result = response.json()
        
        # Verificar si hay datos
        data = result.get('data', [])
        if data is None:
            data = []
        
        num_registros = len(data) - 1 if len(data) > 0 else 0  # -1 por el header
        print(f"✅ {num_registros} registros obtenidos")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la petición: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error al decodificar JSON: {e}")
        return None


def procesar_respuesta_a_csv(respuesta: Dict, nombre_archivo: Optional[str] = None) -> str:
    """
    Procesa la respuesta JSON y guarda los datos en un archivo CSV
    
    Args:
        respuesta: Respuesta JSON del servidor
        nombre_archivo: Nombre del archivo CSV (opcional, usa el del servidor si no se especifica)
    
    Returns:
        Nombre del archivo creado
    """
    if not respuesta or 'data' not in respuesta:
        raise ValueError("Respuesta inválida o sin datos")
    
    # Usar el nombre del servidor o el especificado
    archivo = nombre_archivo or respuesta.get('nombreArchivo', f'rcv_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    
    # Extraer datos
    data_lines = respuesta.get('data', [])
    
    if not data_lines or data_lines is None:
        print("⚠️ No hay datos para procesar")
        return archivo
    
    # Escribir CSV
    with open(archivo, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        
        for line in data_lines:
            # Dividir la línea por punto y coma
            row = line.split(';')
            writer.writerow(row)
    
    print(f"💾 Archivo guardado: {archivo}")
    return archivo


def procesar_respuesta_ventas_json(respuesta: Dict) -> pd.DataFrame:
    """
    Procesa la respuesta JSON de ventas (formato objeto) y convierte a DataFrame
    
    Args:
        respuesta: Respuesta JSON del servidor con data como lista de objetos
    
    Returns:
        DataFrame con los datos de ventas
    """
    if not respuesta or 'data' not in respuesta:
        raise ValueError("Respuesta inválida o sin datos")
    
    data = respuesta.get('data', [])
    
    if not data or data is None:
        print("⚠️ No hay datos para procesar")
        return pd.DataFrame()
    
    # Convertir lista de objetos JSON a DataFrame
    df = pd.DataFrame(data)
    
    if df.empty:
        return df
    
    # Mapear campos JSON a nombres de columnas esperados
    columnas_map = {
        'detNroDoc': 'Nro',
        'detTipoDoc': 'Tipo Doc',
        'detRutDoc': 'RUT Receptor',
        'detDvDoc': 'DV',
        'detRznSoc': 'Razón Social',
        'detFchDoc': 'Fecha Docto',
        'detMntExe': 'Monto Exento',
        'detMntNeto': 'Monto Neto',
        'detMntIVA': 'Monto IVA',
        'detMntTotal': 'Monto Total',
        'detFecRecepcion': 'Fecha Recepción'
    }
    
    # Renombrar solo las columnas que existen
    columnas_renombrar = {k: v for k, v in columnas_map.items() if k in df.columns}
    df = df.rename(columns=columnas_renombrar)
    
    # Seleccionar solo las columnas mapeadas que existen
    columnas_deseadas = [v for k, v in columnas_map.items() if k in columnas_renombrar]
    df = df[columnas_deseadas]
    
    print(f"📊 DataFrame creado: {len(df)} registros, {len(df.columns)} columnas")
    
    return df


def procesar_respuesta_a_dataframe(respuesta: Dict) -> pd.DataFrame:
    """
    Procesa la respuesta JSON y convierte los datos a un DataFrame de pandas
    
    Args:
        respuesta: Respuesta JSON del servidor
    
    Returns:
        DataFrame con los datos
    """
    if not respuesta or 'data' not in respuesta:
        raise ValueError("Respuesta inválida o sin datos")
    
    data_lines = respuesta.get('data', [])
    
    if not data_lines or data_lines is None:
        print("⚠️ No hay datos para procesar")
        return pd.DataFrame()
    
    # Primera línea es el header
    header = data_lines[0].split(';')
    num_columns = len(header)
    
    # Resto son los datos
    rows = []
    for idx, line in enumerate(data_lines[1:], start=2):
        row = line.split(';')
        
        # Ajustar el número de columnas si no coincide
        if len(row) < num_columns:
            # Rellenar con valores vacíos si faltan columnas
            row.extend([''] * (num_columns - len(row)))
        elif len(row) > num_columns:
            # Truncar si hay más columnas (probablemente un ; extra al final)
            row = row[:num_columns]
        
        rows.append(row)
    
    # Crear DataFrame
    df = pd.DataFrame(rows, columns=header)
    
    print(f"📊 DataFrame creado: {len(df)} registros, {len(df.columns)} columnas")
    
    return df


def mostrar_resumen(respuesta: Dict):
    """
    Muestra un resumen de la respuesta obtenida
    
    Args:
        respuesta: Respuesta JSON del servidor
    """
    if not respuesta:
        print("❌ No hay respuesta para mostrar")
        return
    
    print("\n" + "="*60)
    print("RESUMEN DE LA CONSULTA")
    print("="*60)
    
    # Metadata
    metadata = respuesta.get('metaData', {})
    print(f"Conversation ID: {metadata.get('conversationId')}")
    print(f"Transaction ID: {metadata.get('transactionId')}")
    
    # Estado de respuesta
    resp_estado = respuesta.get('respEstado', {})
    print(f"\nEstado: Código {resp_estado.get('codRespuesta')}")
    if resp_estado.get('msgeRespuesta'):
        print(f"Mensaje: {resp_estado.get('msgeRespuesta')}")
    if resp_estado.get('codError'):
        print(f"Error: {resp_estado.get('codError')}")
    
    # Datos
    data = respuesta.get('data', [])
    if data is None:
        data = []
    print(f"\nRegistros obtenidos: {len(data) - 1 if len(data) > 0 else 0}")  # -1 por el header
    print(f"Nombre archivo: {respuesta.get('nombreArchivo', 'N/A')}")
    
    print("="*60 + "\n")


# ==================== FUNCIONES DE CONSULTA ESPECÍFICAS ====================

def consultar_compras_registro(token: str):
    """Consulta las compras en estado REGISTRO"""
    return consultar_rcv(operacion=OPERACION_COMPRA, token=token, estado_contab=ESTADO_REGISTRO)


def consultar_compras_pendiente(token: str):
    """Consulta las compras en estado PENDIENTE"""
    return consultar_rcv(operacion=OPERACION_COMPRA, token=token, estado_contab=ESTADO_PENDIENTE)


def consultar_ventas(
    token: str,
    cod_tipo_doc: str = COD_TIPO_DOC_TODOS,
    rut: str = None,
    dv: str = None,
    periodo: str = None,
    token_recaptcha: str = None,
    csessionid: Optional[str] = None
):
    """Consulta las ventas en estado REGISTRO usando el endpoint JSON"""
    # Usar valores por defecto mínimos
    csessionid = csessionid or token
    periodo = periodo or PERIODO_TRIBUTARIO_DEFAULT
    token_recaptcha = token_recaptcha or TOKEN_RECAPTCHA_DEFAULT

    if not rut or not dv:
        print("❌ RUT y DV son requeridos para consultar ventas")
        return None
    
    endpoint = ENDPOINT_VENTAS
    url = BASE_URL + endpoint
    
    headers = HEADERS_BASE.copy()
    headers["Cookie"] = f"TOKEN={token}; CSESSIONID={csessionid}"
    
    body = {
        "metaData": construir_metadata(token, endpoint),
        "data": construir_data(rut, dv, periodo, OPERACION_VENTA, ESTADO_REGISTRO, token_recaptcha, cod_tipo_doc)
    }
    
    try:
        print(f"  Consultando tipo doc {cod_tipo_doc}...")
        
        response = requests.post(url, headers=headers, json=body, verify=False)
        response.raise_for_status()
        
        result = response.json()
        
        data = result.get('data', [])
        if data is None:
            data = []
        
        num_registros = len(data)
        if num_registros > 0:
            print(f"  ✅ Tipo {cod_tipo_doc}: {num_registros} registros")
        
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la petición: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error al decodificar JSON: {e}")
        return None


# ==================== FUNCIONES DE ANÁLISIS Y RESUMEN ====================

def generar_resumen_compras(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera un resumen por tipo de documento para compras
    
    Args:
        df: DataFrame con los datos de compras
    
    Returns:
        DataFrame con el resumen por tipo de documento
    """
    if df.empty:
        return pd.DataFrame()
    
    # Convertir columnas numéricas
    columnas_numericas = [
        'Monto Exento', 'Monto Neto', 'Monto IVA Recuperable', 
        'Monto Iva No Recuperable', 'IVA uso Comun', 'Monto Total'
    ]
    
    for col in columnas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    # Aplicar signo negativo a notas de crédito (tipo 61)
    # Las notas de crédito deben restarse en los totales
    if 'Tipo Doc' in df.columns:
        for col in columnas_numericas:
            if col in df.columns:
                df.loc[df['Tipo Doc'].astype(str) == '61', col] = -df.loc[df['Tipo Doc'].astype(str) == '61', col]
    
    # Agrupar por tipo de documento
    resumen = df.groupby('Tipo Doc').agg({
        'Nro': 'count',
        'Monto Exento': 'sum',
        'Monto Neto': 'sum',
        'Monto IVA Recuperable': 'sum',
        'IVA uso Comun': 'sum',
        'Monto Iva No Recuperable': 'sum',
        'Monto Total': 'sum'
    }).reset_index()
    
    # Renombrar columnas
    resumen.columns = [
        'Tipo Documento',
        'Total Documentos',
        'Monto Exento',
        'Monto Neto',
        'IVA Recuperable',
        'IVA Uso Común',
        'IVA No Recuperable',
        'Monto Total'
    ]
    
    # Formatear números como enteros
    for col in resumen.columns:
        if col != 'Tipo Documento':
            resumen[col] = resumen[col].astype(int)
    
    return resumen


def generar_resumen_ventas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera un resumen por tipo de documento para ventas
    
    Args:
        df: DataFrame con los datos de ventas
    
    Returns:
        DataFrame con el resumen por tipo de documento
    """
    if df.empty:
        return pd.DataFrame()
    
    # Mapeo de columnas (nombre real -> nombre normalizado)
    columnas_mapa = {}
    for col in df.columns:
        col_lower = col.lower()
        if 'monto exento' in col_lower:
            columnas_mapa['Monto Exento'] = col
        elif 'monto neto' in col_lower:
            columnas_mapa['Monto Neto'] = col
        elif 'monto iva' in col_lower and 'recuperable' not in col_lower:
            columnas_mapa['Monto IVA'] = col
        elif 'monto total' in col_lower:
            columnas_mapa['Monto Total'] = col
    
    # Convertir columnas numéricas (incluyendo Nro que contiene detNroDoc)
    if 'Nro' in df.columns:
        df['Nro'] = pd.to_numeric(df['Nro'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    for nombre_norm, nombre_real in columnas_mapa.items():
        if nombre_real in df.columns:
            df[nombre_real] = pd.to_numeric(df[nombre_real].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    # Aplicar signo negativo a notas de crédito (tipo 61) solo en montos, NO en cantidad
    # Las notas de crédito deben restarse en los totales
    if 'Tipo Doc' in df.columns:
        for nombre_norm, nombre_real in columnas_mapa.items():
            if nombre_real in df.columns:
                df.loc[df['Tipo Doc'].astype(str) == '61', nombre_real] = -df.loc[df['Tipo Doc'].astype(str) == '61', nombre_real]
    
    # Separar tipo 61 y otros para agregación diferente
    df_tipo_61 = df[df['Tipo Doc'].astype(str) == '61'].copy() if 'Tipo Doc' in df.columns else pd.DataFrame()
    df_otros = df[df['Tipo Doc'].astype(str) != '61'].copy() if 'Tipo Doc' in df.columns else df.copy()
    
    # Preparar diccionario de agregación para otros tipos (sum de Nro)
    agg_dict_otros = {'Nro': 'sum'}
    for nombre_norm, nombre_real in columnas_mapa.items():
        if nombre_real in df.columns:
            agg_dict_otros[nombre_real] = 'sum'
    
    # Preparar diccionario de agregación para tipo 61 (count de Nro)
    agg_dict_61 = {'Nro': 'count'}
    for nombre_norm, nombre_real in columnas_mapa.items():
        if nombre_real in df.columns:
            agg_dict_61[nombre_real] = 'sum'
    
    # Agrupar por separado
    resumen_partes = []
    
    if not df_otros.empty:
        resumen_otros = df_otros.groupby('Tipo Doc').agg(agg_dict_otros).reset_index()
        resumen_partes.append(resumen_otros)
    
    if not df_tipo_61.empty:
        resumen_61 = df_tipo_61.groupby('Tipo Doc').agg(agg_dict_61).reset_index()
        # Aplicar signo negativo a la cantidad de documentos tipo 61
        resumen_61['Nro'] = -resumen_61['Nro']
        resumen_partes.append(resumen_61)
    
    # Combinar resultados
    if resumen_partes:
        resumen = pd.concat(resumen_partes, ignore_index=True)
    else:
        return pd.DataFrame()
    
    # Renombrar columnas - construir nombres basados en lo que realmente existe
    nuevas_columnas = ['Tipo Documento', 'Total Documentos']
    for nombre_norm in ['Monto Exento', 'Monto Neto', 'Monto IVA', 'Monto Total']:
        if nombre_norm in columnas_mapa and columnas_mapa[nombre_norm] in resumen.columns:
            nuevas_columnas.append(nombre_norm)
    
    resumen.columns = nuevas_columnas
    
    # Formatear números como enteros
    for col in resumen.columns:
        if col != 'Tipo Documento':
            resumen[col] = resumen[col].astype(int)
    
    return resumen


def generar_resumen_ventas_completo(dataframes_por_tipo: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Genera un resumen completo de ventas combinando todos los tipos de documento
    Incluye tipos sin datos en 0
    
    Args:
        dataframes_por_tipo: Diccionario con tipo de documento como key y DataFrame como value
    
    Returns:
        DataFrame con el resumen completo
    """
    tipos_requeridos = ['33', '39', '48', '61','56','41','110','43']
    
    # Combinar todos los DataFrames
    df_combinado = pd.DataFrame()
    for tipo, df in dataframes_por_tipo.items():
        if not df.empty:
            df_combinado = pd.concat([df_combinado, df], ignore_index=True)
    
    # Si no hay datos o no tiene la columna 'Tipo Doc', crear DataFrame vacío con estructura
    if df_combinado.empty or 'Tipo Doc' not in df_combinado.columns:
        return pd.DataFrame({
            'Tipo Documento': tipos_requeridos,
            'Total Documentos': [0, 0, 0, 0],
            'Monto Exento': [0, 0, 0, 0],
            'Monto Neto': [0, 0, 0, 0],
            'Monto IVA': [0, 0, 0, 0],
            'Monto Total': [0, 0, 0, 0]
        })
    
    # Generar resumen
    resumen = generar_resumen_ventas(df_combinado)
    
    # Si el resumen está vacío, devolver estructura vacía
    if resumen.empty:
        return pd.DataFrame({
            'Tipo Documento': tipos_requeridos,
            'Total Documentos': [0, 0, 0, 0],
            'Monto Exento': [0, 0, 0, 0],
            'Monto Neto': [0, 0, 0, 0],
            'Monto IVA': [0, 0, 0, 0],
            'Monto Total': [0, 0, 0, 0]
        })
    
    # Asegurar que todos los tipos requeridos estén presentes
    tipos_existentes = set(resumen['Tipo Documento'].astype(str))
    tipos_faltantes = set(tipos_requeridos) - tipos_existentes
    
    if tipos_faltantes:
        # Agregar filas con 0 para tipos faltantes
        filas_faltantes = []
        for tipo in tipos_faltantes:
            fila = {'Tipo Documento': tipo}
            for col in resumen.columns:
                if col != 'Tipo Documento':
                    fila[col] = 0
            filas_faltantes.append(fila)
        
        df_faltantes = pd.DataFrame(filas_faltantes)
        resumen = pd.concat([resumen, df_faltantes], ignore_index=True)
    
    # Ordenar por tipo de documento
    resumen['Tipo Documento'] = resumen['Tipo Documento'].astype(str)
    resumen = resumen.sort_values('Tipo Documento').reset_index(drop=True)
    
    return resumen


def mostrar_tabla_resumen(resumen: pd.DataFrame, titulo: str):
    """
    Muestra una tabla resumen formateada en consola con totales
    
    Args:
        resumen: DataFrame con el resumen
        titulo: Título de la tabla
    """
    if resumen.empty:
        print(f"\n⚠️ No hay datos para mostrar en {titulo}")
        return
    
    # Calcular totales
    totales = {}
    for col in resumen.columns:
        if col == 'Tipo Documento':
            totales[col] = 'TOTAL'
        else:
            totales[col] = resumen[col].sum()
    
    # Crear DataFrame con totales
    df_con_totales = pd.concat([resumen, pd.DataFrame([totales])], ignore_index=True)
    
    print(f"\n{'='*80}")
    print(f"{titulo}")
    print(f"{'='*80}")
    print(df_con_totales.to_string(index=False))
    print(f"{'='*80}\n")
    
    return totales


def mostrar_resumen_json(resumen: pd.DataFrame, totales: dict, titulo: str):
    """
    Muestra el resumen en formato JSON
    
    Args:
        resumen: DataFrame con el resumen
        totales: Diccionario con los totales
        titulo: Título del resumen
    """
    if resumen.empty:
        print(f"\n⚠️ No hay datos JSON para mostrar en {titulo}")
        return
    
    # Convertir DataFrame a lista de diccionarios
    datos = resumen.to_dict('records')
    
    # Convertir tipos numpy/pandas a tipos nativos de Python
    def convertir_tipos(obj):
        if isinstance(obj, dict):
            return {k: convertir_tipos(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convertir_tipos(item) for item in obj]
        elif hasattr(obj, 'item'):  # numpy/pandas types
            return obj.item()
        else:
            return obj
    
    # Convertir totales a tipos nativos
    totales_convertidos = convertir_tipos(totales)
    datos_convertidos = convertir_tipos(datos)
    
    # Crear estructura JSON
    resumen_json = {
        "titulo": titulo,
        "detalle": datos_convertidos,
        "totales": totales_convertidos
    }
    
    print("\n" + "="*80)
    print("RESUMEN EN FORMATO JSON")
    print("="*80)
    print(json.dumps(resumen_json, indent=2, ensure_ascii=False))
    print("="*80 + "\n")

def generar_json_consolidado(compras_registro: dict, compras_pendiente: dict, ventas: dict, periodo: str, rut: str, dv: str):
    """
    Genera un JSON consolidado con todos los resultados separados por apartados
    
    Args:
        compras_registro: Diccionario con resumen y totales de compras registro
        compras_pendiente: Diccionario con resumen y totales de compras pendiente
        ventas: Diccionario con resumen y totales de ventas
        periodo: Periodo tributario
        rut: RUT de la empresa
        dv: Dígito verificador
    """
    # Convertir tipos numpy/pandas a tipos nativos
    def convertir_tipos(obj):
        if isinstance(obj, dict):
            return {k: convertir_tipos(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convertir_tipos(item) for item in obj]
        elif hasattr(obj, 'item'):  # numpy/pandas types
            return obj.item()
        else:
            return obj
    
    resultado_final = {
        "empresa": {
            "rut": f"{rut}-{dv}",
            "periodo": periodo
        },
        "compras": {
            "registro": convertir_tipos(compras_registro) if compras_registro else None,
            "pendiente": convertir_tipos(compras_pendiente) if compras_pendiente else None
        },
        "ventas": {
            "registro": convertir_tipos(ventas) if ventas else None
        }
    }
    
    print("\n" + "="*80)
    print("RESULTADO CONSOLIDADO - JSON COMPLETO")
    print("="*80)
    print(json.dumps(resultado_final, indent=2, ensure_ascii=False))
    print("="*80 + "\n")
    
    return resultado_final


# ==================== FUNCIÓN PRINCIPAL PARA IMPORTACIÓN ====================

def obtener_registros_cv(
    rut: str,
    dv: str,
    clave: Optional[str] = None,
    periodo: str = PERIODO_TRIBUTARIO_DEFAULT,
    token_recaptcha: str = TOKEN_RECAPTCHA_DEFAULT,
    sesion: Optional[Dict[str, str]] = None
) -> Optional[Dict]:
    """
    Obtiene los registros de compras y ventas del SII para un RUT específico.
    
    Args:
        rut (str): RUT de la empresa sin puntos ni guión (ej: "77288679")
        dv (str): Dígito verificador (ej: "9")
        clave (str): Clave del SII
        periodo (str): Periodo tributario en formato YYYYMM (ej: "202510")
        token_recaptcha (str): Token de recaptcha
        sesion (dict, optional): Sesión existente con 'token' y 'csessionid'. Si es None, crea una nueva sesión.
    
    Returns:
        dict: JSON consolidado con compras y ventas agrupadas, o None si hay error
    """
    # Desactivar advertencias de SSL
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Obtener sesión (reutilizar si se proporciona)
    if sesion is None:
        if not clave:
            return {"error": "Debe proporcionar clave SII o una sesión activa (token/csessionid)."}

        sesion = obtener_sesion(UserSii(rut=rut, dv=dv, password=clave))
        if not sesion:
            return {"error": "No se pudo autenticar en SII. Verifica credenciales o sesión cacheada."}
    
    token = sesion.get('token')
    csessionid = sesion.get('csessionid', token)

    if not token:
        return {"error": "Sesión inválida: falta token."}
    
    # Variables para almacenar resultados
    resultado_compras_registro = None
    resultado_compras_pendiente = None
    resultado_ventas = None
    
    # 1. Consultar Compras REGISTRO
    respuesta_compras_registro = consultar_rcv(
        operacion=OPERACION_COMPRA, 
        token=token, 
        csessionid=csessionid,
        estado_contab=ESTADO_REGISTRO,
        rut=rut,
        dv=dv,
        periodo=periodo,
        token_recaptcha=token_recaptcha
    )

    
    if respuesta_compras_registro:
        df_compras_registro = procesar_respuesta_a_dataframe(respuesta_compras_registro)
        if not df_compras_registro.empty:
            resumen_compras = generar_resumen_compras(df_compras_registro)
            totales = {}
            for col in resumen_compras.columns:
                if col == 'Tipo Documento':
                    totales[col] = 'TOTAL'
                else:
                    totales[col] = resumen_compras[col].sum()
            
            resultado_compras_registro = {
                "titulo": "RESUMEN REGISTRO DE COMPRAS " + periodo,
                "detalle": resumen_compras.to_dict('records'),
                "totales": totales
            }
    
    
    # 2. Consultar Compras PENDIENTE
    respuesta_compras_pendiente = consultar_rcv(
        operacion=OPERACION_COMPRA, 
        token=token, 
        csessionid=csessionid,
        estado_contab=ESTADO_PENDIENTE,
        rut=rut,
        dv=dv,
        periodo=periodo,
        token_recaptcha=token_recaptcha
    )
    
    if respuesta_compras_pendiente:
        df_compras_pendiente = procesar_respuesta_a_dataframe(respuesta_compras_pendiente)
        
        if not df_compras_pendiente.empty:
            resumen_compras_pend = generar_resumen_compras(df_compras_pendiente)
            totales_pend = {}
            for col in resumen_compras_pend.columns:
                if col == 'Tipo Documento':
                    totales_pend[col] = 'TOTAL'
                else:
                    totales_pend[col] = resumen_compras_pend[col].sum()
            
            resultado_compras_pendiente = {
                "titulo": "RESUMEN COMPRAS PENDIENTES " + periodo,
                "detalle": resumen_compras_pend.to_dict('records'),
                "totales": totales_pend
            }
    
    # 3. Consultar Ventas por tipo de documento
    tipos_documento_ventas = ['33', '39', '48', '61', '56','110','41','43']
    dataframes_ventas = {}
    
    for tipo_doc in tipos_documento_ventas:
        respuesta_ventas = consultar_ventas(
            token, 
            cod_tipo_doc=tipo_doc,
            rut=rut,
            dv=dv,
            periodo=periodo,
            token_recaptcha=token_recaptcha,
            csessionid=csessionid
        )
        
        if respuesta_ventas:
            df_ventas_tipo = procesar_respuesta_ventas_json(respuesta_ventas)
            dataframes_ventas[tipo_doc] = df_ventas_tipo
        else:
            dataframes_ventas[tipo_doc] = pd.DataFrame()
    
    # Generar resumen completo
    resumen_ventas = generar_resumen_ventas_completo(dataframes_ventas)
    totales_ventas = {}
    for col in resumen_ventas.columns:
        if col == 'Tipo Documento':
            totales_ventas[col] = 'TOTAL'
        else:
            totales_ventas[col] = resumen_ventas[col].sum()
    
    resultado_ventas = {
        "titulo": "RESUMEN REGISTRO DE VENTAS " + periodo,
        "detalle": resumen_ventas.to_dict('records'),
        "totales": totales_ventas
    }
    
    # Generar JSON consolidado
    def convertir_tipos(obj):
        if isinstance(obj, dict):
            return {k: convertir_tipos(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convertir_tipos(item) for item in obj]
        elif hasattr(obj, 'item'):  # numpy/pandas types
            return obj.item()
        else:
            return obj
    
    # Preparar datos completos de compras (DataFrame completo)
    compras_completas = None
    if 'df_compras_registro' in locals() and not df_compras_registro.empty:
        compras_completas = convertir_tipos(df_compras_registro.to_dict('records'))
    
    # Preparar datos completos de ventas (DataFrames por tipo de documento)
    ventas_completas = {}
    for tipo_doc, df in dataframes_ventas.items():
        if not df.empty:
            ventas_completas[tipo_doc] = convertir_tipos(df.to_dict('records'))
        else:
            ventas_completas[tipo_doc] = []
    
    resultado_final = {
        "empresa": {
            "rut": f"{rut}-{dv}",
            "periodo": periodo
        },
        "compras": {
            "registro": convertir_tipos(resultado_compras_registro) if resultado_compras_registro else None,
            "pendiente": convertir_tipos(resultado_compras_pendiente) if resultado_compras_pendiente else None,
            "data_completa": compras_completas
        },
        "ventas": {
            "registro": convertir_tipos(resultado_ventas) if resultado_ventas else None,
            "data_completa": ventas_completas
        }
    }
    

    #print(resultado_final)

    return resultado_final


async def obtener_datos_rcv(data: UserSIIData, token_recaptcha: str = TOKEN_RECAPTCHA_DEFAULT):
    """
    Adaptador para endpoint FastAPI.
    Convierte `anio` + `mes` al formato `YYYYMM` y usa la sesión del módulo `login_sii`.
    """
    periodo = f"{data.anio}{str(data.mes).zfill(2)}"
    return obtener_registros_cv(
        rut=data.rut,
        dv=data.dv,
        clave=data.password,
        periodo=periodo,
        token_recaptcha=token_recaptcha
    )


# ==================== MAIN ====================

if __name__ == "__main__":
    print("RCV_service está preparado para ser consumido desde endpoint FastAPI.")

