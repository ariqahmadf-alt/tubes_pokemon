import pygame
import config
from copy import deepcopy
from dataclasses import dataclass
from math import inf
from pathlib import Path
from utils import scale_sprite
from knowledge_base import Atom, KnowledgeBase
from inference_engine import InferenceEngine
from battle_interaction import BattleInteractionHandler

weakness_path = Path(__file__).parent / "assets" / "weaknesses.txt"
type_advantages = set()
with weakness_path.open(encoding="utf-8") as weakness_file:
    for line in weakness_file:
        if "->" not in line:
            continue
        stronger, weaker = (element.strip() for element in line.split("->", 1))
        type_advantages.add((stronger, weaker))

box = pygame.image.load("assets/box.png")
vert_box = pygame.image.load("assets/vert_box.png")
options = pygame.image.load("assets/options.png")

move_logs = []
battle_text = ""
chosen_log = 0
showing_log = True
showing_nodes = False
showing_kb = False
kb_trace_step = 0
turn_count = 0
current_agent = "NPC_A"
battle_started = False
battle_over = False
battle_winner = None
last_search = None
last_interaction = "No interaction has been executed."
inference_engine = InferenceEngine()
knowledge_base = KnowledgeBase.from_json()
interaction_handler = BattleInteractionHandler()
inference_result = None


class MoveLogEntry:
    def __init__(
        self,
        move,
        user,
        npc_a_state,
        npc_b_state,
        actor_pokemon,
        target_pokemon,
    ):
        self.move = move
        self.user = user
        self.actor_pokemon = actor_pokemon
        self.target_pokemon = target_pokemon
        self.npc_a = deepcopy(npc_a_state)
        self.npc_b = deepcopy(npc_b_state)


@dataclass(frozen=True)
class BattleAction:
    actor_index: int
    target_index: int
    move_index: int


class Move:
    def __init__(self, name, pp, value):
        self.name = name

        # power points
        self.pp = pp
        self.max_pp = pp

        # generic value corresponding to the move.
        # eg; ATTACK move of 10 will reduce HP by 10
        self.value = value


class Trainer:
    def __init__(self, name, pokemon, identity=None):
        self.name = name
        self.pokemon = pokemon
        self.identity = identity or name
        self.active_index = 0

    @property
    def active(self):
        if not self.pokemon:
            return None
        return self.pokemon[self.active_index]

    @property
    def is_defeated(self):
        return not any(pokemon.hp > 0 for pokemon in self.pokemon)

    def advance_active(self):
        if not self.pokemon or self.active is None or self.active.hp > 0:
            return False
        for offset in range(1, len(self.pokemon) + 1):
            index = (self.active_index + offset) % len(self.pokemon)
            if self.pokemon[index].hp > 0:
                self.active_index = index
                return True
        return False


class Pokemon:
    def __init__(self, name, hp, moves, element):
        self.name = name
        self.hp = hp
        self.defense = 0
        self.max_hp = hp
        self.moves = moves
        self.pkmn_img = ""
        self.idx = -1
        self.element = element

# load all 10 pokemon
pokemons = [
    Pokemon(
        "KOBRA",
        100,
        [
            Move("ATTACK", 5, 15),
            Move("DEFEND", 5, 15),
            Move("HEAL", 5, 20),
            Move("REST", -1, -1),  # -1 PP means infinite move
        ],
        "poison",
    ),
    Pokemon(
        "BLASTOISE",
        100,
        [
            Move("ATTACK", 5, 15),
            Move("DEFEND", 5, 15),
            Move("HEAL", 5, 20),
            Move("REST", -1, -1),  # -1 PP means infinite move
        ],
        "water",
    ),
    Pokemon(
        "JIGGLYTUFF",
        100,
        [
            Move("ATTACK", 5, 15),
            Move("DEFEND", 5, 15),
            Move("HEAL", 5, 20),
            Move("REST", -1, -1),  # -1 PP means infinite move
        ],
        "fairy",
    ),
    Pokemon(
        "RAPIDASH",
        100,
        [
            Move("ATTACK", 5, 15),
            Move("DEFEND", 5, 15),
            Move("HEAL", 5, 20),
            Move("REST", -1, -1),  # -1 PP means infinite move
        ],
        "fire",
    ),
    Pokemon(
        "HAUNTER",
        100,
        [
            Move("ATTACK", 5, 15),
            Move("DEFEND", 5, 15),
            Move("HEAL", 5, 20),
            Move("REST", -1, -1),  # -1 PP means infinite move
        ],
        "ghost",
    ),
    Pokemon(
        "ONYX",
        100,
        [
            Move("ATTACK", 5, 15),
            Move("DEFEND", 5, 15),
            Move("HEAL", 5, 20),
            Move("REST", -1, -1),  # -1 PP means infinite move
        ],
        "rock",
    ),
    Pokemon(
        "MEGUNIM",
        100,
        [
            Move("ATTACK", 5, 15),
            Move("DEFEND", 5, 15),
            Move("HEAL", 5, 20),
            Move("REST", -1, -1),  # -1 PP means infinite move
        ],
        "grass",
    ),
    Pokemon(
        "LUGIA",
        100,
        [
            Move("ATTACK", 5, 15),
            Move("DEFEND", 5, 15),
            Move("HEAL", 5, 20),
            Move("REST", -1, -1),  # -1 PP means infinite move
        ],
        "flying",
    ),
    Pokemon(
        "CHARIZARD",
        100,
        [
            Move("ATTACK", 5, 15),
            Move("DEFEND", 5, 15),
            Move("HEAL", 5, 20),
            Move("REST", -1, -1),  # -1 PP means infinite move
        ],
        "fire",
    ),
    Pokemon(
        "PIKACHU",
        100,
        [
            Move("ATTACK", 5, 15),
            Move("DEFEND", 5, 15),
            Move("HEAL", 5, 20),
            Move("REST", -1, -1),  # -1 PP means infinite move
        ],
        "electric",
    ),
]

