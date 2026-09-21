"""验证原任务配置、关内交接和失败分支。所有输入均在离线控制器中执行。"""
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import jsonc
import numpy as np
from PIL import Image
from maa.controller import CustomController
from maa.custom_action import CustomAction
from maa.resource import Resource
from maa.tasker import Tasker
from maa.toolkit import Toolkit

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from agent.custom.action.ElysianIntegration import ElysianConfigure, ElysianInStage, ElysianStage, read_settings
from agent.custom.action.ElysianRun import ElysianRun, RunHalt
from agent.custom.utils.ElysianPolicy import RunState, score_signet, gate_order


def load_nodes():
    nodes = {}
    for path in (ROOT / 'resource/base/pipeline').rglob('*.json'):
        nodes.update(jsonc.loads(path.read_text(encoding='utf-8-sig')))
    return nodes


def merge(target, source):
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge(target[key], value)
        else:
            target[key] = value


def selected_overrides(selections=None, controller='安卓端'):
    document = jsonc.loads((ROOT / 'tasks/周常/往世乐土.json').read_text(encoding='utf-8'))
    task = next(t for t in document['task'] if t['name'] == '往世乐土')
    output = {}
    def visit(name):
        option = document['option'][name]
        if option.get('controller') and controller not in option['controller']:
            return
        if option['type'] == 'input':
            value = (selections or {}).get(name, '')
            encoded = json.dumps(option.get('pipeline_override', {}), ensure_ascii=False)
            encoded = encoded.replace('{真我刻印自选优先级_1}', value)
            merge(output, json.loads(encoded))
            return
        cases = option.get('cases', [])
        value = (selections or {}).get(name, option.get('default_case', cases[0]['name'] if cases else None))
        case = next(c for c in cases if c['name'] == value)
        merge(output, case.get('pipeline_override', {}))
        for child in case.get('option', []):
            visit(child)
    for name in task['option']:
        visit(name)
    return output


class SettingsTests(unittest.TestCase):
    def context(self, selections=None):
        self.resource = Resource()
        self.assertTrue(self.resource.post_bundle(ROOT / 'resource/base').wait().succeeded)
        self.assertTrue(self.resource.override_pipeline(selected_overrides(selections)))
        return NS(get_node_data=self.resource.get_node_data)

    def test_original_options_reach_engine(self):
        context = self.context({'往世乐土-刻印优先级自选': 'Yes',
                                '乐土-道中刻印优先级_1': '乐土-道中刻印优先级1_回能',
                                '往世乐土-门的选择优先级': 'Yes',
                                '乐土-选门优先级_1': '乐土选门优先级-1-黄金',
                                '往世乐土-真我刻印自选': '尽善|粉黛'})
        config = read_settings(context)
        self.assertEqual(config['role'], '窈窕谍影')
        self.assertTrue(config['shop_enabled'])
        self.assertEqual(config['buff_priority'][0], '回复能量')
        self.assertEqual(config['gate_priority'][0], '黄金')
        self.assertEqual(config['exclusive_priority'], ['尽善', '粉黛'])
        state = RunState(**config)
        self.assertGreater(score_signet('回复能量', state), score_signet('元素穿透提高', state))
        self.assertEqual(gate_order(state)[0], '黄金')
        self.assertGreater(score_signet('华裳的祝福', state), score_signet('尽善的祝福', state))

    def test_off_switches_revert_to_recommendation(self):
        cfg = read_settings(self.context({'往世乐土-刻印优先级自选': 'No', '往世乐土-门的选择优先级': 'No', '往世乐土-商店处理策略-安卓': '绕过不购买'}))
        self.assertEqual(cfg['buff_priority'], [])
        self.assertEqual(cfg['gate_priority'], [])
        self.assertFalse(cfg['shop_enabled'])

    def test_desktop_does_not_enable_mobile_engine(self):
        nodes = load_nodes()
        merge(nodes, selected_overrides(controller='桌面端'))
        ctx = NS(get_node_data=lambda n: nodes.get(n), override_pipeline=Mock())
        self.assertTrue(ElysianConfigure().run(ctx, NS()))
        ctx.override_pipeline.assert_not_called()

    def test_invalid_exclusive_regex_fails_before_inputs(self):
        context = self.context({'往世乐土-真我刻印自选': '['})
        context.override_pipeline = Mock()
        self.assertFalse(ElysianConfigure().run(context, NS()))
        context.override_pipeline.assert_not_called()

    def test_blank_exclusive_ocr_is_removed_from_mobile_entry_chain(self):
        context = self.context({'往世乐土-真我刻印自选': ''})
        context.override_pipeline = Mock(return_value=True)
        self.assertTrue(ElysianConfigure().run(context, NS()))
        patch = context.override_pipeline.call_args.args[0]
        next_nodes = patch['往事乐土-乐土开始了']['next']
        self.assertEqual(next_nodes, ['乐土关内-接管'])

    def test_original_entry_and_preparation_contain_handoff(self):
        nodes = load_nodes()
        # 原版入口和初始刻印选择必须先运行，接管只作为后置兜底。
        self.assertNotEqual(nodes['往世乐土-开始任务层']['next'][0], '乐土关内-接管')
        self.assertIn('乐土关内-接管', nodes['往世乐土-开始任务层']['next'])
        self.assertNotEqual(nodes['往世乐土-已进入三位导航界面']['next'][0], '乐土关内-接管')
        self.assertEqual(nodes['往事乐土-乐土开始了']['next'][-1], '乐土关内-接管')
        self.assertEqual(nodes['乐土关内-接管']['next'], ['往世乐土-打完领奖-按住alt'])


