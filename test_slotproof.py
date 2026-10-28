# SPDX-License-Identifier: MIT
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from slotproof import Rpc, RpcError, audit, endpoint_label


BLOCK = {'blockhash': 'hash-A', 'previousBlockhash': 'hash-P', 'parentSlot': 99}


class FakeRpc:
    configs = {}
    def __init__(self, url, timeout):
        self.url, self.calls, self.config = url, [], self.configs[url]
    def call(self, method, params=None):
        self.calls.append({'method': method, 'params': params})
        value = self.config[method]
        if isinstance(value, Exception):
            raise value
        return value


class ComparisonTests(unittest.TestCase):
    def run_case(self, a=None, b=None, **kwargs):
        base = {'getGenesisHash': 'cluster-A', 'getSlot': 100, 'getBlock': BLOCK}
        FakeRpc.configs = {'http://a': base | (a or {}), 'http://b': base | (b or {})}
        return audit(['http://a', 'http://b'], rpc_factory=FakeRpc, **kwargs)

    def test_match(self):
        self.assertEqual(self.run_case()['comparison']['status'], 'match')
    def test_slot_drift_is_not_mismatch(self):
        r = self.run_case(b={'getSlot': 140})
        self.assertTrue(r['comparison']['consistent'])
        self.assertTrue(r['endpoints'][0]['lag_exceeds_threshold'])
        for e in r['endpoints']:
            self.assertEqual(e['calls'][-1]['params'][0], 100)
            self.assertEqual(e['calls'][-1]['params'][1]['commitment'], 'finalized')
    def test_cluster_mismatch_suppresses_block_reads(self):
        r = self.run_case(b={'getGenesisHash': 'cluster-B'})
        self.assertEqual(r['comparison']['status'], 'cluster_mismatch')
        self.assertTrue(all(len(e['calls']) == 2 for e in r['endpoints']))
    def test_block_hash_mismatch(self):
        r = self.run_case(b={'getBlock': BLOCK | {'blockhash': 'other'}})
        self.assertFalse(r['comparison']['consistent'])
    def test_parent_mismatch(self):
        r = self.run_case(b={'getBlock': BLOCK | {'parentSlot': 98}})
        self.assertFalse(r['comparison']['consistent'])
    def test_null_block_abstains(self):
        r = self.run_case(b={'getBlock': None})
        self.assertIsNone(r['comparison']['consistent'])
    def test_rpc_error_abstains(self):
        self.assertEqual(self.run_case(b={'getSlot': RpcError('unavailable')})['comparison']['status'], 'insufficient_evidence')
    def test_invalid_slot_rejected(self):
        for slot in [True, -1, 1.5, '100', 2**53]:
            self.assertEqual(self.run_case(b={'getSlot': slot})['endpoints'][1]['reason'], 'invalid_slot')
    def test_lookback(self):
        r = self.run_case(lookback=5)
        self.assertEqual(r['comparison']['target_slot'], 95)
    def test_duplicate_endpoints(self):
        with self.assertRaises(ValueError): audit(['http://a', 'http://a'])
    def test_redacts_url(self):
        label = endpoint_label('https://user:pass@example.org/private-key?token=secret')
        self.assertTrue(label.startswith('example.org#'))
        self.assertNotIn('secret', label)
        self.assertNotIn('private', label)
    def test_partial_does_not_claim_complete(self):
        base = {'getGenesisHash': 'A', 'getSlot': 100, 'getBlock': BLOCK}
        FakeRpc.configs = {'http://a': base, 'http://b': base, 'http://c': base | {'getSlot': RpcError('bad')}}
        r = audit(list(FakeRpc.configs), rpc_factory=FakeRpc)
        self.assertEqual(r['comparison']['status'], 'partial_match')


class TransportTests(unittest.TestCase):
    def test_actual_http_and_envelope_rejection(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                req = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                body = {'jsonrpc': '2.0', 'id': req['id'] + 1, 'result': 'A'}
                self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(body).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            rpc = Rpc('http://127.0.0.1:' + str(server.server_port))
            with self.assertRaisesRegex(RpcError, 'invalid_rpc_envelope'): rpc.call('getGenesisHash')
            self.assertIn('elapsed_ms', rpc.calls[0])
        finally:
            server.shutdown(); server.server_close(); thread.join()
    def test_write_method_forbidden(self):
        with self.assertRaises(ValueError): Rpc('http://localhost').call('sendTransaction')


if __name__ == '__main__': unittest.main(verbosity=2)