# Load the Pokémon sprites used by both NPC battle rosters.
for i in range(10):
    pokemons[i].pkmn_img = pygame.image.load(f"assets/pokemon/pokemon_{i * 2}.png")
    pokemons[i].idx = i

# Draft data is used only by the unchanged pre-battle selection screen.
player_trainer = Trainer(
    "draft NPC A roster",
    [
        pokemons[0],
        pokemons[1],
        pokemons[2],
    ],
)
rival_trainer = Trainer(
    "draft NPC B roster",
    [
        pokemons[3],
        pokemons[4],
        pokemons[5],
    ],
)

rival = rival_trainer.pokemon[0]
npc_a_trainer = None
npc_b_trainer = None


def available_moves(pokemon):
    return [index for index, move in enumerate(pokemon.moves) if move.pp != 0]


def _pokemon_identity(trainer, index):
    pokemon = trainer.pokemon[index]
    return f"{trainer.identity}:{index}:{pokemon.name}"


def _action_label(actor, opponent, action):
    user = actor.pokemon[action.actor_index]
    move = user.moves[action.move_index]
    target_trainer = opponent if move.name.upper() == "ATTACK" else actor
    target = target_trainer.pokemon[action.target_index]
    return f"{user.name} -> {target.name}: {move.name}"


def _legal_actions(actor, opponent):
    actions = []
    for actor_index, pokemon in enumerate(actor.pokemon):
        if pokemon.hp <= 0:
            continue
        for move_index in available_moves(pokemon):
            move = pokemon.moves[move_index]
            target_trainer = (
                opponent if move.name.upper() == "ATTACK" else actor
            )
            target_indices = (
                range(len(target_trainer.pokemon))
                if target_trainer is opponent
                else (actor_index,)
            )
            for target_index in target_indices:
                if target_trainer.pokemon[target_index].hp > 0:
                    actions.append(
                        BattleAction(actor_index, target_index, move_index)
                    )
    return actions


def simulate_move(actor, enemy, move_idx):
    move = actor.moves[move_idx]

    if move_idx == 0:  # ATTACK
        damage = max(move.value - enemy.defense, 0)
        if (actor.element, enemy.element) in type_advantages:
            damage *= 1.5
        elif (enemy.element, actor.element) in type_advantages:
            damage /= 1.5
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


hp_weight = 10
def_weight = 2


def _team_score(trainer):
    return sum(
        pokemon.hp * hp_weight
        + (pokemon.defense * def_weight if pokemon.hp > 0 else 0)
        for pokemon in trainer.pokemon
    )


def evaluate(npc_a_state, npc_b_state):
    if npc_b_state.is_defeated:
        return 100000

    if npc_a_state.is_defeated:
        return -100000

    return _team_score(npc_a_state) - _team_score(npc_b_state)


def _new_search_node(label, maximizing):
    return {
        "label": label,
        "kind": "MAX" if maximizing else "MIN",
        "value": None,
        "alpha": None,
        "beta": None,
        "pruned": False,
        "on_path": False,
        "children": [],
    }


def _search(
    npc_a_state,
    npc_b_state,
    depth,
    maximizing,
    alpha,
    beta,
    pruning,
    metrics=None,
    node=None,
):
    if metrics is not None:
        metrics["nodes"] += 1
    if depth == 0 or npc_a_state.is_defeated or npc_b_state.is_defeated:
        if metrics is not None:
            metrics["leaves"] += 1
        score = evaluate(npc_a_state, npc_b_state)
        if node is not None:
            node["value"] = score
            node["alpha"] = alpha
            node["beta"] = beta
        return score

    actor = npc_a_state if maximizing else npc_b_state
    opponent = npc_b_state if maximizing else npc_a_state
    actions = _legal_actions(actor, opponent)
    if not actions:
        return evaluate(npc_a_state, npc_b_state)

    best_score = -inf if maximizing else inf
    for action_pos, action in enumerate(actions):
        next_a = deepcopy(npc_a_state)
        next_b = deepcopy(npc_b_state)
        next_actor = next_a if maximizing else next_b
        next_opponent = next_b if maximizing else next_a
        user = next_actor.pokemon[action.actor_index]
        target_trainer = (
            next_opponent
            if user.moves[action.move_index].name.upper() == "ATTACK"
            else next_actor
        )
        target = target_trainer.pokemon[action.target_index]
        simulate_move(user, target, action.move_index)
        next_opponent.advance_active()

        child = None
        if node is not None:
            child = _new_search_node(
                _action_label(next_actor, next_opponent, action),
                not maximizing,
            )
            node["children"].append(child)

        score = _search(
            next_a,
            next_b,
            depth - 1,
            not maximizing,
            alpha,
            beta,
            pruning,
            metrics,
            child,
        )
        if maximizing:
            best_score = max(best_score, score)
            alpha = max(alpha, best_score)
        else:
            best_score = min(best_score, score)
            beta = min(beta, best_score)

        if pruning and beta <= alpha:
            if metrics is not None:
                metrics["pruned"] += len(actions) - action_pos - 1
            if node is not None:
                for remaining_action in actions[action_pos + 1 :]:
                    remaining_user = actor.pokemon[remaining_action.actor_index]
                    remaining_target_trainer = (
                        opponent
                        if remaining_user.moves[
                            remaining_action.move_index
                        ].name.upper()
                        == "ATTACK"
                        else actor
                    )
                    remaining_target = remaining_target_trainer.pokemon[
                        remaining_action.target_index
                    ]
                    cut_node = _new_search_node(
                        f"{remaining_user.name} -> {remaining_target.name}: "
                        f"{remaining_user.moves[remaining_action.move_index].name}",
                        not maximizing,
                    )
                    cut_node["pruned"] = True
                    node["children"].append(cut_node)
            break

    if node is not None:
        node["value"] = best_score
        node["alpha"] = alpha
        node["beta"] = beta
    return best_score


