import asyncio
from sii_scraper import scrap_sii
import httpClient as http

semaphore = asyncio.Semaphore(3)  # Solo 3 tareas a la vez

async def run_scrap_for_user(user):
    async with semaphore:
        rut = user["rut"]
        clave = user["clave"]
        mes = "4"
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
    
   
