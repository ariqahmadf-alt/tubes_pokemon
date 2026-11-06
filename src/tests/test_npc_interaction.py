import unittest

from battle_interaction import ActionHint, BattleInteractionHandler
from inference_engine import InferenceEngine
from knowledge_base import Atom, KnowledgeBase


class NPCInteractionTests(unittest.TestCase):
    def setUp(self):
        self.handler = BattleInteractionHandler()

    def test_inferred_type_advantage_maps_to_attack_hint(self):
        knowledge_base = KnowledgeBase.from_json()
        actor_pokemon = "NPC_B:0:KOBRA"
        target_pokemon = "NPC_A:0:BLASTOISE"
        knowledge_base.update_observations(
            [
                Atom("HasTypeAdvantage", ("NPC_B", "NPC_A")),
                Atom("HasDamagingMove", ("NPC_B",)),
                Atom("Controls", ("NPC_B", actor_pokemon)),
                Atom("Controls", ("NPC_A", target_pokemon)),
                Atom("AlivePokemon", (actor_pokemon,)),
                Atom("AlivePokemon", (target_pokemon,)),
                Atom("HasTypeAdvantage", (actor_pokemon, target_pokemon)),
                Atom("HasDamagingMove", (actor_pokemon,)),
            ]
        )
        result = InferenceEngine().infer(knowledge_base)

        self.assertIn(
            ActionHint("NPC_B", "NPC_A", "ATTACK", "R7"),
            self.handler.hints_from(result),
        )
        self.assertIn(
            ActionHint(actor_pokemon, target_pokemon, "ATTACK", "P2"),
            self.handler.hints_from(result),
        )

    def test_action_hint_is_rejected_if_state_or_move_is_invalid(self):
        hint = ActionHint("NPC_A", "NPC_B", "ATTACK", "R7")

        valid, _ = self.handler.validate(
            hint, "NPC_A", "NPC_B", "ATTACK", ["ATTACK", "HEAL"]
        )
        self.assertTrue(valid)

        invalid_target, _ = self.handler.validate(
            hint, "NPC_A", "NPC_A", "ATTACK", ["ATTACK"]
        )
        invalid_move, _ = self.handler.validate(
            hint, "NPC_A", "NPC_B", "ATTACK", ["HEAL"]
        )
        self.assertFalse(invalid_target)
        self.assertFalse(invalid_move)


if __name__ == "__main__":
    unittest.main()
