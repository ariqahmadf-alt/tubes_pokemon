import unittest
from copy import deepcopy
from math import inf
from unittest.mock import patch

import battle
import battle_planning
import config
from battle_planning import hp_band
from planning import PlanResult


def fresh_pokemon(index):
    pokemon = deepcopy(battle.pokemons[index])
    pokemon.hp = pokemon.max_hp
    pokemon.defense = 0
    for move in pokemon.moves:
        move.pp = move.max_pp
    return pokemon


class BattlePlanningTests(unittest.TestCase):
    def setUp(self):
        self.previous_ai_type = config.ai_type
        self.previous_planning = config.use_planning
        self.previous_tolerance = config.plan_tolerance
        config.ai_type = "minimax"
        config.use_planning = True
        battle.player_trainer = battle.Trainer(
            "draft NPC A",
            [fresh_pokemon(0), fresh_pokemon(1), fresh_pokemon(2)],
            identity="NPC_A",
        )
        battle.rival_trainer = battle.Trainer(
            "draft NPC B",
            [fresh_pokemon(3), fresh_pokemon(4), fresh_pokemon(5)],
            identity="NPC_B",
        )
        battle.start_battle()

    def tearDown(self):
        config.ai_type = self.previous_ai_type
        config.use_planning = self.previous_planning
        config.plan_tolerance = self.previous_tolerance

    def decision(self, actor_id="NPC_A"):
        actor, opponent = battle._trainers_for(actor_id)
        inference_result = battle._refresh_inference()
        return battle.plan_battle_turn(
            actor,
            opponent,
            inference_result,
            battle.type_advantages,
            battle.simulate_move,
        )

    def test_low_hp_healable_teammate_selects_recovery_goal(self):
        battle.npc_a_trainer.pokemon[1].hp = 30

        decision = self.decision()

        self.assertEqual(decision.goal, "recover")
        self.assertEqual(decision.rule_id, "G1")
        self.assertEqual(decision.result.status, "plan")
        self.assertEqual(len(decision.result.steps), 2)
        self.assertIsNotNone(decision.hint)
        self.assertEqual(decision.hint.actor_index, 1)
        self.assertEqual(decision.hint.move_name, "HEAL")
        self.assertIn(
            (
                "hp-value",
                battle._pokemon_identity(battle.npc_a_trainer, 1),
                "50.0",
            ),
            decision.result.steps[0].state,
        )
        self.assertIn(
            (
                "hp-value",
                battle._pokemon_identity(battle.npc_a_trainer, 1),
                "70.0",
            ),
            decision.result.steps[-1].state,
        )

    def test_hp_band_boundary_matches_high_min_ratio(self):
        pokemon = fresh_pokemon(0)
        pokemon.hp = 70

        self.assertEqual(
            hp_band(
                pokemon,
                {"low_max_ratio": 0.3, "high_min_ratio": 0.7},
            ),
            "high",
        )

    def test_low_hp_enemy_selects_finish_goal(self):
        battle.player_trainer = battle.Trainer(
            "draft NPC A", [fresh_pokemon(0)], identity="NPC_A"
        )
        battle.rival_trainer = battle.Trainer(
            "draft NPC B", [fresh_pokemon(3)], identity="NPC_B"
        )
        battle.start_battle()
        battle.npc_b_trainer.pokemon[0].hp = 20

        decision = self.decision()

        self.assertEqual(decision.goal, "finish")
        self.assertEqual(decision.rule_id, "G2")
        self.assertEqual(
            decision.goal_object,
            battle._pokemon_identity(battle.npc_b_trainer, 0),
        )
        self.assertEqual(decision.result.status, "plan")
        self.assertEqual(len(decision.result.steps), 2)
        target_id = battle._pokemon_identity(battle.npc_b_trainer, 0)
        self.assertIn(
            ("hp-value", target_id, "5.0"),
            decision.result.steps[0].state,
        )
        self.assertIn(
            ("hp-value", target_id, "0.0"),
            decision.result.steps[-1].state,
        )

    def test_unpressured_enemy_team_selects_win_goal(self):
        for pokemon in battle.npc_a_trainer.pokemon + battle.npc_b_trainer.pokemon:
            pokemon.element = "poison"

        decision = self.decision()

        self.assertEqual(decision.goal, "win")
        self.assertIsNone(decision.goal_object)
        self.assertEqual(decision.rule_id, "G4")
        self.assertEqual(decision.result.status, "plan")
        self.assertGreater(len(decision.result.steps), 2)
        final_state = decision.result.steps[-1].state
        for index, pokemon in enumerate(battle.npc_b_trainer.pokemon):
            self.assertIn(
                (
                    "hp-value",
                    battle._pokemon_identity(battle.npc_b_trainer, index),
                    "0.0",
                ),
                final_state,
            )

    def test_unreachable_finish_goal_falls_back_to_reachable_win_goal(self):
        for pokemon in battle.npc_a_trainer.pokemon + battle.npc_b_trainer.pokemon:
            pokemon.element = "poison"
        battle.npc_b_trainer.pokemon[0].hp = 20
        real_planner = battle_planning._simulated_plan

        def reject_finish_goal(*args, **kwargs):
            if args[2] == "finish":
                return PlanResult(
                    status="no-plan",
                    steps=(),
                    total_cost=0,
                    method="forward (simulated A*)",
                    initial_heuristic=inf,
                    stats={"expanded": 0},
                    reason="forced unreachable finish goal",
                )
            return real_planner(*args, **kwargs)

        with patch(
            "battle_planning._simulated_plan",
            side_effect=reject_finish_goal,
        ):
            decision = self.decision()

        self.assertEqual(decision.goal, "win")
        self.assertEqual(decision.result.status, "plan")
        self.assertIsNotNone(decision.hint)

    def test_backward_setting_uses_exact_forward_simulation(self):
        actor, opponent = battle._trainers_for("NPC_B")
        result = battle._refresh_inference()

        decision = battle.plan_battle_turn(
            actor,
            opponent,
            result,
            battle.type_advantages,
            battle.simulate_move,
            method="backward",
        )

        self.assertEqual(decision.actor, "NPC_B")
        self.assertEqual(decision.result.status, "plan")
        self.assertEqual(decision.result.method, "forward (simulated A*)")
        self.assertIn("uses forward A*", decision.result.reason)

    def test_plan_hint_is_followed_when_within_search_tolerance(self):
        battle.npc_b_trainer.pokemon[0].hp = 20
        decision = self.decision()
        config.plan_tolerance = 1000000
        try:
            action = battle.choose_action(
                "NPC_A",
                mode="minimax",
                plan_hint=decision.hint,
            )
        finally:
            config.plan_tolerance = self.previous_tolerance

        self.assertEqual(action.actor_index, decision.hint.actor_index)
        self.assertEqual(action.target_index, decision.hint.target_index)
        self.assertTrue(battle.last_search["plan_followed"])

    def test_planner_accounts_for_multiple_hits_to_break_shield_and_finish(self):
        battle.npc_b_trainer.pokemon[0].hp = 20
        battle.npc_b_trainer.pokemon[0].defense = 30

        decision = self.decision()

        self.assertEqual(decision.result.status, "plan")
        self.assertEqual(len(decision.result.steps), 3)
        self.assertIsNotNone(decision.hint)
        states = [step.state for step in decision.result.steps]
        target_id = battle._pokemon_identity(battle.npc_b_trainer, 0)
        self.assertIn(("hp-value", target_id, "20.0"), states[0])
        self.assertIn(("defense-value", target_id, "15.0"), states[0])
        self.assertIn(("shielded", target_id), decision.result.steps[0].preconditions)
        self.assertIn(("hp-value", target_id, "20.0"), states[1])
        self.assertIn(("defense-value", target_id, "0.0"), states[1])
        self.assertIn(("hp-value", target_id, "0.0"), states[2])

    def test_planner_restores_spent_pp_before_reusing_a_move(self):
        battle.player_trainer = battle.Trainer(
            "draft NPC A", [fresh_pokemon(0)], identity="NPC_A"
        )
        battle.rival_trainer = battle.Trainer(
            "draft NPC B", [fresh_pokemon(3)], identity="NPC_B"
        )
        battle.start_battle()
        battle.npc_a_trainer.pokemon[0].moves[0].pp = 1
        battle.npc_b_trainer.pokemon[0].hp = 30

        decision = self.decision()

        self.assertEqual(decision.result.status, "plan")
        self.assertEqual(
            [step.action.name for step in decision.result.steps],
            ["attack-neutral", "rest", "attack-neutral"],
        )
        actor_id = battle._pokemon_identity(battle.npc_a_trainer, 0)
        self.assertIn(
            ("pp-value", actor_id, "ATTACK", 0),
            decision.result.steps[0].state,
        )
        self.assertIn(
            ("pp-value", actor_id, "ATTACK", 5),
            decision.result.steps[1].state,
        )

    def test_goal_selection_works_with_single_pokemon_rosters_for_either_npc(self):
        battle.player_trainer = battle.Trainer(
            "draft NPC A", [fresh_pokemon(0)], identity="NPC_A"
        )
        battle.rival_trainer = battle.Trainer(
            "draft NPC B", [fresh_pokemon(3)], identity="NPC_B"
        )
        battle.start_battle()
        for actor_id in ("NPC_A", "NPC_B"):
            with self.subTest(actor=actor_id):
                decision = self.decision(actor_id)
                self.assertEqual(decision.result.status, "plan")
                self.assertIsNotNone(decision.hint)

    def test_planner_handles_roster_sizes_one_through_three_for_both_npcs(self):
        for size in (1, 2, 3):
            battle.player_trainer = battle.Trainer(
                "draft NPC A",
                [fresh_pokemon(index) for index in range(size)],
                identity="NPC_A",
            )
            battle.rival_trainer = battle.Trainer(
                "draft NPC B",
                [fresh_pokemon(index + 3) for index in range(size)],
                identity="NPC_B",
            )
            battle.start_battle()
            for pokemon in battle.npc_a_trainer.pokemon + battle.npc_b_trainer.pokemon:
                pokemon.element = "poison"
            for actor_id in ("NPC_A", "NPC_B"):
                with self.subTest(size=size, actor=actor_id):
                    decision = self.decision(actor_id)
                    self.assertEqual(decision.result.status, "plan")
                    self.assertIsNotNone(decision.hint)
                    self.assertLess(decision.hint.actor_index, size)
                    self.assertLess(decision.hint.target_index, size)

    def test_fainted_pokemon_are_not_grounded_as_plan_actors_or_targets(self):
        battle.npc_a_trainer.pokemon[0].hp = 0
        battle.npc_b_trainer.pokemon[0].hp = 0
        for pokemon in battle.npc_a_trainer.pokemon + battle.npc_b_trainer.pokemon:
            pokemon.element = "poison"

        decision = self.decision()

        self.assertEqual(decision.result.status, "plan")
        planned_actor, planned_target = decision.result.steps[0].action.arguments[:2]
        self.assertNotEqual(
            planned_actor,
            battle._pokemon_identity(battle.npc_a_trainer, 0),
        )
        self.assertNotEqual(
            planned_target,
            battle._pokemon_identity(battle.npc_b_trainer, 0),
        )


if __name__ == "__main__":
    unittest.main()
