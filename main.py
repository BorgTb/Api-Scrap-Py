import asyncio
from sii_scraper import scrap_sii
import httpClient as http

semaphore = asyncio.Semaphore()  # Solo 3 tareas a la vez

def formatear_mes_actual():
    from datetime import datetime
    print(datetime.now().month)
    mes_actual = datetime.now().month - 2 # Restar 1 para obtener el mes anterior restando 1 para formato del sii
    #mes_actual = mes - 1  # Restar 1 para obtener el mes anterior restando 1 para formato del sii
    return str(mes_actual) if mes_actual >= 0 else "0"  # Asegurarse de que sea un stringes

async def run_scrap_for_user(user):
    async with semaphore:
        rut = user["rut"]
        clave = user["clave"]
        mes = formatear_mes_actual() # debe ser el anterior al mes actual pero restandole 1, es decir, enero = 0, febrero = 1, marzo = 2, abril = 3, mayo = 4, junio = 5, julio = 6, agosto = 7, septiembre = 8, octubre = 9, noviembre = 10, diciembre = 11
        anio = "2025"

        try:
            result = await scrap_sii(rut, clave, mes, anio)
            print(result)
            res = http.sendDataToServer(rut, result, mes, anio)
            print(f"✅ Resultado para {rut}: {res.text}")
        except Exception as e:
            print(f"❌ Error para {rut}: {e}")



async def main_async():
    data = http.getUserData()

    if not data:
        print("No data found or error.")
        return

    print(f"🔄 Procesando {len(data)} usuarios...")

    # Crear una lista de tareas
    tasks = [run_scrap_for_user(user) for user in data]

    # Ejecutarlas en paralelo
    await asyncio.gather(*tasks)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
    #res = http.sendDataToServer()
    #print(f"Respuesta del servidor: {res}")
    
   