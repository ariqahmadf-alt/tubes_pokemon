"""Deterministic STRIPS planning with bounded forward and regression search.

The relaxed-plan heuristic uses delete relaxation and maximum proposition cost
(h_max), so it is admissible for non-negative action costs. Planning graphs use
standard no-op propagation and pairwise mutex tests.
"""

from dataclasses import dataclass
from itertools import product
import json
from pathlib import Path
import time


Fact = tuple[str, ...]
State = frozenset[Fact]


@dataclass(frozen=True)
class ActionSchema:
    name: str
    parameters: tuple[tuple[str, str], ...]
    preconditions: tuple[Fact, ...]
    add_effects: tuple[Fact, ...]
    delete_effects: tuple[Fact, ...]
    cost: float = 1


@dataclass(frozen=True)
class Action:
    name: str
    arguments: tuple[str, ...]
    preconditions: tuple[Fact, ...]
    add_effects: tuple[Fact, ...]
    delete_effects: tuple[Fact, ...]
    cost: float = 1

    def __str__(self):
        return f"{self.name}({', '.join(self.arguments)})"


@dataclass(frozen=True)
class PlanStep:
    action: Action
    state: State
    preconditions: tuple[Fact, ...]


@dataclass(frozen=True)
class PlanResult:
    status: str
    steps: tuple[PlanStep, ...]
    total_cost: float
    method: str
    initial_heuristic: float
    stats: dict
    reason: str = ""
    regression_goal: State | None = None


@dataclass(frozen=True)
class PlanningGraph:
    levels: tuple[State, ...]
    fact_mutexes: tuple[frozenset[frozenset[Fact]], ...]
    action_mutexes: tuple[frozenset[frozenset[Action]], ...]
    action_mutex_counts: tuple[int, ...]
    unreachable: bool
    goal_level: int | None


def _read_facts(values):
    return tuple(tuple(value) for value in values)


@dataclass(frozen=True)
class PlanningDomain:
    schemas: tuple[ActionSchema, ...]
    static_predicates: frozenset[str]
    goal_priority: tuple[str, ...]
    hp_bands: dict
    max_graph_levels: int = 18

    @classmethod
    def from_json(cls, path):
        with Path(path).open(encoding="utf-8") as domain_file:
            data = json.load(domain_file)
        schemas = tuple(
            ActionSchema(
                name=item["name"],
                parameters=tuple(item["parameters"].items()),
                preconditions=_read_facts(item.get("preconditions", ())),
                add_effects=_read_facts(item.get("add_effects", ())),
                delete_effects=_read_facts(item.get("delete_effects", ())),
                cost=float(item.get("cost", 1)),
            )
            for item in data["actions"]
        )
        return cls(
            schemas=schemas,
            static_predicates=frozenset(data.get("static_predicates", ())),
            goal_priority=tuple(data.get("goal_priority", ())),
            hp_bands=dict(data.get("hp_bands", {})),
            max_graph_levels=int(data.get("max_graph_levels", 18)),
        )


def _sort_fact(fact):
    return tuple(str(part) for part in fact)


def _sort_action(action):
    return (action.name, action.arguments)


def _substitute(fact, bindings):
    return tuple(bindings.get(term, term) for term in fact)


def _is_static(fact, static_predicates):
    return bool(fact) and fact[0] in static_predicates


def ground_actions(schemas, objects, initial_state, static_predicates=()):
    """Ground schemas deterministically and discard false static preconditions."""
    initial_state = frozenset(initial_state)
    static_predicates = frozenset(static_predicates)
    grounded = []
    for schema in sorted(schemas, key=lambda item: item.name):
        domains = [
            tuple(sorted(objects.get(parameter_type, ())))
            for _, parameter_type in schema.parameters
        ]
        if any(not values for values in domains):
            continue
        assignments = product(*domains) if domains else [()]
        for values in assignments:
            bindings = {
                parameter: value
                for (parameter, _), value in zip(schema.parameters, values)
            }
            preconditions = tuple(
                sorted(
                    (_substitute(fact, bindings) for fact in schema.preconditions),
                    key=_sort_fact,
                )
            )
            if any(
                _is_static(fact, static_predicates) and fact not in initial_state
                for fact in preconditions
            ):
                continue
            grounded.append(
                Action(
                    schema.name,
                    tuple(values),
                    preconditions,
                    tuple(
                        sorted(
                            (_substitute(fact, bindings) for fact in schema.add_effects),
                            key=_sort_fact,
                        )
                    ),
                    tuple(
                        sorted(
                            (_substitute(fact, bindings) for fact in schema.delete_effects),
                            key=_sort_fact,
                        )
                    ),
                    schema.cost,
                )
            )
    return tuple(sorted(grounded, key=_sort_action))


