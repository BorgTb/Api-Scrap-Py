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
    
