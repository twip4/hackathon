import pygame, sys, socket, struct
from pygame.locals import *

from random import randint, choice, seed
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, List, Dict, Tuple, Set

# JEU
NBJOUEUR = 2
NBCASES = 5
BASE_UNITE_SIZE = 12
MAX_TURN = 30
EVENT_PROBA = 5 # Pourcentage
WAIT_TIME = 1000 # Temps à attendre entre chaque action d'un joueur (pour voir ce qu'il se passe)

# AFFICHAGE
HEIGHT = 1000
WIDTH = HEIGHT+400

SIZE_LIEN = (0.35 * (HEIGHT - 40)) / NBCASES
SIZE_CASE = (0.65 * (HEIGHT - 40)) / NBCASES
TOTAL_SIZE_LEN = SIZE_LIEN + SIZE_CASE

# COULEURS
WHITE = (246, 231, 216)
BLUE = (77, 119, 255)
RED = (249, 7, 22)
BLACK = (0, 0, 0)

def ERROR(msg: str) -> None:
    print("[ERROR] {}".format(msg))
    exit()

def send(socket, message):
    socket.send(struct.pack("i", len(message)) + message)

def recv(socket):
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

def build_message(key: str, params: List[Any]) -> bytes:
    msg = key + "|" + '|'.join(map(str, params))
    print("[LOG/MSG] " + msg)
    return msg.encode()

def parse_message(msg: str) -> List[str]:
    return [s.upper() for s in msg.split("|")]

class CASE_FUNCTION:
    NONE = 0
    MULT = 2
    TELEPORT = 3
    BLOCK = 4
    PASS_TURN = 5
    PASS_NEXT_TURN = 6
    DIVIDE = 7

Pos = Tuple[int, int]

@dataclass(eq = True, frozen = True)
class Lien:
    from_case: Pos
    to_case: Pos

    @property
    def direction(self) -> Pos:
        return (self.to_case[0] - self.from_case[0], self.to_case[1] - self.from_case[1])

    @property
    def width(self) -> Tuple[float, float]:
        return (1, 0.35) if self.direction[0] else (0.35, 1)

@dataclass
class Case:
    posx: int
    posy: int
    liens: Set[Lien] = field(default_factory=set)
    function: int = CASE_FUNCTION.NONE
    turn_left: int = 0
    linked_to = None
    pastille = None

    def __post_init__(self) -> None:
        voisins = [(self.posx + x, self.posy + y) for x, y in [(-1, 0), (0, -1), (1, 0), (0, 1)]]
        for vx, vy in voisins:
            if 0 <= vx < NBCASES and 0 <= vy < NBCASES:
                self.liens.add(Lien(self.pos, (vx, vy)))

    @property
    def pos(self) -> Pos:
        return (self.posx, self.posy)

@dataclass
class Unite:
    unite_id: int
    pos: Pos
    size: int

    @property
    def posx(self) -> int:
        return self.pos[0]

    @property
    def posy(self) -> int:
        return self.pos[1]

class Joueur:
    def __init__(self, joueur_id: int, nom: str, default_pos: Pos, color: Tuple[int, int, int], nb_case: int) -> None:
        self.id = joueur_id
        self.nom = nom
        self.color = color
        self.nb_unite = 0
        self.list_unite: Dict[int, Unite] = {0: Unite(self.nb_unite, default_pos, BASE_UNITE_SIZE)}
        self.can_play = True

    def get_unite_by_id(self, idUnite: int) -> Unite:
        res = self.list_unite.get(idUnite)
        if res:
            return res

        print("[ERROR] Aucune unitée avec l'id {} pour le joueur {}".format(idUnite, self.id))
        exit()

    def get_unite_at(self, pos: Pos) -> Optional[Unite]:
        for unite in self.list_unite.values():
            if unite.pos == pos:
                return unite
        return None

    def get_all_unite_pos(self) -> List[Pos]:
        return [unite.pos for unite in self.list_unite.values()]

    def add_unit(self, pos: Pos, size: int) -> None:
        self.nb_unite += 1
        self.list_unite[self.nb_unite] = Unite(self.nb_unite, pos, size)

    def move_unit(self, unite: Unite, new_pos: Pos, size: int) -> None:
        if size == unite.size:
            unite.pos = new_pos
        else:
            unite.size -= size
            self.add_unit(new_pos, size)

    def transfert_unit(self, unite_from: Unite, unite_to: Unite, size: int) -> None:
        unite_from.size -= size
        if unite_from.size <= 0:
            self.kill_unite(unite_from)
        unite_to.size += size

    def kill_unite(self, unite: Unite) -> None:
        del self.list_unite[unite.unite_id]

    def army_total(self):
        return sum(map(lambda x: x.size, self.list_unite.values()))

    def __repr__(self) -> str:
        nb_army = self.army_total()
        name = self.nom
        if len(name) > 10:
            name = name[:7] + "..."
        return "{} : {}".format(name, nb_army)

