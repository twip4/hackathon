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
    dataL = parse_message(data)
    if dataL[0] == "NEWGAME" :
        return "start",dataL[1],dataL[3],(int(dataL[4]),int(dataL[5]))
    if dataL[0] == "NEWTURN" :
        return "turn",dataL[1]
    if dataL[0] == "EVENT" :
        if dataL[1] == '0' :
            return "move",
        if dataL[1] == '1' :
        if dataL[1] == '2' :
        if dataL[1] == '3' :
        if dataL[1] == '4' :
        if dataL[1] == '5' :
        if dataL[1] == '6' :
        if dataL[1] == '7' :

        
        return "event",[dataL[1],dataL[2],dataL[3],dataL[4]]


send("JOIN|EQUIPE DE BG")

data = recuData()
if data[0] == "start" :
    print(data[1])
    for x in range(int(data[1])) :
        for y in range(int(data[1])) :
            position[x,y] = []


position[data[3]] = [int(data[2])]



print(position)
while True :


time.sleep(1)
