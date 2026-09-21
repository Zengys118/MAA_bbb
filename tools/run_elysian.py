"""开发用全流程实机回归。用户入口为项目根目录 exe。"""
import argparse
import json
import sys
import threading
import time
from pathlib import Path
from maa.controller import AdbController
from maa.resource import Resource
from maa.tasker import Tasker
from maa.toolkit import Toolkit
ROOT=Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from agent.custom.action.ElysianRun import ElysianRun, ElysianPause, pipeline
from agent.custom.utils.MumuConnection import resolve_adb_address


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seconds",type=float,default=120)
    parser.add_argument("--assistant-entry",action="store_true",help="使用原助手注册类及磁盘任务资源验证")
    args=parser.parse_args()
    if not 0<args.seconds<=2700: raise SystemExit("seconds must be 0..2700")
    Toolkit.init_option(str(ROOT/"development-notes/auto-log"))
    event=threading.Event()
    runner=ElysianRun(event,lambda msg:print(time.strftime("%H:%M:%S"),msg,flush=True),lambda frame:None,ROOT)
    if args.assistant_entry:
        from agent.custom.action.ElysianRun import AssistantElysianRun
        runner=AssistantElysianRun()
        event=runner.stop_event
    resource=Resource()
    resource.register_custom_action("ElysianRun",runner)
    resource.register_custom_action("ElysianPause",ElysianPause())
    assert resource.post_bundle(ROOT/"resource/base").wait().succeeded
    cfg=json.loads((ROOT/"config/configs/c_1c41b9d8bfce4ff2886d0a9db5355b44.json").read_text(encoding="utf-8"))
    device=next(t for t in cfg["tasks"] if t["name"]=="Controller")["task_option"]["安卓端"]
    address=resolve_adb_address(device["adb_path"],device["address"])
    print("MuMu ADB:",address,flush=True)
    controller=AdbController(device["adb_path"],address,device["screencap_methods"],device["input_methods"],device.get("config",{}),ROOT/"MaaAgentBinary")
    assert controller.post_connection().wait().succeeded
    controller.set_screenshot_target_short_side(720)
    tasker=Tasker();assert tasker.bind(resource,controller)
    job=tasker.post_task("乐土自动-执行") if args.assistant_entry else tasker.post_task("乐土自动-执行",pipeline())
    deadline=time.monotonic()+args.seconds
    try:
        while not job.done and time.monotonic()<deadline and not (ROOT/"development-notes/STOP_AUTO").exists():
            time.sleep(.1)
    finally:
        event.set()
        tasker.post_stop().wait()
        tasker.post_task("乐土自动-暂停",pipeline()).wait()
    print("FINAL",json.dumps(runner.state.to_dict(),ensure_ascii=False),flush=True)


if __name__=="__main__": main()