def minimax(npc_a_state, npc_b_state, depth, maximizing=True):
    return _search(npc_a_state, npc_b_state, depth, maximizing, -inf, inf, False)


def alpha_beta(npc_a_state, npc_b_state, depth, alpha, beta, maximizing=True):
    return _search(
        npc_a_state, npc_b_state, depth, maximizing, alpha, beta, True
    )


def _trainers_for(actor_id):
    if actor_id == "NPC_A":
        return npc_a_trainer, npc_b_trainer
    if actor_id == "NPC_B":
        return npc_b_trainer, npc_a_trainer
    raise ValueError(f"Unknown battle agent: {actor_id}")


def _observed_facts():
    facts = []
    for trainer in (npc_a_trainer, npc_b_trainer):
        for index, pokemon in enumerate(trainer.pokemon):
            identity = _pokemon_identity(trainer, index)
            facts.append(Atom("Controls", (trainer.identity, identity)))
            if pokemon.hp <= 0:
                continue
            facts.append(Atom("AlivePokemon", (identity,)))
            usable_moves = [
                move for move in pokemon.moves if move.pp != 0
            ]
            if pokemon.hp <= pokemon.max_hp * 0.3:
                facts.append(Atom("LowHP", (identity,)))
            if any(move.name.upper() == "ATTACK" for move in usable_moves):
                facts.append(Atom("HasDamagingMove", (identity,)))
            if any(
                move.name.upper() == "ATTACK" and move.value >= 15
                for move in usable_moves
            ):
                facts.append(Atom("HasHighDamagePotential", (identity,)))
            if pokemon.hp < pokemon.max_hp and any(
                move.name.upper() == "HEAL" for move in usable_moves
            ):
                facts.append(Atom("HasHealingMove", (identity,)))

        active = trainer.active
        if active is None or active.hp <= 0:
            continue
        identity = trainer.identity
        usable_moves = [move for move in active.moves if move.pp != 0]
        if active.hp <= active.max_hp * 0.3:
            facts.append(Atom("LowHP", (identity,)))
        if any(move.name.upper() == "ATTACK" for move in usable_moves):
            facts.append(Atom("HasDamagingMove", (identity,)))
        if any(
            move.name.upper() == "ATTACK" and move.value >= 15
            for move in usable_moves
        ):
            facts.append(Atom("HasHighDamagePotential", (identity,)))
        if active.hp < active.max_hp and any(
            move.name.upper() == "HEAL" for move in usable_moves
        ):
            facts.append(Atom("HasHealingMove", (identity,)))

    active_a = npc_a_trainer.active
    active_b = npc_b_trainer.active
    if (
        active_a is not None
        and active_b is not None
        and active_a.hp > 0
        and active_b.hp > 0
    ):
        if (active_a.element, active_b.element) in type_advantages:
            facts.append(Atom("HasTypeAdvantage", ("NPC_A", "NPC_B")))
        if (active_b.element, active_a.element) in type_advantages:
            facts.append(Atom("HasTypeAdvantage", ("NPC_B", "NPC_A")))

    for index_a, pokemon_a in enumerate(npc_a_trainer.pokemon):
        if pokemon_a.hp <= 0:
            continue
        identity_a = _pokemon_identity(npc_a_trainer, index_a)
        for index_b, pokemon_b in enumerate(npc_b_trainer.pokemon):
            if pokemon_b.hp <= 0:
                continue
            identity_b = _pokemon_identity(npc_b_trainer, index_b)
            if (pokemon_a.element, pokemon_b.element) in type_advantages:
                facts.append(Atom("HasTypeAdvantage", (identity_a, identity_b)))
            if (pokemon_b.element, pokemon_a.element) in type_advantages:
                facts.append(Atom("HasTypeAdvantage", (identity_b, identity_a)))
    return facts


def _refresh_inference():
    global inference_result, kb_trace_step
    knowledge_base.update_observations(_observed_facts())
    inference_result = inference_engine.infer(knowledge_base)
    kb_trace_step = 0
    return inference_result


def start_battle():
    global player_trainer, rival_trainer, rival
    global npc_a_trainer, npc_b_trainer, battle_started, battle_over
    global battle_winner, current_agent, turn_count, move_logs, chosen_log
    global last_search, last_interaction, battle_text, showing_kb, showing_nodes

    if player_trainer is None or rival_trainer is None:
        raise RuntimeError("Pre-battle rosters are unavailable.")
    if not player_trainer.pokemon or not rival_trainer.pokemon:
        raise ValueError("Both NPCs must have at least one Pokémon.")

    npc_a_trainer = Trainer(
        "NPC A", deepcopy(player_trainer.pokemon), identity="NPC_A"
    )
    npc_b_trainer = Trainer(
        "NPC B", deepcopy(rival_trainer.pokemon), identity="NPC_B"
    )
    player_trainer = None
    rival_trainer = None
    rival = None
    battle_started = True
    battle_over = False
    battle_winner = None
    current_agent = "NPC_A"
    turn_count = 0
    move_logs = []
    chosen_log = 0
    last_search = None
    last_interaction = "No interaction has been executed."
    showing_kb = False
    showing_nodes = False
    _refresh_inference()
    battle_text = "NPC A is scheduled to act. Press SPACE to advance."


