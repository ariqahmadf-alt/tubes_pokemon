"""Plan battle goals using exact state transitions from the battle simulator."""

from dataclasses import dataclass
from copy import deepcopy
import heapq
from math import ceil, inf
from pathlib import Path
import time

from battle_interaction import PlanHint
from planning import (
    Action,
    PlanningDomain,
    PlanStep,
    PlanResult,
)


DOMAIN_PATH = Path(__file__).parent / "assets" / "planning" / "battle_domain.json"


@dataclass(frozen=True)
class PlanningDecision:
    actor: str
    goal: str | None
    goal_object: str | None
    rule_id: str | None
    result: PlanResult | None
    hint: PlanHint | None


def hp_band(pokemon, bands):
    return _hp_band_value(pokemon.hp, pokemon.max_hp, bands)


def _hp_band_value(hp, max_hp, bands):
    if hp <= 0:
        return "gone"
    ratio = hp / max_hp
    if ratio <= bands["low_max_ratio"]:
        return "low"
    if ratio < bands["high_min_ratio"]:
        return "mid"
    return "high"


def planning_observation(actor, opponent, type_advantages, domain):
    """Return a closed-world state and typed objects for both rosters."""
    state = set()
    all_pokemon = []
    actor_ids = []
    opponent_ids = []
    for trainer, identifiers in ((actor, actor_ids), (opponent, opponent_ids)):
        for index, pokemon in enumerate(trainer.pokemon):
            identity = f"{trainer.identity}:{index}:{pokemon.name}"
            identifiers.append(identity)
            all_pokemon.append((trainer, pokemon, identity))
            state.add(("owner", identity, trainer.identity))
            state.add(("hp", identity, hp_band(pokemon, domain.hp_bands)))
            state.add(
                ("shielded" if pokemon.defense > 0 else "unshielded", identity)
            )
            if pokemon.hp <= 0:
                continue
            for move in pokemon.moves:
                if move.pp == 0:
                    continue
                move_name = move.name.upper()
                if move_name == "ATTACK":
                    state.add(("attack-ready", identity))
                elif move_name == "HEAL":
                    state.add(("heal-ready", identity))
                elif move_name == "DEFEND":
                    state.add(("defend-ready", identity))
                elif move_name == "REST":
                    state.add(("rest-ready", identity))

    bands = domain.hp_bands["values"]
    for band in bands:
        state.add(("live-band", band))
    for before, after in zip(bands, bands[1:]):
        state.add(("drop", before, after))
    for before, after in zip(bands[2::-1], bands[1::-1]):
        state.add(("raise", before, after))

    for actor_trainer, actor_pokemon, actor_id in all_pokemon:
        for target_trainer, target_pokemon, target_id in all_pokemon:
            if actor_trainer is target_trainer:
                continue
            if (actor_pokemon.element, target_pokemon.element) in type_advantages:
                relation = "advantage"
            elif (target_pokemon.element, actor_pokemon.element) in type_advantages:
                relation = "resisted"
            else:
                relation = "neutral"
            state.add((relation, actor_id, target_id))

    objects = {
        "pokemon": tuple(sorted(actor_ids + opponent_ids)),
        "actor-pokemon": tuple(sorted(actor_ids)),
        "enemy-pokemon": tuple(sorted(opponent_ids)),
        "band": tuple(sorted(bands)),
    }
    return frozenset(state), objects, tuple(actor_ids), tuple(opponent_ids)


def _goal_candidates(
    inference_result, actor_id, actor_pokemon_ids, opponent_ids, domain
):
    priorities = {
        goal: index
        for index, goal in enumerate(domain.goal_priority)
    }
    candidates = []
    for derivation in inference_result.derivations:
        conclusion = derivation.conclusion
        if (
            conclusion.predicate != "PlanGoal"
            or conclusion.negated
            or len(conclusion.arguments) != 3
            or conclusion.arguments[0] != actor_id
        ):
            continue
        _, goal, goal_object = conclusion.arguments
        if goal not in priorities:
            continue
        if goal == "win":
            goal_object = None
        elif goal == "recover" and goal_object not in actor_pokemon_ids:
            continue
        elif goal == "finish" and goal_object not in opponent_ids:
            continue
        candidates.append(
            (priorities[goal], goal, goal_object, derivation.rule_id)
        )
    return tuple(
        sorted(
            candidates,
            key=lambda item: (item[0], item[1], item[3], item[2]),
        )
    )


