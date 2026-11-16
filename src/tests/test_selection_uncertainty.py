import unittest
from types import SimpleNamespace

from uncertainty import (
    UtilityScenario,
    calculate_expected_utility,
    evaluate_team,
)


class SelectionUncertaintyTests(unittest.TestCase):
    def test_expected_utility_matches_weighted_outcome_example(self):
        result = calculate_expected_utility(
            [
                UtilityScenario("on time", 0.9, 10),
                UtilityScenario("delayed", 0.1, -20),
            ]
        )

        self.assertAlmostEqual(result, 7.0)

    def test_probabilities_must_be_valid_and_normalized(self):
        with self.assertRaises(ValueError):
            calculate_expected_utility(
                [
                    UtilityScenario("first", 0.9, 1),
                    UtilityScenario("second", 0.2, 1),
                ]
            )
        with self.assertRaises(ValueError):
            calculate_expected_utility([UtilityScenario("invalid", -0.1, 1)])
        with self.assertRaises(ValueError):
            calculate_expected_utility(
                [UtilityScenario("non-finite", float("nan"), 1)]
            )

    def test_maximum_expected_utility_prefers_the_higher_candidate(self):
        candidates = {
            "A": [UtilityScenario("good", 0.9, 10), UtilityScenario("bad", 0.1, -20)],
            "B": [UtilityScenario("certain", 1.0, 6)],
        }
        self.assertEqual(
            max(candidates, key=lambda name: calculate_expected_utility(candidates[name])),
            "A",
        )

        candidates["A"], candidates["B"] = candidates["B"], candidates["A"]
        self.assertEqual(
            max(candidates, key=lambda name: calculate_expected_utility(candidates[name])),
            "B",
        )

    def test_expected_balance_can_change_the_deterministic_matchup_ranking(self):
        player_team = [
            SimpleNamespace(name="Flare", element="fire"),
            SimpleNamespace(name="Brook", element="water"),
            SimpleNamespace(name="Moss", element="grass"),
        ]
        type_advantages = {("grass", "water")}
        grass_team = [SimpleNamespace(name="Leaf", element="grass")]
        fire_team = [SimpleNamespace(name="Flareon", element="fire")]

        grass_evaluation = evaluate_team(
            grass_team, player_team, type_advantages
        )
        fire_evaluation = evaluate_team(fire_team, player_team, type_advantages)

        self.assertTrue(grass_evaluation.probabilities_normalized)
        self.assertAlmostEqual(
            sum(scenario.probability for scenario in grass_evaluation.scenarios),
            1.0,
        )
        self.assertLess(grass_evaluation.expected_utility, fire_evaluation.expected_utility)


if __name__ == "__main__":
    unittest.main()
