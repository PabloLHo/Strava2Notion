from Dependencias import notion_api, strava
from Config import config


if __name__ == '__main__':
    # Get Strava Data
    token = strava.obtenerToken(client_id=config.CLIENT_ID, client_secret=config.CLIENT_SECRET)
    client = strava.StravaIO(access_token=token["access_token"])
    activities = client.get_logged_in_athlete_activities()
    paginas = notion_api.get_pages()

    for activity in activities:
        if not notion_api.obtenerPagina(paginas, activity.id):
            notion_api.create_page(activity)