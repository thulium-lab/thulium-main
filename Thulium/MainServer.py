import socketserver

WM = 'WM'
LOCK_BY_WM = 'LOCK_BY_WM'
def WM_handler(msg,data):
    if len(msg) != 3:
        return None
    channel, meas_time, freq = msg
    if WM not in data:
        data[WM] = {}
    data[WM][channel] = (float(meas_time.strip()),float(freq.strip()))
    # return '%.7f %.7f'%(data[WM][channel][0], data[WM][channel][1])
    return None

def lock_by_WM(msg,data):
    if len(msg) != 1 or WM not in data:
        return ''
    channel = msg[0]
    if channel not in data[WM]:
        return ''
    return '%.7f %.7f'%(data[WM][channel][0], data[WM][channel][1])

handlers ={WM:WM_handler,
           LOCK_BY_WM:lock_by_WM}
debug = True

class MyUDPHandler(socketserver.BaseRequestHandler):
    """
    This class works similar to the TCP handler class, except that
    self.request consists of a pair of data and client socket, and since
    there is no connection the client address must be given explicitly
    when sending data back via sendto().
    """
    all_data = {}
    def handle(self):
        data = self.request[0].strip().decode('utf-8')
        socket = self.request[1]
        prog, *msg = data.split()
        if debug:
            print("{} wrote:".format(self.client_address))
            print(prog,msg)
        if prog in handlers:
            answer = handlers[prog](msg,self.all_data)
            print('Answer:',answer)
            if answer != None:
                socket.sendto(bytes(answer, "utf-8"), self.client_address)
        else:
            print('No handler for ' + prog)
            socket.sendto(bytes('BAD', "utf-8"), self.client_address)
if __name__ == "__main__":
    HOST, PORT = "localhost", 9999
    server = socketserver.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()