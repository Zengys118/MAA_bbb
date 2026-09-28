try:
    from maa.resource import resource
except ImportError:
    # 新版 MaaFw 将注册装饰器迁移到 AgentServer，兼容独立 Agent 运行方式。
    from maa.agent.agent_server import AgentServer as resource
from agent.custom.action.Count import Count
from agent.custom.action.OverridePipe import OverridePipe
from agent.custom.action.IDFRole import RecognitionRole

from agent.custom.action.Notice import Notice

from agent.custom.action.Role.FieryWishingStar import FieryWishingStar
from agent.custom.action.Role.SpinaAstera import SpinaAstera
from agent.custom.action.Role.HerrscherOfTruth import HerrscherOfTruth
from agent.custom.action.Role.LoveElf import LoveElf
from agent.custom.action.Role.FengHuangOfVicissitude import FengHuangOfVicissitude
from agent.custom.action.Role.GeneralFight import GeneralFight  # 真理之律者
from agent.custom.action.Role.Mobius import Mobius  # 梅比乌斯
from agent.custom.action.Role.CharacterCombat import CharacterCombat
from agent.custom.action.ElysianRun import AssistantElysianRun, ElysianPause
from agent.custom.action.ElysianIntegration import ElysianConfigure, ElysianInStage, ElysianStage


@resource.custom_action("ElysianConfigure")
class ElysianConfigure_Cls(ElysianConfigure):
    pass


@resource.custom_recognition("ElysianInStage")
class ElysianInStage_Cls(ElysianInStage):
    pass


@resource.custom_action("ElysianStage")
class ElysianStage_Cls(ElysianStage):
    pass


@resource.custom_action("ElysianRun")
class ElysianRun_Cls(AssistantElysianRun):
    pass


@resource.custom_action("ElysianPause")
class ElysianPause_Cls(ElysianPause):
    pass


@resource.custom_action("CharacterCombat")
class CharacterCombat_Cls(CharacterCombat):
    pass


from agent.custom.recongition.CheckResolution import CheckResolution


@resource.custom_action("Notice")
class Notice_Cls(Notice):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_action("GeneralFight")
# 真理之律者
class GeneralFight_Cls(GeneralFight):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_action("Mobius")
# 梅比乌斯
class Mobius_Cls(Mobius):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_action("IDFRole")
# IDF 角色识别
class IDFRole_Cls(RecognitionRole):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_action("Count")
class Count_Cls(Count):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_action("OverridePipe")
class OverridePipe_Cls(OverridePipe):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_recognition("CheckResolution")
class CheckResolution_Cls(CheckResolution):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_action("FieryWishingStar")
class FieryWishingStar_Cls(FieryWishingStar):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_action("SpinaAstera")
class SpinaAstera_Cls(SpinaAstera):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_action("HerrscherOfTruth")
class HerrscherOfTruth_Cls(HerrscherOfTruth):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_action("LoveElf")
class LoveElf_Cls(LoveElf):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@resource.custom_action("FengHuangOfVicissitude")
class FengHuangOfVicissitude_Cls(FengHuangOfVicissitude):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")
