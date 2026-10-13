"""Actual local relay sockets; no host, supplier, credentials, ledger or audio."""
import socket
import threading
import time
import unittest
from unittest.mock import patch

import neko_desktop_tutor_host as host


class ProxyIdle(unittest.TestCase):
    def relay_after_idle(self, initial_timeout, quiet_seconds):
        learner, downstream = socket.socketpair()
        upstream, provider = socket.socketpair()
        downstream.settimeout(initial_timeout)
        upstream.settimeout(initial_timeout)
        learner.settimeout(2)
        provider.settimeout(2)
        relay = host.Sink(0, extra={'local-test.invalid': None})
        # Reuse actual tunnel/pump methods; only connection creation is directed
        # to this already-connected local socket, never the named remote host.
        with patch.object(host.socket, 'create_connection', return_value=upstream) as connect:
            task = threading.Thread(target=relay._tunnel, args=(downstream, 'local-test.invalid:443'), daemon=True)
            task.start()
            try:
                deadline=time.monotonic()+2
                while upstream.gettimeout() is not None and time.monotonic()<deadline:
                    time.sleep(.005)
                self.assertIsNone(upstream.gettimeout())
                self.assertIsNone(downstream.gettimeout())
                connect.assert_called_once_with(('local-test.invalid',443),timeout=20)
                time.sleep(quiet_seconds)
                self.assertTrue(task.is_alive(), 'quiet must not disconnect an established tunnel')
                learner.sendall(b'new input after quiet')
                self.assertEqual(provider.recv(128),b'new input after quiet')
                provider.sendall(b'new response')
                self.assertEqual(learner.recv(128),b'new response')
            finally:
                for sock in (learner, provider):
                    try: sock.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
                    sock.close()
                task.join(timeout=2)
                relay._server.close()
        self.assertFalse(task.is_alive(), 'peer EOF must close both relay directions')
        self.assertEqual(relay.spent,{})
        self.assertEqual([item['action'] for item in relay.decisions],['allowed_connect'])

    def test_short_inherited_deadline_does_not_end_quiet_or_duplex(self):
        self.relay_after_idle(.04,.15)

    def test_real_twenty_second_quiet_then_new_input_and_eof(self):
        self.relay_after_idle(20,21.2)


if __name__=='__main__':
    unittest.main()
