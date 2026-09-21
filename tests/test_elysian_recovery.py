"""回放实机误触和结算截图的 OCR；输入均为虚拟控制器。"""
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from agent.custom.action.ElysianRun import ElysianRun, RunHalt
from agent.custom.utils.ElysianPolicy import normalize


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runner=ElysianRun(threading.Event(),lambda text:None,lambda image:None,ROOT)
        r=self.runner
        r.context=NS(tasker=NS(stopping=False,controller=Mock()))
        r.context.tasker.controller.post_click_key.return_value.wait.return_value.succeeded=True
        r.read=Mock();r.update_floor=Mock();r.commit_signet=Mock()
        r.phase=Mock();r.click=Mock();r.stop_event.wait=Mock()
        r.detail_attempts=0;r.settlement_requested=True;r.settlement_result_seen=False
        r.settlement_animation_waits=0
        r.checkpoint=Path(self.temp.name)/'pending.json'

    def frame(self,path):
        self.runner.items=json.loads((ROOT/'tests'/path).read_text(encoding='utf-8'))
        self.runner.text=normalize(''.join(i['text'] for i in self.runner.items))

    def test_detail_closes_before_selecting_or_committing(self):
        self.frame('fixtures/elysian/golden-term-overlay.json')
        self.runner.step()
        self.runner.context.tasker.controller.post_click_key.assert_called_once_with(4)
        self.runner.commit_signet.assert_not_called()
        self.runner.click.assert_not_called()

    def test_unresponsive_detail_does_not_retry_forever(self):
        self.frame('fixtures/elysian/golden-term-overlay.json')
        for _ in range(3): self.runner.step()
        with self.assertRaisesRegex(RunHalt,'关闭 3 次'): self.runner.step()
        self.assertEqual(self.runner.context.tasker.controller.post_click_key.call_count,3)

    def test_score_card_is_closed_before_finishing(self):
        self.frame('fixtures/elysian/successful-score.json')
        self.runner.step()
        self.assertTrue(self.runner.settlement_result_seen)
        self.assertNotEqual(self.runner.state.result,'通关')
        self.runner.click.assert_called_once_with(640,650,.8)
        self.assertTrue(json.loads(self.runner.checkpoint.read_text(encoding='utf-8'))['result_seen'])

    def test_old_score_card_does_not_complete_a_new_run(self):
        self.frame('fixtures/elysian/successful-score.json')
        self.runner.settlement_requested=False
        self.runner.step()
        self.assertFalse(self.runner.settlement_result_seen)
        self.assertFalse(self.runner.checkpoint.exists())

    def test_lost_small_boss_gate_unlocks_and_repositions(self):
        r=self.runner
        r.items=[];r.frame=None;r.nav_started=time.monotonic()
        r.target={'box':[800,200,40,70]};r.state.target='首领'
        r.turns=8;r.lost_frames=4;r.nav_recoveries=0;r.nav_steps=0
        r.frame_target=None;r.frame_lost=0;r.shop_done=True;r.final_clear=False
        r.detect_gates=Mock(return_value=[]);r.motion.walk=Mock()
        with patch('agent.custom.action.ElysianRun.red_portals',return_value=[]), patch('agent.custom.action.ElysianRun.dormant_anchors',return_value=[]):
            r.navigate()
        self.assertIsNone(r.target)
        self.assertEqual(r.state.target,'')
        self.assertEqual(r.motion.walk.call_count,2)
        self.assertEqual(r.motion.walk.call_args_list[0].kwargs['dy'],76)
        self.assertEqual(r.motion.walk.call_args_list[1].args[1],-76)
        self.assertEqual(r.nav_recoveries,1)

    def test_gate_click_uses_visible_prompt_position(self):
        self.frame('fixtures/elysian/shop-gate-prompt.json')
        r=self.runner
        r.state.floor=15;r.nav_started=time.monotonic();r.final_clear=False
        r.save=Mock()
        r.navigate()
        r.click.assert_called_once_with(730.5,283.5,1.2)
        self.assertEqual(r.enter_pending,15)

    def test_occluded_floor_digits_do_not_restart_battle_timer(self):
        r=self.runner
        r.state.floor=17
        r.items=[{'text':'7/17','box':[180,15,60,25]}]
        r.floor_since=123
        ElysianRun.update_floor(r)
        self.assertEqual(r.state.floor,17)
        self.assertEqual(r.floor_since,123)

    def test_floor_jump_is_rejected_and_next_floor_needs_two_reads(self):
        r=self.runner
        r.state.floor=8;r.final_clear=False;r.enter_pending=8
        r.items=[{'text':'17/17','box':[96,11,109,23]}]
        ElysianRun.update_floor(r)
        self.assertEqual(r.state.floor,8)
        r.items=[{'text':'9/17','box':[96,11,109,23]}]
        ElysianRun.update_floor(r)
        self.assertEqual(r.state.floor,8)
        ElysianRun.update_floor(r)
        self.assertEqual(r.state.floor,9)
        self.assertFalse(r.battle_finished)
        self.assertIsNone(r.enter_pending)

    def test_settling_cannot_start_another_challenge(self):
        r=self.runner
        r.items=[]
        for text in ('命定的歧路深层序列','首领预览开始战斗','出战位支援位开始战斗'):
            r.text=text
            self.assertFalse(r.frontend())
        self.assertTrue(r.settlement_requested)
        r.click.assert_not_called()

    def test_score_animation_waits_before_dismissing(self):
        r=self.runner
        r.items=[{'text':'点击空白处关闭界面','box':[541,614,197,26]}]
        r.text='点击空白处关闭界面'
        r.step()
        self.assertEqual(r.settlement_animation_waits,1)
        r.click.assert_not_called()
        self.assertFalse(r.settlement_result_seen)


if __name__=='__main__':unittest.main()