def choose_action(actor_id, depth=2, mode="minimax", hints=()):
    global last_search
    actor, opponent = _trainers_for(actor_id)
    if actor.is_defeated or opponent.is_defeated:
        return None

    actions = _legal_actions(actor, opponent)
    if not actions:
        return None

    def is_hinted(action):
        user = actor.pokemon[action.actor_index]
        move = user.moves[action.move_index]
        target_trainer = opponent if move.name.upper() == "ATTACK" else actor
        return bool(
            interaction_handler.matching_hints(
                hints,
                _pokemon_identity(actor, action.actor_index),
                _pokemon_identity(target_trainer, action.target_index),
                move.name,
            )
        )

    actions.sort(
        key=lambda action: (
            not is_hinted(action),
            action.actor_index,
            action.target_index,
            action.move_index,
        )
    )

    maximizing = actor_id == "NPC_A"
    best_score = -inf if maximizing else inf
    best_action = None
    alpha = -inf
    beta = inf
    metrics = {"nodes": 1, "leaves": 0, "pruned": 0}
    root = _new_search_node(
        f"{actor.name} ({'MAX' if maximizing else 'MIN'})", maximizing
    )
    action_scores = []

    for action in actions:
        next_a = deepcopy(npc_a_trainer)
        next_b = deepcopy(npc_b_trainer)
        next_actor = next_a if actor_id == "NPC_A" else next_b
        next_opponent = next_b if actor_id == "NPC_A" else next_a
        user = next_actor.pokemon[action.actor_index]
        move = user.moves[action.move_index]
        target_trainer = (
            next_opponent if move.name.upper() == "ATTACK" else next_actor
        )
        target = target_trainer.pokemon[action.target_index]
        simulate_move(user, target, action.move_index)
        next_opponent.advance_active()

        child = _new_search_node(
            _action_label(next_actor, next_opponent, action),
            not maximizing,
        )
        root["children"].append(child)
        next_maximizing = actor_id == "NPC_B"
        if mode == "alpha-beta":
            score = _search(
                next_a,
                next_b,
                depth - 1,
                next_maximizing,
                alpha,
                beta,
                True,
                metrics,
                child,
            )
        else:
            score = _search(
                next_a,
                next_b,
                depth - 1,
                next_maximizing,
                -inf,
                inf,
                False,
                metrics,
                child,
            )
        action_scores.append(
            {
                "actor_index": action.actor_index,
                "actor": actor.pokemon[action.actor_index].name,
                "target_index": action.target_index,
                "target": target_trainer.pokemon[action.target_index].name,
                "move_index": action.move_index,
                "name": actor.pokemon[action.actor_index]
                .moves[action.move_index]
                .name,
                "score": score,
            }
        )

        if (maximizing and score > best_score) or (
            not maximizing and score < best_score
        ):
            best_score = score
            best_action = action
        if maximizing:
            alpha = max(alpha, best_score)
        else:
            beta = min(beta, best_score)

    root["value"] = best_score
    root["alpha"] = alpha
    root["beta"] = beta
    if best_action is not None:
        chosen_label = _action_label(actor, opponent, best_action)
        for child in root["children"]:
            if child["label"] == chosen_label:
                node = child
                while node is not None:
                    node["on_path"] = True
                    node = next(
                        (
                            item
                            for item in node["children"]
                            if not item["pruned"]
                            and item["value"] == node["value"]
                        ),
                        None,
                    )
                break

    last_search = {
        "actor": actor_id,
        "mode": mode,
        "depth": depth,
        "action_scores": action_scores,
        "best_action": best_action,
        "metrics": metrics,
        "tree": root,
    }
    return best_action


def _finish_battle():
    global battle_over, battle_winner, battle_text
    battle_over = True
    if npc_a_trainer.is_defeated and npc_b_trainer.is_defeated:
        battle_winner = "Draw"
    elif npc_a_trainer.is_defeated:
        battle_winner = npc_b_trainer.name
    else:
        battle_winner = npc_a_trainer.name
    battle_text = f"{battle_winner} wins! The battle is over."


