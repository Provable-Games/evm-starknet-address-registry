# Execution-time association example

`AssociationConsumer` shows how an application can apply its own policy to a
registry link. Its `act(candidate)` entrypoint checks the immediate caller,
confirms that `candidate` is in the consumer's allowed set, and calls
`registry.is_associated(candidate, caller)` during execution before incrementing
`accepted`. The caller and eligibility result are never supplied by the client.

The v1.0.0 registry and the first Sepolia L1-link class can report a link for
the keyless Ethereum address `0x3f17f1962b36e491b30a40b2405849e597ba5fb5`.
The consumer constructor rejects any allowlist containing this address.
The [protocol specification](../../protocol/spec.md#eip-712-authorization)
identifies both affected classes.

`ConsumerForwarder` demonstrates that forwarding changes the immediate caller to
the forwarder. An association belonging to the original account therefore does
not authorize the forwarded call. Applications that support forwarding need a
separate authorization design.

The [local integration suite](../../scripts/integration/README.md) deploys these
examples with the production registry and exercises linked, unlinked, disallowed,
zero-address, forwarded, moved, and revoked cases. This policy belongs to the
consumer; the registry and SDK remain generic.
