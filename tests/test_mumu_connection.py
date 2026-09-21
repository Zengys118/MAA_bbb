import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))
from agent.custom.utils.MumuConnection import resolve_adb_address, _configured_guest


class ConnectionTests(unittest.TestCase):
    def test_only_matching_instance_supplies_guest_address(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / 'vms/device/configs/vm_config.json'
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({'vm': {'nat': {'port_forward': {'adb': {
                'host_port': '16384', 'guest_ip': '192.168.2.103'
            }}}}}), encoding='utf-8')
            adb = root / 'nx_main/adb.exe'
            self.assertEqual(_configured_guest(adb, '127.0.0.1:16384'), '192.168.2.103:5555')
            self.assertIsNone(_configured_guest(adb, '127.0.0.1:16385'))
            self.assertEqual(_configured_guest(adb, '192.168.2.102:5555'), '192.168.2.103:5555')
            other=root/'vms/device2/configs/vm_config.json'
            other.parent.mkdir(parents=True)
            other.write_text(config.read_text(encoding='utf-8'),encoding='utf-8')
            self.assertIsNone(_configured_guest(adb, '192.168.2.102:5555'))

    @patch('agent.custom.utils.MumuConnection.subprocess.run')
    @patch('agent.custom.utils.MumuConnection._configured_guest', return_value='192.168.2.103:5555')
    @patch('agent.custom.utils.MumuConnection._online', side_effect=[[], ['192.168.2.103:5555']])
    def test_reconnect_after_adb_restart(self, online, guest, run):
        self.assertEqual(resolve_adb_address('adb.exe', '127.0.0.1:16384'), '192.168.2.103:5555')
        self.assertEqual(run.call_args.args[0], ['adb.exe', 'connect', '192.168.2.103:5555'])

    @patch('agent.custom.utils.MumuConnection._configured_guest', return_value=None)
    @patch('agent.custom.utils.MumuConnection._online', return_value=['phone-a', 'phone-b'])
    def test_ambiguous_devices_are_not_arbitrarily_selected(self, online, guest):
        with self.assertRaisesRegex(RuntimeError, '多台'):
            resolve_adb_address('adb.exe', '127.0.0.1:16384')
