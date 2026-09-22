import pygame
import config

box = pygame.image.load("assets/box.png")
options = pygame.image.load("assets/options.png")
pikachu = pygame.image.load("assets/pikachu.png")
charizard = pygame.image.load("assets/charizard.png")
logs = []
chosen_option = 0


class Trainer:
    def __init__(self, name):
        self.name = name
        self.moves = ["ATTACK", "DEFEND", "POTION", "RETREAT"]


class Move:
    def __init__(self, name, user, player, enemy):
        self.name = name
        self.user = user
        self.player = player
        self.enemy = enemy


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


def draw(screen):
    sprite = scale_sprite(box, 5, (0, 380))
    screen.blit(sprite[0], sprite[1])


def chosen(option):
    if chosen_option == option:
        return ">"
    else:
        return "-"


def draw_str(screen, font):
    draw(screen)
    screen.blit(
        font.render(
            f"{chosen(0)} ATTACK\n{chosen(1)} DEFEND\n{chosen(2)} POTION\n{chosen(3)} RETREAT",
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
    screen.blit(font.render("PIKACHU", False, "black"), (410, 250))
    screen.blit(font.render("HP: 100/100", False, "black"), (410, 300))
    screen.blit(font.render("CHARIZARD", False, "black"), (70, 20))
    screen.blit(font.render("HP: 100/100", False, "black"), (70, 70))
