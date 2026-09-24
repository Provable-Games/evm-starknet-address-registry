//! Immutable ASCII label validation and exact approved consent templates.
pub fn validate(label: @ByteArray) {
    let length = label.len();
    assert(length >= 1 && length <= 48, 'AR_BAD_LABEL');
    let mut previous_space = true;
    for index in 0..length {
        let byte = label.at(index).unwrap();
        let alphanumeric = (byte >= 65 && byte <= 90)
            || (byte >= 97 && byte <= 122)
            || (byte >= 48 && byte <= 57);
        assert(alphanumeric || (byte == 32 && !previous_space), 'AR_BAD_LABEL');
        previous_space = byte == 32;
    }
    assert(!previous_space, 'AR_BAD_LABEL');
}
pub fn statements(label: @ByteArray) -> (ByteArray, ByteArray, ByteArray) {
    let mut link: ByteArray = "Link my Ethereum address to this ";
    link.append(label);
    link.append(@" account. This does not approve asset transfers.");
    let mut movement: ByteArray = "Move my Ethereum address link from the previous ";
    movement.append(label);
    movement.append(@" account shown here to this account. This does not approve asset transfers.");
    let mut revoke: ByteArray = "Remove my Ethereum address link to the ";
    revoke.append(label);
    revoke
        .append(
            @" account shown here, if any, and cancel requests using the current Ethereum nonce.",
        );
    (link, movement, revoke)
}
