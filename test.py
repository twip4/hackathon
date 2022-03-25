import socket

hote = "www.paulbaudinot.fr"
port = 5000

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.connect((hote, port))
print("Connection on".format(port))

mystring = "JOIN TEST"
b = mystring.encode('utf-8')

socket.send(b)

print("Close")
socket.close()