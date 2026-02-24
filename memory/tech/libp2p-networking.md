<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# libp2p & Networking: Patterns & Reference

> **TL;DR:** libp2p is used sparingly in Storacha -- primarily for IPNI advertisement announcements via GossipSub in `storetheindex`. HTTP is the primary transport for content retrieval (byte-range requests to R2) and UCAN RPC. Storacha's own Go services do NOT create libp2p hosts; they use `go-libstoracha/ipnipublisher` for IPNI publishing. Bitswap is only active in Hoverboard (browser P2P node). No Kademlia DHT -- content routing uses IPNI's indexed HTTP lookup.

> Concepts: libp2p host (P1), GossipSub (P1), multiaddr (P1), Bitswap (P2), IPNI announcements (P1)
> Key repos: storetheindex, indexing-service, go-libstoracha (ipnipublisher)
> Note: libp2p is used sparingly in Storacha — primarily for IPNI advertisement announcements. HTTP is the primary transport for content retrieval and UCAN RPC.

## Role of libp2p in Storacha

```
                    Storacha Network Layer

  Client ←──HTTP──→ Upload Service (go-ucanto)
                          │
  Client ←──HTTP──→ Gateway (Freeway/Cloudflare Worker)
                          │
                    Indexing Service ←──HTTP──→ IPNI (cid.contact)
                          │
                    storetheindex
                          │
                    ┌─────┴─────┐
              libp2p Host    HTTP API
                    │
              GossipSub (advertisement announcements)
              Advertisement sync (dagsync)
```

**Key insight:** libp2p is NOT used for content transfer in Storacha. Content retrieval uses HTTP byte-range requests (blob-fetcher → R2). libp2p is used for IPNI advertisement propagation via GossipSub.

**Important:** Storacha's own Go services (indexing-service, piri) do NOT create libp2p hosts. They communicate via HTTP and use `go-libstoracha/ipnipublisher` for IPNI advertisement publishing (which handles libp2p internally). Only `storetheindex` (the IPNI indexer, a third-party dependency) creates a full libp2p host for P2P advertisement ingestion.

## Patterns

### Pattern: Create a libp2p host (IPNI indexer)
**When:** Setting up a P2P node for advertisement ingestion
**Template:**
```go
import (
    "github.com/libp2p/go-libp2p"
    "github.com/multiformats/go-multiaddr"
)

p2pmaddr, err := multiaddr.NewMultiaddr(p2pAddr)
p2pOpts := []libp2p.Option{
    libp2p.Identity(privKey),           // Ed25519 key → PeerID
    libp2p.ListenAddrs(p2pmaddr),       // e.g., /ip4/0.0.0.0/tcp/3003
}
if cfg.Addresses.NoResourceManager {
    p2pOpts = append(p2pOpts, libp2p.ResourceManager(&network.NullResourceManager{}))
}
p2pHost, err := libp2p.New(p2pOpts...)
defer p2pHost.Close()
```
**Key files:** `storetheindex/command/daemon.go`
**Gotchas:**
- PeerID is derived from the host's cryptographic key pair
- The `NullResourceManager` option disables resource limits (used in some configs)

### Pattern: Connect to GossipSub mesh (IPNI)
**When:** Subscribing to IPNI advertisement announcements
**Template:**
```go
import (
    "github.com/ipni/go-libipni/announce"
    "github.com/ipni/go-libipni/dagsync"
    "github.com/libp2p/go-libp2p/core/peer"
)

// Initialize ingester with the p2p host
ingester, err := ingest.NewIngester(cfg.Ingest, p2pHost, indexer, reg, dstore, dsTmp)

// Bootstrap: connect to known peers for gossip mesh
if len(cfg.Bootstrap.Peers) != 0 {
    addrs, err := cfg.Bootstrap.PeerAddrs()
    // connect to minimum peers for mesh participation
}
```
**Key files:** `storetheindex/internal/ingest/ingest.go`, `storetheindex/config/ingest.go`

