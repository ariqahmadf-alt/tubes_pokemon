import unittest
from copy import deepcopy

import battle
import config
from knowledge_base import Atom


def fresh_pokemon(index):
    pokemon = deepcopy(battle.pokemons[index])
    pokemon.hp = pokemon.max_hp
    pokemon.defense = 0
    for move in pokemon.moves:
        move.pp = move.max_pp
    return pokemon


class TwoNPCBattleTests(unittest.TestCase):
    def setUp(self):
        self.previous_ai_type = config.ai_type
        config.ai_type = "minimax"
        battle.player_trainer = battle.Trainer(
            "draft NPC A", [fresh_pokemon(0), fresh_pokemon(1)]
        )
        battle.rival_trainer = battle.Trainer(
            "draft NPC B", [fresh_pokemon(3), fresh_pokemon(4)]
        )
        battle.rival = battle.rival_trainer.pokemon[0]
        battle.start_battle()

    def tearDown(self):
        config.ai_type = self.previous_ai_type

    def test_battle_state_has_only_two_independent_npc_participants(self):
        self.assertIsNone(battle.player_trainer)
        self.assertIsNone(battle.rival_trainer)
        self.assertFalse(hasattr(battle, "player"))
        self.assertEqual(
            {battle.npc_a_trainer.identity, battle.npc_b_trainer.identity},
            {"NPC_A", "NPC_B"},
        )
        self.assertIsNot(battle.npc_a_trainer.active, battle.npc_b_trainer.active)

    def test_space_step_advances_one_alternating_npc_action(self):
        self.assertEqual(battle.current_agent, "NPC_A")
        self.assertTrue(battle.advance_battle())
        self.assertEqual(battle.turn_count, 1)
        self.assertEqual(battle.current_agent, "NPC_B")
        self.assertTrue(battle.advance_battle())
        self.assertEqual(battle.turn_count, 2)
        self.assertEqual(battle.current_agent, "NPC_A")

    def test_alpha_beta_preserves_minimax_scores_for_both_roles(self):
        state_a = deepcopy(battle.npc_a_trainer)
        state_b = deepcopy(battle.npc_b_trainer)

        for maximizing in (True, False):
            with self.subTest(maximizing=maximizing):
                minimax_score = battle.minimax(
                    deepcopy(state_a), deepcopy(state_b), 2, maximizing
                )
                alpha_beta_score = battle.alpha_beta(
                    deepcopy(state_a),
                    deepcopy(state_b),
                    2,
                    float("-inf"),
                    float("inf"),
                    maximizing,
                )
                self.assertEqual(minimax_score, alpha_beta_score)

    def test_defeated_active_pokemon_is_replaced_without_player_input(self):
        trainer = battle.Trainer(
            "NPC B",
            [fresh_pokemon(3), fresh_pokemon(4)],
            identity="NPC_B",
        )
        trainer.pokemon[0].hp = 0
        self.assertTrue(trainer.advance_active())
        self.assertEqual(trainer.active_index, 1)
        self.assertGreater(trainer.active.hp, 0)

    def test_live_battle_facts_reflect_hp_and_either_type_advantage(self):
        pokemon_a = battle.npc_a_trainer.active
        pokemon_b = battle.npc_b_trainer.active
        pokemon_a.element = "water"
        pokemon_b.element = "fire"
        pokemon_a.hp = 20
        facts = set(battle._observed_facts())
        self.assertIn(Atom("LowHP", ("NPC_A",)), facts)
        self.assertIn(Atom("HasTypeAdvantage", ("NPC_A", "NPC_B")), facts)

        pokemon_a.element = "fire"
        pokemon_b.element = "water"
        facts = set(battle._observed_facts())
        self.assertIn(Atom("HasTypeAdvantage", ("NPC_B", "NPC_A")), facts)

        bench_a = battle.npc_a_trainer.pokemon[1]
        bench_b = battle.npc_b_trainer.pokemon[1]
        bench_a.element = "water"
        bench_b.element = "fire"
        facts = set(battle._observed_facts())
        self.assertIn(
            Atom(
                "HasTypeAdvantage",
                (
                    battle._pokemon_identity(battle.npc_a_trainer, 1),
                    battle._pokemon_identity(battle.npc_b_trainer, 1),
                ),
            ),
            facts,
        )

    def test_action_can_use_a_bench_pokemon_and_target_a_bench_opponent(self):
        battle.npc_a_trainer.pokemon.append(fresh_pokemon(2))
        battle.npc_b_trainer.pokemon.append(fresh_pokemon(5))

        for pokemon in battle.npc_a_trainer.pokemon:
            for move in pokemon.moves:
                move.pp = 0
        attacker = battle.npc_a_trainer.pokemon[1]
        attacker.moves[0].pp = 5
        attacker.moves[0].value = 100

        for pokemon in battle.npc_b_trainer.pokemon:
            for move in pokemon.moves:
                move.pp = 0
        battle.npc_b_trainer.pokemon[0].defense = 200
        battle.npc_b_trainer.pokemon[1].hp = 40
        battle.npc_b_trainer.pokemon[2].defense = 200

        action = battle.choose_action("NPC_A", depth=2, mode="minimax")
        self.assertEqual(action, battle.BattleAction(1, 1, 0))

        self.assertTrue(battle.advance_battle())
        self.assertEqual(battle.move_logs[-1].actor_pokemon, attacker.name)
        self.assertEqual(
            battle.move_logs[-1].target_pokemon,
            battle.npc_b_trainer.pokemon[1].name,
        )
        self.assertIn("on NPC B's", battle.battle_text)

    def test_defeated_npc_stops_turn_progression_and_declares_winner(self):
        battle.player_trainer = battle.Trainer(
            "draft NPC A", [fresh_pokemon(0)]
        )
        battle.player_trainer.pokemon[0].moves[0].value = 200
        battle.rival_trainer = battle.Trainer(
            "draft NPC B", [fresh_pokemon(3)]
        )
        battle.rival_trainer.pokemon[0].hp = 10
        battle.rival = battle.rival_trainer.pokemon[0]
        battle.start_battle()

        self.assertTrue(battle.advance_battle())
        self.assertTrue(battle.battle_over)
        self.assertEqual(battle.battle_winner, "NPC A")
        self.assertFalse(battle.advance_battle())
        self.assertEqual(battle.turn_count, 1)


if __name__ == "__main__":
    unittest.main()