def _first_step_hint(
    plan_result,
    goal,
    goal_object,
    rule_id,
    actor,
    opponent,
    simulate_move,
    domain,
):
    if plan_result.status != "plan" or not plan_result.steps:
        return None, "Plan has no executable first step."
    step = plan_result.steps[0]
    action = step.action
    actor_ids = {
        f"{actor.identity}:{index}:{pokemon.name}": index
        for index, pokemon in enumerate(actor.pokemon)
    }
    opponent_ids = {
        f"{opponent.identity}:{index}:{pokemon.name}": index
        for index, pokemon in enumerate(opponent.pokemon)
    }
    if action.name.startswith("attack-"):
        actor_id, target_id = action.arguments[:2]
        move_name = "ATTACK"
        target_indices = opponent_ids
    elif action.name == "defend":
        actor_id = action.arguments[0]
        target_id = actor_id
        move_name = "DEFEND"
        target_indices = actor_ids
    elif action.name == "heal":
        actor_id = action.arguments[0]
        target_id = actor_id
        move_name = "HEAL"
        target_indices = actor_ids
    elif action.name == "rest":
        actor_id = action.arguments[0]
        target_id = actor_id
        move_name = "REST"
        target_indices = actor_ids
    else:
        return None, f"Unsupported planned action: {action.name}."

    if actor_id not in actor_ids or target_id not in target_indices:
        return None, "Plan step refers to a Pokémon outside the current rosters."
    actor_index = actor_ids[actor_id]
    target_index = target_indices[target_id]
    user = actor.pokemon[actor_index]
    move_index = next(
        (
            index
            for index, move in enumerate(user.moves)
            if move.name.upper() == move_name and move.pp != 0
        ),
        None,
    )
    if move_index is None:
        return None, "The planned move is not available."

    next_actor = deepcopy(actor)
    next_opponent = deepcopy(opponent)
    next_user = next_actor.pokemon[actor_index]
    if move_name == "ATTACK":
        target_trainer = next_opponent
    else:
        target_trainer = next_actor
    next_target = target_trainer.pokemon[target_index]
    simulate_move(next_user, next_target, move_index)

    predicted_state = plan_result.steps[0].state
    expected_values = {
        "hp-value": next_target.hp,
        "defense-value": next_target.defense,
    }
    for predicate, expected_value in expected_values.items():
        planned_value = next(
            (
                float(fact[2])
                for fact in predicted_state
                if fact[:2] == (predicate, target_id)
            ),
            None,
        )
        if planned_value is None or planned_value != expected_value:
            return None, (
                f"Dry run disagreed with planned {predicate}: "
                f"expected {planned_value}, got {expected_value}."
            )
    planned_pp = next(
        (
            int(fact[3])
            for fact in predicted_state
            if fact[:3] == ("pp-value", actor_id, move_name)
        ),
        None,
    )
    if planned_pp is None or planned_pp != next_user.moves[move_index].pp:
        return None, "Dry run disagreed with planned move PP."

    return (
        PlanHint(
            actor=actor.identity,
            goal=goal,
            goal_object=goal_object,
            rule_id=rule_id,
            action_name=action.name,
            actor_index=actor_index,
            target_index=target_index,
            move_name=move_name,
        ),
        "",
    )


def _pokemon_state(pokemon):
    return (
        float(pokemon.hp),
        float(pokemon.defense),
        tuple(move.pp for move in pokemon.moves),
    )


def _state_facts(actor, opponent, state, static_facts, domain):
    dynamic_predicates = {
        "hp",
        "shielded",
        "unshielded",
        "attack-ready",
        "heal-ready",
        "defend-ready",
        "rest-ready",
        "hp-value",
        "defense-value",
        "pp-value",
    }
    facts = {fact for fact in static_facts if fact[0] not in dynamic_predicates}
    for trainer, pokemon_states in zip((actor, opponent), state):
        for index, (pokemon, values) in enumerate(
            zip(trainer.pokemon, pokemon_states)
        ):
            identity = f"{trainer.identity}:{index}:{pokemon.name}"
            hp, defense, move_pp = values
            facts.add(
                ("hp", identity, _hp_band_value(hp, pokemon.max_hp, domain.hp_bands))
            )
            facts.add(("hp-value", identity, repr(hp)))
            facts.add(("defense-value", identity, repr(defense)))
            facts.add(("shielded" if defense > 0 else "unshielded", identity))
            for move_index, move in enumerate(pokemon.moves):
                pp = move_pp[move_index]
                move_name = move.name.upper()
                facts.add(("pp-value", identity, move_name, int(pp)))
                if hp <= 0 or pp == 0:
                    continue
                predicate = {
                    "ATTACK": "attack-ready",
                    "HEAL": "heal-ready",
                    "DEFEND": "defend-ready",
                    "REST": "rest-ready",
                }.get(move_name)
                if predicate:
                    facts.add((predicate, identity))
    return frozenset(facts)