class HandoffTests(unittest.TestCase):
    def recognize(self, rows, hud=False):
        ocr = NS(hit=True, all_results=[NS(**r) for r in rows])
        context = NS(run_recognition=lambda name, image: ocr if name == '乐土自动-OCR' else NS(hit=hud))
        return ElysianInStage().analyze(context, NS(image=None))

    def test_no_handoff_in_preparation(self):
        self.assertIsNone(self.recognize([{'text': '开始战斗 出战位 支援位', 'box': [200, 200, 900, 400]}]))

    def test_initial_signet_handoff_before_any_selection(self):
        self.assertIsNotNone(self.recognize([
            {'text': '华裳的祝福', 'box': [650, 200, 250, 50]},
            {'text': '选择刻印', 'box': [1020, 650, 200, 50]}]))

    def test_initial_signet_handoff_uses_title_when_button_is_disabled(self):
        self.assertIsNotNone(self.recognize([
            {'text': '请选择英桀的刻印', 'box': [506, 141, 195, 27]},
            {'text': '「真我」的刻印', 'box': [518, 95, 244, 41]},
            {'text': '「华裳」的祝福+', 'box': [645, 193, 212, 35]}]))

    def test_resume_requires_floor_and_hud(self):
        rows = [{'text': '抵达层数 6/17', 'box': [100, 10, 180, 30]}]
        self.assertIsNone(self.recognize(rows, False))
        self.assertIsNotNone(self.recognize(rows, True))

    def test_stage_cannot_start_new_run(self):
        runner = ElysianStage()
        runner.text = '命定的歧路深层序列'
        runner.settlement_requested = False
        with self.assertRaises(RunHalt):
            runner.frontend()

    def test_lost_near_gate_retreats_instead_of_forward(self):
        runner = ElysianRun(threading.Event(), Mock(), Mock(), ROOT)
        runner.context = Mock()
        runner.items = []
        runner.nav_started = time.monotonic()
        runner.target = {'box': [580, 200, 150, 130]}
        runner.state.target = '黄金'
        runner.detect_gates = Mock(return_value=[])
        runner.shop_done = True
        runner.lost_frames = 0
        runner.motion.walk = Mock()
        runner.phase = Mock()
        runner.navigate()
        runner.motion.walk.assert_called_once_with(runner.context, 0, .25, dy=76)

    def test_initial_empty_build_closes_gain_list_before_waiting(self):
        runner = ElysianRun(threading.Event(), Mock(), Mock(), ROOT)
        runner.state = RunState(floor=1, role_verified=True)
        runner.final_exit = False
        runner.items = [{'text': '增益列表', 'box': [260, 18, 138, 42]}]
        runner.text = '增益列表 追忆之证'
        runner.phase = Mock()
        runner.click_text = Mock(return_value=True)
        runner.sync_pause()
        runner.click_text.assert_called_once_with('^返回$', [0, 0, 210, 90], .6)

    def test_dialogue_with_choice_text_is_handled_before_signet_selection(self):
        runner = ElysianRun(threading.Event(), Mock(), Mock(), ROOT)
        runner.read = Mock(return_value='历史跳过限时挑战成功额外获得一次选择刻印的机会')
        runner.items = [
            {'text': '历史', 'box': [196, 22, 92, 33]},
            {'text': '跳过', 'box': [1154, 23, 87, 29]},
            {'text': '限时挑战成功，额外获得一次选择刻印的机会', 'box': [206, 578, 535, 32]},
        ]
        runner.text = runner.read.return_value
        runner.update_floor = Mock()
        runner.commit_signet = Mock()
        runner.frontend = Mock()
        runner.select_signet = Mock()
        runner.step()
        runner.frontend.assert_called_once_with()
        runner.select_signet.assert_not_called()


