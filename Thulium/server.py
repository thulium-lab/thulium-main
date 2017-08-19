import cv2

from tornado import websocket, web, ioloop, httpserver, gen

from PyQt5.QtCore import (QThread)

clients = []


class IndexHandler(web.RequestHandler):
    def get(self):
        self.render("index.html")


class WSHandler(websocket.WebSocketHandler):
    def open(self):
        if self not in clients:
            clients.append(self)

    def on_close(self):
        if self in clients:
            clients.remove(self)


class PyServer(QThread):
    def __init__(self, parent=None, signals=None, globals=None):
        super(PyServer, self).__init__()
        self.parent = parent
        self.signals = signals
        self.globals = globals
        return

    def run(self):
        self.signals.wvlChanged.connect(self.sendWvl)
        self.signals.newImageRead.connect(self.sendImg)
        app = web.Application([
            (r'/', IndexHandler),
            (r'/camera', WSHandler),
        ])
        http_server = httpserver.HTTPServer(app)
        http_server.listen(8000)
        ioloop.IOLoop.instance().start()

    def sendWvl(self, wvls):
        for client in clients:
            client.write_message('wvl ' + wvls, binary=False)
        return

    def sendImg(self):
        img = cv2.imencode('.jpg', self.globals['image'])[1].tostring()
        for client in clients:
            client.write_message(img, binary=True)
        return