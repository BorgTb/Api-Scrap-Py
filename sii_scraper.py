from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio


ANYO_MAP = {
    str(year): str(index) for index, year in enumerate(range(1983, 2026))
}

def ajustar_anyo(anyo):
    return ANYO_MAP.get(str(anyo), None)

def verificar_autenticacion(cadena):
    import re
    match = re.search(r"El código de este mensaje es ([\d.]+)", cadena)
    if match:
        ultimos_dos = match.group(1)[-2:]
        return ultimos_dos != "20"
    return True

def extraer_remanente(html):
    soup = BeautifulSoup(html, "html.parser")
    filas = soup.select("table.borde_tabla_f29_xslt tr")

    for fila in filas:
        if "Remanente de crédito fiscal" in fila.text:
            celda = fila.select_one("td.tabla_td_fixed_b_right")
            return celda.text.strip() if celda else 0

    return 0

def extraer_monto(html):
    soup = BeautifulSoup(html, "lxml")

    # Buscar la tabla que contiene "DECLARACIONES VIGENTES"
    tabla = soup.find("table", class_="tabla_internet")
    if not tabla:
        return None

    titulo = tabla.find("td", colspan="4")
    if not titulo or "DECLARACIONES VIGENTES" not in titulo.text:
        return None

    # Buscar la fila donde están los valores
    fila_datos = titulo.find_parent("tr").find_next_sibling("tr").find_next_sibling("tr")
    if not fila_datos:
        return None

    # Obtener los <div class="gwt-Label">
    labels = fila_datos.find_all("div", class_="gwt-Label")
    if len(labels) < 2:
        return None

    # El segundo label es el monto
    monto = labels[1].text.strip()
    return monto


async def scrap_sii(rut, password, mes, anio):
    anio_value = ajustar_anyo(anio)
    if anio_value is None:
        return {"error": "Año no soportado"}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # 1. Ir a login
            await page.goto("https://zeusr.sii.cl/AUT2000/InicioAutenticacion/IngresoRutClave.html")
            await page.fill("#rutcntr", rut)
            await page.fill("#clave", password)
            await page.click("#bt_ingresar")
            await page.wait_for_timeout(3000)

            # 2. Verificar autenticación
            if await page.query_selector("#titulo"):
                contenido = await page.inner_text("#titulo")
                if not verificar_autenticacion(contenido):
                    await browser.close()
                    return {"error": "Credenciales incorrectas"}

            

            # 3. Ir al formulario
            await page.goto("https://www4.sii.cl/rfiInternet/consulta/index.html#rfiSelFormularioPeriodo", timeout=60000)
            await page.wait_for_timeout(2000)

            # 4. Seleccionar formulario
            await page.select_option("select.gwt-ListBox", "0")
            await page.wait_for_timeout(1000)

            selects = await page.query_selector_all('div[title="Seleccione Período tributario para el que desea ingresar datos"] select.gwt-ListBox')
            if len(selects) < 2:
                return {"error": "No se encontraron selectores de año/mes"}


            print("✅ Selectores encontrados:", anio_value, mes)
            await selects[0].select_option(anio_value)
            await page.wait_for_timeout(1000)
            await selects[1].select_option(mes)
            await page.wait_for_timeout(1000)

            
            btn = await page.query_selector('button.gwt-Button[title="Presione aquí para desplegar datos previamente ingresados para el formulario y período seleccionado."]')
            if btn:
                print("✅ Botón encontrado")
                print("Visible:", await btn.is_visible())
                print("Enabled:", await btn.is_enabled())
            else:
                print("❌ Botón NO encontrado")

            await page.click('button.gwt-Button[title="Presione aquí para desplegar datos previamente ingresados para el formulario y período seleccionado."]')
            await page.wait_for_timeout(3000)

            # 6. Extraer folio
            folio_element = await page.query_selector('a[href="#rfiSelFormularioPeriodo"]')
            folio = await folio_element.inner_text() if folio_element else None

            if not folio:
                return {"error": "No se encontró el folio"}

            # Evaluar estado del folio
            if folio == "Guardado":
                return {"error": "No se ha pagado el SII"}
            elif folio == "Ver:":
                return {"error": "El pago se encuentra en proceso"}
            else:
                # dar click en el folio para obtener más detalles
                monto = extraer_monto(await page.content())
                await folio_element.click()
                await page.wait_for_timeout(3000)
                # click on <button type="button" class="gwt-Button">Ver Datos</button>
                await page.click('button.gwt-Button:has-text("Ver Datos")')
                await page.wait_for_timeout(3000)
                remanente = extraer_remanente(await page.content())
            
            print("✅ Remanente encontrado:", remanente)
            print("✅ Monto encontrado:", monto)
            print("✅ Folio encontrado:", folio)


        

            return {
                "folio": folio,
                "remanente": remanente,
                "monto": monto,
            }

        except Exception as e:
            return {"error": str(e)}
        finally:
            await browser.close()
