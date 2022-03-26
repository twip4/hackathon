import pygame, sys, socket, struct
from pygame.locals import *

from random import randint, choice, random, seed
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
            return "move",(int(dataL[2]),int(dataL[3])),dataL[4],dataL[5],dataL[6],dataL[7]
        if dataL[1] == '1' :
            return "stay",(int(dataL[2]),int(dataL[3])),dataL[4]
        if dataL[1] == '2' :
            return "double",((int(dataL[2])),int(dataL[3]))
        if dataL[1] == '3' :
            return "tp",((int(dataL[2])),int(dataL[3])),((int(dataL[4])),int(dataL[5]))
        if dataL[1] == '4' :
            return "inacess",((int(dataL[2])),int(dataL[3])),dataL[4]
        if dataL[1] == '5' :
            return "freeze",((int(dataL[2])),int(dataL[3]))
        if dataL[1] == '6' :
            return "freezeAdv",((int(dataL[2])),int(dataL[3]))
        if dataL[1] == '7' :
            return "divis",((int(dataL[2])),int(dataL[3]))


ID_GROUPE = 0
NB_GROUPE = 1

class Soldats:
    def __init__(self,joueurId,groupeId,tuplePos,size):
        self.joueurId = joueurId
        self.groupeId = groupeId
        self.tuplePos = tuplePos
        self.size = size

    def getPos(self):
        return self.tuplePos
    
    def setPosSoldat(self,nouvellePos):
        self.tuplePos = nouvellePos

    def setSize(self,nouvelleSize):
        self.size -= nouvelleSize
    
    def getJoueurId(self):
        return self.joueurId

class Evenements:
    def __init__(self,posEvents,typeEvent,niveauEvent,tempsEvent):
        self.posEvents = posEvents
        self.typeEvent = typeEvent
        self.niveauEvent = niveauEvent
        self.tempsEvent = tempsEvent

    def getPosEvent(self):
        return self.posEvents

class Grille:
    def __init__(self,nbCases,soldatDepart):
        self.dicoRisk = self.constructionDico(nbCases)
        self.setCasesEnnemies = set()
        self.setCasesAllies = set()
        self.setCasesMalus = set()
        self.setCasesBonus = set()
        self.setCasesLibres = set(self.dicoRisk.keys())
        
        self.setCasesAllies.add(soldatDepart.getPos())
        #self.setCasesLibres.remove(soldatDepart.getPos())
    def constructionDico(self,nbCases):   
        dicoRisk = {}     
        for i in range(nbCases):
            for j in range(nbCases):
                dicoRisk[(i,j)] = [None]
        return dicoRisk

    def getEvents(self):
        return self.setCasesEnnemies
    
    def getSoldats(self):
        return self.setCasesAllies

    def voisinagePossibles(self,pos):
        ##pos est un tuple de int
        listePosPossibles = []
        listeVoisinsPossibles = [(pos[0]+1,pos[1]),(pos[0]-1,pos[1]),(pos[0],pos[1]+1),(pos[0],pos[1]-1)]
        print(listeVoisinsPossibles)  
        for posPossible in listeVoisinsPossibles:
            if posPossible in self.setCasesLibres:
                listePosPossibles.append(posPossible)
        return listePosPossibles

    def deplacementSoldat(self,soldat,newPos,newSoldat=False,sizeSoldat=None):
        if soldat.getJoueurId() != ID_GROUPE:    
            self.setCasesEnnemies.remove(soldat.getPos())
            self.setCasesLibres.add(soldat.getPos())
            soldat.setPosSoldat(newPos)
            self.setCasesLibres.remove(newPos)
            self.setCasesEnnemies.add(newPos)
        else:    
            #on regarde si un nouveau groupe de soldat est crée
            if newSoldat == True:
                soldatNouveau = soldat(ID_GROUPE,NB_GROUPES,newPos,sizeSoldat)
                #on diminue la taille du soldat 
                soldat.setSize(sizeSoldat)
                NB_GROUPES += 1

            else:
                print(self.setCasesAllies)
                self.setCasesAllies.remove(soldat.getPos())
                self.setCasesLibres.add(soldat.getPos())
                soldat.setPosSoldat(newPos)
                self.setCasesLibres.remove(newPos)
                self.setCasesAllies.add(newPos)

    def suppressionEvent(self,event):
        if event in self.setCasesMalus:
            self.setCasesMalus.remove(event)
        else:
            self.setCasesBonus.remove(event)
        self.setCasesLibres.add(event.getPosEvent())
    
    def mortSoldat(self,soldat):
        ##on regarde si c'est un ennemi ou un allié
        if soldat.getJoueurId() == ID_GROUPE:
            self.setCasesAllies.remove(soldat)
        else:
            self.setCasesEnnemies.remove(soldat)
        self.setCasesLibres.add(soldat.getPos())
    
    def addEvent(self,event):
        self.setCasesMalus.add(event.getPosEvent())
        self.setCasesLibres.remove(event.getPosEvent())

def verOu(tupleDepart,tupleCible):
    if tupleDepart[0] < tupleCible[0] :
        if tupleDepart[1] == tupleCible[1] :
            return "E"
        if tupleDepart[1] < tupleCible[1] :
            return choice(["E","S"])
        if tupleDepart[1] > tupleCible[1] :
            return choice(["E","N"])
    if tupleDepart[0] > tupleCible[0] :
        if tupleDepart[1] == tupleCible[1] :
            return "W"
        if tupleDepart[1] < tupleCible[1] :
            return choice(["W","S"])
        if tupleDepart[1] > tupleCible[1] :
            return choice(["W","N"])
    if tupleDepart[0] == tupleCible[0] :
        if tupleDepart[1] < tupleCible[1] :
            return "S"
        if tupleDepart[1] > tupleCible[1] :
            return "N"


send("JOIN|PAUL LE BG")


data = recuData()       
if data[0] == "start" :
    ID_GROUPE = int(data[2])
    SoldatsStart = Soldats(ID_GROUPE,int(data[2]),data[3],10)
    grille = Grille(int(data[1]),SoldatsStart)

listEvent = ["tp","inacess"]

while True :
    data = recuData()
    if data[0] == "turn" :
        pos = grille.voisinagePossibles(SoldatsStart.getPos())
        cible = choice(pos)
        print(cible)
        direction = verOu(SoldatsStart.getPos(),cible)
        print("MOVE|0|12|"+direction)
        nouvellePos = SoldatsStart.getPos()
        if direction == "N":
            nouvellePos = (nouvellePos[0],nouvellePos[1]-1)
        elif direction == "S":
            nouvellePos = (nouvellePos[0],nouvellePos[1]+1)
        elif direction == "W":
            nouvellePos = (nouvellePos[0]-1,nouvellePos[1])
        else:
            nouvellePos = (nouvellePos[0]+1,nouvellePos[1])            
        grille.deplacementSoldat(SoldatsStart,nouvellePos   )
        send("MOVE|0|12|"+direction)
    if data[0] in listEvent:
        event = Evenements(data[1],"nul",1,1000)
        grille.addEvent(event)
