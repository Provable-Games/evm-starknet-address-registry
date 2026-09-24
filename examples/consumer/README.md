# Execution-time association example

`AssociationConsumer` shows how an application can apply its own policy to a
registry link. Its `act(candidate)` entrypoint checks the immediate caller,
confirms that `candidate` is in the consumer's allowed set, and calls
`registry.is_associated(candidate, caller)` during execution before incrementing
`accepted`. The caller and eligibility result are never supplied by the client.

`ConsumerForwarder` demonstrates that forwarding changes the immediate caller to
the forwarder. An association belonging to the original account therefore does
not authorize the forwarded call. Applications that support forwarding need a
separate authorization design.

The [local integration suite](../../scripts/integration/README.md) deploys these
examples with the production registry and exercises linked, unlinked, disallowed,
zero-address, forwarded, moved, and revoked cases. This policy belongs to the
consumer; the registry and SDK remain generic.
