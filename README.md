# SlotProof

A read-only CLI for Solana developers reproducing RPC disagreements. It checks cluster identity, fixes commitment to finalized, chooses the minimum observed finalized slot minus an optional lookback, and compares block identity at that exact slot. It emits timestamped JSON evidence, structured failures, and endpoint labels that omit URL paths, credentials and query strings.

## Run

Python 3.11+; no pip packages, wallet, API subscription or funded account required for the included tests.

```sh
python3 -m unittest -v test_slotproof
python3 slotproof.py https://api.devnet.solana.com https://api.testnet.solana.com
# Intentionally mixed clusters: expect cluster_mismatch and exit code 2.
python3 slotproof.py https://api.mainnet-beta.solana.com https://solana-rpc.publicnode.com --lookback 8
# Read-only mainnet calls cost no onchain gas. Public RPCs may block or rate-limit.
```

Exit 0 means all sampled block identities match. Exit 2 means mismatch, partial/unavailable evidence, or invalid input. A provider error is never a successful comparison. No sendTransaction method exists; the transport accepts only getGenesisHash, getSlot, getBlock and getVersion.

## Evidence collected 28 October 2026

14 tests passed, including exact-slot requests, cluster mismatch, parent/hash mismatch, null blocks, invalid slot types, URL redaction, partial results, an actual local HTTP envelope failure and forbidden write methods. These deterministic tests use fixtures, not live provider observations.

Live calls to devnet and testnet returned different genesis hashes; comparison correctly abstained before block comparison. A mainnet run read a finalized block from Solana's public RPC, but PublicNode returned HTTP 403 from this environment, so no two-provider mainnet agreement is claimed. A separate dRPC run also returned 403. No provider SLA, users, revenue or performance benchmark is claimed.

### Recorded test output

```text
test_block_hash_mismatch (test_slotproof.ComparisonTests.test_block_hash_mismatch) ... ok
test_cluster_mismatch_suppresses_block_reads (test_slotproof.ComparisonTests.test_cluster_mismatch_suppresses_block_reads) ... ok
test_duplicate_endpoints (test_slotproof.ComparisonTests.test_duplicate_endpoints) ... ok
test_invalid_slot_rejected (test_slotproof.ComparisonTests.test_invalid_slot_rejected) ... ok
test_lookback (test_slotproof.ComparisonTests.test_lookback) ... ok
test_match (test_slotproof.ComparisonTests.test_match) ... ok
test_null_block_abstains (test_slotproof.ComparisonTests.test_null_block_abstains) ... ok
test_parent_mismatch (test_slotproof.ComparisonTests.test_parent_mismatch) ... ok
test_partial_does_not_claim_complete (test_slotproof.ComparisonTests.test_partial_does_not_claim_complete) ... ok
test_redacts_url (test_slotproof.ComparisonTests.test_redacts_url) ... ok
test_rpc_error_abstains (test_slotproof.ComparisonTests.test_rpc_error_abstains) ... ok
test_slot_drift_is_not_mismatch (test_slotproof.ComparisonTests.test_slot_drift_is_not_mismatch) ... ok
test_actual_http_and_envelope_rejection (test_slotproof.TransportTests.test_actual_http_and_envelope_rejection) ... ok
test_write_method_forbidden (test_slotproof.TransportTests.test_write_method_forbidden) ... ok

----------------------------------------------------------------------
Ran 14 tests in 0.526s

OK
```

### Live mixed-cluster evidence

```json
{
  "schema_version": 1,
  "mode": "live_read_only",
  "observed_at": "2026-10-28T10:01:30.829357+00:00",
  "commitment": "finalized",
  "max_lag_slots": 32,
  "lookback_slots": 0,
  "endpoints": [
    {
      "endpoint": "api.devnet.solana.com#3d423a3cdf",
      "calls": [
        {
          "request": {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getGenesisHash",
            "params": []
          },
          "started_at": "2026-10-28T10:01:16.608361+00:00",
          "response": {
            "jsonrpc": "2.0",
            "result": "EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG",
            "id": 1
          },
          "elapsed_ms": 4764.78,
          "finished_at": "2026-10-28T10:01:21.373173+00:00"
        },
        {
          "request": {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "getSlot",
            "params": [
              {
                "commitment": "finalized"
              }
            ]
          },
          "started_at": "2026-10-28T10:01:21.373192+00:00",
          "response": {
            "jsonrpc": "2.0",
            "result": 516018121,
            "id": 2
          },
          "elapsed_ms": 9455.48,
          "finished_at": "2026-10-28T10:01:30.828694+00:00"
        }
      ],
      "genesis": "EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG",
      "slot": 516018121,
      "status": "ready"
    },
    {
      "endpoint": "api.testnet.solana.com#e57ac4ca8d",
      "calls": [
        {
          "request": {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getGenesisHash",
            "params": []
          },
          "started_at": "2026-10-28T10:01:16.610321+00:00",
          "response": {
            "jsonrpc": "2.0",
            "result": "4uhcVJyU9pJkvQyS88uRDiswHXSCkY3zQawwpjk2NsNY",
            "id": 1
          },
          "elapsed_ms": 5137.18,
          "finished_at": "2026-10-28T10:01:21.747527+00:00"
        },
        {
          "request": {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "getSlot",
            "params": [
              {
                "commitment": "finalized"
              }
            ]
          },
          "started_at": "2026-10-28T10:01:21.747591+00:00",
          "response": {
            "jsonrpc": "2.0",
            "result": 457665252,
            "id": 2
          },
          "elapsed_ms": 2606.12,
          "finished_at": "2026-10-28T10:01:24.353731+00:00"
        }
      ],
      "genesis": "4uhcVJyU9pJkvQyS88uRDiswHXSCkY3zQawwpjk2NsNY",
      "slot": 457665252,
      "status": "ready"
    }
  ],
  "comparison": {
    "status": "cluster_mismatch",
    "consistent": null
  },
  "limitations": [
    "Agreement is not proof of chain truth or provider independence.",
    "Observations are not simultaneous; slot lag is descriptive, not a fault verdict.",
    "A skipped/pruned target block is unavailable, never a mismatch.",
    "Only block identity is compared, not account state or transaction execution."
  ]
}

```

