import socket
import json

sock = socket.socket()
sock.connect(('localhost', 9080))
string = input()
sock.send(bytes(string, 'utf-8'))

result = json.loads(str(sock.recv(4096), 'utf-8'))
sock.close()

print(result)
