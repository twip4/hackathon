import pygame, sys, socket, struct
from pygame.locals import *

import time

from random import randint, choice, seed
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, List, Dict, Tuple, Set

hote = "localhost"
port = 5000

position = {}

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.connect((hote, port))
print("Connection on".format(port))

def ERROR(msg: str) -> None:
    print("[ERROR] {}".format(msg))
    exit()

def send(message):
    message = message.encode()
    socket.send(struct.pack("i", len(message)) + message)

def recv():
    try:
        size = struct.unpack("i", socket.recv(struct.calcsize("i")))[0]
        data = ""
        while len(data) < size:
            msg = socket.recv(size - len(data))
            if not msg:
                ERROR("Problème lors de la reception du socket {}".format(socket))
            data += msg.decode()
        return data
    except:
        exit()


def parse_message(msg: str) -> List[str]:
    return [s.upper() for s in msg.split("|")]



def recuData():
    data = recv()
    if data == "Au tour de l'équipe TEST" :
        send("STAY")

send("JOIN|EQUIPE BOT")

while True :
    recuData()
    time.sleep(0.5)
