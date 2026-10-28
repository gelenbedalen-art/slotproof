#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only, exact-slot Solana RPC comparison. Python 3.11+, no dependencies."""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request


class RpcError(Exception):
    pass


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def endpoint_label(url):
    """Never publish API keys in path, userinfo, query or fragment."""
    p = urllib.parse.urlsplit(url)
    return (p.hostname or 'unknown') + '#' + hashlib.sha256(url.encode()).hexdigest()[:10]


class Rpc:
    ALLOWED = {'getGenesisHash', 'getSlot', 'getBlock', 'getVersion'}

    def __init__(self, url, timeout=12):
        if urllib.parse.urlsplit(url).scheme not in ('https', 'http'):
            raise ValueError('HTTP(S) RPC URL required')
        self.url, self.timeout, self.calls = url, timeout, []

    def call(self, method, params=None):
        if method not in self.ALLOWED:
            raise ValueError('Method is not read-only allowlisted')
        request = {'jsonrpc': '2.0', 'id': len(self.calls) + 1,
                   'method': method, 'params': params or []}
        record = {'request': request, 'started_at': utcnow()}
        start = time.monotonic()
        self.calls.append(record)
        try:
            req = urllib.request.Request(self.url, data=json.dumps(request).encode(),
                                         headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise RpcError('response_too_large')
                body = json.loads(raw)
            record['response'] = body
            if not isinstance(body, dict) or body.get('jsonrpc') != '2.0' or body.get('id') != request['id']:
                raise RpcError('invalid_rpc_envelope')
            if 'error' in body:
                # Provider error messages may contain credentials; retain only numeric code.
                code = body['error'].get('code') if isinstance(body['error'], dict) else None
                record['response'] = {'jsonrpc': '2.0', 'id': request['id'], 'error': {'code': code}}
                raise RpcError('rpc_error_' + str(code))
            if 'result' not in body:
                raise RpcError('missing_result')
            return body['result']
        except urllib.error.HTTPError as exc:
            record['error'] = 'http_' + str(exc.code)
            raise RpcError(record['error']) from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            record['error'] = 'transport_or_json_error'
            raise RpcError(record['error']) from None
        except RpcError as exc:
            record['error'] = str(exc)
            raise
        finally:
            record['elapsed_ms'] = round((time.monotonic() - start) * 1000, 2)
            record['finished_at'] = utcnow()


def observe(rpc):
    row = {'endpoint': endpoint_label(rpc.url), 'calls': rpc.calls}
    try:
        genesis = rpc.call('getGenesisHash')
        if not isinstance(genesis, str) or not genesis:
            raise RpcError('invalid_genesis')
        row['genesis'] = genesis
        slot = rpc.call('getSlot', [{'commitment': 'finalized'}])
        if type(slot) is not int or slot < 0 or slot > 2**53 - 1:
            raise RpcError('invalid_slot')
        row.update(slot=slot, status='ready')
    except RpcError as exc:
        row.update(status='unavailable', reason=str(exc))
    return row


def block_identity(block):
    if not isinstance(block, dict):
        raise RpcError('block_unavailable')
    for key in ('blockhash', 'previousBlockhash'):
        if not isinstance(block.get(key), str) or not block[key]:
            raise RpcError('invalid_block_identity')
    if type(block.get('parentSlot')) is not int or block['parentSlot'] < 0:
        raise RpcError('invalid_parent_slot')
    return {key: block[key] for key in ('blockhash', 'previousBlockhash', 'parentSlot')}


def compare(rows, target_slot, max_lag):
    ready = [r for r in rows if r.get('genesis') and type(r.get('slot')) is int]
    hashes = {r['genesis'] for r in ready}
    if len(hashes) > 1:
        return {'status': 'cluster_mismatch', 'consistent': None}
    if not ready:
        return {'status': 'insufficient_evidence', 'consistent': None}
    tip = max(r['slot'] for r in ready)
    for r in ready:
        r['lag_slots'] = tip - r['slot']
        r['lag_exceeds_threshold'] = r['lag_slots'] > max_lag
    identities = [json.dumps(r['block'], sort_keys=True) for r in rows if r.get('block')]
    # A failed provider is never silently converted into a successful comparison.
    if len(identities) < 2:
        return {'status': 'insufficient_evidence', 'consistent': None}
    consistent = len(set(identities)) == 1
    return {'status': ('match' if len(identities) == len(rows) else 'partial_match') if consistent else 'block_identity_mismatch',
            'consistent': consistent, 'compared_responses': len(identities), 'target_slot': target_slot}


def audit(urls, timeout=12, max_lag=32, lookback=0, rpc_factory=Rpc):
    if len(urls) < 2 or len(urls) > 8 or len(set(urls)) != len(urls):
        raise ValueError('Provide 2 to 8 distinct endpoints; duplicate URLs do not count as independent evidence')
    if max_lag < 0 or lookback < 0 or timeout <= 0:
        raise ValueError('Invalid thresholds')
    rpcs = [rpc_factory(url, timeout) for url in urls]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(rpcs)) as pool:
        rows = list(pool.map(observe, rpcs))
    ready = [r for r in rows if r['status'] == 'ready']
    target = max(0, min((r['slot'] for r in ready), default=0) - lookback)
    if ready and len({r['genesis'] for r in ready}) == 1:
        def read_pair(pair):
            rpc, row = pair
            if row['status'] != 'ready':
                return
            try:
                block = rpc.call('getBlock', [target, {'commitment': 'finalized',
                    'transactionDetails': 'none', 'rewards': False, 'maxSupportedTransactionVersion': 0}])
                row['block'] = block_identity(block)
                row['status'] = 'observed'
            except RpcError as exc:
                row.update(status='block_unavailable', reason=str(exc))
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(rpcs)) as pool:
            list(pool.map(read_pair, zip(rpcs, rows)))
    result = compare(rows, target, max_lag)
    return {'schema_version': 1, 'mode': 'live_read_only', 'observed_at': utcnow(),
            'commitment': 'finalized', 'max_lag_slots': max_lag,
            'lookback_slots': lookback, 'endpoints': rows, 'comparison': result,
            'limitations': ['Agreement is not proof of chain truth or provider independence.',
                'Observations are not simultaneous; slot lag is descriptive, not a fault verdict.',
                'A skipped/pruned target block is unavailable, never a mismatch.',
                'Only block identity is compared, not account state or transaction execution.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('endpoints', nargs='+')
    parser.add_argument('--timeout', type=float, default=12)
    parser.add_argument('--max-lag', type=int, default=32)
    parser.add_argument('--lookback', type=int, default=0)
    args = parser.parse_args()
    try:
        result = audit(args.endpoints, args.timeout, args.max_lag, args.lookback)
        print(json.dumps(result, indent=2))
        return 0 if result['comparison']['status'] == 'match' else 2
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    raise SystemExit(main())
