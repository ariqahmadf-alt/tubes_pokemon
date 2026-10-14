from pathlib import Path

import pygame
import battle
from utils import scale_sprite

pkmn_icon = pygame.image.load("assets/pkmn_icon.png")
selected = 0
rival_chooses = False

# This function chooses a rival team based on the player's team and the weaknesses/advantages of each Pokemon type. It reads a file containing type advantages, scores potential rival teams against the player's team, and uses a hill-climbing algorithm to find the best possible rival team. The chosen team is then assigned to the rival trainer in the battle.
def choose_rival_team():
    weakness_path = Path(__file__).parent / "assets" / "weaknesses.txt"
    advantages = set()
    with weakness_path.open(encoding="utf-8") as weakness_file:
        for line in weakness_file:
            if "->" not in line:
                continue
            stronger, weaker = (element.strip() for element in line.split("->", 1))
            advantages.add((stronger, weaker))

    player_team = battle.player_trainer.pokemon
    team_size = len(battle.rival_trainer.pokemon)
    candidates = [pokemon for pokemon in battle.pokemons if pokemon not in player_team]

    def score(team):
        return sum(
            int((rival_pokemon.element, player_pokemon.element) in advantages)
            - int((player_pokemon.element, rival_pokemon.element) in advantages)
            for rival_pokemon in team
            for player_pokemon in player_team
        )

    # Keep the current rival roster as the starting state when it is valid.
    team = []
    for pokemon in battle.rival_trainer.pokemon:
        if pokemon in candidates and pokemon not in team:
            team.append(pokemon)
    for pokemon in candidates:
        if len(team) == team_size:
            break
        if pokemon not in team:
            team.append(pokemon)

    # Steepest-ascent hill climbing: replace one team member with an unused
    # candidate whenever that produces the largest matchup-score improvement.
    while True:
        current_score = score(team)
        best_team = team
        best_score = current_score

        for slot in range(team_size):
            for candidate in candidates:
                if candidate in team:
                    continue
                neighbor = team.copy()
                neighbor[slot] = candidate
                neighbor_score = score(neighbor)
                if neighbor_score > best_score:
                    best_team = neighbor
                    best_score = neighbor_score

        if best_score == current_score:
            break
        team = best_team

    battle.rival_trainer.pokemon = team
    battle.rival = team[0]


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