def _copy_with_state(pokemon, values):
    copied = deepcopy(pokemon)
    copied.hp, copied.defense = values[:2]
    for move, pp in zip(copied.moves, values[2]):
        move.pp = pp
    return copied


def _goal_reached(state, actor, opponent, goal, goal_object, domain):
    if goal == "recover":
        for index, pokemon in enumerate(actor.pokemon):
            identity = f"{actor.identity}:{index}:{pokemon.name}"
            if identity == goal_object:
                return (
                    _hp_band_value(
                        state[0][index][0], pokemon.max_hp, domain.hp_bands
                    )
                    == "high"
                )
        return False
    if goal == "finish":
        for index, pokemon in enumerate(opponent.pokemon):
            identity = f"{opponent.identity}:{index}:{pokemon.name}"
            if identity == goal_object:
                return state[1][index][0] <= 0
        return False
    if goal == "win":
        return all(values[0] <= 0 for values in state[1])
    raise ValueError(f"Unknown battle planning goal: {goal}")


def _goal_heuristic(
    state, actor, opponent, goal, goal_object, type_advantages, domain
):
    if goal == "recover":
        for index, pokemon in enumerate(actor.pokemon):
            identity = f"{actor.identity}:{index}:{pokemon.name}"
            if identity != goal_object:
                continue
            missing_hp = (
                domain.hp_bands["high_min_ratio"] * pokemon.max_hp
                - state[0][index][0]
            )
            healing = max(
                (
                    move.value
                    for move in pokemon.moves
                    if move.name.upper() == "HEAL"
                ),
                default=0,
            )
            return ceil(max(missing_hp, 0) / healing) if healing > 0 else inf
        return inf

    targets = (
        tuple(range(len(opponent.pokemon)))
        if goal == "win"
        else tuple(
            index
            for index, pokemon in enumerate(opponent.pokemon)
            if f"{opponent.identity}:{index}:{pokemon.name}" == goal_object
        )
    )
    lower_bound = 0
    for target_index in targets:
        target = opponent.pokemon[target_index]
        hp = state[1][target_index][0]
        if hp <= 0:
            continue
        max_damage = 0.0
        for attacker in actor.pokemon:
            if attacker.hp <= 0:
                continue
            for move in attacker.moves:
                if move.name.upper() != "ATTACK":
                    continue
                multiplier = (
                    1.5
                    if (attacker.element, target.element) in type_advantages
                    else 1 / 1.5
                    if (target.element, attacker.element) in type_advantages
                    else 1
                )
                max_damage = max(max_damage, move.value * multiplier)
        if max_damage <= 0:
            return inf
        lower_bound += ceil(hp / max_damage)
    return lower_bound


