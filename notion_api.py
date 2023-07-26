import requests
from config import DATABASE_ID, NOTION_TOKEN
import pytz
from datetime import datetime


headers = {
    "Authorization": "Bearer " + NOTION_TOKEN,
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

    payload = {"parent": {"database_id": DATABASE_ID}, "properties": data}

    res = requests.post(create_url, headers=headers, json=payload)
    return res


def obtenerPagina(pages, id):

    for actividad in pages:
        if actividad["properties"]["Identificador"]["rich_text"][0]["plain_text"] == str(id):
            return True
    return False


def get_pages(num_pages=None):

    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    get_all = num_pages is None
    page_size = 100 if get_all else num_pages

    payload = {"page_size": page_size}
    response = requests.post(url, json=payload, headers=headers)

    data = response.json()

    results = data["results"]
    while data["has_more"] and get_all:
        payload = {"page_size": page_size, "start_cursor": data["next_cursor"]}
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        results.extend(data["results"])

    return results
