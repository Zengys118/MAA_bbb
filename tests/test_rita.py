import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.append(str(Path(__file__).resolve().parents[1]))
from agent.custom.action.ElysianRealmSelection import ElysianRealmSelection
from agent.custom.action.Role.CharacterCombat import CharacterCombat


class RitaRegressionTests(unittest.TestCase):
    def test_lightning_rejects_physical_penetration(self):
        score = ElysianRealmSelection.score
        self.assertGreater(score("每秒提高元素穿透，可叠加层数"), score("每秒提高物理穿透，可叠加层数"))

    def test_mixed_elemental_signet_is_not_rejected(self):
        score = ElysianRealmSelection.score
        self.assertGreater(score("根据银币数提高物理和元素伤害"), score("根据银币数回复生命和能量"))

    def test_missing_huashang_refuses_input(self):
        argv = NS(custom_action_param=json.dumps({"character": "窈窕谍影", "variant": "elysian_huashang"}))
        self.assertFalse(CharacterCombat().run(None, argv))

    def test_menu_never_receives_combat_input(self):
        capture = NS(wait=lambda: NS(get=lambda: None))
        context = NS(tasker=NS(stopping=False, controller=NS(post_screencap=lambda: capture)), run_recognition=lambda *a: None)
        argv = NS(custom_action_param=json.dumps({"character": "窈窕谍影", "variant": "elysian_huashang", "confirmed_signet": "华裳"}), task_detail=NS(task_id=1))
        self.assertTrue(CharacterCombat().run(context, argv))


if __name__ == "__main__":
    unittest.main()
