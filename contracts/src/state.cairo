//! Checked arithmetic used by membership and replay state transitions.
use core::num::traits::CheckedAdd;
pub fn next_nonce(value: u256) -> u256 {
    value.checked_add(1).expect('AR_NONCE_OVERFLOW')
}
pub fn next_count(value: u64) -> u64 {
    value.checked_add(1).expect('AR_COUNT_OVERFLOW')
}
pub fn page_length(count: u64, offset: u64, limit: u32) -> u64 {
    assert(limit >= 1 && limit <= 100, 'AR_BAD_PAGE_LIMIT');
    if offset >= count {
        return 0;
    }
    let remaining = count - offset;
    let limit: u64 = limit.into();
    if remaining < limit {
        remaining
    } else {
        limit
    }
}