def advance_battle():
    global current_agent, turn_count, battle_text, last_interaction

    if not battle_started or battle_over:
        return False

    npc_a_trainer.advance_active()
    npc_b_trainer.advance_active()
    if npc_a_trainer.is_defeated or npc_b_trainer.is_defeated:
        _finish_battle()
        return False

    actor, opponent = _trainers_for(current_agent)
    result = _refresh_inference()
    hints = interaction_handler.hints_from(result)
    action = choose_action(
        current_agent, depth=2, mode=config.ai_type, hints=hints
    )
    if action is None:
        return False

    user = actor.pokemon[action.actor_index]
    move = user.moves[action.move_index]
    target_trainer = opponent if move.name.upper() == "ATTACK" else actor
    target = target_trainer.pokemon[action.target_index]
    if user.hp <= 0 or target is None or target.hp <= 0 or move.pp == 0:
        last_interaction = (
            f"{actor.name}'s selected action was rejected because "
            "the battle state no longer permits it."
        )
        return False

    matching = interaction_handler.matching_hints(
        hints,
        _pokemon_identity(actor, action.actor_index),
        _pokemon_identity(target_trainer, action.target_index),
        move.name,
    )
    available_names = [
        available_move.name
        for available_move in user.moves
        if available_move.pp != 0
    ]
    valid_hints = []
    for hint in matching:
        valid, _ = interaction_handler.validate(
            hint,
            current_agent,
            target_trainer.identity,
            move.name,
            available_names,
        )
        if valid:
            valid_hints.append(hint)

    actor.active_index = action.actor_index
    target_trainer.active_index = action.target_index
    simulate_move(user, target, action.move_index)
    target_trainer.advance_active()
    move_logs.append(
        MoveLogEntry(
            move,
            actor.name,
            npc_a_trainer,
            npc_b_trainer,
            user.name,
            target.name,
        )
    )
    turn_count += 1

    if valid_hints:
        rules = ", ".join(sorted({hint.rule_id for hint in valid_hints}))
        last_interaction = (
            f"{rules} inferred {user.name} -> {target.name}: {move.name}; "
            "action executed."
        )
    elif matching:
        last_interaction = (
            f"The inferred {matching[0].action} intent was invalidated; "
            f"the search-selected {user.name} -> {target.name}: {move.name} "
            "action was executed instead."
        )
    elif any(
        hint.actor == current_agent
        or hint.actor.startswith(f"{current_agent}:")
        for hint in hints
    ):
        actor_hints = [
            hint
            for hint in hints
            if hint.actor == current_agent
            or hint.actor.startswith(f"{current_agent}:")
        ]
        hint_summary = ", ".join(
            sorted({f"{hint.rule_id}:{hint.action}" for hint in actor_hints})
        )
        last_interaction = (
            f"KB inferred {hint_summary}; search selected {user.name} -> "
            f"{target.name}: {move.name} after evaluating the strategic "
            "consequences."
        )
    else:
        last_interaction = (
            f"{actor.name}'s search-selected action was {user.name} -> "
            f"{target.name}: {move.name}; "
            "no applicable inferred intent matched."
        )

    if npc_a_trainer.is_defeated or npc_b_trainer.is_defeated:
        _finish_battle()
        _refresh_inference()
    else:
        current_agent = "NPC_B" if current_agent == "NPC_A" else "NPC_A"
        next_name = npc_a_trainer.name if current_agent == "NPC_A" else npc_b_trainer.name
        battle_text = (
            f"{actor.name}'s {user.name} used {move.name} on "
            f"{target_trainer.name}'s {target.name}.\n"
            f"{next_name} is scheduled. Press SPACE to continue."
        )
        _refresh_inference()
    return True


def printLogs():
    for log in move_logs:
        print(log.move.name, log.user)


def draw_pokemon(screen, font):
    screen.blit(font.render("NPC A", False, "black"), (20, 0))
    screen.blit(font.render("NPC B", False, "black"), (490, 0))
    _draw_trainer(npc_a_trainer, 0, screen, font, True)
    _draw_trainer(npc_b_trainer, 475, screen, font, False)


def _draw_trainer(trainer, x, screen, font, flip):
    for index, pokemon in enumerate(trainer.pokemon[:3]):
        y = 35 + index * 105
        is_active = index == trainer.active_index
        if is_active:
            pygame.draw.rect(screen, (230, 240, 255), (x, y - 5, 455, 100))
        sprite = scale_sprite(
            pokemon.pkmn_img,
            1,
            (x + 5, y + 5),
            0,
            flip,
        )
        screen.blit(sprite[0], sprite[1])
        color = "grey" if pokemon.hp <= 0 else "black"
        marker = ">" if is_active else "-"
        screen.blit(
            font.render(f"{marker}{pokemon.name}", False, color),
            (x + 80, y + 5),
        )
        screen.blit(
            font.render(f"HP: {pokemon.hp:.0f}/{pokemon.max_hp}", False, color),
            (x + 80, y + 35),
        )
        screen.blit(
            font.render(f"DEF: {pokemon.defense:.0f}", False, color),
            (x + 80, y + 65),
        )


def draw_battle_text(screen, font):
    sprite = scale_sprite(box, 5, (0, 380))
    screen.blit(sprite[0], sprite[1])

    for line_index, line in enumerate(battle_text.splitlines()):
        screen.blit(
            font.render(line, False, "black"),
            (30, 410 + line_index * 26),
        )


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
        y = 40 + ((i - chosen_log) * 150)
        log = move_logs[i]
        screen.blit(
            font.render(f"{i + 1}", False, "black"),
            (900 - 230, y),
        )
        npc_a_hp = sum(pokemon.hp for pokemon in log.npc_a.pokemon)
        npc_b_hp = sum(pokemon.hp for pokemon in log.npc_b.pokemon)
        screen.blit(font.render(f"{npc_a_hp:.0f}", False, (0, 130, 0)), (670, y))
        screen.blit(
            font.render("/", False, "black"),
            (765, y),
        )
        screen.blit(font.render(f"{npc_b_hp:.0f}", False, (170, 0, 0)), (805, y))
        npc_a_defense = sum(pokemon.defense for pokemon in log.npc_a.pokemon)
        npc_b_defense = sum(pokemon.defense for pokemon in log.npc_b.pokemon)
        screen.blit(
            font.render(f"{npc_a_defense:.0f}", False, (0, 0, 150)),
            (670, y + 40),
        )
        screen.blit(
            font.render(f"{npc_b_defense:.0f}", False, (0, 0, 150)),
            (805, y + 40),
        )
        text = font.render(
            f"{log.actor_pokemon} > {log.target_pokemon}: {log.move.name}",
            False,
            "black",
        )
        side = text.get_rect(topleft=(670, y + 80))
        if log.user == "NPC B":
            side = text.get_rect(topright=(930, y + 80))
        screen.blit(text, side)


