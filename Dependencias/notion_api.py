import requests
from Config import config
import pytz
import json
from datetime import datetime


headers = {
    "Authorization": "Bearer " + config.NOTION_TOKEN,
    "accept": "application/json",
    "Notion-Version": "2022-06-28",
    "content-type": "application/json"
}


def cambioTiempo(segundos):

    if segundos < 3600:
        minutos = segundos // 60
        segundos_restantes = segundos % 60
        return f"{minutos}:{segundos_restantes:02}"
    else:
        horas = segundos // 3600
        segundos_restantes = segundos % 3600
        minutos = segundos_restantes // 60
        segundos_restantes_final = segundos_restantes % 60
        return f"{horas:02}:{minutos:02}:{segundos_restantes_final:02}"


def obtenerRitmo(velocidad):
    ritmo_min_km = 1000 / velocidad / 60
    minutos = int(ritmo_min_km)
    segundos_decimal = (ritmo_min_km - minutos) * 60
    segundos = int(segundos_decimal)

    # Formatea el resultado como "minutos:segundos"
    formato_min_seg = f"{minutos:02d}:{segundos:02d} min/Km"
    return formato_min_seg


def create_page(actividad):

    create_url = "https://api.notion.com/v1/pages"

    published_date = actividad.start_date.isoformat()
    zona_horaria_strava = pytz.timezone(actividad.timezone[-13:])

    # Convierte la fecha y hora UTC a la zona horaria asociada
    fecha_utc_obj = datetime.strptime(published_date[0:-6], "%Y-%m-%dT%H:%M:%S")
    fecha_con_timezone = fecha_utc_obj.replace(tzinfo=pytz.utc).astimezone(zona_horaria_strava)


    ritmo = obtenerRitmo(actividad.average_speed)
    tiempo = cambioTiempo(actividad.moving_time)

    data = {
            "Identificador": {"rich_text": [{"text": {"content": str(actividad.id)}}]},
            "Tipo deporte": {"select": {"name": actividad.type}},
            "Nombre": {"title": [{"text": {"content": actividad.name}}]},
            "Fecha": {"date": {"start": fecha_con_timezone.strftime("%Y-%m-%dT%H:%M:%S"), "end": None}},
            "Distancia": {"rich_text": [{"text": {"content": str(actividad.distance / 1000) + " Km"}}]},
            "Tiempo": {"rich_text": [{"text": {"content": tiempo}}]},
            "Ritmo": {"rich_text": [{"text": {"content": ritmo}}]},
            "URL": {"url": "https://www.strava.com/activities/" + str(actividad.id)}
    }
    payload = {"parent": {"database_id": config.DATABASE_ID}, "properties": data}

    res = requests.post(create_url, headers=headers, json=payload)

    comprobarDatos(data)


def obtenerPagina(pages, id):

    for actividad in pages:
        if actividad["properties"]["Identificador"]["rich_text"][0]["plain_text"] == str(id):
            return True
    return False


def get_pages(num_pages=None):

    url = f"https://api.notion.com/v1/databases/{config.DATABASE_ID}/query"
    get_all = num_pages is None
    page_size = 100 if get_all else num_pages

    payload = {"page_size": page_size}
    response = requests.post(url, json=payload, headers=headers)

    data = response.json()

    results = data["results"]
    while data["has_more"] and get_all:
        payload = {"page_size": page_size, "start_cursor": data["next_cursor"]}
        url = f"https://api.notion.com/v1/databases/{config.DATABASE_ID}/query"
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        results.extend(data["results"])

    return results


def comprobarDatos(data):
    tipo = data["Tipo deporte"]["select"]["name"]

    marcas = cogerMarcas(tipo)
    if len(marcas) == 0:
        actualizarMarca(data, "Duracion", "Mayor duración")
        actualizarMarca(data, "Ritmo", "Mejor ritmo")
        actualizarMarca(data, "Distancia", "Mayor distancia")
    else:
        if float(marcas[0]["properties"]["Distancia"]["rich_text"][0]["text"]["content"][:-2]) < float(data["Distancia"]["rich_text"][0]["text"]["content"][:-2]):
            actualizarMarca(data, "Mayor distancia", marcas[0]["id"])
        if not compararTiempos(marcas[1]["properties"]["Ritmo"]["rich_text"][0]["text"]["content"][:-6], data["Ritmo"]["rich_text"][0]["text"]["content"][:-6]):
            actualizarMarca(data, "Mejor ritmo", marcas[1]["id"])
        if compararTiempos(marcas[2]["properties"]["Tiempo"]["rich_text"][0]["text"]["content"], data["Tiempo"]["rich_text"][0]["text"]["content"]):
            actualizarMarca(data, "Mayor duración", marcas[2]["id"])


def cogerMarcas(tipo, num_pages=None):
    url = f"https://api.notion.com/v1/databases/{config.DATABASE_MARCAS_ID}/query"

    get_all = num_pages is None
    page_size = 100 if get_all else num_pages

    payload = {"page_size": page_size}
    response = requests.post(url, json=payload, headers=headers)

    data = response.json()

    results = data["results"]
    while data["has_more"] and get_all:
        payload = {"page_size": page_size, "start_cursor": data["next_cursor"]}
        url = f"https://api.notion.com/v1/databases/{config.DATABASE_MARCAS_ID}/query"
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        results.extend(data["results"])
    res = list()
    for actividad in results:
        if actividad["properties"]["Tipo deporte"]["select"]["name"] == tipo:
            res.append(actividad)
    return res


def actualizarMarca(datos, marca, id):

    url = ""
    if id != "":
        url = "https://api.notion.com/v1/pages/" + id
    else:
        url = "https://api.notion.com/v1/pages"

    updateData = {
        "properties": {
            "Identificador": {"rich_text": [{"text": {"content": datos["Identificador"]["rich_text"][0]["text"]["content"]}}]},
            "Tipo deporte": {"select": {"name": datos["Tipo deporte"]["select"]["name"]}},
            "Nombre": {"title": [{"text": {"content": marca }}]},
            "Fecha": {"date": {"start": datos["Fecha"]["date"]["start"], "end": None}},
            "Distancia": {"rich_text": [{"text": {"content": datos["Distancia"]["rich_text"][0]["text"]["content"]}}]},
            "Tiempo": {"rich_text": [{"text": {"content": datos["Tiempo"]["rich_text"][0]["text"]["content"]}}]},
            "Ritmo": {"rich_text": [{"text": {"content": datos["Ritmo"]["rich_text"][0]["text"]["content"]}}]},
            "URL": {"url": datos["URL"]["url"]}
        }
    }

    if id == "":
        payload = {"parent": {"database_id": config.DATABASE_MARCAS_ID}, "properties": updateData["properties"]}
        res = requests.post(url, headers=headers, json=payload)
    else:
        data = json.dumps(updateData)
        response = requests.request("PATCH", url, headers=headers, data=data)


def compararTiempos(tiempo, tiempo_2):

    if len(tiempo.split(":")) == 3:
        horas, minutos, segundos = tiempo.split(':')
        total_segundos = int(horas) * 3600 + int(minutos) * 60 + int(segundos)
    else:
        minutos, segundos = tiempo.split(':')
        total_segundos = int(minutos) * 60 + int(segundos)

    if len(tiempo_2.split(":")) == 3:
        horas, minutos, segundos = tiempo_2.split(':')
        total_segundos_2 = int(horas) * 3600 + int(minutos) * 60 + int(segundos)
    else:
        minutos, segundos = tiempo_2.split(':')
        total_segundos_2 = int(minutos) * 60 + int(segundos)

    if total_segundos < total_segundos_2:
        return True
    return False