def applicable(state, action):
    return all(fact in state for fact in action.preconditions)


def result(state, action):
    if not applicable(state, action):
        missing = tuple(
            fact for fact in action.preconditions if fact not in state
        )
        raise ValueError(f"Action {action} is not applicable; missing {missing}.")
    return frozenset((set(state) - set(action.delete_effects)) | set(action.add_effects))


def validate_plan(initial_state, plan):
    """Return each state after a step, stopping with a missing-precondition report."""
    states = [frozenset(initial_state)]
    for index, action in enumerate(plan):
        state = states[-1]
        missing = tuple(fact for fact in action.preconditions if fact not in state)
        if missing:
            return tuple(states), {
                "valid": False,
                "step": index,
                "action": action,
                "missing": missing,
            }
        states.append(result(state, action))
    return tuple(states), {"valid": True, "step": None, "action": None, "missing": ()}


def _relaxed_h_max(state, goal, actions):
    if goal.issubset(state):
        return 0
    costs = {fact: 0.0 for fact in state}
    changed = True
    while changed:
        changed = False
        for action in actions:
            if any(fact not in costs for fact in action.preconditions):
                continue
            action_cost = action.cost + max(
                (costs[fact] for fact in action.preconditions), default=0.0
            )
            for fact in action.add_effects:
                if fact not in costs or action_cost < costs[fact]:
                    costs[fact] = action_cost
                    changed = True
    if any(fact not in costs for fact in goal):
        return float("inf")
    return max((costs[fact] for fact in goal), default=0.0)


def ignore_delete_lists_h_add(state, goal, actions):
    """Return h_add from delete relaxation; it is informative but not admissible."""
    if goal.issubset(state):
        return 0.0
    costs = {fact: 0.0 for fact in state}
    changed = True
    while changed:
        changed = False
        for action in actions:
            if any(fact not in costs for fact in action.preconditions):
                continue
            action_cost = action.cost + sum(
                costs[fact] for fact in action.preconditions
            )
            for fact in action.add_effects:
                if fact not in costs or action_cost < costs[fact]:
                    costs[fact] = action_cost
                    changed = True
    if any(fact not in costs for fact in goal):
        return float("inf")
    return sum(costs[fact] for fact in goal)


def ignore_delete_lists_heuristic(state, goal, actions):
    """Delete-relaxed h_max; admissible with non-negative action costs."""
    return _relaxed_h_max(state, goal, actions)


def _make_steps(initial_state, actions):
    states, validation = validate_plan(initial_state, actions)
    if not validation["valid"]:
        raise ValueError(f"Planner produced an invalid plan: {validation}.")
    return tuple(
        PlanStep(action, states[index + 1], action.preconditions)
        for index, action in enumerate(actions)
    )


def _result(
    status,
    initial_state,
    goal,
    actions,
    method,
    initial_heuristic,
    stats,
    reason="",
    regression_goal=None,
):
    return PlanResult(
        status=status,
        steps=_make_steps(initial_state, actions) if status == "plan" else (),
        total_cost=sum(action.cost for action in actions) if status == "plan" else 0,
        method=method,
        initial_heuristic=initial_heuristic,
        stats=stats,
        reason=reason,
        regression_goal=regression_goal,
    )


