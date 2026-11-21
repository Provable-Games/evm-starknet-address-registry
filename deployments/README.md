# Deployment records

The [Mainnet registry](https://voyager.online/contract/0x00c865a977617dc70027c0a7b455ed5a34d1ad615267d8bf5359747a56b31337)
uses the `Loot Survivor` label and an address ending in `1337`. `mainnet.json`
records its transaction and constructor readback. The
[verified class](https://voyager.online/class/0x0125d11441d1e4971f3e327474fcd6878ca80c9941017cbacd643383ee227156)
has separate declaration evidence in `mainnet-class.json`.

[Sepolia registry deployment](sepolia.json) records the testnet instance
separately.

[Native L1 link on Sepolia](sepolia-l1-link.json) records a Safe v1.4.1
with two required signatures out of three owners, the canonical bridge
message, the destination account's consent, and a successful Loot Dungeon
`LinkedAccount` entry. The isolated dungeon used an ERC-721 fixture held by
the Safe and a root built with the game's snapshot encoder.
