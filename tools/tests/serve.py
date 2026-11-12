# Tiny local web server for tests, started inside each test script
import threading, http.server, socketserver, functools
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
def start(root, port):
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', port), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
