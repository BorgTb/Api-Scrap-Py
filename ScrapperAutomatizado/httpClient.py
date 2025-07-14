import requests

def getUserData():
    url = "https://telegestor.cl/Automatizacion_tareas/Main/UsuariosImpagoF29.php"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        data = response.json()  # Parse the JSON response
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    
def sendDataToServer(rut, data,mes,anio):
    url = "https://telegestor.cl/Automatizacion_tareas/Main/gestor_tareas.php"    

    if not data:
        print("No data provided to send.")
        return None
    if data.get('error'):
        print(f"Error in data: {data['error']}")
        return None


    data.update({"success": "1"})  # Add an action to the data if needed
    data.update({"tarea": "pago_sii_python"})  # Specify the action for the server
    data.update({"rut_empresa": formatearRut(rut)})  # Add the user's RUT to the data
    data.update({"mes": formatearMes(mes)})  # Add a date to the data, adjust as needed
    data.update({"anyo": anio})  # Add a year to the data, adjust as needed
    data.update({"remanente": formatearRemanente(data.get("remanente", ""))})  # Format remanente

    
    try:
        response = requests.post(url, data, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error sending data: {e}")
        return None
    


def formatearRut(rut):
    """
    Formatea el RUT eliminando puntos y guiones y el digito verificador.
    Por ejemplo, '12.345.678-9' se convierte en '12345678'
    """
    if not rut:
        return None
    # Eliminar puntos y guiones
    rut = rut.replace('.', '').replace('-', '')
    # Retornar el RUT sin el dígito verificador
    return rut[:-1] if len(rut) > 1 else rut

def formatearMes(mes):
    """
    Formatea el mes a dos dígitos y le suma 1.
    Por ejemplo, '4' se convierte en '05'
    """
    if not mes:
        return None
    mes = int(mes) + 1  # Sumar 1 al mes
    return f"{mes:02d}"  # Convierte a cadena con dos dígitos

def formatearRemanente(remanente):
    """
    Formatea el remanente a dos decimales.
    Por ejemplo, '42.958.636' se convierte en '42958636'
    """
    if not remanente:
        return None
    # Eliminar puntos y convertir a entero
    remanente = remanente.replace('.', '')
    return int(remanente) if remanente.isdigit() else None