# AI OVERLAY
def draw_ai_brain(screen, font):
    left = 625
    scaled = scale_sprite(vert_box, 10, (900 - 325, -50))
    screen.blit(scaled[0], scaled[1])
    screen.blit(font.render(f"AI SEARCH - TURN {turn_count}", False, "black"), (left, 0))
    if last_search is None:
        screen.blit(font.render("Waiting for SPACE", False, "black"), (left, 50))
        return

    mode_text = "ALPHA-BETA" if last_search["mode"] == "alpha-beta" else "MINIMAX"
    screen.blit(font.render(f"AGENT: {last_search['actor']}", False, "black"), (left, 45))
    screen.blit(font.render(f"MODE: {mode_text}", False, "black"), (left, 80))
    screen.blit(font.render(f"DEPTH: {last_search['depth']}", False, "black"), (left, 115))
    action_font = _node_font(14)
    screen.blit(
        action_font.render("POKEMON > TARGET / MOVE / SCORE", False, "black"),
        (left, 165),
    )

    y = 205
    best_action = last_search["best_action"]
    ranked_actions = sorted(
        last_search["action_scores"],
        key=lambda action: action["score"],
        reverse=last_search["actor"] == "NPC_A",
    )
    for action in ranked_actions[:7]:
        is_best = (
            action["actor_index"] == best_action.actor_index
            and action["target_index"] == best_action.target_index
            and action["move_index"] == best_action.move_index
        )
        prefix = ">" if is_best else "-"
        color = (0, 140, 0) if is_best else "black"
        screen.blit(
            action_font.render(
                f"{prefix}{action['actor']}>{action['target']} "
                f"{action['name']}: {action['score']:.0f}",
                False,
                color,
            ),
            (left, y),
        )
        y += 30

    if len(ranked_actions) > 7:
        screen.blit(
            action_font.render(
                f"...{len(ranked_actions) - 7} more in node tree",
                False,
                "black",
            ),
            (left, y),
        )
        y += 30

    metrics = last_search["metrics"]
    y += 12
    screen.blit(font.render(f"NODES: {metrics['nodes']}", False, "black"), (left, y))
    y += 36
    screen.blit(font.render(f"LEAVES: {metrics['leaves']}", False, "black"), (left, y))
    y += 36
    if last_search["mode"] == "alpha-beta":
        screen.blit(
            font.render(f"PRUNED: {metrics['pruned']}", False, (190, 0, 0)),
            (left, y),
        )


# Toggle with N. The tree is the exact search recorded for the last NPC action.
_node_fonts = {}


def _node_font(size):
    if size not in _node_fonts:
        _node_fonts[size] = pygame.font.Font("assets/pkmn.ttf", size)
    return _node_fonts[size]


def _fmt_score(value):
    if value is None:
        return ""
    if value >= 100000:
        return "WIN"
    if value <= -100000:
        return "LOSE"
    return str(int(value))


def _fmt_bound(value):
    if value == inf:
        return "inf"
    if value == -inf:
        return "-inf"
    return _fmt_score(value)


def _dashed_line(screen, color, p1, p2, dash=6, gap=5, width=1):
    x1, y1 = p1
    x2, y2 = p2
    length = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1)
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    pos = 0
    while pos < length:
        end = min(pos + dash, length)
        pygame.draw.line(
            screen,
            color,
            (x1 + dx * pos, y1 + dy * pos),
            (x1 + dx * end, y1 + dy * end),
            width,
        )
        pos += dash + gap


def _center_text(screen, font, text, color, center):
    surf = font.render(text, False, color)
    screen.blit(surf, surf.get_rect(center=center))


