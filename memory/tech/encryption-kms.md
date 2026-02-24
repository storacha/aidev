<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Encryption & KMS: Patterns & Reference

> **TL;DR:** Storacha uses envelope encryption (KEK/DEK). The RSA-OAEP-3072 key pair lives in Google Cloud KMS (private key never leaves hardware). Clients generate AES-GCM-256 DEKs, encrypt data, wrap the DEK with the RSA public key. Decryption requires a UCAN-authorized `space/encryption/key/decrypt` invocation to ucan-kms (Cloudflare Worker). ECDH P-256 key agreement available for agent-to-agent encryption. Paid plan required.

> Concepts: KEK/DEK envelope encryption (P0), ucan-kms service (P0), Google Cloud KMS RSA-OAEP (P0), ECDH P-256 key agreement (P0), AES-GCM-256 (P0)
> Key repos: ucan-kms, upload-service (access-client)

## How Encryption Works

```
Client                              ucan-kms (Cloudflare Worker)         Google Cloud KMS
  │                                       │                                    │
  │  space/encryption/setup               │                                    │
  │──────────────────────────────────────>│                                    │
  │  (UCAN invocation, space DID)         │  Create/get RSA key pair           │
  │                                       │──────────────────────────────────>│
  │                                       │  RSA-OAEP-3072-SHA256             │
  │  { publicKey (PEM), algorithm }       │<──────────────────────────────────│
  │<──────────────────────────────────────│                                    │
  │                                       │                                    │
  │  Generate DEK (AES-GCM-256)          │                                    │
  │  Encrypt data with DEK               │                                    │
  │  Encrypt DEK with RSA public key     │                                    │
  │  Store: encrypted data + wrapped DEK │                                    │
  │                                       │                                    │
  │  space/encryption/key/decrypt         │                                    │
  │──────────────────────────────────────>│                                    │
  │  (UCAN invocation, wrapped DEK)       │  asymmetricDecrypt                │
  │                                       │──────────────────────────────────>│
  │  { decryptedSymmetricKey }            │  plaintext DEK                    │
  │<──────────────────────────────────────│<──────────────────────────────────│
  │                                       │                                    │
  │  Decrypt data with DEK               │                                    │
```

**Key insight:** RSA private key NEVER leaves Google KMS. Client encrypts DEK with RSA public key; only the KMS can unwrap it.

## Patterns

### Pattern: Setup encryption for a space
**When:** Initializing encryption for a space (first time)
**Template:**
```js
// Client side
const receipt = await SpaceEncryptionSetup
  .invoke({
    issuer: agent,
    audience: ucanKmsServiceDID,
    with: spaceDID,
    nb: {},
    proofs: [delegation],
  })
  .execute(connection)
// receipt.out.ok = { publicKey: '<PEM string>', algorithm: 'RSA_DECRYPT_OAEP_3072_SHA256', provider: 'google-kms' }

// Server side (handler):
// 1. Validate UCAN
// 2. Check space has paid plan
// 3. Call Google KMS to create/retrieve RSA key pair
const sanitizedKeyId = sanitizeSpaceDIDForKMSKeyId(request.space)
const keyName = `projects/${projectId}/locations/${loc}/keyRings/${ring}/cryptoKeys/${sanitizedKeyId}`
// purpose: ASYMMETRIC_DECRYPT, algorithm: RSA_DECRYPT_OAEP_3072_SHA256
```
**Key files:** `ucan-kms/src/handlers/encryptionSetup.js`, `ucan-kms/src/services/googleKms.js`
**Gotchas:**
- Requires a paid plan (subscription check)
- KMS key ID is derived from sanitized Space DID
- Public key returned in PEM format