### Live mainnet partial observation

```json
{
  "schema_version": 1,
  "mode": "live_read_only",
  "observed_at": "2026-10-28T10:01:25.170849+00:00",
  "commitment": "finalized",
  "max_lag_slots": 32,
  "lookback_slots": 8,
  "endpoints": [
    {
      "endpoint": "api.mainnet-beta.solana.com#d6092b5f25",
      "calls": [
        {
          "request": {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getGenesisHash",
            "params": []
          },
          "started_at": "2026-10-28T10:01:15.237532+00:00",
          "response": {
            "jsonrpc": "2.0",
            "result": "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d",
            "id": 1
          },
          "elapsed_ms": 3866.18,
          "finished_at": "2026-10-28T10:01:19.103744+00:00"
        },
        {
          "request": {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "getSlot",
            "params": [
              {
                "commitment": "finalized"
              }
            ]
          },
          "started_at": "2026-10-28T10:01:19.103766+00:00",
          "response": {
            "jsonrpc": "2.0",
            "result": 462434892,
            "id": 2
          },
          "elapsed_ms": 2928.02,
          "finished_at": "2026-10-28T10:01:22.031808+00:00"
        },
        {
          "request": {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "getBlock",
            "params": [
              462434884,
              {
                "commitment": "finalized",
                "transactionDetails": "none",
                "rewards": false,
                "maxSupportedTransactionVersion": 0
              }
            ]
          },
          "started_at": "2026-10-28T10:01:22.032792+00:00",
          "response": {
            "jsonrpc": "2.0",
            "result": {
              "blockHeight": 440459472,
              "blockTime": 1793181679,
              "blockhash": "J7WuuYPf3MSzApiG4kGCgViU6arf8XRjwuqRwHpFrTPb",
              "parentSlot": 462434883,
              "previousBlockhash": "5VjJXc8ExrsayJ9r36hhoSsQT5dbTkDufzterpGfN9PV"
            },
            "id": 3
          },
          "elapsed_ms": 3137.55,
          "finished_at": "2026-10-28T10:01:25.170389+00:00"
        }
      ],
      "genesis": "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d",
      "slot": 462434892,
      "status": "observed",
      "block": {
        "blockhash": "J7WuuYPf3MSzApiG4kGCgViU6arf8XRjwuqRwHpFrTPb",
        "previousBlockhash": "5VjJXc8ExrsayJ9r36hhoSsQT5dbTkDufzterpGfN9PV",
        "parentSlot": 462434883
      },
      "lag_slots": 0,
      "lag_exceeds_threshold": false
    },
    {
      "endpoint": "solana-rpc.publicnode.com#c435df7494",
      "calls": [
        {
          "request": {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getGenesisHash",
            "params": []
          },
          "started_at": "2026-10-28T10:01:15.238700+00:00",
          "error": "http_403",
          "elapsed_ms": 4476.9,
          "finished_at": "2026-10-28T10:01:19.715619+00:00"
        }
      ],
      "status": "unavailable",
      "reason": "http_403"
    }
  ],
  "comparison": {
    "status": "insufficient_evidence",
    "consistent": null
  },
  "limitations": [
    "Agreement is not proof of chain truth or provider independence.",
    "Observations are not simultaneous; slot lag is descriptive, not a fault verdict.",
    "A skipped/pruned target block is unavailable, never a mismatch.",
    "Only block identity is compared, not account state or transaction execution."
  ]
}

```

## Scope and limitations

- Equal responses do not establish truth, consensus, or provider independence.
- Slot observations are not simultaneous. Lag is descriptive, not proof of faulty behavior.
- Skipped or pruned target slots stay unavailable; they are never called inconsistent.
- This version compares blockhash, previousBlockhash and parentSlot, not account state, transaction execution or throughput.
- Do not publish a private RPC URL in shell history. Evidence labels remove credentials, but your own command history is outside this tool.

## Proposed next milestone (not completed)

Request: USD 1,500 for a focused four-week public-goods release, subject to the foundation's review. 20h × $25: schema/transport hardening and HTTP failure coverage; 24h × $25: reproducible multi-provider fixtures, CI and regression captures; 16h × $25: documentation, packaging and a developer walkthrough. Acceptance: reviewer can run tests with one command, reproduce the included failure cases, and inspect independently acquired raw responses with timestamps. No paid RPC or mainnet write is required by this proposed scope.

## Maintainer

gelenbedalen / KalenSolves. The developer owns scope, architecture, implementation review, tests and delivery. Early prototype; no external users or funding received for this project are claimed.

## References

- https://solana.com/docs/rpc
- https://solana.com/docs/rpc/http/getgenesishash
- https://solana.com/docs/rpc/http/getslot
- https://solana.com/docs/rpc/http/getblock
- https://solana.publicnode.com/

## License

MIT License

Copyright (c) 2026 gelenbedalen

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
