use contracts::interface::{LinkRequest, MoveRequest, RevokeRequest, Signature};

#[test]
fn request_and_signature_serde_use_low_limbs_first() {
    let ethereum_address = 17.try_into().unwrap();
    let account_address = 19.try_into().unwrap();
    let previous_account_address = 23.try_into().unwrap();
    let ethereum_nonce = u256 { low: 29, high: 31 };
    let recipient_nonce = u256 { low: 37, high: 41 };
    let deadline = 18446744073709551615;
    let link = LinkRequest {
        ethereum_address, account_address, ethereum_nonce, recipient_nonce, deadline,
    };
    let movement = MoveRequest {
        ethereum_address,
        account_address,
        previous_account_address,
        ethereum_nonce,
        recipient_nonce,
        deadline,
    };
    let revocation = RevokeRequest {
        ethereum_address,
        current_account_address: previous_account_address,
        ethereum_nonce,
        deadline,
    };
    let signature = Signature {
        r: u256 { low: 43, high: 47 }, s: u256 { low: 53, high: 59 }, y_parity: true,
    };
    let mut data = array![];
    Serde::serialize(@link, ref data);
    assert(data == array![17, 19, 29, 31, 37, 41, 18446744073709551615], 'LINK_SERDE');
    let mut data = array![];
    Serde::serialize(@movement, ref data);
    assert(data == array![17, 19, 23, 29, 31, 37, 41, 18446744073709551615], 'MOVE_SERDE');
    let mut data = array![];
    Serde::serialize(@revocation, ref data);
    assert(data == array![17, 23, 29, 31, 18446744073709551615], 'REVOKE_SERDE');
    let mut data = array![];
    Serde::serialize(@signature, ref data);
    assert(data == array![43, 47, 53, 59, 1], 'SIGNATURE_SERDE');
}

#[test]
fn bytearray_boundary_has_no_magic_prefix() {
    let full: ByteArray = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    let extra: ByteArray = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    let word = 0x41414141414141414141414141414141414141414141414141414141414141;
    let mut data = array![];
    Serde::serialize(@full, ref data);
    assert(data == array![1, word, 0, 0], 'LABEL31_SERDE');
    let mut data = array![];
    Serde::serialize(@extra, ref data);
    assert(data == array![1, word, 65, 1], 'LABEL32_SERDE');
}

#[test]
fn strict_signature_serde_preserves_canonical_words_and_remainder() {
    for parity in 0..2_u32 {
        let signature = Signature {
            r: u256 { low: 11, high: 22 }, s: u256 { low: 33, high: 44 }, y_parity: parity == 1,
        };
        let mut words = array![];
        Serde::serialize(@signature, ref words);
        assert(words == array![11, 22, 33, 44, parity.into()], 'CANONICAL_SIGNATURE');
        words.append(99);
        let mut input = words.span();
        let decoded: Signature = Serde::deserialize(ref input).unwrap();
        assert(
            decoded.r == signature.r
                && decoded.s == signature.s
                && decoded.y_parity == signature.y_parity,
            'SERDE_ROUNDTRIP',
        );
        assert(input == array![99].span(), 'REMAINDER');
    }
    for length in 0..5_u32 {
        let mut words = array![];
        for _ in 0..length {
            words.append(0);
        }
        let mut input = words.span();
        assert(Serde::<Signature>::deserialize(ref input).is_none(), 'INSUFFICIENT_SIGNATURE');
    }
    for parity in array![2, 0x800000000000011000000000000000000000000000000000000000000000000]
        .span() {
        let mut input = array![1, 0, 1, 0, *parity].span();
        assert(Serde::<Signature>::deserialize(ref input).is_none(), 'NONCANONICAL_PARITY');
    };
}
