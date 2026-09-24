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
showing_log = True
last_rival_turn = 0

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

        simulate_move(self, enemy, move_idx)

        b_text = self.name + " used " + move.name + "!\n(" + str(move.value) + ")"

        move_entry = MoveLogEntry(move, self.name)
        logs.append(move_entry)

        return (b_text, logs)


player = Pokemon(
    "PIKACHU",
    100,
    [
        Move("ATTACK", 5, 10),
        Move("DEFEND", 5, 10),
        Move("HEAL", 5, 10),
        Move("REST", -1, -1),  # -1 PP means infinite move
    ],
)
rival = Pokemon(
    "CHARIZARD",
    100,
    [
        Move("ATTACK", 5, 10),
        Move("DEFEND", 5, 10),
        Move("HEAL", 5, 10),
        Move("REST", -1, -1),  # -1 PP means infinite move
    ],
)

# Baru Minimax
from math import inf


def available_moves(pokemon):
    return [
        index
        for index, move in enumerate(pokemon.moves)
        if move.pp != 0
    ]


def simulate_move(actor, enemy, move_idx):
    move = actor.moves[move_idx]

    if move_idx == 0:  # ATTACK
        damage = max(move.value - enemy.defense, 0)
        enemy.hp = max(enemy.hp - damage, 0)
        enemy.defense = max(enemy.defense - move.value, 0)

    elif move_idx == 1:  # DEFEND
        actor.defense += move.value

    elif move_idx == 2:  # HEAL
        actor.hp = min(actor.hp + move.value, actor.max_hp)

    elif move_idx == 3:  # REST
        for actor_move in actor.moves:
            actor_move.pp = actor_move.max_pp

    if move.pp != -1:
        move.pp -= 1


def evaluate(rival_state, player_state):
    if player_state.hp <= 0:
        return 100000

    if rival_state.hp <= 0:
        return -100000

    return (
        (rival_state.hp - player_state.hp) * 10
        + (rival_state.defense - player_state.defense) * 2
    )


def minimax(rival_state, player_state, depth, maximizing):
    if depth == 0 or rival_state.hp <= 0 or player_state.hp <= 0:
        return evaluate(rival_state, player_state)

    if maximizing:
        best_score = -inf

        for move_idx in available_moves(rival_state):
            next_rival = deepcopy(rival_state)
            next_player = deepcopy(player_state)

            simulate_move(next_rival, next_player, move_idx)

            score = minimax(
                next_rival,
                next_player,
                depth - 1,
                False,
            )

            best_score = max(best_score, score)

        return best_score

    best_score = inf

    for move_idx in available_moves(player_state):
        next_rival = deepcopy(rival_state)
        next_player = deepcopy(player_state)

        simulate_move(next_player, next_rival, move_idx)

        score = minimax(
            next_rival,
            next_player,
            depth - 1,
            True,
        )

        best_score = min(best_score, score)

    return best_score


def choose_rival_move(depth=2):
    best_move = 0
    best_score = -inf

    for move_idx in available_moves(rival):
        simulated_rival = deepcopy(rival)
        simulated_player = deepcopy(player)

        simulate_move(
            simulated_rival,
            simulated_player,
            move_idx,
        )

        score = minimax(
            simulated_rival,
            simulated_player,
            depth - 1,
            False,
        )

        if score > best_score:
            best_score = score
            best_move = move_idx

    return best_move

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

    scaled = scale_sprite(charizard, 4, (410, 10))
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
            font.render(f"{log.player.hp}", False, (0, 205, 0)),
            (900 - 130, y),
        )
        screen.blit(
            font.render("/", False, "black"),
            (900 - 50, y),
        )
        screen.blit(
            font.render(f"{log.rival.hp}", False, (205, 0, 0)),
            (900 - 10, y),
        )
        text = font.render(f"{log.move.name}", False, "black")
        side = text.get_rect(topleft=(900 - 230, y + 40))
        if log.user == "CHARIZARD":
            side = text.get_rect(topright=(900 + 40, y + 40))
        screen.blit(text, side)


def draw_ai_brain(screen, font):
    scaled = scale_sprite(vert_box, 8, (900 - 260, -50))
    screen.blit(scaled[0], scaled[1])

    screen.blit(
        font.render(f"AI (TURN {last_rival_turn}):", False, "black"),
        (675, 0),
    )
