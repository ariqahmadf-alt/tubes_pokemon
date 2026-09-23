import pygame
import config
from copy import deepcopy

box = pygame.image.load("assets/box.png")
vert_box = pygame.image.load("assets/vert_box.png")
options = pygame.image.load("assets/options.png")
pikachu = pygame.image.load("assets/pikachu.png")
charizard = pygame.image.load("assets/charizard.png")
move_logs = []
chosen_move = 0
battle_text = ""
chosen_log = 0

# 0 - player chooses move
# 1 - player uses move
# 2 - enemy chooses move
# 3 - enemy uses move
turn_step = 0


class MoveLogEntry:
    def __init__(self, move, user):
        self.move = move
        self.user = user
        self.player = deepcopy(player)
        self.rival = deepcopy(rival)


class Move:
    def __init__(self, name, pp, value):
        self.name = name

        # power points
        self.pp = pp
        self.max_pp = pp

        # generic value corresponding to the move.
        # eg; ATTACK move of 10 will reduce HP by 10
        self.value = value


class Pokemon:
    def __init__(self, name, hp, moves):
        self.name = name
        self.hp = hp
        self.defense = 0
        self.max_hp = hp
        self.moves = moves

    def choose_move(self, move_idx, b_text, logs, enemy):
        move = self.moves[move_idx]
        match move_idx:
            case 0:
                enemy.hp -= move.value - enemy.defense
            case 1:
                self.defense += move.value
            case 2:
                self.hp = min(self.hp + move.value, self.max_hp)
            case 3:
                for move in self.moves:
                    move.pp = move.max_pp
        # use PP if it's not an infinite move
        if move.pp != -1:
            move.pp -= 1
        b_text = self.name + " used " + move.name + "!"
        move_entry = MoveLogEntry(move, self.name)
        logs.append(move_entry)
        return (b_text, logs)


player = Pokemon(
    "PIKACHU",
    100,
    [
        Move("ATTACK2", 5, 10),
        Move("DEFEND", 5, 10),
        Move("HEAL", 5, 10),
        Move("REST", -1, -1),  # -1 PP means infinite move
    ],
)
rival = Pokemon(
    "CHARIZARD",
    100,
    [
        Move("ATTACK1", 5, 10),
        Move("DEFEND", 5, 10),
        Move("HEAL", 5, 10),
        Move("REST", -1, -1),  # -1 PP means infinite move
    ],
)


def printLogs():
    for log in move_logs:
        print(log.name, log.user)


def scale_sprite(sprite, scale, pos, rot=0):
    scaled = pygame.transform.scale(
        sprite,
        (
            sprite.get_width() * scale,
            sprite.get_height() * scale,
        ),
    )
    scaled = pygame.transform.rotate(scaled, rot)
    rect = scaled.get_rect()
    rect.x = pos[0]
    rect.y = pos[1]
    return (scaled, rect)


# cycle thru moves when pressing up/down
def inc_chosen_move(inc, co):
    co += inc
    if co > 3:
        co = 0
    elif co < 0:
        co = 3
    return co


def draw_moves(screen, font):
    sprite = scale_sprite(box, 5, (0, 380))
    screen.blit(sprite[0], sprite[1])

    def chosen(move):
        str = ""
        if chosen_move == move:
            str = ">"
        else:
            str = "-"
        str += moves[move].name
        if moves[move].pp != -1:
            str += f"  ({moves[move].pp}/{moves[move].max_pp})"

        return str

    moves = player.moves

    screen.blit(font.render(chosen(0), False, "black"), (30, 410))
    screen.blit(font.render(chosen(1), False, "black"), (30, 450))
    screen.blit(font.render(chosen(2), False, "black"), (30, 490))
    screen.blit(font.render(chosen(3), False, "black"), (30, 530))


def draw_battle_text(screen, font):
    sprite = scale_sprite(box, 5, (0, 380))
    screen.blit(sprite[0], sprite[1])

    screen.blit(
        font.render(
            battle_text,
            False,
            "black",
        ),
        (30, 410),
    )


def draw_pokemon(screen):
    scaled = scale_sprite(pikachu, 4, (60, 132))
    screen.blit(scaled[0], scaled[1])

    scaled = scale_sprite(charizard, 4, (410, 0))
    screen.blit(scaled[0], scaled[1])


def draw_stats(screen, font):
    screen.blit(font.render(player.name, False, "black"), (380, 250))
    screen.blit(
        font.render(f"HP: {player.hp}/{player.max_hp}", False, "black"), (380, 300)
    )
    screen.blit(font.render(rival.name, False, "black"), (70, 20))
    screen.blit(font.render(f"HP: {rival.hp}/{rival.max_hp}", False, "black"), (70, 70))


def draw_logs(screen, font):
    scaled = scale_sprite(vert_box, 8, (900 - 260, -50))
    screen.blit(scaled[0], scaled[1])

    screen.blit(
        font.render("MOVE LOG:", False, "black"),
        (675, 0),
    )

    for i in range(len(move_logs)):
        if i < chosen_log:
            continue
        y = 40 + ((i - chosen_log) * 110)
        log = move_logs[i]
        screen.blit(
            font.render(f"{i + 1}", False, "black"),
            (900 - 230, y),
        )
        screen.blit(
            font.render(f"{log.player.hp}/{log.rival.hp}", False, "black"),
            (900 - 110, y),
        )
        text = font.render(f"{log.move.name}", False, "black")
        side = text.get_rect(topleft=(900 - 230, y + 40))
        if log.user == "CHARIZARD":
            side = text.get_rect(topright=(900 + 40, y + 40))
        screen.blit(text, side)
