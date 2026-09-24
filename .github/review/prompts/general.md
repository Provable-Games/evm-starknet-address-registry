Review the change as one repository-wide reviewer. Follow relevant behavior across
the protocol, Cairo contract, TypeScript SDK, integration tooling, examples, build,
and CI rather than treating changed files in isolation.

For Cairo and Starknet code, examine interfaces, hashing and signature validation,
caller authorization, nonce and storage transitions, rollback, enumeration, events,
ABI agreement, resource bounds, and Scarb or Starknet Foundry coverage. For protocol
artifacts, verify the specification, ABI, vectors, exact signing statements, schemas,
labels, and generated or consumed representations remain coherent and deterministic.
Do not request a protocol change reserved for explicit approval unless the change
introduces a concrete unresolved inconsistency.

For the TypeScript SDK and integrations, examine lossless values, typed-data parity,
provider and account selection, network and block-consistency races, serialization,
errors, package and browser compatibility, cross-stack behavior, and meaningful test
coverage. Keep application policy outside the generic contract and SDK.

For security, build, and CI changes, examine trust boundaries, credential isolation,
exact-revision binding, safe publication, dependency and runtime pins, routing,
caching, failure handling, and whether required checks can pass without doing their
intended work. Distinguish recorded evidence from proposed gates. Apply the shared
policy.