def planning_graph(initial_state, goal, actions, max_levels=18):
    """Build a bounded planning graph and identify the first non-mutex goal level."""
    initial_state = frozenset(initial_state)
    goal = frozenset(goal)
    levels = [initial_state]
    fact_mutex_levels = [frozenset()]
    action_mutex_levels = []
    action_mutex_counts = []
    goal_level = 0 if goal.issubset(initial_state) else None
    levelled_off = False
    if goal_level is not None and _goals_non_mutex(goal, fact_mutex_levels[0]):
        return PlanningGraph(
            tuple(levels), tuple(fact_mutex_levels), (), (), False, goal_level
        )

    for _ in range(max_levels):
        facts = levels[-1]
        fact_mutex = fact_mutex_levels[-1]
        applicable_actions = [
            action for action in actions if applicable(facts, action)
        ]
        graph_actions = list(applicable_actions)
        graph_actions.extend(
            Action(
                "no-op",
                fact,
                (fact,),
                (fact,),
                (),
                0,
            )
            for fact in sorted(facts, key=_sort_fact)
        )
        graph_actions.sort(key=_sort_action)

        mutex = set()
        for first_index, first in enumerate(graph_actions):
            first_pre = set(first.preconditions)
            first_add = set(first.add_effects)
            first_delete = set(first.delete_effects)
            for second in graph_actions[first_index + 1 :]:
                second_pre = set(second.preconditions)
                second_add = set(second.add_effects)
                second_delete = set(second.delete_effects)
                inconsistent_effects = bool(
                    first_add & second_delete or second_add & first_delete
                )
                interference = bool(
                    first_delete & (second_pre | second_add)
                    or second_delete & (first_pre | first_add)
                )
                competing_needs = any(
                    frozenset((a, b)) in fact_mutex
                    for a in first_pre
                    for b in second_pre
                    if a != b
                )
                if inconsistent_effects or interference or competing_needs:
                    mutex.add(frozenset((first, second)))
        action_mutex_counts.append(len(mutex))
        action_mutex_levels.append(frozenset(mutex))

        next_facts = frozenset(
            set().union(*(set(action.add_effects) for action in graph_actions))
        )
        producers = {
            fact: [
                action
                for action in graph_actions
                if fact in action.add_effects
            ]
            for fact in next_facts
        }
        next_mutex = set()
        ordered_facts = sorted(next_facts, key=_sort_fact)
        for first_index, first_fact in enumerate(ordered_facts):
            for second_fact in ordered_facts[first_index + 1 :]:
                first_producers = producers[first_fact]
                second_producers = producers[second_fact]
                if not any(
                    frozenset((first_action, second_action)) not in mutex
                    for first_action in first_producers
                    for second_action in second_producers
                ):
                    next_mutex.add(frozenset((first_fact, second_fact)))
        levels.append(next_facts)
        fact_mutex_levels.append(frozenset(next_mutex))

        if goal.issubset(next_facts) and _goals_non_mutex(goal, next_mutex):
            goal_level = len(levels) - 1
            break
        if (
            next_facts == facts
            and next_mutex == set(fact_mutex)
        ):
            levelled_off = True
            break

    reachable = goal_level is not None
    return PlanningGraph(
        tuple(levels),
        tuple(fact_mutex_levels),
        tuple(action_mutex_levels),
        tuple(action_mutex_counts),
        levelled_off and not reachable,
        goal_level,
    )


def _goals_non_mutex(goal, mutexes):
    return all(
        frozenset((first, second)) not in mutexes
        for index, first in enumerate(sorted(goal, key=_sort_fact))
        for second in sorted(goal, key=_sort_fact)[index + 1 :]
    )


def _timed_out(start, time_budget_ms):
    return time_budget_ms is not None and (
        (time.perf_counter() - start) * 1000 >= time_budget_ms
    )


def forward_search(
    initial_state,
    goal,
    actions,
    method="astar",
    max_expansions=10000,
    time_budget_ms=50,
    static_predicates=(),
    graph=None,
    heuristic="h_max",
):
    """Find a plan using BFS or A*, returning explicit no-plan/limit results."""
    start = time.perf_counter()
    initial_state = frozenset(initial_state)
    goal = frozenset(goal)
    actions = tuple(sorted(actions, key=_sort_action))
    graph = graph or planning_graph(initial_state, goal, actions)
    if heuristic not in ("h_max", "h_add"):
        raise ValueError("heuristic must be 'h_max' or 'h_add'.")
    estimate = (
        _relaxed_h_max
        if heuristic == "h_max"
        else ignore_delete_lists_h_add
    )
    relaxed_h0 = estimate(initial_state, goal, actions)
    graph_h0 = graph.goal_level or 0
    h0 = max(relaxed_h0, graph_h0)
    stats = {
        "expanded": 0,
        "generated": 0,
        "levels": max(len(graph.levels) - 1, 0),
        "action_mutexes": sum(graph.action_mutex_counts),
        "fact_mutexes": sum(len(level) for level in graph.fact_mutexes),
        "elapsed_ms": 0.0,
    }

    def finish(status, path=(), reason=""):
        stats["elapsed_ms"] = (time.perf_counter() - start) * 1000
        return _result(
            status, initial_state, goal, path, method, h0, dict(stats), reason
        )

    if goal.issubset(initial_state):
        return finish("plan")
    if graph.unreachable:
        return finish("no-plan", reason="unreachable by planning graph")
    if relaxed_h0 == float("inf"):
        return finish("no-plan", reason="goal is unreachable under delete relaxation")
    if method not in ("bfs", "astar"):
        raise ValueError("method must be 'bfs' or 'astar'.")

    serial = 0
    frontier = [
        (h0 if method == "astar" else 0.0, serial, initial_state, ())
    ]
    best_cost = {initial_state: 0.0}
    while frontier:
        if _timed_out(start, time_budget_ms):
            return finish("limit", reason="wall-clock budget exceeded")
        _, _, state, path = frontier.pop(0)
        path_cost = (
            sum(action.cost for action in path)
            if method == "astar"
            else len(path)
        )
        if path_cost != best_cost.get(state):
            continue
        if goal.issubset(state):
            return finish("plan", path)
        if stats["expanded"] >= max_expansions:
            return finish("limit", reason="maximum expansions exceeded")
        stats["expanded"] += 1
        for action in actions:
            if not applicable(state, action):
                continue
            next_state = result(state, action)
            next_cost = best_cost[state] + (
                action.cost if method == "astar" else 1
            )
            if next_state in best_cost and best_cost[next_state] <= next_cost:
                continue
            best_cost[next_state] = next_cost
            next_path = path + (action,)
            stats["generated"] += 1
            serial += 1
            if method == "bfs" and goal.issubset(next_state):
                return finish("plan", next_path)
            priority = (
                len(next_path)
                if method == "bfs"
                else next_cost + estimate(next_state, goal, actions)
            )
            item = (priority, serial, next_state, next_path)
            if method == "bfs":
                frontier.append(item)
            else:
                insert_at = len(frontier)
                while insert_at and frontier[insert_at - 1][:2] > item[:2]:
                    insert_at -= 1
                frontier.insert(insert_at, item)
    return finish("no-plan", reason="frontier exhausted")