def node_overlay(screen, font):
    if last_search is None:
        screen.blit(
            _node_font(16).render("SEARCH TREE: press SPACE to advance", False, "black"),
            (15, 15),
        )
        return
    root = last_search["tree"]
    ai_mode = last_search["mode"]
    search_depth = last_search["depth"]

    W, H = screen.get_size()
    f_big = _node_font(16)
    f_mid = _node_font(14)
    f_small = _node_font(12)

    GREEN = (0, 150, 0)
    RED = (190, 0, 0)
    GREY = (170, 170, 170)
    DARK = (70, 70, 70)
    ORANGE = (200, 90, 0)
    BLUE = (20, 90, 170)

    # panel semi-transparan menutupi layar battle
    panel = pygame.Surface((W, H), pygame.SRCALPHA)
    panel.fill((250, 250, 250, 240))
    screen.blit(panel, (0, 0))

    # ---------- header ----------
    mode_text = (
        "ALPHA-BETA (PRUNING)" if ai_mode == "alpha-beta" else "MINIMAX (NO PRUNING)"
    )
    screen.blit(
        f_big.render(
            f"AI SEARCH TREE - TURN {turn_count} - {last_search['actor']}",
            False,
            "black",
        ),
        (15, 8),
    )
    screen.blit(
        f_mid.render(f"{mode_text}   DEPTH: {search_depth}   [N] CLOSE", False, DARK),
        (15, 32),
    )

    # --------- priority --------
    screen.blit(f_big.render(f"AI Priority (weights):", False, "black"), (15, 55))
    screen.blit(f_big.render(f"HP: {hp_weight}", False, "black"), (15, 80))
    screen.blit(f_big.render(f"DEF: {def_weight}", False, "black"), (15, 110))

    # ---------- layout ----------
    mids = root["children"]
    total_slots = sum(max(len(m["children"]), 1) for m in mids) or 1
    margin = 30
    slot_w = (W - margin * 2) / total_slots
    y_root, y_mid, y_leaf = 105, 265, 430

    positions = {}  # id(node) -> (x, y)
    slot = 0
    for m in mids:
        n_kids = max(len(m["children"]), 1)
        first = margin + slot_w * (slot + 0.5)
        last = margin + slot_w * (slot + n_kids - 0.5)
        positions[id(m)] = ((first + last) / 2, y_mid)
        for k, leaf in enumerate(m["children"]):
            positions[id(leaf)] = (margin + slot_w * (slot + k + 0.5), y_leaf)
        slot += n_kids
    if mids:
        positions[id(root)] = (
            (positions[id(mids[0])][0] + positions[id(mids[-1])][0]) / 2,
            y_root,
        )
    else:
        positions[id(root)] = (W / 2, y_root)

    # ---------- garis (edge) ----------
    def draw_edges(node):
        px, py = positions[id(node)]
        for c in node["children"]:
            cx, cy = positions[id(c)]
            if c["pruned"]:
                _dashed_line(screen, GREY, (px, py), (cx, cy))
            elif c["on_path"]:
                pygame.draw.line(screen, GREEN, (px, py), (cx, cy), 4)
            else:
                pygame.draw.line(screen, DARK, (px, py), (cx, cy), 2)
            draw_edges(c)

    draw_edges(root)

    # ---------- node ----------
    # root
    rx, ry = positions[id(root)]
    _center_text(
        screen,
        f_mid,
        f"{root['label']} ({root['kind']})",
        "black",
        (rx, ry - 48),
    )
    r_rect = pygame.Rect(0, 0, 56, 56)
    r_rect.center = (rx, ry)
    pygame.draw.rect(screen, (220, 232, 250), r_rect, border_radius=8)
    pygame.draw.rect(screen, ORANGE, r_rect, 4, border_radius=8)
    _center_text(screen, f_mid, _fmt_score(root["value"]), "black", (rx, ry))

    leaves_seen = 0
    leaves_cut = 0

    for m in mids:
        mx, my = positions[id(m)]
        on_path = m["on_path"]
        edge = GREEN if on_path else (GREY if m["pruned"] else DARK)

        _center_text(screen, f_mid, m["label"], "black", (mx, my - 50))
        _center_text(screen, f_small, m["kind"], DARK, (mx, my - 36))
        pygame.draw.circle(screen, (225, 245, 230), (mx, my), 26)
        pygame.draw.circle(screen, edge, (mx, my), 26, 4 if on_path else 2)
        _center_text(screen, f_mid, _fmt_score(m["value"]), "black", (mx, my))

        if ai_mode == "alpha-beta" and m["alpha"] is not None:
            _center_text(
                screen, f_small, f"a={_fmt_bound(m['alpha'])}", DARK, (mx, my + 40)
            )
            _center_text(
                screen, f_small, f"b={_fmt_bound(m['beta'])}", DARK, (mx, my + 54)
            )

        if not m["children"]:
            leaves_seen += 1  # terminal (HP habis) -> node ini sendiri leaf

        for leaf in m["children"]:
            lx, ly = positions[id(leaf)]
            box = pygame.Rect(0, 0, min(int(slot_w) - 6, 50), 40)
            box.center = (lx, ly)
            if leaf["pruned"]:
                leaves_cut += 1
                pygame.draw.rect(screen, (240, 243, 248), box, border_radius=6)
                pygame.draw.rect(screen, (200, 205, 215), box, 2, border_radius=6)
                _center_text(screen, f_small, leaf["label"][:3], GREY, (lx, ly + 30))
                continue
            leaves_seen += 1
            pygame.draw.rect(screen, (220, 232, 250), box, border_radius=6)
            pygame.draw.rect(
                screen,
                GREEN if leaf["on_path"] else BLUE,
                box,
                4 if leaf["on_path"] else 2,
                border_radius=6,
            )
            _center_text(screen, f_small, _fmt_score(leaf["value"]), "black", (lx, ly))
            _center_text(screen, f_small, leaf["label"][:3], DARK, (lx, ly + 30))

    # ---------- footer ----------
    pygame.draw.line(screen, "black", (15, 510), (W - 15, 510), 2)
    total = leaves_seen + leaves_cut
    stat = f"LEAVES: {leaves_seen}/{total}"
    if ai_mode == "alpha-beta":
        stat += f"   PRUNED: {leaves_cut}"
    screen.blit(f_mid.render(stat, False, "black"), (15, 520))

    best_label = next((c["label"] for c in mids if c["on_path"]), None)
    if best_label is not None:
        screen.blit(
            f_mid.render(
                f"BEST: {best_label} ({_fmt_score(root['value'])})", False, GREEN
            ),
            (15, 545),
        )
    screen.blit(
        f_small.render(
            "GREEN: CHOSEN, DASHED/FADED: PRUNED; NPC A MAXIMIZES, NPC B MINIMIZES",
            False,
            DARK,
        ),
        (15, 575),
    )


