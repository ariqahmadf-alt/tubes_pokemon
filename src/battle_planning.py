"""Translate battle observations and KB goals into grounded planning problems."""

from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
import time

from battle_interaction import PlanHint
from planning import (
    PlanningDomain,
    PlanResult,
    PlanningGraph,
    forward_search,
    ground_actions,
    planning_graph,
    regression_search,
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
    graph: PlanningGraph | None


def hp_band(pokemon, bands):
    if pokemon.hp <= 0:
        return "gone"
    ratio = pokemon.hp / pokemon.max_hp
    if ratio <= bands["low_max_ratio"]:
        return "low"
    if ratio <= bands["high_min_ratio"]:
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


def _goal_candidates(inference_result, actor_id, opponent_ids, domain):
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
        candidates.append(
            (priorities[goal], goal, goal_object, derivation.rule_id)
        )
    return tuple(
        sorted(
            candidates,
            key=lambda item: (item[0], item[1], item[3], item[2]),
        )
    )


def _goal_facts(goal, goal_object, opponent_ids):
    if goal == "recover":
        return frozenset({("hp", goal_object, "high")})
    if goal == "finish":
        return frozenset({("hp", goal_object, "gone")})
    if goal == "win":
        return frozenset(("hp", identity, "gone") for identity in opponent_ids)
    raise ValueError(f"Unknown battle planning goal: {goal}")


def _scope_problem(state, objects, actor_ids, opponent_ids, goal, goal_object):
    if goal == "recover":
        planning_actors = (goal_object,)
        planning_targets = ()
        schema_names = {"heal"}
    elif goal == "finish":
        planning_actors = actor_ids
        planning_targets = (goal_object,)
        schema_names = {
            "attack-advantaged",
            "attack-neutral",
            "attack-resisted",
            "break-shield",
            "rest",
        }
    else:
        planning_actors = actor_ids
        planning_targets = opponent_ids
        schema_names = {
            "attack-advantaged",
            "attack-neutral",
            "attack-resisted",
            "break-shield",
            "rest",
        }

    actor_set = set(planning_actors)
    target_set = set(planning_targets)
    state_target_set = (
        {goal_object} if goal == "recover" else target_set
    )
    relevant_ids = actor_set | target_set
    scoped_facts = set()
    for fact in state:
        predicate = fact[0]
        if predicate in ("drop", "raise"):
            scoped_facts.add(fact)
        elif predicate in ("advantage", "neutral", "resisted"):
            if fact[1] in actor_set and fact[2] in target_set:
                scoped_facts.add(fact)
        elif predicate in ("hp", "shielded", "unshielded"):
            if fact[1] in state_target_set:
                scoped_facts.add(fact)
        elif predicate in (
            "attack-ready",
            "heal-ready",
            "defend-ready",
            "rest-ready",
        ):
            if fact[1] in actor_set:
                scoped_facts.add(fact)

    scoped_objects = {
        "pokemon": tuple(sorted(relevant_ids)),
        "actor-pokemon": tuple(sorted(actor_set)),
        "enemy-pokemon": tuple(sorted(target_set)),
        "band": objects["band"],
    }
    return frozenset(scoped_facts), scoped_objects, schema_names


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
    if action.name.startswith("attack-") or action.name == "break-shield":
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
        original_target = opponent.pokemon[target_index]
        target_trainer = next_opponent
    else:
        original_target = actor.pokemon[target_index]
        target_trainer = next_actor
    next_target = target_trainer.pokemon[target_index]
    simulate_move(next_user, next_target, move_index)

    predicted_state = plan_result.steps[0].state
    target_expected = next(
        (
            fact[2]
            for fact in predicted_state
            if fact[:2] == ("hp", target_id)
        ),
        None,
    )
    if target_expected and action.name != "break-shield":
        actual_band = hp_band(next_target, domain.hp_bands)
        prior_band = hp_band(original_target, domain.hp_bands)
        band_order = {"gone": 0, "low": 1, "mid": 2, "high": 3}
        if move_name == "ATTACK":
            agrees = (
                next_target.hp < original_target.hp
                and (
                    actual_band == target_expected
                    or band_order[actual_band] < band_order[target_expected]
                    or actual_band == prior_band
                )
            )
        elif move_name == "HEAL":
            agrees = (
                next_target.hp > original_target.hp
                and (
                    actual_band == target_expected
                    or band_order[actual_band] > band_order[target_expected]
                    or actual_band == prior_band
                )
            )
        else:
            agrees = actual_band == target_expected
        if not agrees:
            return None, (
                "Dry run disagreed with the planned HP band: "
                f"expected {target_expected}, got {actual_band}."
            )
    if action.name == "defend" and next_target.defense <= 0:
        return None, "Dry run did not produce the planned shield."
    if action.name == "break-shield" and next_target.defense > 0:
        return None, "Dry run did not break the planned shield."

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


def plan_battle_turn(
    actor,
    opponent,
    inference_result,
    type_advantages,
    simulate_move,
    method="forward",
    heuristic="h_add",
    max_expansions=2500,
    time_budget_ms=80,
):
    if method not in ("forward", "backward"):
        raise ValueError("method must be 'forward' or 'backward'.")
    started = time.perf_counter()
    domain = PlanningDomain.from_json(DOMAIN_PATH)
    initial_state, objects, _, opponent_ids = planning_observation(
        actor, opponent, type_advantages, domain
    )
    candidates = _goal_candidates(inference_result, actor.identity, opponent_ids, domain)
    if not candidates:
        return PlanningDecision(actor.identity, None, None, None, None, None, None)

    _, goal, goal_object, rule_id = candidates[0]
    goal_facts = _goal_facts(goal, goal_object, opponent_ids)
    actor_ids = tuple(
        f"{actor.identity}:{index}:{pokemon.name}"
        for index, pokemon in enumerate(actor.pokemon)
    )
    initial_state, objects, schema_names = _scope_problem(
        initial_state,
        objects,
        actor_ids,
        opponent_ids,
        goal,
        goal_object,
    )
    actions = ground_actions(
        tuple(schema for schema in domain.schemas if schema.name in schema_names),
        objects,
        initial_state,
        domain.static_predicates,
    )
    graph = planning_graph(
        initial_state,
        goal_facts,
        actions,
        max_levels=domain.max_graph_levels,
    )
    if method == "backward":
        result = regression_search(
            initial_state,
            goal_facts,
            actions,
            max_expansions=max_expansions,
            time_budget_ms=max(
                time_budget_ms - (time.perf_counter() - started) * 1000, 0
            ),
            static_predicates=domain.static_predicates,
            graph=graph,
        )
    else:
        result = forward_search(
            initial_state,
            goal_facts,
            actions,
            method="astar",
            max_expansions=max_expansions,
            time_budget_ms=max(
                time_budget_ms - (time.perf_counter() - started) * 1000, 0
            ),
            static_predicates=domain.static_predicates,
            graph=graph,
            heuristic=heuristic,
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
            reason=reason,
            regression_goal=result.regression_goal,
        )
    stats = dict(result.stats)
    stats["elapsed_ms"] = (time.perf_counter() - started) * 1000
    result = type(result)(
        status=result.status,
        steps=result.steps,
        total_cost=result.total_cost,
        method=("forward (A*)" if method == "forward" else "backward (regression)"),
        initial_heuristic=result.initial_heuristic,
        stats=stats,
        reason=result.reason,
        regression_goal=result.regression_goal,
    )
    return PlanningDecision(
        actor.identity,
        goal,
        goal_object,
        rule_id,
        result,
        hint,
        graph,
    )
