import unittest

from battle_interaction import ActionHint, BattleInteractionHandler
from inference_engine import InferenceEngine
from knowledge_base import Atom, KnowledgeBase


class NPCInteractionTests(unittest.TestCase):
    def setUp(self):
        self.handler = BattleInteractionHandler()

    def test_inferred_type_advantage_maps_to_attack_hint(self):
        knowledge_base = KnowledgeBase.from_json()
        knowledge_base.update_observations(
            [
                Atom("HasTypeAdvantage", ("NPC_B", "NPC_A")),
                Atom("HasDamagingMove", ("NPC_B",)),
            ]
        )
        result = InferenceEngine().infer(knowledge_base)

        self.assertIn(
            ActionHint("NPC_B", "NPC_A", "ATTACK", "R7"),
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