def draw_kb_overlay(screen, font):
    width, height = screen.get_size()
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill((248, 250, 255, 242))
    screen.blit(panel, (0, 0))
    title_font = _node_font(17)
    detail_font = _node_font(12)
    muted = (75, 85, 100)
    green = (0, 125, 45)
    orange = (175, 95, 0)
    blue = (25, 80, 155)
    red = (165, 35, 35)

    screen.blit(
        title_font.render("BATTLE KNOWLEDGE BASE / INFERENCE TRACE", False, "black"),
        (16, 8),
    )
    screen.blit(
        detail_font.render(
            "[I] CLOSE   UP/DOWN: STEP THROUGH RULE EVALUATIONS",
            False,
            muted,
        ),
        (16, 34),
    )
    if not battle_started or inference_result is None:
        screen.blit(
            detail_font.render("Battle knowledge has not been initialized.", False, muted),
            (16, 70),
        )
        return

    active_a = npc_a_trainer.active
    active_b = npc_b_trainer.active
    screen.blit(
        detail_font.render(
            f"NPC_A ({active_a.name if active_a else 'DEFEATED'}) "
            f"<Opponent> NPC_B ({active_b.name if active_b else 'DEFEATED'})",
            False,
            blue,
        ),
        (16, 62),
    )
    scheduled = "Battle ended" if battle_over else f"{current_agent} scheduled"
    screen.blit(
        detail_font.render(
            f"Turn {turn_count if battle_over else turn_count + 1} | "
            f"{scheduled} | Waiting for SPACE: "
            f"{'no' if battle_over else 'yes'}",
            False,
            muted,
        ),
        (16, 82),
    )

    screen.blit(title_font.render("FACTS LOADED", False, blue), (16, 112))
    facts = list(inference_result.initial_facts)
    left_facts = facts[: (len(facts) + 1) // 2]
    right_facts = facts[(len(facts) + 1) // 2 :]
    for column, column_facts in enumerate((left_facts, right_facts)):
        x = 16 + column * 235
        y = 138
        for fact in column_facts:
            if y > 320:
                screen.blit(
                    detail_font.render(
                        f"... {len(column_facts) - column_facts.index(fact)} more",
                        False,
                        muted,
                    ),
                    (x, y),
                )
                break
            screen.blit(detail_font.render(str(fact), False, "black"), (x, y))
            y += 18

    trace = inference_result.evaluations
    screen.blit(title_font.render("RULE EVALUATION", False, blue), (500, 112))
    if trace:
        index = min(kb_trace_step, len(trace) - 1)
        evaluation = trace[index]
        rule_status = (
            "MATCHED"
            if evaluation["matched"]
            else "CONTRADICTED"
            if any(
                condition["status"] in ("contradicted", "partially contradicted")
                for condition in evaluation["conditions"]
            )
            else "UNKNOWN / NOT ENTAILED"
        )
        screen.blit(
            detail_font.render(
                f"Step {index + 1}/{len(trace)} | Iteration {evaluation['iteration']} | "
                f"{evaluation['rule_id']} | {rule_status}",
                False,
                green
                if evaluation["matched"]
                else red
                if rule_status == "CONTRADICTED"
                else orange,
            ),
            (500, 138),
        )
        y = 160
        for line in (evaluation["description"],):
            screen.blit(detail_font.render(line[:54], False, muted), (500, y))
            y += 18
        for condition in evaluation["conditions"]:
            state = condition["status"].upper()
            color = (
                green
                if condition["status"] == "entailed"
                else red
                if "contradicted" in condition["status"]
                else orange
            )
            screen.blit(
                detail_font.render(
                    f"{condition['condition']} : {state}", False, color
                ),
                (500, y),
            )
            y += 18
            if condition["matches"]:
                screen.blit(
                    detail_font.render(
                        f"  facts: {', '.join(condition['matches'])[:62]}",
                        False,
                        muted,
                    ),
                    (500, y),
                )
                y += 18
            elif condition["contradictions"]:
                screen.blit(
                    detail_font.render(
                        f"  contradictory fact: {condition['contradictions'][0]}",
                        False,
                        red,
                    ),
                    (500, y),
                )
                y += 18
        if evaluation["substitutions"]:
            substitution = evaluation["substitutions"][0]
            screen.blit(
                detail_font.render(f"Substitution: {substitution}", False, muted),
                (500, min(y, 286)),
            )
    else:
        screen.blit(
            detail_font.render("No rules are configured.", False, orange),
            (500, 140),
        )

    screen.blit(title_font.render("INFERRED FACTS / ACTION INTENTS", False, green), (16, 344))
    y = 370
    derived = inference_result.derivations
    if not derived:
        screen.blit(
            detail_font.render("No new facts were entailed in this inference pass.", False, muted),
            (16, y),
        )
    else:
        for derivation in derived[:6]:
            screen.blit(
                detail_font.render(
                    f"{derivation.rule_id} {dict(derivation.substitution)} "
                    f"=> {derivation.conclusion}",
                    False,
                    green,
                ),
                (16, y),
            )
            y += 18
        if len(derived) > 6:
            screen.blit(
                detail_font.render(f"... and {len(derived) - 6} more", False, muted),
                (16, y),
            )

    pokemon_intents = sorted(
        fact
        for fact in inference_result.facts
        if fact.predicate == "PokemonActionIntent"
    )
    if pokemon_intents:
        final = (
            f"{len(pokemon_intents)} Pokémon intent(s); "
            f"{pokemon_intents[0]}"
        )
    else:
        action_intents = sorted(
            fact
            for fact in inference_result.facts
            if fact.predicate == "ActionIntent"
        )
        final = (
            ", ".join(str(fact) for fact in action_intents)
            or "No action intent is entailed."
        )
    screen.blit(
        detail_font.render(f"Final conclusion: {final[:100]}", False, blue),
        (16, 510),
    )
    screen.blit(
        detail_font.render(f"Result: {last_interaction[:105]}", False, "black"),
        (16, 532),
    )
    winner = f"Winner: {battle_winner}" if battle_over else "Winner: undecided"
    screen.blit(detail_font.render(winner, False, blue), (16, 554))
