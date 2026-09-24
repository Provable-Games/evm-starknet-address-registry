# Association preview example

`loadAssociationPreview` shows how a client can read registry associations for an
account and compare them with an application-supplied allowed set. It renders loading,
error, or ready state. A successful empty result can prompt registration; every
ready state can offer another Ethereum wallet. Display the snapshot block with any
matches so users know when the preview was observed.

The host supplies an authenticated `RegistryReader`, account, concrete block, and
allowed set. Discard render callbacks from superseded loads. For signing, the host
also supplies the selected EIP-1193 provider and `AccountAdapter`; a mutable
adapter must increment `generation` and emit `subscribeChange` for every account,
chain, or disconnect transition.

Signing uses the selected wallet's `eth_signTypedData_v4` path. Submit calls through
the application's approved account execution flow. The preview is informational;
the [consumer contract](../consumer/README.md) demonstrates checking association
during execution.