### Pattern: Decrypt a wrapped DEK
**When:** Retrieving encrypted content — need to unwrap the symmetric key
**Template:**
```js
// Client side
const receipt = await SpaceEncryptionKeyDecrypt
  .invoke({
    issuer: agent,
    audience: ucanKmsServiceDID,
    with: spaceDID,
    nb: { encryptedSymmetricKey: wrappedDEKBytes },
    proofs: [delegation],
  })
  .execute(connection)
// receipt.out.ok = { decryptedSymmetricKey: '<base64 encoded key>' }

// Server side:
// 1. Validate decrypt delegation
// 2. Check subscription
// 3. Check revocation status
// 4. Call Google KMS asymmetricDecrypt
const response = await fetch(`${KMS_URL}/${keyVersion}:asymmetricDecrypt`, {
  method: 'POST',
  body: JSON.stringify({ ciphertext: base64Ciphertext })
})
```
**Key files:** `ucan-kms/src/handlers/keyDecryption.js`, `ucan-kms/src/services/googleKms.js`
**Gotchas:**
- Revocation is checked before decryption (revoked delegations can't decrypt)
- Rate-limited per space
- Generic error messages to prevent information leakage

### Pattern: ECDH key agreement (client-side P2P encryption)
**When:** Establishing a shared secret between two principals for direct encryption
**Template:**
```js
import { EcdhKeypair } from '@web3-storage/access-client/crypto/p256-ecdh'

// Create an ECDH key pair (P-256 curve)
const keypair = await EcdhKeypair.create()
// keypair.did → did:key derived from P-256 public key

// Derive a shared AES-GCM-256 key from another principal's DID
const sharedKey = await keypair.deriveSharedKey(otherDid)
// Uses: webcrypto.subtle.deriveKey({ name: 'ECDH', public: otherPubKey },
//   privateKey, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt'])

// Encrypt data for another DID
const encrypted = await keypair.encryptForDid(data, otherDid)
// Under the hood: deriveSharedKey → AES-GCM encrypt
```
**Key files:** `upload-service/packages/access-client/src/crypto/p256-ecdh.js`
**Gotchas:**
- P-256 public key is encoded as a `did:key` — `didFromPubkey()` / `ecdhKeyFromDid()`
- WebCrypto API used throughout (`crypto.subtle`)
- AES-GCM nonce must be unique per encryption (critical!)

### Pattern: ucan-kms service definition (ucanto)
**When:** Understanding the service structure
**Template:**
```js
// Service interface (ucanto pattern)
export function createService(ctx, env) {
  return {
    space: {
      encryption: {
        setup: UcantoServer.provideAdvanced({
          capability: EncryptionSetup,
          audience: AudienceSchema,
          handler: async ({ capability, invocation }) => {
            return handleEncryptionSetup(request, invocation, ctx, env)
          }
        }),
        key: {
          decrypt: UcantoServer.provideAdvanced({
            capability: EncryptionKeyDecrypt,
            audience: AudienceSchema,
            handler: async ({ capability, invocation }) => {
              return handleKeyDecryption(request, invocation, ctx, env)
            }
          })
        }
      }
    }
  }
}
```
**Key files:** `ucan-kms/src/service.js`, `ucan-kms/src/api.types.ts`

## Key Types

```typescript
// Service interface
interface Service {
  space: {
    encryption: {
      setup: ServiceMethod<SpaceEncryptionSetup, EncryptionSetupResult, Failure>
      key: {
        decrypt: ServiceMethod<SpaceEncryptionKeyDecrypt, KeyDecryptResult, Failure>
      }
    }
  }
}

// Context required by handlers
interface Context {
  ucanKmsSigner: Signer
  kms: KMSService         // Google KMS integration
  revocationStatusClient: RevocationStatusClient
  subscriptionStatusService: SubscriptionStatusService
  kmsRateLimiter: KmsRateLimiter
}
```

## Key Files Index

| Role | File |
|------|------|
| Service definition | `ucan-kms/src/service.js` |
| Service types | `ucan-kms/src/api.types.ts` |
| Setup handler | `ucan-kms/src/handlers/encryptionSetup.js` |
| Decrypt handler | `ucan-kms/src/handlers/keyDecryption.js` |
| Google KMS integration | `ucan-kms/src/services/googleKms.js` |
| ECDH P-256 key agreement | `upload-service/packages/access-client/src/crypto/p256-ecdh.js` |

## Security Features

- **UCAN authorization**: Every KMS operation requires valid UCAN delegation
- **Revocation checking**: Checked before key decryption
- **Rate limiting**: Per-space rate limits on KMS operations
- **SecureString**: Memory hygiene — sensitive data auto-zeroed on disposal
- **Paid plan required**: Encryption setup requires active subscription
- **Generic errors**: Error messages sanitized to prevent information leakage

## Design Rationale

- **KEK/DEK separation**: The RSA key (KEK) stays in Google KMS hardware; only symmetric DEKs are wrapped/unwrapped. This limits blast radius — compromising a DEK exposes one piece of content, not the master key.
- **RSA-OAEP-3072**: Chosen for async key wrapping (client encrypts with public key, only KMS can decrypt). 3072-bit RSA provides ~128 bits of security, matching AES-256.
- **ECDH for P2P**: Used for direct agent-to-agent encryption (e.g., sharing encrypted content). The DID-based key agreement means any two principals can derive a shared secret from their public DIDs alone.
- **Cloudflare Worker + Google KMS**: The Worker handles UCAN auth and business logic; Google KMS handles the cryptographic heavy lifting in hardware-secured boundaries.

## Authoritative Specs
- [UCAN KMS Source](https://github.com/storacha/ucan-kms)
- [WNFS Spec (encryption model)](https://github.com/wnfs-wg/spec)
