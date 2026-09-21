import sys
import json
import unittest
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from agent.custom.utils.ElysianPolicy import RunState, score_signet, choose_gate, read_floor, choice_rows, signet_detail_open


class PolicyTests(unittest.TestCase):
    def setUp(self): self.state=RunState()
    def test_real_core_selection_does_not_open_description(self):
        rows=json.loads((Path(__file__).parent/'fixtures/elysian/golden-core-choice.json').read_text(encoding='utf-8'))
        self.assertFalse(signet_detail_open(rows))
        chosen=max(choice_rows(rows),key=lambda r:score_signet(r['text'],self.state))
        self.assertIn('黄金的咏叹',chosen['text'])
        x,y=chosen['point']
        self.assertTrue(520<x<625 and 180<y<323)
        # 点击点必须远离这次失败现场中的正文和蓝色词条区域。
        self.assertFalse(any(i['box'][0] <= x <= i['box'][0]+i['box'][2] and i['box'][1] <= y <= i['box'][1]+i['box'][3] for i in rows))
    def test_real_detail_with_visible_underlying_core_page(self):
        rows=json.loads((Path(__file__).parent/'fixtures/elysian/golden-term-overlay.json').read_text(encoding='utf-8'))
        self.assertTrue(signet_detail_open(rows))
        self.assertFalse(signet_detail_open([i for i in rows if i['text']!='X']))
    def test_split_floor_ocr(self):
        rows=[{"text":"抵达层数", "box":[99,16,90,22]}, {"text":"6/17", "box":[190,16,55,22]}]
        self.assertEqual(read_floor(rows),(6,17))
    def test_hp_is_not_a_floor(self):
        self.assertIsNone(read_floor([{"text":"5158/5158","box":[296,620,160,30]}]))
    def test_floor_cannot_exceed_displayed_total(self):
        self.assertIsNone(read_floor([{'text':'抵达层数-18/17','box':[96,11,109,23]}]))
        self.assertEqual(read_floor([{'text':'抵达层数-18/18','box':[96,11,109,23]}]),(18,18))
    def test_defence_is_below_damage(self):
        self.assertGreater(score_signet("能量越多，造成的元素伤害越高",self.state),score_signet("能量越多，受到的全伤害越低",self.state))
    def test_combo_trigger_does_not_make_energy_equal_to_damage(self):
        self.assertGreater(score_signet("连击数达到150时清空全部连击数，全伤害提高",self.state),
                           score_signet("连击数达到150时清空全部连击数，回复能量",self.state))
    def test_enemy_attack_reduction_is_defence_and_adaptive_penetration_is_offence(self):
        defence=score_signet("被因果转轮命中的敌人下一次攻击全伤害降低",self.state)
        penetration=score_signet("因果转轮命中没有护盾保护或护盾被击破的敌人时，自身获得穿透",self.state)
        self.assertLess(defence,180)  # 不应当作增伤在商店购买。
        self.assertGreater(penetration,score_signet("全伤害提高",self.state))
        self.assertLess(score_signet("物理穿透提高",self.state),0)
    def test_required_exclusive_first(self):
        self.assertGreater(score_signet("华裳的祝福",self.state),score_signet("尽善的祝福",self.state))
        self.state.record("华裳")
        self.assertGreater(score_signet("尽善的祝福",self.state),score_signet("华裳的祝福",self.state))
    def test_core_changes_gate_preference(self):
        gates=[{"cls_index":19,"score":.9},{"cls_index":1,"score":.8}]
        self.assertEqual(choose_gate(gates,self.state)["cls_index"],19)
        self.state.record("黄金的咏叹")
        self.assertEqual(choose_gate(gates,self.state)["cls_index"],1)
    def test_actual_kalpas_core_name_changes_gate_preference(self):
        core="鏖兵·鏖剪·鏖馘·鏖灭"
        self.assertGreater(score_signet(core+" 核心 充能提高生命上限",self.state),
                           score_signet("鏖斗·鏖战·鏖杀·鏖灭 核心 造成火焰元素伤害",self.state))
        gates=[{"cls_index":1,"score":.9},{"cls_index":15,"score":.8}]
        self.assertEqual(choose_gate(gates,self.state)["cls_index"],1)
        self.state.record(core)
        self.assertEqual(choose_gate(gates,self.state)["cls_index"],15)
    def test_low_confidence_not_used(self):
        self.assertIsNone(choose_gate([{"cls_index":19,"score":.4}],self.state))
    def test_core_record_committed_only_once(self):
        self.state.record("黄金的余音","黄金");self.state.record("黄金的余音","黄金")
        self.assertEqual(self.state.families["黄金"],1)


if __name__=="__main__":unittest.main()
