import pygame
import battle
from utils import scale_sprite

pkmn_icon = pygame.image.load("assets/pkmn_icon.png")
selected = 0


def draw(screen, font):
    player_pokemon = battle.player_trainer.pokemon
    gap = 90
    for p in range(len(player_pokemon)):
        player_pkmn = player_pokemon[p]
        arrow_pos = 40 if selected == p else 30
        screen.blit(font.render(">", False, "black"), (arrow_pos, 20 + p * gap))
        icon = scale_sprite(pkmn_icon, 4, (60, p * gap))
        screen.blit(font.render(player_pkmn.name, False, "black"), (160, 10 + p * gap))
        screen.blit(icon[0], icon[1])
        screen.blit(
            font.render(str(player_pkmn.hp) + " HP", False, "black"),
            (450, 10 + p * gap),
        )


def draw_pkmn_stats(screen, font):
    scaled = scale_sprite(battle.vert_box, 8, (900 - 260, -50))
    screen.blit(scaled[0], scaled[1])
    this_pkmn = battle.player_trainer.pokemon[selected]
    screen.blit(font.render(this_pkmn.moves[0].name, False, "black"), (680, 10))
    screen.blit(font.render(str(this_pkmn.moves[0].value), False, "black"), (880, 10))

    screen.blit(font.render(this_pkmn.moves[1].name, False, "black"), (680, 70))
    screen.blit(font.render(str(this_pkmn.moves[1].value), False, "black"), (880, 70))

    screen.blit(font.render(this_pkmn.moves[2].name, False, "black"), (680, 130))
    screen.blit(font.render(str(this_pkmn.moves[2].value), False, "black"), (880, 130))

    screen.blit(font.render(this_pkmn.moves[3].name, False, "black"), (680, 190))
    screen.blit(font.render(str(this_pkmn.moves[3].value), False, "black"), (880, 190))


def next_pokemon():
    battle.player_trainer.pokemon[selected] = battle.pokemons[
        battle.player_trainer.pokemon[selected].idx + 1
    ]


def prev_pokemon():
    battle.player_trainer.pokemon[selected] = battle.pokemons[
        battle.player_trainer.pokemon[selected].idx - 1
    ]
