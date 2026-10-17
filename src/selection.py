from pathlib import Path

import pygame
import battle
from utils import scale_sprite
from utils import scale_sprite_vec2

bigbox = pygame.image.load("assets/bigbox.png")

pkmn_icon = pygame.image.load("assets/pkmn_icon.png")
selected = 0
rival_chooses = False

# Local-search debugger. The search runs synchronously, so the overlay lets us
# inspect the recorded iterations afterward rather than animating the search.
show_debug_overlay = False
debug_steps = []
debug_step_index = 0
debug_run = None
_debug_fonts = None


# This function chooses a rival team based on the player's team and the weaknesses/advantages of each Pokemon type. It reads a file containing type advantages, scores potential rival teams against the player's team, and uses a hill-climbing algorithm to find the best possible rival team. The chosen team is then assigned to the rival trainer in the battle.
def choose_rival_team():
    global debug_steps, debug_step_index, debug_run
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

    # Record a snapshot of the inputs before the rival roster changes.
    debug_steps = []
    debug_step_index = 0
    debug_run = {
        "player": [(pokemon.name, pokemon.element) for pokemon in player_team],
        "candidate_count": len(candidates),
        "initial_score": score(team),
        "initial_team": [pokemon.name for pokemon in team],
    }

    # Steepest-ascent hill climbing: replace one team member with an unused
    # candidate whenever that produces the largest matchup-score improvement.
    while True:
        current_score = score(team)
        best_team = team
        best_score = current_score
        tested_moves = []  # Debug data only; does not affect the search.

        for slot in range(team_size):
            for candidate in candidates:
                if candidate in team:
                    continue
                neighbor = team.copy()
                neighbor[slot] = candidate
                neighbor_score = score(neighbor)
                tested_moves.append(
                    {
                        "score": neighbor_score,
                        "slot": slot,
                        "old": team[slot].name,
                        "new": candidate.name,
                    }
                )
                if neighbor_score > best_score:
                    best_team = neighbor
                    best_score = neighbor_score

        winning_swap = next(
            (
                (slot, team[slot].name, best_team[slot].name)
                for slot in range(team_size)
                if team[slot] is not best_team[slot]
            ),
            None,
        )
        debug_steps.append(
            {
                "team": [
                    (pokemon.name, pokemon.element, score([pokemon]))
                    for pokemon in team
                ],
                "score": current_score,
                "best_score": best_score,
                "winning_swap": winning_swap,
                "evaluated": len(tested_moves),
                "top_moves": sorted(
                    tested_moves, key=lambda move: move["score"], reverse=True
                )[:5],
            }
        )

        if best_score == current_score:
            break
        team = best_team

    debug_run["final_score"] = score(team)
    debug_run["final_team"] = [pokemon.name for pokemon in team]
    debug_run["total_evaluated"] = sum(step["evaluated"] for step in debug_steps)
    debug_step_index = len(debug_steps) - 1

    battle.rival_trainer.pokemon = team
    battle.rival = team[0]


def move_debug_step(amount):
    """Navigate saved hill-climbing iterations (keyboard handling is in main.py)."""
    global debug_step_index
    if debug_steps:
        debug_step_index = max(0, min(debug_step_index + amount, len(debug_steps) - 1))


