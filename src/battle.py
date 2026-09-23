import pygame
import config
from copy import deepcopy

box = pygame.image.load("assets/box.png")
options = pygame.image.load("assets/options.png")
pikachu = pygame.image.load("assets/pikachu.png")
charizard = pygame.image.load("assets/charizard.png")
move_logs = []
chosen_move = 0
battle_text = ""


class MoveLogEntry:
    def __init__(self, name, user):
        self.name = name
        self.user = user
        self.player = deepcopy(player)
        self.rival = deepcopy(rival)


class Pokemon:
    def __init__(self, name, hp):
        self.name = name
        self.hp = hp
        self.defense = 0
        self.max_hp = hp
        self.moves = ["ATTACK", "DEFEND", "HEAL", "REST"]

    def choose_move(self, move_idx, b_text, logs, enemy):
        match move_idx:
            case 0:
                enemy.hp -= 30 - enemy.defense
                b_text = self.name + " attacked!"
            case 1:
                self.defense += 10
                b_text = self.name + " defended!"
            case 2:
                self.hp += 10
                b_text = self.name + " healed!"
            case 3:
                b_text = self.name + " rested!"
        move = MoveLogEntry(self.moves[move_idx], self.name)
        logs.append(move)
        return (b_text, logs)


player = Pokemon("PIKACHU", 100)
rival = Pokemon("CHARIZARD", 100)


def printLogs():
    for log in move_logs:
        print(log.name, log.user)


def scale_sprite(sprite, scale, pos):
    scaled = pygame.transform.scale(
        sprite,
        (
            sprite.get_width() * scale,
            sprite.get_height() * scale,
        ),
    )
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
        if chosen_move == move:
            return ">"
        else:
            return "-"

    screen.blit(
        font.render(
            f"{chosen(0)} ATTACK\n{chosen(1)} DEFEND\n{chosen(2)} POTION\n{chosen(3)} ---",
            False,
            "black",
        ),
        (30, 410),
    )


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
    screen.blit(font.render(player.name, False, "black"), (410, 250))
    screen.blit(
        font.render(f"HP: {player.hp}/{player.max_hp}", False, "black"), (410, 300)
    )
    screen.blit(font.render(rival.name, False, "black"), (70, 20))
    screen.blit(font.render(f"HP: {rival.hp}/{rival.max_hp}", False, "black"), (70, 70))
