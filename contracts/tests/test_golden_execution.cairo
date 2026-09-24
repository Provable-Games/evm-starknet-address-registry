// Generated from independent protocol/vectors.json; storage seeding is test-only.
use contracts::interface::{IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait};
use snforge_std::cheatcodes::events::Event;
use snforge_std::cheatcodes::storage::{map_entry_address, store};
use snforge_std::{
    ContractClassTrait, DeclareResultTrait, EventSpyTrait, declare, spy_events,
    start_cheat_block_timestamp_global, start_cheat_caller_address, start_cheat_chain_id_global,
};
use starknet::{ContractAddress, SyscallResultTrait};
#[test]
fn execute_golden_0() {
    start_cheat_chain_id_global(23448594291968334);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(@array![1, 0, 0, 6055827926331057845544057991026, 13], registry)
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![0, 0].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![0, 0].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        118392661602862932221173705796653290549413119731538510511556647074259381935,
        array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 0, 0, 0, 0,
            2000000000, 276874716590149336249291301223372706150,
            94198483320217079003194908363339723609, 121115603520546289496506904200279970449,
            69788707696642659981615319586221553619, 0,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'GOLD_MAPPING',
    );
    assert(reader.get_ethereum_nonce(ethereum) == 1, 'GOLD_NONCE');
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 1,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            0,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            1,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![1, 0],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![1, 0],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_1() {
    start_cheat_chain_id_global(23448594291968334);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(@array![1, 0, 0, 6055827926331057845544057991026, 13], registry)
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![0, 0].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_to_starknet"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![226156424291633194186662080095093570025917938800079226639565781489028034303].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_count"),
            array![226156424291633194186662080095093570025917938800079226639565781489028034303]
                .span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_addresses"),
            array![226156424291633194186662080095093570025917938800079226639565781489028034303, 0]
                .span(),
        ),
        array![721457446580647751014191829380889690493307935711].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_index_plus_one"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                226156424291633194186662080095093570025917938800079226639565781489028034303,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![0, 0].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![0, 0].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        1006914996534709224607738575252571802087119588540572262759330458818632830651,
        array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121,
            226156424291633194186662080095093570025917938800079226639565781489028034303, 0, 0, 0, 0,
            2000000000, 270334482191384323981611876273264539309,
            199569434305247174000543659522006997699, 295560279056450577682467977437764686494,
            103821034360859076519428720853809592607, 1,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'GOLD_MAPPING',
    );
    assert(reader.get_ethereum_nonce(ethereum) == 1, 'GOLD_NONCE');
    assert(
        reader
            .get_recipient_nonce(
                226156424291633194186662080095093570025917938800079226639565781489028034303
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 1,
        'GOLD_PAIR',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 1,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            226156424291633194186662080095093570025917938800079226639565781489028034303,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            2,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![1, 0],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            226156424291633194186662080095093570025917938800079226639565781489028034303,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![1, 0],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![1, 0],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_2() {
    start_cheat_chain_id_global(23448594291968334);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(@array![1, 0, 0, 6055827926331057845544057991026, 13], registry)
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![0, 0].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_to_starknet"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![226156424291633194186662080095093570025917938800079226639565781489028034303].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_count"),
            array![226156424291633194186662080095093570025917938800079226639565781489028034303]
                .span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_addresses"),
            array![226156424291633194186662080095093570025917938800079226639565781489028034303, 0]
                .span(),
        ),
        array![721457446580647751014191829380889690493307935711].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_index_plus_one"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                226156424291633194186662080095093570025917938800079226639565781489028034303,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![0, 0].span(),
    );
    start_cheat_caller_address(registry, 2457.try_into().unwrap());
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        934512645634985500479763787408240173630153827023378265377072214039549757247,
        array![
            721457446580647751014191829380889690493307935711,
            226156424291633194186662080095093570025917938800079226639565781489028034303, 0, 0,
            2000000000, 171620415995980845199331678379576761178,
            181181586486959214830069773954525279721, 41860035880016236160160949108053984038,
            158274952591883054089757475755207257156, 0,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(reader.get_starknet_address(ethereum) == 0.try_into().unwrap(), 'GOLD_MAPPING');
    assert(reader.get_ethereum_nonce(ethereum) == 1, 'GOLD_NONCE');
    assert(
        reader
            .get_recipient_nonce(
                226156424291633194186662080095093570025917938800079226639565781489028034303
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 1,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            226156424291633194186662080095093570025917938800079226639565781489028034303,
                            0, 4,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![1, 0],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            226156424291633194186662080095093570025917938800079226639565781489028034303,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![1, 0],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_3() {
    start_cheat_chain_id_global(23448594291968334);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(@array![1, 0, 0, 6055827926331057845544057991026, 13], registry)
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![0, 0].span(),
    );
    start_cheat_caller_address(registry, 2457.try_into().unwrap());
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        934512645634985500479763787408240173630153827023378265377072214039549757247,
        array![
            721457446580647751014191829380889690493307935711, 0, 0, 0, 2000000000,
            131044356555442890308756980402717748657, 210342756932625143716137989060218674283,
            127228870402610913059818634657301193, 29003271107234186579974808122380747102, 1,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(reader.get_starknet_address(ethereum) == 0.try_into().unwrap(), 'GOLD_MAPPING');
    assert(reader.get_ethereum_nonce(ethereum) == 1, 'GOLD_NONCE');
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![1, 0],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_4() {
    start_cheat_chain_id_global(393402133025997798000961);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(@array![11155111, 0, 0, 6055827926331057845544057991026, 13], registry)
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        118392661602862932221173705796653290549413119731538510511556647074259381935,
        array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            57949805205350981570844082709525235839, 95842270187528311981425868698979306821,
            83620641768188133376992410112653163017, 82191588066282803756463242812361162070, 0,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'GOLD_MAPPING',
    );
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'GOLD_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            0,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            1,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_5() {
    start_cheat_chain_id_global(393402133025997798000961);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(@array![11155111, 0, 0, 6055827926331057845544057991026, 13], registry)
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_to_starknet"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![226156424291633194186662080095093570025917938800079226639565781489028034303].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_count"),
            array![226156424291633194186662080095093570025917938800079226639565781489028034303]
                .span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_addresses"),
            array![226156424291633194186662080095093570025917938800079226639565781489028034303, 0]
                .span(),
        ),
        array![721457446580647751014191829380889690493307935711].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_index_plus_one"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                226156424291633194186662080095093570025917938800079226639565781489028034303,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![23, 4503599627370496].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        1006914996534709224607738575252571802087119588540572262759330458818632830651,
        array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121,
            226156424291633194186662080095093570025917938800079226639565781489028034303, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            206453149567685665070912392713735013281, 219393732946582001920856112639874458951,
            86226967274066690867104330345236989702, 62121595381060441930281641916165708156, 1,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'GOLD_MAPPING',
    );
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'GOLD_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                226156424291633194186662080095093570025917938800079226639565781489028034303
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 1532495540865888858358347027150309183618739122183602200,
        'GOLD_PAIR',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            226156424291633194186662080095093570025917938800079226639565781489028034303,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            2,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            226156424291633194186662080095093570025917938800079226639565781489028034303,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![24, 4503599627370496],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_6() {
    start_cheat_chain_id_global(393402133025997798000961);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(@array![11155111, 0, 0, 6055827926331057845544057991026, 13], registry)
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_to_starknet"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![226156424291633194186662080095093570025917938800079226639565781489028034303].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_count"),
            array![226156424291633194186662080095093570025917938800079226639565781489028034303]
                .span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_addresses"),
            array![226156424291633194186662080095093570025917938800079226639565781489028034303, 0]
                .span(),
        ),
        array![721457446580647751014191829380889690493307935711].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_index_plus_one"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                226156424291633194186662080095093570025917938800079226639565781489028034303,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![23, 4503599627370496].span(),
    );
    start_cheat_caller_address(registry, 2457.try_into().unwrap());
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        934512645634985500479763787408240173630153827023378265377072214039549757247,
        array![
            721457446580647751014191829380889690493307935711,
            226156424291633194186662080095093570025917938800079226639565781489028034303, 17,
            4722366482869645213696, 18446744073709551615, 331989821528211312880792194059352489151,
            175768904391022779114326833548475951267, 172969729350252697928127338761766902204,
            10631114116541750298101663290031372175, 1,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(reader.get_starknet_address(ethereum) == 0.try_into().unwrap(), 'GOLD_MAPPING');
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'GOLD_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                226156424291633194186662080095093570025917938800079226639565781489028034303
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 1532495540865888858358347027150309183618739122183602200,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            226156424291633194186662080095093570025917938800079226639565781489028034303,
                            0, 4,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            226156424291633194186662080095093570025917938800079226639565781489028034303,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![24, 4503599627370496],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_7() {
    start_cheat_chain_id_global(393402133025997798000961);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(@array![11155111, 0, 0, 6055827926331057845544057991026, 13], registry)
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    start_cheat_caller_address(registry, 2457.try_into().unwrap());
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        934512645634985500479763787408240173630153827023378265377072214039549757247,
        array![
            721457446580647751014191829380889690493307935711, 0, 17, 4722366482869645213696,
            18446744073709551615, 189357533268767833164014521802089889347,
            250244412838690331489517090284589317823, 77485289009544446224523572079656730908,
            135444013685062543361827230171340535670, 1,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(reader.get_starknet_address(ethereum) == 0.try_into().unwrap(), 'GOLD_MAPPING');
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'GOLD_NONCE',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_8() {
    start_cheat_chain_id_global(23448594291968334);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class.deploy_at(@array![1, 0, 0, 65, 1], registry).unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        118392661602862932221173705796653290549413119731538510511556647074259381935,
        array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            22238125522029383857099693537162198234, 283794859728674924657236903085389198338,
            51735949323130985307287807189504288983, 115382800369504341635703830304020505972, 0,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'GOLD_MAPPING',
    );
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'GOLD_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            0,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            1,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_9() {
    start_cheat_chain_id_global(393402133025997798000961);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(
            @array![
                11155111, 0, 0,
                450372781218019534991820931561920405995240993321236205011389816015765825, 30,
            ],
            registry,
        )
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        118392661602862932221173705796653290549413119731538510511556647074259381935,
        array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            88871462520611323208391762045432567413, 197043122119403086171853798735686625271,
            106814648724064008957165035559018805056, 89971459439317173418892410330585722195, 1,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'GOLD_MAPPING',
    );
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'GOLD_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            0,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            1,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_10() {
    start_cheat_chain_id_global(23448594291968334);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(
            @array![
                1, 0, 1,
                115295431991813000957906158479851623934781694290236468482915792900036051265, 0, 0,
            ],
            registry,
        )
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        118392661602862932221173705796653290549413119731538510511556647074259381935,
        array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            192386296451564579883986923854275433229, 65031520483123556785023737834632843808,
            174290547607613065733276908690444580900, 81456843653181943624412583030459140476, 0,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'GOLD_MAPPING',
    );
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'GOLD_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            0,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            1,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_11() {
    start_cheat_chain_id_global(393402133025997798000961);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(
            @array![
                11155111, 0, 1,
                115295431991813000957906158479851623934781694290236468482915792900036051265, 65, 1,
            ],
            registry,
        )
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        118392661602862932221173705796653290549413119731538510511556647074259381935,
        array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            218042738385383184764626980492766141686, 171208982116704763137202312061041093654,
            266595509146695031557769392689500743336, 50493972789133085489927708306921324117, 0,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'GOLD_MAPPING',
    );
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'GOLD_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            0,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            1,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn execute_golden_12() {
    start_cheat_chain_id_global(23448594291968334);
    start_cheat_block_timestamp_global(100);
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(
            @array![
                1, 0, 1,
                115295431991813000957906158479851623934781694290236468482915792900036051265,
                22205092492409474635413935167312247210305, 17,
            ],
            registry,
        )
        .unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        118392661602862932221173705796653290549413119731538510511556647074259381935,
        array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            117541539112154026267015082154642574609, 53590031021417581639623396819204770215,
            123376430487120131999811403443063467876, 93423816245519567453082202972668791335, 1,
        ]
            .span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'GOLD_MAPPING',
    );
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'GOLD_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'GOLD_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            0,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            1,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'GOLD_EVENTS',
    );
}
#[test]
fn unsigned_golden_0() {
    start_cheat_chain_id_global('SN_MAIN');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class.deploy_at(@array![1, 0, 0, 65, 1], registry).unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_to_starknet"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![452312848583266388373324160190187140051835877600158453595190225338656852121].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_count"),
            array![452312848583266388373324160190187140051835877600158453595190225338656852121]
                .span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_addresses"),
            array![452312848583266388373324160190187140051835877600158453595190225338656852121, 0]
                .span(),
        ),
        array![721457446580647751014191829380889690493307935711].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_index_plus_one"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        924721843728457642046450709855086375553246761384863197579636433244766369444,
        array![721457446580647751014191829380889690493307935711].span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(reader.get_starknet_address(ethereum) == 0.try_into().unwrap(), 'UNSIGNED_MAPPING');
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'UNSIGNED_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'UNSIGNED_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            0, 3,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'UNSIGNED_EVENTS',
    );
}
#[test]
fn unsigned_golden_1() {
    start_cheat_chain_id_global('SN_MAIN');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class.deploy_at(@array![1, 0, 0, 65, 1], registry).unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_to_starknet"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![452312848583266388373324160190187140051835877600158453595190225338656852121].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_count"),
            array![452312848583266388373324160190187140051835877600158453595190225338656852121]
                .span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_addresses"),
            array![452312848583266388373324160190187140051835877600158453595190225338656852121, 0]
                .span(),
        ),
        array![721457446580647751014191829380889690493307935711].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_index_plus_one"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        33530722123114163495537150410121452060380698766397091934058216439154184856,
        array![721457446580647751014191829380889690493307935711].span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'UNSIGNED_MAPPING',
    );
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301393,
        'UNSIGNED_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'UNSIGNED_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'UNSIGNED_EVENTS',
    );
}
#[test]
fn unsigned_golden_2() {
    start_cheat_chain_id_global('SN_SEPOLIA');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class.deploy_at(@array![11155111, 0, 0, 65, 1], registry).unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_to_starknet"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![452312848583266388373324160190187140051835877600158453595190225338656852121].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_count"),
            array![452312848583266388373324160190187140051835877600158453595190225338656852121]
                .span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_addresses"),
            array![452312848583266388373324160190187140051835877600158453595190225338656852121, 0]
                .span(),
        ),
        array![721457446580647751014191829380889690493307935711].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_index_plus_one"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        924721843728457642046450709855086375553246761384863197579636433244766369444,
        array![721457446580647751014191829380889690493307935711].span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(reader.get_starknet_address(ethereum) == 0.try_into().unwrap(), 'UNSIGNED_MAPPING');
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301394,
        'UNSIGNED_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'UNSIGNED_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            1213293078385536787199108047425788666059335243598577587069513353622615676613,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            0, 3,
                        ],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            988009767576052647314861782225598850481172693862110282949715272835855761435,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![18, 4722366482869645213696],
                    },
                ),
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'UNSIGNED_EVENTS',
    );
}
#[test]
fn unsigned_golden_3() {
    start_cheat_chain_id_global('SN_SEPOLIA');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class.deploy_at(@array![11155111, 0, 0, 65, 1], registry).unwrap_syscall();
    store(
        registry,
        map_entry_address(
            selector!("ethereum_to_starknet"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![452312848583266388373324160190187140051835877600158453595190225338656852121].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_count"),
            array![452312848583266388373324160190187140051835877600158453595190225338656852121]
                .span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_addresses"),
            array![452312848583266388373324160190187140051835877600158453595190225338656852121, 0]
                .span(),
        ),
        array![721457446580647751014191829380889690493307935711].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_index_plus_one"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![1].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("ethereum_nonce"),
            array![721457446580647751014191829380889690493307935711].span(),
        ),
        array![17, 4722366482869645213696].span(),
    );
    store(
        registry,
        map_entry_address(
            selector!("recipient_nonce"),
            array![
                452312848583266388373324160190187140051835877600158453595190225338656852121,
                721457446580647751014191829380889690493307935711,
            ]
                .span(),
        ),
        array![19, 18446744073709551616].span(),
    );
    start_cheat_caller_address(
        registry,
        452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
    );
    let mut spy = spy_events();
    starknet::syscalls::call_contract_syscall(
        registry,
        33530722123114163495537150410121452060380698766397091934058216439154184856,
        array![721457446580647751014191829380889690493307935711].span(),
    )
        .unwrap_syscall();
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = 721457446580647751014191829380889690493307935711.try_into().unwrap();
    assert(
        reader
            .get_starknet_address(
                ethereum,
            ) == 452312848583266388373324160190187140051835877600158453595190225338656852121
            .try_into()
            .unwrap(),
        'UNSIGNED_MAPPING',
    );
    assert(
        reader
            .get_ethereum_nonce(
                ethereum,
            ) == 1606938044258990275541962092341162602522202993782792835301393,
        'UNSIGNED_NONCE',
    );
    assert(
        reader
            .get_recipient_nonce(
                452312848583266388373324160190187140051835877600158453595190225338656852121
                    .try_into()
                    .unwrap(),
                ethereum,
            ) == 6277101735386680763835789423207666416102355444464034512916,
        'UNSIGNED_PAIR',
    );
    assert(
        spy
            .get_events()
            .events == array![
                (
                    registry,
                    Event {
                        keys: array![
                            858446140938378784240430741772175703523500764517914556554214632816048963719,
                            452312848583266388373324160190187140051835877600158453595190225338656852121,
                            721457446580647751014191829380889690493307935711,
                        ],
                        data: array![20, 18446744073709551616],
                    },
                ),
            ],
        'UNSIGNED_EVENTS',
    );
}
#[test]
fn discovery_golden_0() {
    start_cheat_chain_id_global('SN_MAIN');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(@array![1, 0, 0, 6055827926331057845544057991026, 13], registry)
        .unwrap_syscall();
    let domain = IAddressRegistryDispatcher { contract_address: registry }.get_signing_domain();
    let mut encoded = array![];
    Serde::serialize(@domain, ref encoded);
    assert(
        encoded == array![
            0, 26899160088882821328536115052092457108599598059662819187271233390, 27, 0, 49, 1, 1,
            0, 23448594291968334,
            904625697166532776746648320380374280103671755200316906558344360591037812207,
            125093535240129887569074911296881531153, 110404133716933170115531505989749725049,
            189658599041125578823373522385658837362, 79376061231093848512690094662291888346, 0,
            6055827926331057845544057991026, 13, 3,
            135008037165458766378001666807806573839467519875076415417503967996695308393,
            203410329024071933794205563286168399140766312979814401125598797961559744612,
            196820204380717037630701052555755366871803310613440632180782461850764014195, 46, 1, 4,
            136816509756017481284084809992335684563032505609569864616241721825792041062,
            202189601281297007468069936750192201026055647257160631157764373391728407072,
            172070118944528469333729966975542798913126118724425072133427922700932965231,
            207483430888696409464197723707140009909579565458068332684446877248226816869,
            35939496669965209140141912878, 12, 4,
            145581486065409345332921711139246115939185236789099912180908054683071377003,
            57342704621096779559007082004376720052978685782135983548113409656956919923,
            184521408412782992131904411869721959581385140860916044354363817536558735474,
            179234615877601049643730564832244762072901989287121702415990998815950267762,
            479125147232832445441326, 10, 0, 110930206544728495286297369759959639412, 16,
        ],
        'DISCOVERY_WORDS',
    );
}
#[test]
fn discovery_golden_1() {
    start_cheat_chain_id_global('SN_SEPOLIA');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(@array![11155111, 0, 0, 6055827926331057845544057991026, 13], registry)
        .unwrap_syscall();
    let domain = IAddressRegistryDispatcher { contract_address: registry }.get_signing_domain();
    let mut encoded = array![];
    Serde::serialize(@domain, ref encoded);
    assert(
        encoded == array![
            0, 26899160088882821328536115052092457108599598059662819187271233390, 27, 0, 49, 1,
            11155111, 0, 393402133025997798000961,
            904625697166532776746648320380374280103671755200316906558344360591037812207,
            132014068120151897747629557600868702335, 313282833508112223449706128452439770975,
            232661571609975967100743626658410948519, 71632310414091801678371079925280028048, 0,
            6055827926331057845544057991026, 13, 3,
            135008037165458766378001666807806573839467519875076415417503967996695308393,
            203410329024071933794205563286168399140766312979814401125598797961559744612,
            196820204380717037630701052555755366871803310613440632180782461850764014195, 46, 1, 4,
            136816509756017481284084809992335684563032505609569864616241721825792041062,
            202189601281297007468069936750192201026055647257160631157764373391728407072,
            172070118944528469333729966975542798913126118724425072133427922700932965231,
            207483430888696409464197723707140009909579565458068332684446877248226816869,
            35939496669965209140141912878, 12, 4,
            145581486065409345332921711139246115939185236789099912180908054683071377003,
            57342704621096779559007082004376720052978685782135983548113409656956919923,
            184521408412782992131904411869721959581385140860916044354363817536558735474,
            179234615877601049643730564832244762072901989287121702415990998815950267762,
            479125147232832445441326, 10, 0, 110930206544728495286299063037947832673, 16,
        ],
        'DISCOVERY_WORDS',
    );
}
#[test]
fn discovery_golden_2() {
    start_cheat_chain_id_global('SN_MAIN');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class.deploy_at(@array![1, 0, 0, 65, 1], registry).unwrap_syscall();
    let domain = IAddressRegistryDispatcher { contract_address: registry }.get_signing_domain();
    let mut encoded = array![];
    Serde::serialize(@domain, ref encoded);
    assert(
        encoded == array![
            0, 26899160088882821328536115052092457108599598059662819187271233390, 27, 0, 49, 1, 1,
            0, 23448594291968334,
            904625697166532776746648320380374280103671755200316906558344360591037812207,
            125093535240129887569074911296881531153, 110404133716933170115531505989749725049,
            189658599041125578823373522385658837362, 79376061231093848512690094662291888346, 0, 65,
            1, 2, 135008037165458766378001666807806573839467519875076415417503967996695308393,
            203410024139201390676146222207350458553282723280727018452843797566249267314,
            636338272854322220220479000435297892774135886638, 20, 4,
            136816509756017481284084809992335684563032505609569864616241721825792041062,
            202189601281297007468069936750192201026055417887277127401136818341458505591,
            194576847526773800834510756135170967819569516798314740149807935969602593903,
            179246128720992524020487673162601373427865103423213524296748417864504079150, 0, 0, 3,
            145581486065409345332921711139246115939185236789099912180908054683071377003,
            57342704621096779557923913354338864612572307720139288492562282260254695529,
            180441883239518718201220735500556580933494572103387008218763756193931553134,
            2780292387438410085984545596185389688551014481356672865462979181897006, 29, 0,
            110930206544728495286297369759959639412, 16,
        ],
        'DISCOVERY_WORDS',
    );
}
#[test]
fn discovery_golden_3() {
    start_cheat_chain_id_global('SN_SEPOLIA');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(
            @array![
                11155111, 0, 0,
                450372781218019534991820931561920405995240993321236205011389816015765825, 30,
            ],
            registry,
        )
        .unwrap_syscall();
    let domain = IAddressRegistryDispatcher { contract_address: registry }.get_signing_domain();
    let mut encoded = array![];
    Serde::serialize(@domain, ref encoded);
    assert(
        encoded == array![
            0, 26899160088882821328536115052092457108599598059662819187271233390, 27, 0, 49, 1,
            11155111, 0, 393402133025997798000961,
            904625697166532776746648320380374280103671755200316906558344360591037812207,
            132014068120151897747629557600868702335, 313282833508112223449706128452439770975,
            232661571609975967100743626658410948519, 71632310414091801678371079925280028048, 0,
            450372781218019534991820931561920405995240993321236205011389816015765825, 30, 3,
            135008037165458766378001666807806573839467519875076415417503967996695308393,
            203410027601288128832085686573542407886225002537935793632675739665281663297,
            115068540675341213309169455724260140229568293855946283016758390712932921206,
            8809359449419499898815243549545562490696494, 18, 4,
            136816509756017481284084809992335684563032505609569864616241721825792041062,
            202189601281297007468069936750192201026055420491861705166939657180574466369,
            115295431991813000957906158479851623934611000235348008828069632596430515744,
            184452255201790469742189992808694681950791590687695612546452832442192455027,
            874348494791897019628663404745402257352306976415072622501248212562734, 29, 4,
            145581486065409345332921711139246115939185236789099912180908054683071377003,
            57342704621096779557936213157250705026855982456683000165116952737174602049,
            115295431991813000151826274849478233439874160161548295940031417477042365984,
            172146624182258403015277752223498542303093389028368095295759117369901737760,
            47887388500357159509665336490275332183962782176328349169374946606, 27, 0,
            110930206544728495286299063037947832673, 16,
        ],
        'DISCOVERY_WORDS',
    );
}
#[test]
fn discovery_golden_4() {
    start_cheat_chain_id_global('SN_MAIN');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(
            @array![
                1, 0, 1,
                115295431991813000957906158479851623934781694290236468482915792900036051265, 0, 0,
            ],
            registry,
        )
        .unwrap_syscall();
    let domain = IAddressRegistryDispatcher { contract_address: registry }.get_signing_domain();
    let mut encoded = array![];
    Serde::serialize(@domain, ref encoded);
    assert(
        encoded == array![
            0, 26899160088882821328536115052092457108599598059662819187271233390, 27, 0, 49, 1, 1,
            0, 23448594291968334,
            904625697166532776746648320380374280103671755200316906558344360591037812207,
            125093535240129887569074911296881531153, 110404133716933170115531505989749725049,
            189658599041125578823373522385658837362, 79376061231093848512690094662291888346, 1,
            115295431991813000957906158479851623934781694290236468482915792900036051265, 0, 0, 3,
            135008037165458766378001666807806573839467519875076415417503967996695308393,
            203410027601288128832085686573542407886225002537935793632675739665281663297,
            115294545697608033037403280734712594701558204444790022445938615547742679663,
            2640297292876033030600029999722052220196385582, 19, 4,
            136816509756017481284084809992335684563032505609569864616241721825792041062,
            202189601281297007468069936750192201026055420491861705166939657180574466369,
            115295431991813000957906158479851623934781027516584560437389050086350092142,
            57259622694790292569095949683182356107849764351143617646400979818091147109,
            794575178375706732574625587566603329289229838776009526466191533949481774, 30, 4,
            145581486065409345332921711139246115939185236789099912180908054683071377003,
            57342704621096779557936213157250705026855982456683000165116952737174602049,
            115295431991813000954757408934420477878160961735046280308920150808539982182,
            57211553823620245433443948743396433687350943250911869532140457493590011495,
            3417880721894187133843042222367729166388605834993899909307326227758, 28, 0,
            110930206544728495286297369759959639412, 16,
        ],
        'DISCOVERY_WORDS',
    );
}
#[test]
fn discovery_golden_5() {
    start_cheat_chain_id_global('SN_SEPOLIA');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(
            @array![
                11155111, 0, 1,
                115295431991813000957906158479851623934781694290236468482915792900036051265, 65, 1,
            ],
            registry,
        )
        .unwrap_syscall();
    let domain = IAddressRegistryDispatcher { contract_address: registry }.get_signing_domain();
    let mut encoded = array![];
    Serde::serialize(@domain, ref encoded);
    assert(
        encoded == array![
            0, 26899160088882821328536115052092457108599598059662819187271233390, 27, 0, 49, 1,
            11155111, 0, 393402133025997798000961,
            904625697166532776746648320380374280103671755200316906558344360591037812207,
            132014068120151897747629557600868702335, 313282833508112223449706128452439770975,
            232661571609975967100743626658410948519, 71632310414091801678371079925280028048, 1,
            115295431991813000957906158479851623934781694290236468482915792900036051265, 65, 1, 3,
            135008037165458766378001666807806573839467519875076415417503967996695308393,
            203410027601288128832085686573542407886225002537935793632675739665281663297,
            115295428529726262801966694113659674601839415033027693303083850801003655282,
            636338272854322220220479000435297892774135886638, 20, 5,
            136816509756017481284084809992335684563032505609569864616241721825792041062,
            202189601281297007468069936750192201026055420491861705166939657180574466369,
            115295431991813000957906158479851623934781691685651890717112954060920090487,
            194576847526773800834510756135170967819569516798314740149807935969602593903,
            179246128720992524020487673162601373427865103423213524296748417864504079150, 0, 0, 4,
            145581486065409345332921711139246115939185236789099912180908054683071377003,
            57342704621096779557936213157250705026855982456683000165116952737174602049,
            115295431991813000957893858676939783520498019553692756810361122423116144745,
            180441883239518718201220735500556580933494572103387008218763756193931553134,
            2780292387438410085984545596185389688551014481356672865462979181897006, 29, 0,
            110930206544728495286299063037947832673, 16,
        ],
        'DISCOVERY_WORDS',
    );
}
#[test]
fn discovery_golden_6() {
    start_cheat_chain_id_global('SN_MAIN');
    let registry: ContractAddress =
        904625697166532776746648320380374280103671755200316906558344360591037812207
        .try_into()
        .unwrap();
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    class
        .deploy_at(
            @array![
                1, 0, 1,
                115295431991813000957906158479851623934781694290236468482915792900036051265,
                22205092492409474635413935167312247210305, 17,
            ],
            registry,
        )
        .unwrap_syscall();
    let domain = IAddressRegistryDispatcher { contract_address: registry }.get_signing_domain();
    let mut encoded = array![];
    Serde::serialize(@domain, ref encoded);
    assert(
        encoded == array![
            0, 26899160088882821328536115052092457108599598059662819187271233390, 27, 0, 49, 1, 1,
            0, 23448594291968334,
            904625697166532776746648320380374280103671755200316906558344360591037812207,
            125093535240129887569074911296881531153, 110404133716933170115531505989749725049,
            189658599041125578823373522385658837362, 79376061231093848512690094662291888346, 1,
            115295431991813000957906158479851623934781694290236468482915792900036051265,
            22205092492409474635413935167312247210305, 17, 4,
            135008037165458766378001666807806573839467519875076415417503967996695308393,
            203410027601288128832085686573542407886225002537935793632675739665281663297,
            115295431991813000957906158479851623934781694280062309976018125561050190952,
            186313515926959559988041852310736907680349104367996549663621824628616425075,
            439788663598, 5, 5,
            136816509756017481284084809992335684563032505609569864616241721825792041062,
            202189601281297007468069936750192201026055420491861705166939657180574466369,
            115295431991813000957906158479851623934781694290236468482915792900036051265,
            115295428529726262801966694035586510308062137836542918316465269463776326432,
            172070118944528469669051654312551140779954793453870716602735247429356381472,
            129534570244956675401712351947032523566, 16, 5,
            145581486065409345332921711139246115939185236789099912180908054683071377003,
            57342704621096779557936213157250705026855982456683000165116952737174602049,
            115295431991813000957906158479851623934781694290236468482915756754163953525,
            195154654574019110646721874688461396858052877779553511204382244339567390307,
            179197816913696108192784647572364600244727757381630685881636263090671853637,
            2361030639207737799440109284844846, 14, 0, 110930206544728495286297369759959639412, 16,
        ],
        'DISCOVERY_WORDS',
    );
}
