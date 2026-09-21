"""面板控制回归：仅虚拟控制器，绝不连接模拟器。"""
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.append(str(Path(__file__).resolve().parents[1]))
from agent.custom.action.ElysianPanelAction import ElysianPanelAction


class Job:
    def __init__(self, success=True): self.succeeded = success
    def wait(self): return self


class Controller:
    def __init__(self): self.inputs = []; self.fail_move = False; self.on_down = lambda: None
    def post_touch_down(self, *args):
        self.inputs.append(("down", args)); self.on_down(); return Job()
    def post_touch_move(self, *args):
        self.inputs.append(("move", args)); return Job(not self.fail_move)
    def post_touch_up(self): self.inputs.append(("up", ())); return Job()
    def post_click(self, *args): self.inputs.append(("click", args)); return Job()


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.controller = Controller()
        self.context = NS(tasker=NS(controller=self.controller, stopping=False))
        self.action = ElysianPanelAction(threading.Event(), lambda text: None, lambda frame: None)
        self.action.capture = lambda ctx: None

    def test_release_even_when_move_fails(self):
        self.controller.fail_move = True
        with self.assertRaisesRegex(RuntimeError, "摇杆移动失败"):
            self.action.walk(self.context)
        self.assertEqual([i[0] for i in self.controller.inputs], ["down", "move", "up"])

    def test_stop_between_down_and_move_releases(self):
        self.controller.on_down = self.action.stop_event.set
        self.action.walk(self.context)
        self.assertEqual([i[0] for i in self.controller.inputs], ["down", "up"])

    def test_stopped_before_walk_has_no_input(self):
        self.action.stop_event.set()
        self.action.walk(self.context)
        self.assertFalse(self.controller.inputs)

    def test_menu_refuses_forward(self):
        self.action.arena = lambda *args: False
        self.assertTrue(self.action.run(self.context, None))
        self.assertIn("不是可操作关卡", self.action.outcome)
        self.assertFalse(self.controller.inputs)

    def test_enter_requires_both_label_and_prompt(self):
        self.action.operation = "enter"
        for missing in ("面板-门前身份", "面板-前往"):
            self.action.hit = lambda ctx, name, frame: None if name == missing else NS(box=(1, 2, 3, 4))
            self.action.run(self.context, None)
        self.assertFalse(self.controller.inputs)

    def test_enter_rechecks_identity_and_clicks_prompt(self):
        self.action.operation = "enter"
        self.action.hit = lambda *args: NS(box=(700, 260, 60, 30))
        with patch.object(self.action.stop_event, "wait", return_value=False):
            self.action.run(self.context, None)
        self.assertEqual(self.controller.inputs, [("click", (730, 275))])

    def test_navigation_ends_at_confirmed_gate_without_clicking(self):
        self.action.confirmed_gate = lambda *args: True
        self.action.navigate(self.context)
        self.assertIn("已到", self.action.outcome)
        self.assertFalse(self.controller.inputs)

    def test_navigation_does_not_start_during_battle(self):
        self.action.confirmed_gate = lambda *args: None
        self.action.arena = lambda *args: True
        self.action.hit = lambda *args: None
        self.action.navigate(self.context)
        self.assertIn("尚未确认战斗结束", self.action.outcome)
        self.assertFalse(self.controller.inputs)

    def test_visible_other_gate_reports_names_without_turning(self):
        self.action.target = "浮生"
        self.action.confirmed_gate = lambda *args: None
        self.action.arena = lambda *args: True
        self.action.hit = lambda *args: True
        self.context.run_recognition = lambda *args: NS(raw_detail={"all": [
            {"cls_index": 19, "score": .9, "box": [600, 200, 60, 60]}]})
        self.action.navigate(self.context)
        self.assertIn("当前识别到：黄金", self.action.outcome)
        self.assertFalse(self.controller.inputs)

    def test_navigation_moves_then_stops_at_gate(self):
        self.action.confirmed_gate = lambda *args: bool(self.controller.inputs)
        self.action.arena = lambda *args: True
        self.action.hit = lambda *args: True
        self.context.run_recognition = lambda *args: NS(raw_detail={"all": [
            {"cls_index": 19, "score": .9, "box": [680, 200, 120, 120]}]})
        self.action.navigate(self.context)
        self.assertEqual([i[0] for i in self.controller.inputs], ["down", "move", "up"])
        self.assertIn("已到「黄金」", self.action.outcome)


if __name__ == "__main__": unittest.main()
