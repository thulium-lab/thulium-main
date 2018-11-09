import socket
import sys
import time

HOST, PORT = "localhost", 9999
# data = " ".join(sys.argv[1:])

# SOCK_DGRAM is the socket type to use for UDP sockets
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# As you can see, there is no connect() call; UDP has no connections.
# Instead, data is directly sent to the recipient via sendto().
for i in range(10):

    sock.sendto(bytes('WM 402 %i 12 \n'%(i), "utf-8"), (HOST, PORT))
    print('Send: ','WM 402 %i 12 \n'%(i))
    # received = str(sock.recv(1024), "utf-8")
    # print("Received: {}".format(received))
    time.sleep(2)