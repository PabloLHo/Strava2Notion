from stravaio import *
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import os
import threading


token = {}

def obtenerToken(client_id=None, client_secret=None):
    global token
    if client_id is None:
        client_id = os.getenv('STRAVA_CLIENT_ID', None)
        if client_id is None:
            raise ValueError('client_id is None')
    if client_secret is None:
        client_secret = os.getenv('STRAVA_CLIENT_SECRET', None)
        if client_secret is None:
            raise ValueError('client_secret is None')

    port = 8000
    pedirAutorizacion(client_id, client_secret, port)
    return token


def pedirAutorizacion(client_id, client_secret, port):
    params_oauth = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": f"http://localhost:{port}/authorization_successful",
        "scope": "read,profile:read_all,activity:read",
        "state": 'https://github.com/sladkovm/strava-http',
        "approval_prompt": "force"
    }
    values_url = urllib.parse.urlencode(params_oauth)
    base_url = 'https://www.strava.com/oauth/authorize'
    rv = base_url + '?' + values_url

    driver = webdriver.Chrome()
    driver.minimize_window()
    driver.get(rv)
    boton = driver.find_element(By.ID, "email").send_keys("")
    boton = driver.find_element(By.ID, "password").send_keys("")
    driver.find_element(By.ID, "password").send_keys(Keys.ENTER)
    servidor_thread = threading.Thread(target=obtenerAutorizacion, args=(port, client_id, client_secret))
    servidor_thread.start()
    boton = driver.find_element(By.ID, "authorize")
    boton.click()
    servidor_thread.join()


def obtenerAutorizacion(port, client_id, client_secret):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', port))
        s.listen()
        conn, addr = s.accept()
        request_bytes = b''
        with conn:
            while True:
                chunk = conn.recv(512)
                request_bytes += chunk

                if request_bytes.endswith(b'\r\n\r\n'):
                    break
            conn.sendall(b'HTTP/1.1 200 OK\r\n\r\nsuccess\r\n')

        request = request_bytes.decode('utf-8')
        status_line = request.split('\n', 1)[0]

        method, raw_url, protocol_version = status_line.split(' ')

        url = urllib.parse.urlparse(raw_url)
        query_string = url.query
        query_params = urllib.parse.parse_qs(query_string, keep_blank_values=True)

        if url.path == "/authorization_successful":
            code = query_params.get('code')[0]
            logger.debug(f"code: {code}")
            params = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code"
            }
            r = requests.post("https://www.strava.com/oauth/token", params)
            data = r.json()
            logger.debug(f"Authorized athlete: {data.get('access_token', 'Oeps something went wrong!')}")
        else:
            data = url.path.encode()
        global token
        token = data
