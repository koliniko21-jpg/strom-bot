
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Создаем простой веб-сервер, чтобы Render видел открытый порт
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

if __name__ == "__main__":
    # Запускаем веб-сервер в фоновом потоке
    threading.Thread(target=run_http_server, daemon=True).start()
    
    # Запускаем вашего бота
    os.system("python bot.py")
