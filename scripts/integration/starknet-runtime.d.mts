/** Small dev-only runtime port; external result structures must be validated. */
export interface NativeCall {
  readonly contractAddress: string;
  readonly entrypoint: string;
  readonly calldata: readonly string[];
}
export interface NativeAccount {
  readonly address: string;
  simulate(calls: readonly NativeCall[]): Promise<unknown>;
  execute(calls: readonly NativeCall[]): Promise<unknown>;
  wait(transactionHash: string): Promise<unknown>;
}
export function nativeSelector(name: string): string;
export function createNativeAccount(
  url: string,
  address: string,
  publicTestPrivateKey: string,
): NativeAccount;