def regression_search(
    initial_state,
    goal,
    actions,
    max_expansions=10000,
    time_budget_ms=50,
    static_predicates=(),
    graph=None,
):
    """Search backward using relevant, consistent actions and STRIPS regression."""
    start = time.perf_counter()
    initial_state = frozenset(initial_state)
    initial_static = frozenset(
        fact
        for fact in initial_state
        if _is_static(fact, static_predicates)
    )
    goal = frozenset(goal)
    actions = tuple(sorted(actions, key=_sort_action))
    graph = graph or planning_graph(initial_state, goal, actions)
    h0 = max(
        _relaxed_h_max(initial_state, goal, actions),
        graph.goal_level or 0,
    )
    stats = {
        "expanded": 0,
        "generated": 0,
        "levels": max(len(graph.levels) - 1, 0),
        "action_mutexes": sum(graph.action_mutex_counts),
        "fact_mutexes": sum(len(level) for level in graph.fact_mutexes),
        "elapsed_ms": 0.0,
    }

    def finish(status, path=(), reason="", regressed_goal=None):
        stats["elapsed_ms"] = (time.perf_counter() - start) * 1000
        return _result(
            status,
            initial_state,
            goal,
            path,
            "backward",
            h0,
            dict(stats),
            reason,
            regressed_goal,
        )

    if goal.issubset(initial_state):
        return finish("plan", regressed_goal=goal)
    if graph.unreachable or h0 == float("inf"):
        return finish("no-plan", reason="unreachable by planning graph")

    serial = 0
    frontier = [(0, serial, goal, ())]
    visited = {goal}
    while frontier:
        if _timed_out(start, time_budget_ms):
            return finish("limit", reason="wall-clock budget exceeded")
        _, _, subgoal, reverse_path = frontier.pop(0)
        if subgoal.issubset(initial_state):
            return finish(
                "plan",
                tuple(reversed(reverse_path)),
                regressed_goal=subgoal,
            )
        if stats["expanded"] >= max_expansions:
            return finish("limit", reason="maximum expansions exceeded")
        stats["expanded"] += 1
        for action in actions:
            additions = set(action.add_effects)
            deletions = set(action.delete_effects)
            if not (additions & set(subgoal)):
                continue
            if deletions & set(subgoal):
                continue
            regressed = (
                set(subgoal) - additions
            ) | {
                fact
                for fact in action.preconditions
                if not _is_static(fact, static_predicates)
            }
            if any(
                _is_static(fact, static_predicates) and fact not in initial_static
                for fact in action.preconditions
            ):
                continue
            regressed_state = frozenset(regressed)
            if regressed_state in visited:
                continue
            visited.add(regressed_state)
            stats["generated"] += 1
            serial += 1
            next_path = reverse_path + (action,)
            if regressed_state.issubset(initial_state):
                return finish(
                    "plan",
                    tuple(reversed(next_path)),
                    regressed_goal=regressed_state,
                )
            frontier.append((len(next_path), serial, regressed_state, next_path))
    return finish("no-plan", reason="regression frontier exhausted")
