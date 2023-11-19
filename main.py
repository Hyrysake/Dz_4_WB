import pathlib
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import mimetypes
import json
import logging
from threading import Thread
import socket
from datetime import datetime

BASE_DIR = pathlib.Path(__file__).resolve().parent
SERVER_IP = socket.gethostname()
SERVER_PORT_HTTP = 3000
SERVER_PORT_SOCKET = 5000
BUFFER_SIZE = 1024


def send_data_to_socket(data):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(data, (SERVER_IP, SERVER_PORT_SOCKET))
    client_socket.close()


class MyHTTPHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        send_data_to_socket(body)
        self.send_response(302)
        self.send_header("Location", "/index")
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == '/':
            self.send_html('index.html')
        elif parsed_url.path == '/message':
            self.send_html('message.html')
        elif parsed_url.path == '/index':
            self.send_html('index.html')
        else:
            file_path = BASE_DIR / 'static' / parsed_url.path[1:]
            if file_path.exists():
                self.send_static(file_path)

            else:
                self.send_html('error.html', 404)

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        with open(BASE_DIR / 'templates' / filename, "rb") as file:
            self.wfile.write(file.read())

    def send_static(self, filename):
        self.send_response(200)
        mime_type, _ = mimetypes.guess_type(filename)
        self.send_header('Content-type', mime_type if mime_type else 'text/plain')
        self.end_headers()

        with open(filename, "rb") as file:
            self.wfile.write(file.read())


def run_http_server(server=HTTPServer, handler=MyHTTPHandler):
    address = ("", SERVER_PORT_HTTP)
    http_server = server(address, handler)

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def save_data(data):
    decoded_data = urllib.parse.unquote_plus(data.decode())
    try:
        payload = {key: value for key, value in [el.split("=") for el in decoded_data.split("&")]}
        text_message = {str(datetime.now()): payload}

        data_file_path = BASE_DIR / 'data' / 'data.json'

        if not data_file_path.exists():
            with open(data_file_path, 'w', encoding='utf-8') as new_file:
                new_file.write('{}')

        with open(data_file_path, 'r', encoding='utf-8') as existing_file:
            try:
                entries = json.load(existing_file)
            except json.JSONDecodeError:
                entries = {}

        entries.update(text_message)

        with open(data_file_path, 'w', encoding='utf-8') as file:
            json.dump(entries, file, ensure_ascii=False, indent=2)

    except ValueError as err:
        logging.error(f"Error parsing data {decoded_data}: {err}")
    except OSError as err:
        logging.error(f"Error writing data {decoded_data}: {err}")


def run_socket_server(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ip, port
    print(server_address)
    server_socket.bind(server_address)

    try:
        while True:
            data, _ = server_socket.recvfrom(BUFFER_SIZE)
            save_data(data)

    except KeyboardInterrupt:
        logging.info("Socket server stopped")
    finally:
        server_socket.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")

    thread_http_server = Thread(target=run_http_server)
    thread_http_server.start()

    thread_socket_server = Thread(target=run_socket_server, args=(SERVER_IP, SERVER_PORT_SOCKET))
    thread_socket_server.start()
