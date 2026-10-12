import pygame
import battle
from utils import scale_sprite

pkmn_icon = pygame.image.load("assets/pkmn_icon.png")
selected = 0


def draw(screen, font):
    player_pokemon = battle.player_trainer.pokemon
    rival_pokemon = battle.rival_trainer.pokemon

    # player's pokemon
    screen.blit(font.render("PLAYER:", False, "black"), (10, 0))
    gap = 70
    player_y = 50
    for p in range(len(player_pokemon)):
        player_pkmn = player_pokemon[p]
        arrow_pos = 40 if selected == p else 30
        screen.blit(
            font.render(">", False, "black"), (arrow_pos, player_y + 10 + p * gap)
        )
        icon = scale_sprite(pkmn_icon, 4, (60, player_y - 10 + p * gap))
        screen.blit(
            font.render(player_pkmn.name, False, "black"), (160, player_y + p * gap)
        )
        screen.blit(icon[0], icon[1])
        screen.blit(
            font.render(str(player_pkmn.hp) + " HP", False, "black"),
            (450, player_y + p * gap),
        )

    # rival's pokemon
    screen.blit(font.render("RIVAL:", False, "black"), (10, 300))
    rival_y = 350
    for p in range(len(rival_pokemon)):
        rival_pkmn = rival_pokemon[p]
        arrow_pos = 40 if selected == p else 30
        icon = scale_sprite(pkmn_icon, 4, (60, rival_y - 10 + p * gap))
        screen.blit(
            font.render(rival_pkmn.name, False, "black"), (160, rival_y + p * gap)
        )
        screen.blit(icon[0], icon[1])
        screen.blit(
            font.render(str(rival_pkmn.hp) + " HP", False, "black"),
            (450, rival_y + p * gap),
        )


def draw_pkmn_stats(screen, font):
    scaled = scale_sprite(battle.vert_box, 8, (900 - 260, -50))
    screen.blit(scaled[0], scaled[1])
    this_pkmn = battle.player_trainer.pokemon[selected]

    screen.blit(font.render(this_pkmn.name + ":", False, "black"), (680, 10))

    y_offset = 60

    screen.blit(font.render(this_pkmn.moves[0].name, False, "black"), (680, y_offset))
    screen.blit(
        font.render(str(this_pkmn.moves[0].value), False, "black"), (880, y_offset)
    )

    y_offset += 60

    screen.blit(font.render(this_pkmn.moves[1].name, False, "black"), (680, y_offset))
    screen.blit(
        font.render(str(this_pkmn.moves[1].value), False, "black"), (880, y_offset)
    )
    y_offset += 60

    screen.blit(font.render(this_pkmn.moves[2].name, False, "black"), (680, y_offset))
    screen.blit(
        font.render(str(this_pkmn.moves[2].value), False, "black"), (880, y_offset)
    )

    y_offset += 60
    screen.blit(font.render(this_pkmn.moves[3].name, False, "black"), (680, y_offset))
    screen.blit(
        font.render(str(this_pkmn.moves[3].value), False, "black"), (880, y_offset)
    )


def next_pokemon():
    battle.player_trainer.pokemon[selected] = battle.pokemons[
        battle.player_trainer.pokemon[selected].idx + 1
    ]


def prev_pokemon():
    battle.player_trainer.pokemon[selected] = battle.pokemons[
        battle.player_trainer.pokemon[selected].idx - 1
    ]
