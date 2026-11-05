import unittest

from inference_engine import InferenceEngine
from knowledge_base import Atom, KnowledgeBase


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self):
        self.knowledge_base = KnowledgeBase.from_json()
        self.engine = InferenceEngine()

    def test_forward_chaining_derives_finishing_attack(self):
        self.knowledge_base.update_observations(
            [
                Atom("LowHP", ("NPC_B",)),
                Atom("HasHighDamagePotential", ("NPC_A",)),
                Atom("HasDamagingMove", ("NPC_A",)),
            ]
        )

        result = self.engine.infer(self.knowledge_base)

        self.assertIn(
            Atom("OpportunityToFinish", ("NPC_A", "NPC_B")), result.facts
        )
        self.assertIn(
            Atom("ActionIntent", ("NPC_A", "NPC_B", "ATTACK")), result.facts
        )
        self.assertTrue(any(step.rule_id == "R3" for step in result.derivations))

    def test_rules_work_for_either_opponent(self):
        for actor, target in (("NPC_A", "NPC_B"), ("NPC_B", "NPC_A")):
            with self.subTest(actor=actor):
                self.knowledge_base.update_observations(
                    [
                        Atom("LowHP", (target,)),
                        Atom("HasDamagingMove", (actor,)),
                        Atom("HasHighDamagePotential", (actor,)),
                        Atom("HasTypeAdvantage", (actor, target)),
                    ]
                )
                result = self.engine.infer(self.knowledge_base)
                self.assertIn(
                    Atom("ExploitTypeAdvantage", (actor, target)), result.facts
                )
                self.assertIn(
                    Atom("ActionIntent", (actor, target, "ATTACK")), result.facts
                )

    def test_self_healing_requires_low_hp_and_available_move(self):
        self.knowledge_base.update_observations(
            [Atom("LowHP", ("NPC_A",)), Atom("HasHealingMove", ("NPC_A",))]
        )
        result = self.engine.infer(self.knowledge_base)
        self.assertIn(Atom("ConsiderSelfHealing", ("NPC_A",)), result.facts)
        self.assertIn(
            Atom("ActionIntent", ("NPC_A", "NPC_A", "HEAL")), result.facts
        )

    def test_self_healing_is_not_inferred_without_a_healing_move(self):
        self.knowledge_base.update_observations([Atom("LowHP", ("NPC_A",))])
        result = self.engine.infer(self.knowledge_base)
        self.assertNotIn(
            Atom("ActionIntent", ("NPC_A", "NPC_A", "HEAL")), result.facts
        )
        self.assertEqual(result.ask(Atom("HasHealingMove", ("NPC_A",))), "unknown")

    def test_status_interaction_rule_works_when_status_is_observed(self):
        self.knowledge_base.update_observations(
            [
                Atom("UnderStatusEffect", ("NPC_B",)),
                Atom("HasDamagingMove", ("NPC_A",)),
            ]
        )
        result = self.engine.infer(self.knowledge_base)
        self.assertIn(
            Atom("ExploitOpponentStatus", ("NPC_A", "NPC_B")), result.facts
        )
        self.assertIn(
            Atom("ActionIntent", ("NPC_A", "NPC_B", "ATTACK")), result.facts
        )

    def test_missing_information_remains_unknown(self):
        self.knowledge_base.update_observations([])
        result = self.engine.infer(self.knowledge_base)
        self.assertEqual(result.ask(Atom("UnderStatusEffect", ("NPC_B",))), "unknown")
        status_rule = next(
            step for step in result.evaluations if step["rule_id"] == "R4"
        )
        self.assertFalse(status_rule["matched"])

    def test_explicit_negation_is_contradiction_not_unknown(self):
        self.knowledge_base.update_observations(
            [Atom("LowHP", ("NPC_B",), negated=True)]
        )
        result = self.engine.infer(self.knowledge_base)
        self.assertEqual(result.ask(Atom("LowHP", ("NPC_B",))), "contradicted")

        self.knowledge_base.update_observations(
            [Atom("UnderStatusEffect", ("NPC_B",), negated=True)]
        )
        result = self.engine.infer(self.knowledge_base)
        status_evaluation = next(
            step for step in result.evaluations if step["rule_id"] == "R4"
        )
        self.assertEqual(status_evaluation["conditions"][1]["status"], "partially contradicted")

    def test_observations_replace_without_removing_base_facts(self):
        self.knowledge_base.update_observations([Atom("LowHP", ("NPC_B",))])
        self.knowledge_base.update_observations([])
        result = self.engine.infer(self.knowledge_base)
        self.assertNotIn(Atom("LowHP", ("NPC_B",)), result.facts)
        self.assertIn(Atom("Opponent", ("NPC_A", "NPC_B")), result.facts)


if __name__ == "__main__":
    unittest.main()
