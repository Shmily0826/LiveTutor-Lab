"""Actual relay protocol denial without network or changes to the shared ledger."""
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from neko_desktop_tutor_host import Sink

class OfflineRelay(unittest.TestCase):
    def test_offline_never_creates_or_resets_missing_corrupt_or_other_round_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Path(folder)/'ledger'
            for original in (None,b'invalid JSON',json.dumps({'round':'other-round','budgets':{'api.deepseek.com':2000},'spent':{'api.deepseek.com':594}}).encode()):
                if original is None:ledger.unlink(missing_ok=True)
                else:ledger.write_bytes(original)
                with self.assertRaisesRegex(RuntimeError,'will not create or reset'):
                    Sink(2000,cap_file=ledger,round_id='bargein-autocheck-20261012',offline=True)
                self.assertEqual(ledger.read_bytes() if ledger.exists() else None,original)

    def test_connect_and_absolute_http_refused_before_spend_and_ledger_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Path(folder)/'ledger'
            original=json.dumps({'round':'bargein-autocheck-20261012',
                'budgets':{'api.deepseek.com':2000,'www.lanlan.app':None,'www.lanlan.tech':0},
                'spent':{'api.deepseek.com':594,'www.lanlan.app':58}}).encode()
            ledger.write_bytes(original)
            sink=Sink(2000,extra={'www.lanlan.app':None,'www.lanlan.tech':0},cap_file=ledger,
                      round_id='bargein-autocheck-20261012',offline=True)
            try:
                with patch.object(sink,'_spend') as spend,patch.object(sink,'_tunnel') as tunnel,patch.object(sink,'_forward') as forward:
                    for request in (b'CONNECT api.deepseek.com:443 HTTP/1.1\r\n\r\n',
                                    b'CONNECT www.lanlan.app:443 HTTP/1.1\r\n\r\n',
                                    b'GET http://api.deepseek.com/test HTTP/1.1\r\n\r\n'):
                        client,server=socket.socketpair();client.settimeout(2)
                        try:
                            client.sendall(request);sink._handle(server)
                            self.assertIn(b'403 NEKO_EGRESS_OFFLINE',client.recv(2048))
                        finally:client.close();server.close()
                    spend.assert_not_called();tunnel.assert_not_called();forward.assert_not_called()
                self.assertEqual(ledger.read_bytes(),original)
                self.assertEqual(sink.spent,{'api.deepseek.com':594,'www.lanlan.app':58})
            finally:sink._server.close()

    def test_normal_relay_keeps_its_existing_accounting(self):
        sink=Sink(2)
        client,server=socket.socketpair();client.settimeout(2)
        try:
            with patch.object(sink,'_tunnel') as tunnel:
                client.sendall(b'CONNECT api.deepseek.com:443 HTTP/1.1\r\n\r\n');sink._handle(server)
                self.assertIn(b'200 Connection established',client.recv(2048))
                tunnel.assert_called_once();self.assertEqual(sink.spent['api.deepseek.com'],1)
        finally:client.close();server.close();sink._server.close()

if __name__=='__main__':unittest.main(verbosity=2)