def _simulated_successors(
    state, actor, opponent, goal, goal_object, type_advantages, simulate_move
):
    if goal == "recover":
        actor_indices = tuple(
            index
            for index, pokemon in enumerate(actor.pokemon)
            if f"{actor.identity}:{index}:{pokemon.name}" == goal_object
        )
    else:
        actor_indices = tuple(range(len(actor.pokemon)))

    for actor_index in actor_indices:
        actor_pokemon = actor.pokemon[actor_index]
        actor_hp, _, actor_pp = state[0][actor_index]
        if actor_hp <= 0:
            continue
        for move_index, move in enumerate(actor_pokemon.moves):
            if actor_pp[move_index] == 0:
                continue
            move_name = move.name.upper()
            if goal == "recover" and move_name not in ("HEAL", "REST"):
                continue
            if goal != "recover" and move_name not in ("ATTACK", "REST"):
                continue
            if move_name == "REST" and all(
                pp == available_move.max_pp
                for pp, available_move in zip(actor_pp, actor_pokemon.moves)
            ):
                continue

            if move_name == "ATTACK":
                if goal == "finish":
                    targets = tuple(
                        index
                        for index, pokemon in enumerate(opponent.pokemon)
                        if f"{opponent.identity}:{index}:{pokemon.name}"
                        == goal_object
                        and state[1][index][0] > 0
                    )
                else:
                    targets = tuple(
                        index
                        for index, values in enumerate(state[1])
                        if values[0] > 0
                    )
            else:
                targets = (actor_index,)

            for target_index in targets:
                next_actor_pokemon = _copy_with_state(
                    actor_pokemon, state[0][actor_index]
                )
                if move_name == "ATTACK":
                    next_target_pokemon = _copy_with_state(
                        opponent.pokemon[target_index], state[1][target_index]
                    )
                else:
                    next_target_pokemon = next_actor_pokemon
                simulate_move(
                    next_actor_pokemon,
                    next_target_pokemon,
                    move_index,
                )
                next_state = [list(state[0]), list(state[1])]
                next_state[0][actor_index] = _pokemon_state(next_actor_pokemon)
                if move_name == "ATTACK":
                    next_state[1][target_index] = _pokemon_state(
                        next_target_pokemon
                    )
                next_state = (tuple(next_state[0]), tuple(next_state[1]))

                actor_id = (
                    f"{actor.identity}:{actor_index}:{actor_pokemon.name}"
                )
                target_trainer = opponent if move_name == "ATTACK" else actor
                target_pokemon = target_trainer.pokemon[target_index]
                target_id = (
                    f"{target_trainer.identity}:{target_index}:"
                    f"{target_pokemon.name}"
                )
                if move_name == "ATTACK":
                    if (
                        actor_pokemon.element,
                        target_pokemon.element,
                    ) in type_advantages:
                        action_name = "attack-advantaged"
                    elif (
                        target_pokemon.element,
                        actor_pokemon.element,
                    ) in type_advantages:
                        action_name = "attack-resisted"
                    else:
                        action_name = "attack-neutral"
                    arguments = (actor_id, target_id)
                else:
                    action_name = move_name.lower()
                    arguments = (actor_id,)
                yield (
                    action_name,
                    arguments,
                    actor_index,
                    target_index,
                    move_index,
                    next_state,
                )


def _simulated_plan(
    actor,
    opponent,
    goal,
    goal_object,
    type_advantages,
    simulate_move,
    domain,
    static_facts,
    time_budget_ms,
    max_expansions,
):
    started = time.perf_counter()
    initial_state = (
        tuple(_pokemon_state(pokemon) for pokemon in actor.pokemon),
        tuple(_pokemon_state(pokemon) for pokemon in opponent.pokemon),
    )
    initial_heuristic = _goal_heuristic(
        initial_state, actor, opponent, goal, goal_object, type_advantages, domain
    )
    stats = {
        "expanded": 0,
        "generated": 0,
        "states": 1,
        "levels": 0,
        "action_mutexes": 0,
        "fact_mutexes": 0,
        "elapsed_ms": 0.0,
    }

    def finish(status, steps=(), reason=""):
        stats["elapsed_ms"] = (time.perf_counter() - started) * 1000
        return PlanResult(
            status=status,
            steps=tuple(steps),
            total_cost=float(len(steps)) if status == "plan" else 0,
            method="forward (simulated A*)",
            initial_heuristic=initial_heuristic,
            stats=dict(stats),
            reason=reason,
        )

    if _goal_reached(initial_state, actor, opponent, goal, goal_object, domain):
        return finish("plan")
    if initial_heuristic == inf:
        return finish("no-plan", reason="No legal action can reach the goal.")

    serial = 0
    frontier = [(initial_heuristic, 0, serial, initial_state)]
    best_cost = {initial_state: 0}
    parents = {}

    def build_steps(final_state):
        transitions = []
        current_state = final_state
        while current_state != initial_state:
            previous_state, transition = parents[current_state]
            transitions.append((previous_state, transition, current_state))
            current_state = previous_state
        transitions.reverse()
        steps = []
        previous_facts = _state_facts(
            actor, opponent, initial_state, static_facts, domain
        )
        for previous_state, transition, next_state in transitions:
            (
                action_name,
                arguments,
                actor_index,
                target_index,
                move_index,
            ) = transition
            next_facts = _state_facts(
                actor, opponent, next_state, static_facts, domain
            )
            actor_id = arguments[0]
            target_id = arguments[1] if len(arguments) > 1 else actor_id
            preconditions = tuple(
                sorted(
                    (
                        fact
                        for fact in previous_facts
                        if fact[1] in (actor_id, target_id)
                        and (
                            fact[0]
                            in (
                                "hp",
                                "hp-value",
                                "defense-value",
                                "pp-value",
                                "attack-ready",
                                "heal-ready",
                                "defend-ready",
                                "rest-ready",
                                "shielded",
                                "unshielded",
                            )
                            or (
                                fact[0] in ("advantage", "neutral", "resisted")
                                and fact[1:3] == (actor_id, target_id)
                            )
                        )
                    ),
                    key=lambda fact: tuple(str(part) for part in fact),
                )
            )
            action = Action(
                action_name,
                arguments,
                preconditions,
                tuple(sorted(next_facts - previous_facts, key=str)),
                tuple(sorted(previous_facts - next_facts, key=str)),
            )
            steps.append(PlanStep(action, next_facts, preconditions))
            previous_facts = next_facts
        return tuple(steps)

    while frontier:
        if (time.perf_counter() - started) * 1000 >= time_budget_ms:
            return finish("limit", reason="wall-clock budget exceeded")
        _, cost, _, state = heapq.heappop(frontier)
        if cost != best_cost.get(state):
            continue
        if _goal_reached(state, actor, opponent, goal, goal_object, domain):
            return finish("plan", build_steps(state))
        if stats["expanded"] >= max_expansions:
            return finish("limit", reason="maximum expansions exceeded")
        stats["expanded"] += 1
        for (
            action_name,
            arguments,
            actor_index,
            target_index,
            move_index,
            next_state,
        ) in _simulated_successors(
            state,
            actor,
            opponent,
            goal,
            goal_object,
            type_advantages,
            simulate_move,
        ):
            next_cost = cost + 1
            if next_state in best_cost and best_cost[next_state] <= next_cost:
                continue
            best_cost[next_state] = next_cost
            parents[next_state] = (
                state,
                (
                    action_name,
                    arguments,
                    actor_index,
                    target_index,
                    move_index,
                ),
            )
            stats["generated"] += 1
            serial += 1
            estimate = _goal_heuristic(
                next_state,
                actor,
                opponent,
                goal,
                goal_object,
                type_advantages,
                domain,
            )
            stats["states"] = len(best_cost)
            heapq.heappush(
                frontier,
                (next_cost + 2 * estimate, next_cost, serial, next_state),
            )
    return finish("no-plan", reason="frontier exhausted")


