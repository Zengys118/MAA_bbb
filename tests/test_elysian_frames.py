"""本次实机遇到的场景回放，避免修复后再次丢失锚点和楼层。"""
import json
import sys
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
FRAME_ROOT=ROOT/'tests/fixtures/runs'
sys.path.append(str(ROOT))
from agent.custom.utils.ElysianVision import dormant_anchors,red_portals
from agent.custom.utils.ElysianPolicy import read_floor

@unittest.skipUnless((FRAME_ROOT/'20260908-180739/1788862080265001200-floor15.png').exists(),
                     '历史实机截图未随源码发布')
class FrameTests(unittest.TestCase):
    def test_single_blue_portal(self):
        frame=np.array(Image.open(FRAME_ROOT/'20260908-180739/1788862080265001200-floor15.png'))[:,:,::-1]
        found=red_portals(frame)
        self.assertTrue(any(abs(r['box'][0]+r['box'][2]/2-547)<15 for r in found))
    def test_purple_wall_is_not_a_portal(self):
        frame=np.array(Image.open(FRAME_ROOT/'20260908-175958/1788861707980381100-floor14.png'))[:,:,::-1]
        self.assertFalse(red_portals(frame))
    def test_red_portals(self):
        frame=np.array(Image.open(FRAME_ROOT/'20260908-172136/1788859403156740100-floor7.png'))[:,:,::-1]
        self.assertEqual(len(red_portals(frame)),3)
    def test_cyan_wall_details_are_not_anchors(self):
        frame=np.array(Image.open(FRAME_ROOT/'20260908-173254/1788860031757912400-floor7.png'))[:,:,::-1]
        self.assertFalse(dormant_anchors(frame))
        self.assertFalse(red_portals(frame))
    def test_three_unopened_anchors(self):
        path=FRAME_ROOT/'20260908-170919/1788858614301317600-floor6.png'
        frame=np.array(Image.open(path).convert('RGB'))[:,:,::-1]
        found=dormant_anchors(frame)
        self.assertEqual(len(found),3)
        centers=[b['box'][0]+b['box'][2]/2 for b in found]
        self.assertTrue(all(abs(a-b)<15 for a,b in zip(centers,[700,812,979])))
    def test_blue_scenery_is_not_an_anchor_group(self):
        path=FRAME_ROOT/'20260908-170919/1788858628737197900-floor6.png'
        frame=np.array(Image.open(path).convert('RGB'))[:,:,::-1]
        self.assertFalse(dormant_anchors(frame))
    def test_real_ocr_floor(self):
        path=FRAME_ROOT/'20260908-170919/1788858628737197900-floor6.json'
        self.assertEqual(read_floor(json.loads(path.read_text(encoding='utf-8'))),(6,17))

if __name__=='__main__': unittest.main()
