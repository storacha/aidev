# ucan-kms

Cloudflare Worker providing encryption key management for Storacha spaces. KEK/DEK envelope encryption with Google Cloud KMS.

## Quick Reference

```bash
npm install
npm run test:unit       # Unit tests
npm run type-check      # TypeScript check
npm run build           # esbuild → dist/worker.mjs
```

## Structure

```
src/
  index.js             # CF Worker entry point (fetch handler)
  service.js           # UCAN service (2 capabilities)
  handlers/
    encryptionSetup.js # space/encryption/setup handler
    keyDecryption.js   # space/encryption/key/decrypt handler
  kms/
    kmsClient.js       # Google Cloud KMS client
  types/               # TypeScript type definitions
```

## UCAN Capabilities

| Capability | Handler | Purpose |
|---|---|---|
| `space/encryption/setup` | `encryptionSetup.js` | Initialize encryption for a space (generate KEK, store in KMS) |
| `space/encryption/key/decrypt` | `keyDecryption.js` | Decrypt a DEK using the space's KEK |

## Encryption Model

- **KEK** (Key Encryption Key): RSA-OAEP-3072, managed by Google Cloud KMS
- **DEK** (Data Encryption Key): AES-GCM-256, generated per content, encrypted with KEK
- **Key agreement**: ECDH P-256 for client ↔ service key exchange
- **Envelope encryption**: DEK encrypts content, KEK encrypts DEK, KMS protects KEK

## What Breaks If You Change Things Here

- Encryption format changes break decryption of existing encrypted content
- KMS key rotation requires backward-compatible decryption
- Rate limiting logic affects encryption operation availability
- No spec document exists for these capabilities
