"""Expected-utility evaluation for rival-team selection.

The player roster is known, but which player Pokemon will be the relevant
matchup is not. With no usage history available, scenarios use a uniform prior
over that roster. This is an explicit modeling assumption, not observed data.
"""

from dataclasses import dataclass
import math
from typing import Collection, Protocol, Sequence, Tuple


PROBABILITY_SOURCE = (
    "Uniform prior over the player's current roster; no usage history is available."
)
PROBABILITY_TOLERANCE = 1e-9


class PokemonMatchup(Protocol):
    name: str
    element: str


@dataclass(frozen=True)
class UtilityScenario:
    name: str
    probability: float
    utility: float


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    probability: float
    matchup_margin: int
    utility: float
    contribution: float


@dataclass(frozen=True)
class TeamEvaluation:
    scenarios: Tuple[ScenarioResult, ...]
    expected_utility: float

    @property
    def probabilities_normalized(self):
        return math.isclose(
            sum(scenario.probability for scenario in self.scenarios),
            1.0,
            rel_tol=0.0,
            abs_tol=PROBABILITY_TOLERANCE,
        )


def calculate_expected_utility(scenarios: Sequence[UtilityScenario]) -> float:
    """Return sum(P(outcome) * utility), rejecting invalid probability models."""
    if not scenarios:
        raise ValueError("Expected utility requires at least one scenario.")

    probability_total = 0.0
    expected_utility = 0.0
    for scenario in scenarios:
        probability = scenario.probability
        utility = scenario.utility
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("Scenario probabilities must be finite values in [0, 1].")
        if not math.isfinite(utility):
            raise ValueError("Scenario utilities must be finite.")
        probability_total += probability
        expected_utility += probability * utility

    if not math.isclose(
        probability_total,
        1.0,
        rel_tol=0.0,
        abs_tol=PROBABILITY_TOLERANCE,
    ):
        raise ValueError("Scenario probabilities must sum to 1.")
    return expected_utility


def evaluate_team(
    team: Sequence[PokemonMatchup],
    player_team: Sequence[PokemonMatchup],
    type_advantages: Collection[Tuple[str, str]],
) -> TeamEvaluation:
    """Evaluate balance across equally likely opposing active-Pokemon scenarios.

    A positive matchup margin means the rival team has more type advantages;
    a negative margin means the player has more. Utility is the negative
    absolute margin, so zero is balanced and increasingly extreme matchups
    receive lower utility.
    """
    if not player_team:
        raise ValueError("Cannot evaluate uncertainty without a player roster.")

    scenario_probability = 1.0 / len(player_team)
    scenarios = []
    matchup_margins = []
    for player_pokemon in player_team:
        margin = sum(
            int((rival_pokemon.element, player_pokemon.element) in type_advantages)
            - int((player_pokemon.element, rival_pokemon.element) in type_advantages)
            for rival_pokemon in team
        )
        utility = -abs(margin)
        scenarios.append(
            UtilityScenario(
                f"Player's {player_pokemon.name}",
                scenario_probability,
                utility,
            )
        )
        matchup_margins.append(margin)

    # Assign any floating-point remainder to the last outcome so the model is
    # normalized even for roster sizes whose reciprocal is not exactly binary.
    scenarios[-1] = UtilityScenario(
        scenarios[-1].name,
        1.0 - sum(item.probability for item in scenarios[:-1]),
        scenarios[-1].utility,
    )
    expected_utility = calculate_expected_utility(scenarios)
    results = tuple(
        ScenarioResult(
            name=scenario.name,
            probability=scenario.probability,
            matchup_margin=matchup_margins[index],
            utility=scenario.utility,
            contribution=scenario.probability * scenario.utility,
        )
        for index, scenario in enumerate(scenarios)
    )
    return TeamEvaluation(results, expected_utility)