class Game:
    def __init__(self) -> None:
        self.positionJoueur = [(0, 0), (NBCASES - 1, NBCASES - 1), (NBCASES - 1, 0), (0, NBCASES - 1)]

        #DEFINE: Style
        self.colorJoueur = [(0, 255, 0), (255, 160, 122), (240, 15, 220), (0, 0, 0)]

        #DEFINE: Reseau
        self.serveur: Serveur = Serveur()
        self.serveur.getJoueurs()

        # Annonce du début de la partie
        print("[INFO] Tous les joueurs ont rejoins, début de la partie")
        for i, player in enumerate(self.serveur.players):
            send(player, build_message("NEWGAME", [NBCASES, NBJOUEUR, i, *self.positionJoueur[i]]))

        #DEFINE: Joueurs
        self.listJoueurs = [Joueur(i, self.serveur.team_name[i], self.positionJoueur[i], self.colorJoueur[i], NBCASES) for i in range(len(self.serveur.players))]

        #DEFINE: jeu
        self.list_cases = [[Case(i, j) for j in range(NBCASES)] for i in range(NBCASES)]
        self.proba_case_function = EVENT_PROBA
        self.listFonctionCase: List[str] = ["DIVIDE", "MULT", "NULL", "PASS", "ENNEMIPASS"]
        self.case_functions: Dict[int, Any] = {
            CASE_FUNCTION.MULT: self.mult,
            CASE_FUNCTION.TELEPORT: self.teleport,
            CASE_FUNCTION.PASS_TURN: self.pass_turn,
            CASE_FUNCTION.PASS_NEXT_TURN: self.pass_next_turn,
            CASE_FUNCTION.DIVIDE: self.divide
        }

    def in_game(self, pos: Pos) -> bool:
        return pos[0] >= 0 and pos[0] < NBCASES and pos[1] >= 0 and pos[1] < NBCASES

    def get_case_at(self, pos: Pos) -> Optional[Case]:
        if pos is None or not self.in_game(pos):
            return None
        return self.list_cases[pos[0]][pos[1]]

    def moveUnite(self, player_id: int, params: List[str]) -> None:
        joueur = self.listJoueurs[player_id]
        unite = joueur.get_unite_by_id(int(params[0]))

        if not unite:
            ERROR("Aucune unite avec l'id {} pour le joueur {}".format(params[0], player_id))

        if not joueur.can_play:
            joueur.can_play = True
            return

        ##MOUVEMENT
        to_move_count = int(params[1])

        if to_move_count > unite.size:
            ERROR('{} : déplacement de {} sur {} max'.format(player_id, to_move_count, unite.size))
            exit()

        direction = params[2]
        new_pos = self.get_new_pos(unite.pos, direction)
        if new_pos is None:
            exit()
        case = self.get_case_at(new_pos)
        if case is None:
            ERROR("Case en dehors du plateau")
            exit()

        # S'il y a un événement spécial sur la prochaine case du joueur
        # On regarde en premier les pre-événements
        if case.function == CASE_FUNCTION.BLOCK:
            # Si un joueur essaye d'aller sur une case qui est bloquée, c'est une erreur
            ERROR("Déplacement sur une case bloquée")
        
        # Si on déplace qu'une partie de nos unités
        if to_move_count <= unite.size:
            unite_owner, unite_at_new_pos = self.get_unite_at_position(new_pos)
            if unite_owner and unite_at_new_pos:
                if unite_owner == joueur:
                    joueur.transfert_unit(unite, unite_at_new_pos, to_move_count)
                # On se déplace sur une unité adverse
                else:
                    # Si l'adversaire à plus d'unité, alors il reste
                    if unite_at_new_pos.size > to_move_count:
                        unite_at_new_pos.size -= to_move_count
                        joueur.kill_unite(unite)
                    # Si on a plus d'unite que l'adversaire, alors on prend sa place
                    elif unite_at_new_pos.size < to_move_count:
                        unite.size -= unite_at_new_pos.size
                        unite.pos = new_pos
                        unite_owner.kill_unite(unite_at_new_pos)
                    # Les deux unites on la même taille, les deux meurent
                    else:
                        unite_owner.kill_unite(unite_at_new_pos)
                        joueur.kill_unite(unite)
            # S'il n'y a pas déjà une unité à cette position
            else:
                joueur.move_unit(unite, new_pos, to_move_count)

        # S'il y a une fonction sur la case
        if case.function:
            self.case_functions[case.function](joueur, case, unite)

    def divide(self, joueur: Joueur, case: Case, unite: Unite) -> None:
        unite.size = max(1, unite.size // 2)
        case.function = CASE_FUNCTION.NONE

    def mult(self, joueur: Joueur, case: Case, unite: Unite) -> None:
        unite.size *= 2
        case.function = CASE_FUNCTION.NONE

    def pass_turn(self, joueur: Joueur, case: Case, unite: Unite) -> None:
        joueur.can_play = False
        case.function = CASE_FUNCTION.NONE

    def teleport(self, joueur: Joueur, case: Case, unite: Unite) -> None:
        other_case = case.linked_to
        unite.pos = other_case.pos

        case.function = CASE_FUNCTION.NONE
        other_case.function = CASE_FUNCTION.NONE

    def pass_next_turn(self, joueur: Joueur, case: Case, unite: Unite) -> None:
        self.listJoueurs[(joueur.id + 1) % len(self.listJoueurs)].can_play = False
        case.function = CASE_FUNCTION.NONE

    # Renvoie l'unité à la position donnée
    def get_unite_at_position(self, pos: Pos) -> Tuple[Optional[Joueur], Optional[Unite]]:
        for joueur in self.listJoueurs:
            unite = joueur.get_unite_at(pos)
            if unite:
                return (joueur, unite)
        return (None, None)

    def actualiseCases(self) -> Optional[bytes]:
        casesOccupes = []
        for joueur in self.listJoueurs:
            casesOccupes.extend(joueur.get_all_unite_pos())

        casesVides = []
        for i in range(NBCASES):
            for j in range(NBCASES):
                case = self.list_cases[i][j]
                if not (i, j) in casesOccupes and not case.function:
                    casesVides.append(case)

        if len(casesVides) == 0:
            return None

        if randint(0, 100) <= self.proba_case_function:
            random_case = choice(casesVides)
            random_function_id = randint(2, 7)
            random_case.function = random_function_id
            params = [*random_case.pos]

            if random_function_id == CASE_FUNCTION.TELEPORT:
                random_case.turn_left = -1
                pastille = (randint(0, 255), randint(0, 255), randint(0,255))
                casesVides.remove(random_case)
                if len(casesVides) == 0:
                    random_case.function = CASE_FUNCTION.NONE
                    return None
                other_case = choice(casesVides)
                other_case.function = random_function_id

                random_case.linked_to = other_case
                other_case.linked_to = random_case

                random_case.pastille = pastille
                other_case.pastille = pastille

                params.append(other_case.posx)
                params.append(other_case.posy)
            elif random_function_id == CASE_FUNCTION.BLOCK:
                random_temps = randint(1, 5)
                params.append(str(random_temps))
                random_case.turn_left = random_temps
            msg = build_message(str(random_function_id), params)
            return msg
        return None

    def get_new_pos(self, depart: Pos, direction: str) -> Pos:
        if direction == "N":
            return (depart[0], depart[1] - 1)
        elif direction == "S":
            return (depart[0], depart[1] + 1)
        elif direction == "E":
            return (depart[0] + 1, depart[1])
        elif direction == "W":
            return (depart[0] - 1, depart[1])

        ERROR("Direction {} non valide !".format(direction))


    # Le joueur ne fait rien
    def stay(self, player_id: int, params: List[str]) -> None:
        pass

    def handle_command(self, player_id: int, command: str, params: List[str]) -> None:
        commands: Dict[str, Callable[[int, List[str]], None]]
        commands = {'MOVE': self.moveUnite, "STAY": self.stay}
        command_to_call = commands.get(command)
        if command_to_call:
            command_to_call(player_id, params)
        else:
            ERROR("Commande '{}' invalide".format(command))

class Interface(Game):
    def __init__(self) -> None:
        super().__init__()
        pygame.init()        
        self.pause = False 
        self.nb_tour = 0
        self.init()

        self.last_actions: List[List[bytes]] = [[] for i in range(len(self.serveur.players))]
        self.run()

    def init(self) -> None:
        self.display = pygame.display.set_mode((WIDTH, HEIGHT), 0, 32)
        self.sprite_soldier = pygame.image.load("sprite/one_soldier.png").convert()
        self.dicoSpriteCaseFunction = {
            CASE_FUNCTION.MULT: pygame.image.load("sprite/mult.png").convert_alpha(), 
            CASE_FUNCTION.TELEPORT: pygame.image.load("sprite/teleport.png").convert_alpha(), 
            CASE_FUNCTION.BLOCK: pygame.image.load("sprite/block.png").convert_alpha(), 
            CASE_FUNCTION.PASS_TURN: pygame.image.load("sprite/pass.png").convert_alpha(), 
            CASE_FUNCTION.PASS_NEXT_TURN: pygame.image.load("sprite/ennemiepass.png").convert_alpha(),
            CASE_FUNCTION.DIVIDE: pygame.image.load("sprite/divide.png").convert_alpha()
        }
        self.font = pygame.font.Font(None, 76)
        self.font_unite = pygame.font.Font(None, int(SIZE_CASE*0.8))

    # Début de la partie une fois que tous les joueurs ont rejoins
    def run(self) -> None:
        self.render()
        pygame.time.wait(WAIT_TIME)

        # Chaque tour de boucle représente un tour de jeu
        while not self.is_game_over():
            print('[LOG] New turn')
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:    
                        self.pause = not self.pause

            if self.pause:
                pygame.time.wait(16)
                continue

            self.update()
            pygame.time.wait(WAIT_TIME)
            self.render()
            pygame.display.update()

            new_event = self.actualiseCases()
            if new_event:
                for last_actions in self.last_actions:
                    last_actions.append(new_event)

            self.nb_tour += 1

        self.end_game()

    def end_game(self):
        self.render()
        self.display.blit(self.font.render("Terminé !", True, (255, 0, 0)), (WIDTH - self.font.size("Terminé !")[0] - 100, HEIGHT / 2))
        pygame.display.update()
        print('[LOG] Partie terminée !!')
        still_alive = self.get_players_alive()

        if len(still_alive) == 0:
            print("[LOG] Personne n'a gagné, EGALITE !")
        elif len(still_alive) > 0:
            print("Félicitation à l'équipe {} qui est gagnante de cette partie !".format(still_alive[0].nom))
        elif self.nb_tour >= MAX_TURN:
            print("[LOG] Personne n'a gagné, EGALITE !")

        # On attend que le joueur quitte l'application
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                    pygame.quit()
                    sys.exit()

    def get_players_alive(self):
        return list(filter(lambda x: x.army_total() > 0, self.listJoueurs))

    def is_game_over(self):
        # S'il ne reste aucun joueur ou qu'un seul encore en vie
        return self.nb_tour >= MAX_TURN or len(list(filter(lambda x: x.army_total() > 0, self.listJoueurs))) <= 1

    def affichageJoueur(self) -> None:
        for joueur in self.listJoueurs:
            for i in range(NBCASES):
                for unite_id, unite in joueur.list_unite.items():
                    x = 20 + unite.posx * TOTAL_SIZE_LEN
                    y = 20 + unite.posy * TOTAL_SIZE_LEN
                    size = unite.size // 4 + 1
                    for i in range(size):
                        self.display.blit(pygame.transform.scale(self.sprite_soldier, (SIZE_CASE / size, SIZE_CASE)), (x + i * SIZE_CASE/size, y))

                    self.display.blit(self.font_unite.render(str(unite.size), True, joueur.color), (x+(SIZE_CASE/3) , (y+(SIZE_CASE/2))))

            self.display.blit(self.font.render("{!r}".format(joueur), True, joueur.color), (WIDTH - 450, 25 + joueur.id * 75))

    def affichageDamier(self) -> None:
        self.display.fill(WHITE)
        for row in self.list_cases:
            for case in row:
                if not case:
                    continue

                x = 20 + case.posx * TOTAL_SIZE_LEN
                y = 20 + case.posy * TOTAL_SIZE_LEN

                for lien in case.liens:
                    draw_x, draw_y = (x, y)
                    idx = 1 - (lien.direction[0] != 0)

                    add = [SIZE_LIEN * lien.direction[idx], (SIZE_CASE / 2) - (SIZE_LIEN * lien.width[1 - idx] / 2)]
                    draw_x += add[idx]
                    draw_y += add[1 - idx]

                    if idx == 0:
                        off = [SIZE_CASE / 2, 0]
                    else:
                        off = [0, SIZE_CASE / 2]

                    pygame.draw.rect(self.display, RED, 
                            list(map(int, (draw_x, draw_y, SIZE_LIEN * lien.width[0] + off[0], SIZE_LIEN * lien.width[1] + off[1]))))

                if not case.function:
                    pygame.draw.rect(self.display, BLUE, list(map(int, (x, y, SIZE_CASE, SIZE_CASE))))
                else:
                    self.display.blit(pygame.transform.scale(self.dicoSpriteCaseFunction[case.function], (SIZE_CASE, SIZE_CASE)), (x, y))
                    if case.function == CASE_FUNCTION.TELEPORT:
                        pygame.draw.rect(self.display, case.pastille, list(map(int, (x, y, SIZE_CASE / 8, SIZE_CASE / 8))))

    def update(self) -> None:
        for player_id, player in enumerate(self.serveur.players):
            # Si le joueur est hors jeu
            if self.listJoueurs[player_id].army_total() == 0:
                continue
            # Si on passe le tour du joueur
            if not self.listJoueurs[player_id].can_play:
                print("[LOG] Le joueur {} ne peut pas jouer ce tour !".format(player_id))
                self.listJoueurs[player_id].can_play = True
                continue
            print("[LOG] Au tour de l'équipe {}".format(self.listJoueurs[player_id].nom))
            send(player, build_message("NEWTURN", [len(self.last_actions[player_id])]))
            for last_action in self.last_actions[player_id]:
                print("SENDING LAST ACTION " + last_action.decode())
                send(player, last_action)

            self.last_actions[player_id].clear()
            move = recv(player)
            if not move:
                ERROR("Erreur dans la reception du joueur {}".format(player_id))

            command, *params = parse_message(move)
            self.handle_command(int(player_id), command, params)
            for other_player_id, other_player in enumerate(self.serveur.players):
                if other_player_id != player_id:
                    if command == "MOVE":
                        msg = build_message("0", [player_id, *params])
                    elif command == "STAY":
                        msg = build_message("1", [player_id])
                    self.last_actions[other_player_id].append(msg)

            self.render()
            if self.is_game_over():
                self.end_game()

            pygame.time.wait(WAIT_TIME)
        
        for row in self.list_cases:
            for case in row:
                if case.turn_left > 0:
                    case.turn_left -= 1
                    if case.turn_left == 0:
                        case.function = CASE_FUNCTION.NONE

    def render(self) -> None:
        self.affichageDamier()
        self.affichageJoueur()
        pygame.display.update()

class Serveur:
    def __init__(self) -> None:
        PORT = 5000
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('', PORT)) 
        self.team_name: List[str] = []
        # Attente de la connexion des joueurs
        self.players: List[socket.socket] = []
        print("[INFO] SERVEUR STARTUP sur le port {}".format(PORT))

    def getJoueurs(self) -> None:
        print("[INFO] WAITING FOR PLAYER")
        while len(self.players) < NBJOUEUR:
            self.socket.listen(5)
            client, address = self.socket.accept()
            print("[INFO] {} connecté".format(address))
            response = recv(client)
            if not response:
                send(client, build_message("ERROR", ["Erreur dans la reception du message"]))
                client.close()
                continue

            command, *params = parse_message(response)
            if command != 'JOIN' or len(params) != 1:
                send(client, build_message("ERROR", ["Vous devez en premier JOIN avec un nom d'équipe"]))
                client.close()
                continue

            print("[INFO] Nouveau client accepté avec le nom {}".format(params[0]))
            self.players.append(client)
            self.team_name.append(params[0])

if __name__ ==  "__main__":
    Interface()