### Pattern: Use multiaddr for IPNI endpoint configuration
**When:** Configuring IPNI provider addresses
**Template:**
```go
import (
    "github.com/ipni/go-libipni/maurl"
    "github.com/multiformats/go-multiaddr"
    "github.com/libp2p/go-libp2p/core/peer"
)

// Convert URL to multiaddr
url, _ := url.Parse("https://provider.example.com")
ma, _ := maurl.FromURL(url)

// Build provider AddrInfo
providerInfo := peer.AddrInfo{
    ID:    peerID,
    Addrs: []multiaddr.Multiaddr{ma},
}

// Use in IPNI options
server.WithIPNI(providerInfo, metadata.Default.New(metadata.IpfsGatewayHttp{}))
```
**Key files:** `indexing-service/cmd/server.go`

### Pattern: Publish IPNI advertisements (go-libstoracha)
**When:** Making content discoverable via IPNI
**Template:**
```go
import "github.com/storacha/go-libstoracha/ipnipublisher"

pub := ipnipublisher.New(...)

// Publish advertisement with multihash entries
link, err := pub.Publish(ctx, providerInfo, contextID, digestIterator, metadata)
// Creates a signed advertisement in the IPNI chain

// Announce to indexers
err = pub.Announce(ctx, link, announceAddrs)
// Sends HTTP or gossipsub announcement
```
**Key files:** `go-libstoracha/ipnipublisher/`

## Multiaddr Quick Reference

```
/ip4/127.0.0.1/tcp/4001                    # IPv4 + TCP
/ip4/0.0.0.0/udp/4001/quic-v1              # QUIC transport
/ip6/::1/tcp/8080/ws                        # IPv6 + WebSocket
/dns4/example.com/tcp/443/https             # DNS + HTTPS
/ip4/1.2.3.4/tcp/4001/p2p/12D3KooW...      # Full peer address
```

Format: `/<protocol>/<value>/<protocol>/<value>/...`
Binary: TLV (type-length-value) with varint protocol codes from multicodec table.

## GossipSub Quick Reference

```go
import pubsub "github.com/libp2p/go-libp2p-pubsub"

ps, _ := pubsub.NewGossipSub(ctx, host)
topic, _ := ps.Join("topic-name")
sub, _ := topic.Subscribe()

// Receive
msg, _ := sub.Next(ctx)

// Publish
topic.Publish(ctx, []byte("data"))
```

Key concepts:
- **Mesh**: Each peer maintains D connections per topic (eager push — full messages)
- **Gossip**: IHAVE/IWANT protocol for lazy pull (metadata only)
- **Heartbeat**: Periodic mesh maintenance (graft/prune) + gossip emission
- **Scoring** (v1.1): Peers scored by behavior; low-scoring peers pruned

## Bitswap in Storacha

Bitswap is referenced primarily in **IPNI metadata/protocol handling**, not as a direct transfer protocol. The primary retrieval path uses HTTP byte-range requests:

```
Gateway → Locator → blob-fetcher (HTTP range) → R2/S3
```

Bitswap metadata appears in indexing service test utilities and provider records for IPNI compatibility, but Storacha's architecture is HTTP-first.

## Key Files Index

| Role | File |
|------|------|
| libp2p host creation | `storetheindex/command/daemon.go` |
| IPNI ingester (gossipsub) | `storetheindex/internal/ingest/ingest.go` |
| IPNI config (gossip/bootstrap) | `storetheindex/config/ingest.go`, `storetheindex/config/bootstrap.go` |
| Multiaddr → IPNI opts | `indexing-service/cmd/server.go` |
| IPNI publisher (go-libstoracha) | `go-libstoracha/ipnipublisher/` |

## P1/P2 Details: Protocol Usage Status

| Protocol | Status | Where Used | Notes |
|----------|--------|------------|-------|
| **Noise** | Active | All P2P services | Default libp2p connection encryption |
| **GossipSub** | Active | storetheindex | IPNI advertisement announcements |
| **Bitswap** | Active (Hoverboard only) | hoverboard | Block exchange via miniswap |
| **DAGSync** | Active | storetheindex, indexing-service | Advertisement content sync |
| **GraphSync** | Not used | - | Replaced by DAGSync |
| **WebRTC** | Not used | - | Not needed (HTTP-first) |
| **WebTransport** | Not used | - | Not needed |
| **QUIC** | Not used | - | TCP is default transport |

