"""真实截图回放：虚拟控制器不会连接或操作模拟器。"""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from maa.controller import CustomController
from maa.resource import Resource
from maa.tasker import Tasker
from maa.toolkit import Toolkit

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from agent.custom.action.Role.CharacterCombat import CharacterCombat


class ScreenshotController(CustomController):
    def __init__(self):
        super().__init__()
        self.frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.inputs = []

    def connect(self): return True
    def request_uuid(self): return "offline-rita-regression"
    def screencap(self): return self.frame
    def get_features(self): return 0
    def click(self, x, y):
        self.inputs.append((x, y))
        return True

    def touch_down(self, contact, x, y, pressure=1):
        self.inputs.append(("down", contact, x, y))
        return True

    def touch_move(self, contact, x, y, pressure=1):
        self.inputs.append(("move", contact, x, y))
        return True

    def touch_up(self, contact=0):
        self.inputs.append(("up",))
        return True


Toolkit.init_option(str(ROOT / "tests/.offline-log"))
resource = Resource()
resource.register_custom_action("CharacterCombat", CharacterCombat())
assert resource.post_bundle(ROOT / "resource/base").wait().succeeded
controller = ScreenshotController()
assert controller.post_connection().wait().succeeded
tasker = Tasker()
assert tasker.bind(resource, controller)

for filename in ("rita-floor8-after-reward.png", "rita-floor8-dialogue.png", "tutorial-pause.png"):
    frame = Image.open(ROOT / "tests/fixtures/captures" / filename).convert("RGB").resize((1280, 720), Image.Resampling.BILINEAR)
    controller.frame = np.array(frame)[:, :, ::-1].copy()
    controller.inputs.clear()
    # 去掉后继，测试一次完整 CustomAction 的所有内部识别/动作。
    result = tasker.post_task("角色战斗-窈窕谍影-华裳", {"角色战斗-窈窕谍影-华裳": {"next": []}}).wait()
    assert not controller.inputs, (filename, controller.inputs)
    print(json.dumps({"frame": filename, "input_count": len(controller.inputs), "passed": True}, ensure_ascii=False))

# 复用真实战斗 HUD 样本，验证接口确实能发送预期动作，而非始终拒绝。
# 此样本是爱莉教学，只验证输入接口，不作为丽塔伤害/通关证据。
frame = Image.open(ROOT / "tests/fixtures/captures/elysia-tutorial-attack.png").convert("RGB").resize((1280, 720), Image.Resampling.BILINEAR)
controller.frame = np.array(frame)[:, :, ::-1].copy()
controller.inputs.clear()
result = tasker.post_task("角色战斗-窈窕谍影-华裳", {"角色战斗-窈窕谍影-华裳": {"next": []}}).wait()
assert result.succeeded, "active HUD callback failed"
# 华裳不能混入风致星环流，也不能因伪“锁定目标”定时跳跃。
assert controller.inputs[:2] == [(1208, 147), (1203, 285)], controller.inputs
assert controller.inputs[2:] and set(controller.inputs[2:]) == {(1045, 512)}, controller.inputs
print("ACTIVE HUD INTERFACE CHECK PASSED (virtual inputs only)")

# 贝纳勒斯实机截图中英桀助战为 600/600，验证它真正进入动作序列。
resource.register_custom_action("CharacterCombat", CharacterCombat())
boss_frame=ROOT/'tests/fixtures/runs/20260908-174017/1788860477162028600-floor8.png'
if boss_frame.exists():
    frame=Image.open(boss_frame).convert('RGB')
    controller.frame=np.array(frame)[:,:,::-1].copy()
    controller.inputs.clear()
    tasker.post_task("角色战斗-窈窕谍影-华裳", {"角色战斗-窈窕谍影-华裳": {"next": []}}).wait()
    assert (938,424) in controller.inputs, controller.inputs
    assert (1045,512) in controller.inputs, controller.inputs
    print("BOSS READY SUPPORT CHECK PASSED (virtual inputs only)")

print("OFFLINE FRAME CHECKS PASSED")
