// Resource scenarios use test-only setup; reports isolate the named registry call.
use crate::resource_helpers::benchmark;
#[test]
#[feature("safe_dispatcher")]
fn resource_link_size0_first() {
    benchmark(0, 0, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_link_size1_first() {
    benchmark(0, 1, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_link_size2_first() {
    benchmark(0, 2, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_link_size10_first() {
    benchmark(0, 10, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_link_size100_first() {
    benchmark(0, 100, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_link_size1000_first() {
    benchmark(0, 1000, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_move_size1_first() {
    benchmark(1, 1, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_move_size2_first() {
    benchmark(1, 2, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_move_size10_first() {
    benchmark(1, 10, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_move_size100_first() {
    benchmark(1, 100, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_move_size1000_first() {
    benchmark(1, 1000, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_unlink_size1_first() {
    benchmark(2, 1, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_unlink_size2_first() {
    benchmark(2, 2, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_unlink_size10_first() {
    benchmark(2, 10, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_unlink_size100_first() {
    benchmark(2, 100, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_unlink_size1000_first() {
    benchmark(2, 1000, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_linked_size1_first() {
    benchmark(3, 1, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_linked_size2_first() {
    benchmark(3, 2, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_linked_size10_first() {
    benchmark(3, 10, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_linked_size100_first() {
    benchmark(3, 100, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_linked_size1000_first() {
    benchmark(3, 1000, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_unlinked_size0_first() {
    benchmark(4, 0, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_unlinked_size1_first() {
    benchmark(4, 1, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_unlinked_size2_first() {
    benchmark(4, 2, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_unlinked_size10_first() {
    benchmark(4, 10, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_unlinked_size100_first() {
    benchmark(4, 100, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_unlinked_size1000_first() {
    benchmark(4, 1000, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_cancel_size0_first() {
    benchmark(5, 0, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_cancel_size1_first() {
    benchmark(5, 1, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_cancel_size2_first() {
    benchmark(5, 2, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_cancel_size10_first() {
    benchmark(5, 10, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_cancel_size100_first() {
    benchmark(5, 100, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_cancel_size1000_first() {
    benchmark(5, 1000, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_page_size0_first() {
    benchmark(6, 0, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_page_size1_first() {
    benchmark(6, 1, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_page_size2_first() {
    benchmark(6, 2, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_page_size10_first() {
    benchmark(6, 10, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_page_size100_first() {
    benchmark(6, 100, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_page_size1000_first() {
    benchmark(6, 1000, 0, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_move_size10_middle() {
    benchmark(1, 10, 5, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_move_size10_last() {
    benchmark(1, 10, 9, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_unlink_size10_middle() {
    benchmark(2, 10, 5, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_unlink_size10_last() {
    benchmark(2, 10, 9, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_linked_size10_middle() {
    benchmark(3, 10, 5, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_revoke_linked_size10_last() {
    benchmark(3, 10, 9, "Loot Survivor", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_link_label1() {
    benchmark(0, 1, 0, "A", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_link_label30() {
    benchmark(0, 1, 0, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_link_label31() {
    benchmark(0, 1, 0, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_link_label32() {
    benchmark(0, 1, 0, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_link_label48() {
    benchmark(0, 1, 0, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", 100);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_page_size1000_limit0() {
    benchmark(6, 1000, 0, "Loot Survivor", 0);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_page_size1000_limit1() {
    benchmark(6, 1000, 0, "Loot Survivor", 1);
}
#[test]
#[feature("safe_dispatcher")]
fn resource_page_size1000_limit101() {
    benchmark(6, 1000, 0, "Loot Survivor", 101);
}

#[test]
#[feature("safe_dispatcher")]
fn resource_nonce_overflow() {
    benchmark(7, 1, 0, "Loot Survivor", 100);
}

#[test]
#[feature("safe_dispatcher")]
fn resource_count_overflow() {
    benchmark(8, 1, 0, "Loot Survivor", 100);
}

#[test]
#[feature("safe_dispatcher")]
fn resource_signature_rejection() {
    benchmark(9, 1, 0, "Loot Survivor", 100);
}