### Noise Protocol
Connection encryption for all libp2p P2P communications:
- **Go:** `github.com/flynn/noise v1.1.0` (indirect via go-libp2p)
- **JS:** `@chainsafe/libp2p-noise` (in hoverboard)
- Default encryter — no explicit configuration needed

### Bitswap in Hoverboard
The only active Bitswap implementation in Storacha:
```javascript
import { Miniswap, BITSWAP_PROTOCOL } from 'miniswap'

export function enableBitswap(libp2p, blockstore) {
  const miniswap = new Miniswap({
    async has(cid) { /* check blockstore */ },
    async get(cid) { /* fetch from blockstore */ }
  })
  libp2p.handle(BITSWAP_PROTOCOL, miniswap.handler)
}
```
**Key files:** `hoverboard/src/libp2p.js`

Go services use Bitswap only as a metadata protocol indicator in IPNI test utilities (`ipnimeta.Bitswap{}`), not for active transfer.

### Hoverboard libp2p Host (JS — Browser P2P)
```javascript
const libp2p = await createLibp2p({
  privateKey,
  addresses: { listen: [listenAddr.toString()] },
  transports: [transport()],           // cf-libp2p-ws-transport (WebSockets)
  streamMuxers: [yamux(), mplex()],    // Yamux primary, Mplex fallback
  connectionEncrypters: [noise()],
  services: { identify: identify() }
})
```
**Key files:** `hoverboard/src/libp2p.js`

### GossipSub Configuration (storetheindex)
```go
sub, err := dagsync.NewSubscriber(h, ing.lsys,
    dagsync.RecvAnnounce(
        cfg.PubSubTopic,  // Default: "/indexer/ingest/mainnet"
        announce.WithAllowPeer(reg.Allowed),
        announce.WithFilterIPs(reg.FilterIPsEnabled()),
        announce.WithResend(cfg.ResendDirectAnnounce),
    ),
)
```

**Bootstrap peers** (hardcoded IPFS mainnet):
```
/dns4/lotus-bootstrap.ipfsforce.com/tcp/41778/p2p/12D3KooWGhuf...
/dns4/bootstrap-0.starpool.in/tcp/12757/p2p/12D3KooWGHpBMeZb...
```

**Key files:** `storetheindex/internal/ingest/ingest.go`, `storetheindex/config/bootstrap.go`

### Common libp2p Configuration Defaults
- **Connection encrypter:** Noise (implicit via libp2p)
- **Stream muxers:** Yamux (primary), Mplex (fallback in hoverboard)
- **Transport:** TCP (Go services), WebSockets (hoverboard/browsers)
- **Services:** Identify (peer capabilities exchange)
- **Resource management:** NullResourceManager for testing/lightweight deployments

## Design Rationale

- **HTTP over libp2p for content**: Storacha uses Cloudflare Workers (Freeway) for content serving and HTTP byte-range requests for block fetching. This simplifies deployment, enables CDN caching, and avoids the complexity of maintaining P2P connections for retrieval.
- **GossipSub for IPNI only**: The IPNI advertisement announcement protocol uses gossipsub for efficient, decentralized propagation of advertisement notifications. This is the main P2P interaction.
- **No Kademlia DHT**: Content routing goes through IPNI's indexed lookup (HTTP API at `cid.contact`) rather than DHT traversal. IPNI provides O(1) lookups vs DHT's O(log n) hops.
- **Multiaddr for addressing**: Used throughout for transport-agnostic peer addressing in IPNI provider records, even when the actual transport is HTTP.
- **DAGSync over GraphSync**: GraphSync is not used — DAGSync (simpler, HTTP-compatible) handles advertisement content synchronization between publishers and indexers.
- **Bitswap limited to Hoverboard**: Only the browser-facing P2P node uses Bitswap. All server-side retrieval uses HTTP byte-range requests — simpler, cacheable, CDN-compatible.

## Authoritative Specs
- [libp2p Specs](https://github.com/libp2p/specs)
- [Bitswap Spec](https://github.com/ipfs/specs/blob/main/BITSWAP.md)
- [IPNI (InterPlanetary Network Indexer)](https://github.com/ipni/specs)