class FrameworkTests(unittest.TestCase):
    """真实 Maa 执行原入口和接管节点，游戏行为使用替身，不能触碰模拟器。"""
    def test_success_and_failure_route(self):
        Toolkit.init_option(str(ROOT / 'development-notes/integration-log'))
        with tempfile.TemporaryDirectory() as folder:
            image_path = Path(folder) / 'blank.png'
            Image.fromarray(np.zeros((720, 1280, 3), dtype=np.uint8)).save(image_path)
            for success in (True, False):
                with self.subTest(success=success):
                    events = []
                    class Probe(CustomAction):
                        def run(self, context, argv):
                            params = json.loads(argv.custom_action_param or '{}')
                            events.append(params)
                            return success if params.get('role') else True
                    resource = Resource()
                    resource.register_custom_action('ElysianConfigure', ElysianConfigure())
                    resource.register_custom_action('ElysianStage', Probe())
                    resource.register_custom_action('Probe', Probe())
                    self.assertTrue(resource.post_bundle(ROOT / 'resource/base').wait().succeeded)
                    class OfflineController(CustomController):
                        def connect(self): return True
                        def request_uuid(self): return 'elysian-offline-integration'
                        def get_features(self): return 0
                        def screencap(self): return np.zeros((720, 1280, 3), dtype=np.uint8)
                        def no_input(self, *args): return False
                        start_app = stop_app = click = swipe = touch_down = touch_move = touch_up = click_key = input_text = key_down = key_up = no_input
                    controller = OfflineController()
                    self.assertTrue(controller.post_connection().wait().succeeded)
                    tasker = Tasker()
                    self.assertTrue(tasker.bind(resource, controller))
                    override = selected_overrides({'往世乐土-刻印优先级自选': 'No'})
                    merge(override, {
                        '往世乐土-开始任务层': {'next': ['测试-准备完成'], 'pre_delay': 0, 'post_delay': 0},
                        '测试-准备完成': {'action': {'type': 'Custom', 'param': {'custom_action': 'Probe', 'custom_action_param': {'prepared': True}}}, 'next': ['乐土关内-接管'], 'pre_delay': 0, 'post_delay': 0},
                        '乐土关内-接管': {'recognition': 'DirectHit'},
                        '往世乐土-打完领奖-按住alt': {'recognition': 'DirectHit', 'action': {'type': 'Custom', 'param': {'custom_action': 'Probe', 'custom_action_param': {'reward': True}}}, 'next': [], 'pre_delay': 0, 'post_delay': 0},
                    })
                    job = tasker.post_task('往世乐土-开始任务层', override).wait()
                    self.assertTrue(events[0].get('prepared'))
                    self.assertEqual(events[1]['role'], '窈窕谍影')
                    self.assertEqual(any(e.get('reward') for e in events), success)
                    self.assertFalse(resource.get_node_data('乐土关内-接管')['enabled'])
                    tasker.post_stop().wait()


if __name__ == '__main__':
    unittest.main()