def draw_debug_overlay(screen):
    """Display the last local-search run on the team-selection screen."""
    if not show_debug_overlay:
        return

    width, height = screen.get_size()
    panel = pygame.Rect(20, 20, width - 40, height - 40)
    # screen.blit(bg, panel.topleft)
    # pygame.draw.rect(screen, (90, 178, 225), panel, 2, border_radius=8)

    # draw box
    box, rect = scale_sprite_vec2(bigbox, (4.6, 2.75), (20, 20), 0)
    screen.blit(box, rect)

    global _debug_fonts
    if _debug_fonts is None:
        _debug_fonts = (
            pygame.font.Font("assets/pkmn.ttf", 24),
            pygame.font.Font("assets/pkmn.ttf", 18),
            pygame.font.Font("assets/pkmn.ttf", 15),
        )
    title_font, font, small = _debug_fonts
    white = (0, 0, 0)
    muted = (0, 0, 0)
    cyan = (20, 0, 250)
    green = (0, 150, 0)
    gold = (150, 100, 0)

    def label(text, x, y, color=white, face=font, max_width=None):
        text = str(text)
        if max_width is not None and face.size(text)[0] > max_width:
            while text and face.size(text + "...")[0] > max_width:
                text = text[:-1]
            text += "..."
        screen.blit(face.render(text, True, color), (x, y))

    left = panel.x + 26
    right = panel.right - 26
    label("LOCAL SEARCH OVERLAY", left, panel.y + 19, cyan, title_font)
    pygame.draw.line(
        screen, (66, 87, 106), (left, panel.y + 83), (right, panel.y + 83), 1
    )

    if not debug_steps or debug_run is None:
        label(
            "Press SPACE to have the rival choose a team!", left, panel.y + 116, muted
        )
        return

    step = debug_steps[debug_step_index]
    last_step = debug_step_index == len(debug_steps) - 1
    label(
        f"START {debug_run['initial_score']:+d}  >  FINAL {debug_run['final_score']:+d}",
        left,
        panel.y + 99,
        green,
    )
    label(
        f"Candidates: {debug_run['candidate_count']}    Tested swaps: "
        f"{debug_run['total_evaluated']}",
        left + 365,
        panel.y + 101,
        muted,
        small,
    )
    label(
        "Player: "
        + ", ".join(f"{name} ({element})" for name, element in debug_run["player"]),
        left,
        panel.y + 129,
        muted,
        small,
        panel.width - 52,
    )
    pygame.draw.line(
        screen, (66, 87, 106), (left, panel.y + 156), (right, panel.y + 156), 1
    )

    label(
        f"ITERATION {debug_step_index + 1} / {len(debug_steps)}",
        left,
        panel.y + 169,
        cyan,
    )
    label(
        "NO IMPROVEMENT" if last_step else "IMPROVEMENT FOUND",
        left + 300,
        panel.y + 171,
        gold if last_step else green,
        small,
    )
    label(
        f"Current score: {step['score']:+d}    Best neighbor: {step['best_score']:+d}",
        left,
        panel.y + 201,
        white,
    )

    label("Individual matchup scores:", left, panel.y + 242, muted, small)
    for i, (name, element, contribution) in enumerate(step["team"]):
        if i >= 5:
            label(
                f"... and {len(step['team']) - 5} more",
                left + 15,
                panel.y + 271 + i * 28,
                muted,
                small,
            )
            break
        label(
            f"{i + 1}. {name}  [{element}]",
            left + 15,
            panel.y + 269 + i * 28,
            white,
            font,
            290,
        )
        label(
            f"{contribution:+d}",
            left + 345,
            panel.y + 269 + i * 28,
            (
                green
                if contribution > 0
                else (gold if contribution == 0 else (249, 130, 133))
            ),
        )

    detail_y = panel.y + 437
    if step["winning_swap"] is None:
        label(
            "No improvement - search stopped",
            left,
            detail_y,
            gold,
            small,
            400,
        )
    else:
        slot, old, new = step["winning_swap"]
        label(
            f"Chosen: slot {slot + 1}, {old} -> {new}",
            left,
            detail_y,
            green,
            small,
            410,
        )
        label(
            f"Gain: +{step['best_score'] - step['score']}",
            left,
            detail_y + 24,
            green,
            small,
        )

    chart_x = left + 440
    label("SCORE PROGRESSION", chart_x, panel.y + 242, muted, small)
    chart = pygame.Rect(chart_x + 8, panel.y + 280, max(100, right - chart_x - 22), 102)
    pygame.draw.rect(screen, (23, 35, 51), chart, border_radius=4)
    scores = [entry["score"] for entry in debug_steps]
    lo, hi = min(scores), max(scores)
    spread = max(1, hi - lo)
    points = [
        (
            int(chart.x + 18 + (i * (chart.width - 36) / max(1, len(scores) - 1))),
            int(chart.bottom - 16 - ((value - lo) * (chart.height - 32) / spread)),
        )
        for i, value in enumerate(scores)
    ]
    if len(points) > 1:
        pygame.draw.lines(screen, green, False, points, 2)
    for i, point in enumerate(points):
        pygame.draw.circle(
            screen,
            gold if i == debug_step_index else cyan,
            (int(point[0]), int(point[1])),
            5 if i == debug_step_index else 3,
        )
    label(f"min {lo:+d}", chart.x + 8, chart.bottom + 3, muted, small)
    label(f"max {hi:+d}", chart.right - 77, chart.bottom + 3, muted, small)

    label(
        f"TOP TESTED SWAPS ({step['evaluated']} evaluated)",
        chart_x,
        panel.y + 420,
        muted,
        small,
    )
    for i, move in enumerate(step["top_moves"][:3]):
        delta = move["score"] - step["score"]
        label(
            f"{move['score']:+d} ({delta:+d})  {move['old']} > {move['new']}",
            chart_x + 6,
            panel.y + 446 + 25 * i,
            green if delta > 0 else muted,
            small,
            right - chart_x - 8,
        )
    if not step["top_moves"]:
        label(
            "No valid replacement candidates.", chart_x + 6, panel.y + 446, muted, small
        )


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