def plan_battle_turn(
    actor,
    opponent,
    inference_result,
    type_advantages,
    simulate_move,
    method="forward",
    max_expansions=2500,
    time_budget_ms=80,
):
    if method not in ("forward", "backward"):
        raise ValueError("method must be 'forward' or 'backward'.")
    started = time.perf_counter()
    domain = PlanningDomain.from_json(DOMAIN_PATH)
    observed_state, _, actor_pokemon_ids, opponent_ids = planning_observation(
        actor, opponent, type_advantages, domain
    )
    candidates = _goal_candidates(
        inference_result,
        actor.identity,
        actor_pokemon_ids,
        opponent_ids,
        domain,
    )
    if not candidates:
        return PlanningDecision(actor.identity, None, None, None, None, None)

    _, goal, goal_object, rule_id = candidates[0]
    result = _simulated_plan(
        actor,
        opponent,
        goal,
        goal_object,
        type_advantages,
        simulate_move,
        domain,
        observed_state,
        max(time_budget_ms - (time.perf_counter() - started) * 1000, 0),
        max_expansions,
    )
    if method == "backward":
        backward_notice = (
            "Exact battle simulation uses forward A* for either method setting."
        )
        result = PlanResult(
            status=result.status,
            steps=result.steps,
            total_cost=result.total_cost,
            method=result.method,
            initial_heuristic=result.initial_heuristic,
            stats=result.stats,
            reason=" ".join(
                part for part in (result.reason, backward_notice) if part
            ),
        )
    hint, reason = _first_step_hint(
        result,
        goal,
        goal_object,
        rule_id,
        actor,
        opponent,
        simulate_move,
        domain,
    )
    if result.status == "plan" and reason:
        result = type(result)(
            status=result.status,
            steps=result.steps,
            total_cost=result.total_cost,
            method=result.method,
            initial_heuristic=result.initial_heuristic,
            stats=result.stats,
            reason=" ".join(
                part for part in (result.reason, reason) if part
            ),
            regression_goal=result.regression_goal,
        )
    stats = dict(result.stats)
    stats["elapsed_ms"] = (time.perf_counter() - started) * 1000
    result = PlanResult(
        status=result.status,
        steps=result.steps,
        total_cost=result.total_cost,
        method=result.method,
        initial_heuristic=result.initial_heuristic,
        stats=stats,
        reason=result.reason,
    )
    return PlanningDecision(
        actor.identity,
        goal,
        goal_object,
        rule_id,
        result,
        hint,
    )
