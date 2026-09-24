// Generated inputs from frozen independent protocol/vectors.json; expected hashes are not
// recomputed.
use contracts::interface::{LinkRequest, MoveRequest, RevokeRequest, Signature};
use contracts::{eip712, labels, signature};
#[test]
fn golden_0_link() {
    let label: ByteArray = "Loot Survivor";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = link;
    let _ = (movement, revoke);
    assert(
        statement == "Link my Ethereum address to this Loot Survivor account. This does not approve asset transfers.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0x65b742837ea6b93cdfbbd3a0baacd502349a33587ede448f85492607c4671c17,
        'STATEMENT_HASH',
    );
    let request = LinkRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        account_address: 0x0100000000000000000000000000000000000000000000112233445566778899
            .try_into()
            .unwrap(),
        ethereum_nonce: 0,
        recipient_nonce: 0,
        deadline: 2000000000,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(23448594291968334, registry);
    assert(salt == 0x530f100dd34727e18578e9bba03257795e1c2377263264f0767ec02842ed9911, 'SALT');
    let domain = eip712::domain(1, salt);
    assert(domain == 0x3bb745f8400ed774c08562eab64d18da8eaeeae1f5e352d15bbc7059c595f972, 'DOMAIN');
    let message = eip712::link_hash(
        @request, eip712::hash_text(@statement), 23448594291968334, registry,
    );
    assert(message == 0x002d874491dae622012e22b9fd76085ce966f1a7659c0e8111405a00d989e855, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0x7133ca9a9ed34917e3621d564065d1a4adabe31069574899a393710b636af645, 'DIGEST');
    let sig = Signature {
        r: 32054082864566009766317123769755874612124753352045096831863296625798680170854,
        s: 23747866639367079828318254026448245233199580379531701289182785824233514029713,
        y_parity: false,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 0, 0, 0, 0,
            2000000000, 276874716590149336249291301223372706150,
            94198483320217079003194908363339723609, 121115603520546289496506904200279970449,
            69788707696642659981615319586221553619, 0,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_1_move() {
    let label: ByteArray = "Loot Survivor";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = movement;
    let _ = (link, revoke);
    assert(
        statement == "Move my Ethereum address link from the previous Loot Survivor account shown here to this account. This does not approve asset transfers.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0x820b33d4250d4062535281cb2445e2662841428b0b7a188ca840630202c13edb,
        'STATEMENT_HASH',
    );
    let request = MoveRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        account_address: 0x0100000000000000000000000000000000000000000000112233445566778899
            .try_into()
            .unwrap(),
        previous_account_address: 0x0080000000000000000000000000000000000000000000000000aabbccddeeff
            .try_into()
            .unwrap(),
        ethereum_nonce: 0,
        recipient_nonce: 0,
        deadline: 2000000000,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(23448594291968334, registry);
    assert(salt == 0x530f100dd34727e18578e9bba03257795e1c2377263264f0767ec02842ed9911, 'SALT');
    let domain = eip712::domain(1, salt);
    assert(domain == 0x3bb745f8400ed774c08562eab64d18da8eaeeae1f5e352d15bbc7059c595f972, 'DOMAIN');
    let message = eip712::move_hash(
        @request, eip712::hash_text(@statement), 23448594291968334, registry,
    );
    assert(message == 0xcbc85635ff4721b2ddda2c3bbf733a336c5275751e63a7f6039b9973e41e6842, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0xbf0988e6621d26ea5736def7ebd46f8292b93d8a34f412ba42d5ba14ec9dbc0d, 'DIGEST');
    let sig = Signature {
        r: 67909959470462242767047895284175174212059847743917941614463626437286801979053,
        s: 35328467308493208210074026430013137189338337301807502483708455470338154992286,
        y_parity: true,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121,
            226156424291633194186662080095093570025917938800079226639565781489028034303, 0, 0, 0, 0,
            2000000000, 270334482191384323981611876273264539309,
            199569434305247174000543659522006997699, 295560279056450577682467977437764686494,
            103821034360859076519428720853809592607, 1,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_2_revoke() {
    let label: ByteArray = "Loot Survivor";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = revoke;
    let _ = (link, movement);
    assert(
        statement == "Remove my Ethereum address link to the Loot Survivor account shown here, if any, and cancel requests using the current Ethereum nonce.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0xa4f7f5839724ac58c9708a7be5ceba3be9b671e3c8f147071a897a7f294b12ac,
        'STATEMENT_HASH',
    );
    let request = RevokeRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        current_account_address: 0x0080000000000000000000000000000000000000000000000000aabbccddeeff
            .try_into()
            .unwrap(),
        ethereum_nonce: 0,
        deadline: 2000000000,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(23448594291968334, registry);
    assert(salt == 0x530f100dd34727e18578e9bba03257795e1c2377263264f0767ec02842ed9911, 'SALT');
    let domain = eip712::domain(1, salt);
    assert(domain == 0x3bb745f8400ed774c08562eab64d18da8eaeeae1f5e352d15bbc7059c595f972, 'DOMAIN');
    let message = eip712::revoke_hash(
        @request, eip712::hash_text(@statement), 23448594291968334, registry,
    );
    assert(message == 0x3456b8c3f7267c467427b0fcb316f140e27e290c587053969aa389349879407d, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0x326ad734f5b0a8e844fd33545013bb64a5f549bf994b78ab9954b0461484807c, 'DIGEST');
    let sig = Signature {
        r: 61652899092273201635035165987881988742030375046853074298514368628053853444954,
        s: 53858175492265289685675890348882210827897957604403089848000718941945631163174,
        y_parity: false,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            226156424291633194186662080095093570025917938800079226639565781489028034303, 0, 0,
            2000000000, 171620415995980845199331678379576761178,
            181181586486959214830069773954525279721, 41860035880016236160160949108053984038,
            158274952591883054089757475755207257156, 0,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_3_revoke() {
    let label: ByteArray = "Loot Survivor";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = revoke;
    let _ = (link, movement);
    assert(
        statement == "Remove my Ethereum address link to the Loot Survivor account shown here, if any, and cancel requests using the current Ethereum nonce.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0xa4f7f5839724ac58c9708a7be5ceba3be9b671e3c8f147071a897a7f294b12ac,
        'STATEMENT_HASH',
    );
    let request = RevokeRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        current_account_address: 0x0000000000000000000000000000000000000000000000000000000000000000
            .try_into()
            .unwrap(),
        ethereum_nonce: 0,
        deadline: 2000000000,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(23448594291968334, registry);
    assert(salt == 0x530f100dd34727e18578e9bba03257795e1c2377263264f0767ec02842ed9911, 'SALT');
    let domain = eip712::domain(1, salt);
    assert(domain == 0x3bb745f8400ed774c08562eab64d18da8eaeeae1f5e352d15bbc7059c595f972, 'DOMAIN');
    let message = eip712::revoke_hash(
        @request, eip712::hash_text(@statement), 23448594291968334, registry,
    );
    assert(message == 0x374718cb5e1735b35020646fbf31d52c5f53bbbfe00de47ba67e53b2dfe1a094, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0x61b424d9fad6ff70b28dfb80f25e4acdd127b3c27e94b72d51d36e39099d38ef, 'DIGEST');
    let sig = Signature {
        r: 71575931193709321864999354128758572304869901508400074349482000036825050934705,
        s: 9869301740819316654427215261848751103466058003961293838205815473514252501705,
        y_parity: true,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711, 0, 0, 0, 2000000000,
            131044356555442890308756980402717748657, 210342756932625143716137989060218674283,
            127228870402610913059818634657301193, 29003271107234186579974808122380747102, 1,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_4_link() {
    let label: ByteArray = "Loot Survivor";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = link;
    let _ = (movement, revoke);
    assert(
        statement == "Link my Ethereum address to this Loot Survivor account. This does not approve asset transfers.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0x65b742837ea6b93cdfbbd3a0baacd502349a33587ede448f85492607c4671c17,
        'STATEMENT_HASH',
    );
    let request = LinkRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        account_address: 0x0100000000000000000000000000000000000000000000112233445566778899
            .try_into()
            .unwrap(),
        ethereum_nonce: 1606938044258990275541962092341162602522202993782792835301393,
        recipient_nonce: 6277101735386680763835789423207666416102355444464034512915,
        deadline: 18446744073709551615,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(393402133025997798000961, registry);
    assert(salt == 0xebb0143a1a4473f486c1882ca93c075f6350fc14777c5e949472d193a3d9187f, 'SALT');
    let domain = eip712::domain(11155111, salt);
    assert(domain == 0x35e3e193c805147b90ef21e5aa103590af08fd1fd8a208a3e91f17d5ac8867a7, 'DOMAIN');
    let message = eip712::link_hash(
        @request, eip712::hash_text(@statement), 393402133025997798000961, registry,
    );
    assert(message == 0x7e0c2ffa4d88fab72c1056c4d5e038c244092e4b433ae622c94f4bb8a9867d97, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0xa8564c87d92760ff850746a5ddc51a01e4b156c0c28be4eb20af2a7e89d7575c, 'DIGEST');
    let sig = Signature {
        r: 32613434550488230734369662383168237824743992973348667524693527388567356377215,
        s: 27968348128185472110740122325438034545000882863748487308925575255394299836937,
        y_parity: false,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            57949805205350981570844082709525235839, 95842270187528311981425868698979306821,
            83620641768188133376992410112653163017, 82191588066282803756463242812361162070, 0,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_5_move() {
    let label: ByteArray = "Loot Survivor";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = movement;
    let _ = (link, revoke);
    assert(
        statement == "Move my Ethereum address link from the previous Loot Survivor account shown here to this account. This does not approve asset transfers.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0x820b33d4250d4062535281cb2445e2662841428b0b7a188ca840630202c13edb,
        'STATEMENT_HASH',
    );
    let request = MoveRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        account_address: 0x0100000000000000000000000000000000000000000000112233445566778899
            .try_into()
            .unwrap(),
        previous_account_address: 0x0080000000000000000000000000000000000000000000000000aabbccddeeff
            .try_into()
            .unwrap(),
        ethereum_nonce: 1606938044258990275541962092341162602522202993782792835301393,
        recipient_nonce: 6277101735386680763835789423207666416102355444464034512915,
        deadline: 18446744073709551615,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(393402133025997798000961, registry);
    assert(salt == 0xebb0143a1a4473f486c1882ca93c075f6350fc14777c5e949472d193a3d9187f, 'SALT');
    let domain = eip712::domain(11155111, salt);
    assert(domain == 0x35e3e193c805147b90ef21e5aa103590af08fd1fd8a208a3e91f17d5ac8867a7, 'DOMAIN');
    let message = eip712::move_hash(
        @request, eip712::hash_text(@statement), 393402133025997798000961, registry,
    );
    assert(message == 0x9a8931cc1f4801dc6dd7181e46157a5b15c92c03ddedbcc624c9711f1d47ca1f, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0x1684ed7c9e97bb3a91ca8ac94a1417615e5dd031381c7b9f3aa3538854063794, 'DIGEST');
    let sig = Signature {
        r: 74655818734683202539964637584227889666094426010715778142671639419362694955937,
        s: 21138883513172085367169116731705996936029781196855935659024207526181028824838,
        y_parity: true,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121,
            226156424291633194186662080095093570025917938800079226639565781489028034303, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            206453149567685665070912392713735013281, 219393732946582001920856112639874458951,
            86226967274066690867104330345236989702, 62121595381060441930281641916165708156, 1,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_6_revoke() {
    let label: ByteArray = "Loot Survivor";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = revoke;
    let _ = (link, movement);
    assert(
        statement == "Remove my Ethereum address link to the Loot Survivor account shown here, if any, and cancel requests using the current Ethereum nonce.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0xa4f7f5839724ac58c9708a7be5ceba3be9b671e3c8f147071a897a7f294b12ac,
        'STATEMENT_HASH',
    );
    let request = RevokeRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        current_account_address: 0x0080000000000000000000000000000000000000000000000000aabbccddeeff
            .try_into()
            .unwrap(),
        ethereum_nonce: 1606938044258990275541962092341162602522202993782792835301393,
        deadline: 18446744073709551615,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(393402133025997798000961, registry);
    assert(salt == 0xebb0143a1a4473f486c1882ca93c075f6350fc14777c5e949472d193a3d9187f, 'SALT');
    let domain = eip712::domain(11155111, salt);
    assert(domain == 0x35e3e193c805147b90ef21e5aa103590af08fd1fd8a208a3e91f17d5ac8867a7, 'DOMAIN');
    let message = eip712::revoke_hash(
        @request, eip712::hash_text(@statement), 393402133025997798000961, registry,
    );
    assert(message == 0xaae1b2216b42d9e655bd3dade7d8e7bec315f7b693e8a764b3b41133f039c08a, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0xc77ee35221df248a6cda6ad46f03b7761ea394254fd3ca280137d27b19a2d6cf, 'DIGEST');
    let sig = Signature {
        r: 59811058817277365171427835683602407837999300861649001967831348616240159603903,
        s: 3617580674583428428610990018045620017532407035203443812985065721891001539004,
        y_parity: true,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            226156424291633194186662080095093570025917938800079226639565781489028034303, 17,
            4722366482869645213696, 18446744073709551615, 331989821528211312880792194059352489151,
            175768904391022779114326833548475951267, 172969729350252697928127338761766902204,
            10631114116541750298101663290031372175, 1,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_7_revoke() {
    let label: ByteArray = "Loot Survivor";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = revoke;
    let _ = (link, movement);
    assert(
        statement == "Remove my Ethereum address link to the Loot Survivor account shown here, if any, and cancel requests using the current Ethereum nonce.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0xa4f7f5839724ac58c9708a7be5ceba3be9b671e3c8f147071a897a7f294b12ac,
        'STATEMENT_HASH',
    );
    let request = RevokeRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        current_account_address: 0x0000000000000000000000000000000000000000000000000000000000000000
            .try_into()
            .unwrap(),
        ethereum_nonce: 1606938044258990275541962092341162602522202993782792835301393,
        deadline: 18446744073709551615,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(393402133025997798000961, registry);
    assert(salt == 0xebb0143a1a4473f486c1882ca93c075f6350fc14777c5e949472d193a3d9187f, 'SALT');
    let domain = eip712::domain(11155111, salt);
    assert(domain == 0x35e3e193c805147b90ef21e5aa103590af08fd1fd8a208a3e91f17d5ac8867a7, 'DOMAIN');
    let message = eip712::revoke_hash(
        @request, eip712::hash_text(@statement), 393402133025997798000961, registry,
    );
    assert(message == 0x7e418b19ad07f5b4fdad32a82e9618292788d5d95bea27084b0dc81d6fc5ad74, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0xa18a31bf9be811a2d25ea53cd5bc6b629c4347f0e218dd17d7ef770c617970db, 'DIGEST');
    let sig = Signature {
        r: 85153761109490027390535027055513505453120600288474537670117138878721943469635,
        s: 46089209562025062961573945378741262437042653671914071670638398778228527366428,
        y_parity: true,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711, 0, 17, 4722366482869645213696,
            18446744073709551615, 189357533268767833164014521802089889347,
            250244412838690331489517090284589317823, 77485289009544446224523572079656730908,
            135444013685062543361827230171340535670, 1,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_8_link() {
    let label: ByteArray = "A";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = link;
    let _ = (movement, revoke);
    assert(
        statement == "Link my Ethereum address to this A account. This does not approve asset transfers.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0x8ffd21fecacfcf755df8516b7242491134d9219939685af74fb1c4ff43fc9d85,
        'STATEMENT_HASH',
    );
    let request = LinkRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        account_address: 0x0100000000000000000000000000000000000000000000112233445566778899
            .try_into()
            .unwrap(),
        ethereum_nonce: 1606938044258990275541962092341162602522202993782792835301393,
        recipient_nonce: 6277101735386680763835789423207666416102355444464034512915,
        deadline: 18446744073709551615,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(23448594291968334, registry);
    assert(salt == 0x530f100dd34727e18578e9bba03257795e1c2377263264f0767ec02842ed9911, 'SALT');
    let domain = eip712::domain(1, salt);
    assert(domain == 0x3bb745f8400ed774c08562eab64d18da8eaeeae1f5e352d15bbc7059c595f972, 'DOMAIN');
    let message = eip712::link_hash(
        @request, eip712::hash_text(@statement), 23448594291968334, registry,
    );
    assert(message == 0xd1ef26024d9c1e6f1d54cb01095045b7ab168d1bc5dbad595e92445744cbe4f9, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0x02b0c0001c1561b41a7b32c1b49f1929337b44684d29e8cc4348b7c8ba99723f, 'DIGEST');
    let sig = Signature {
        r: 96570386588469223464566126262813960644916565236901942591831805071597069958362,
        s: 39262732411701070501462229734523742926682078240453960818119407400668111104215,
        y_parity: false,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            22238125522029383857099693537162198234, 283794859728674924657236903085389198338,
            51735949323130985307287807189504288983, 115382800369504341635703830304020505972, 0,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_9_link() {
    let label: ByteArray = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = link;
    let _ = (movement, revoke);
    assert(
        statement == "Link my Ethereum address to this AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA account. This does not approve asset transfers.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0xad2448910624c3de31085e5ef58c83e66516415e78d166fa9668583e4af55f8b,
        'STATEMENT_HASH',
    );
    let request = LinkRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        account_address: 0x0100000000000000000000000000000000000000000000112233445566778899
            .try_into()
            .unwrap(),
        ethereum_nonce: 1606938044258990275541962092341162602522202993782792835301393,
        recipient_nonce: 6277101735386680763835789423207666416102355444464034512915,
        deadline: 18446744073709551615,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(393402133025997798000961, registry);
    assert(salt == 0xebb0143a1a4473f486c1882ca93c075f6350fc14777c5e949472d193a3d9187f, 'SALT');
    let domain = eip712::domain(11155111, salt);
    assert(domain == 0x35e3e193c805147b90ef21e5aa103590af08fd1fd8a208a3e91f17d5ac8867a7, 'DOMAIN');
    let message = eip712::link_hash(
        @request, eip712::hash_text(@statement), 393402133025997798000961, registry,
    );
    assert(message == 0x87769476dec1386532dfb3cbe62a69263e2985084ede91a965da39054d79698f, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0xcdddc01bfdb3d028dc5b674396d71283b6ed2e0697a41104094c68245c5cb79d, 'DIGEST');
    let sig = Signature {
        r: 67050299980282006790929453255639213296885477616606157184341093532405593871989,
        s: 30615701173342058807015107642390634952185206451930810084806322365584251270976,
        y_parity: true,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            88871462520611323208391762045432567413, 197043122119403086171853798735686625271,
            106814648724064008957165035559018805056, 89971459439317173418892410330585722195, 1,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_10_link() {
    let label: ByteArray = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = link;
    let _ = (movement, revoke);
    assert(
        statement == "Link my Ethereum address to this AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA account. This does not approve asset transfers.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0x9e4d7b2f3d0fe7b3a50c01110632fc6b8c7fc1f3380cc0e46c7bfc633f744c3e,
        'STATEMENT_HASH',
    );
    let request = LinkRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        account_address: 0x0100000000000000000000000000000000000000000000112233445566778899
            .try_into()
            .unwrap(),
        ethereum_nonce: 1606938044258990275541962092341162602522202993782792835301393,
        recipient_nonce: 6277101735386680763835789423207666416102355444464034512915,
        deadline: 18446744073709551615,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(23448594291968334, registry);
    assert(salt == 0x530f100dd34727e18578e9bba03257795e1c2377263264f0767ec02842ed9911, 'SALT');
    let domain = eip712::domain(1, salt);
    assert(domain == 0x3bb745f8400ed774c08562eab64d18da8eaeeae1f5e352d15bbc7059c595f972, 'DOMAIN');
    let message = eip712::link_hash(
        @request, eip712::hash_text(@statement), 23448594291968334, registry,
    );
    assert(message == 0x597e410a936a0503057ebaa272bc3450c353dfc73f378a92e3e0fbec55ab3d68, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0xf310a11bec808c72a28e39ff71bb65f7ebe1d2ada99d1d16423c302006bf4066, 'DIGEST');
    let sig = Signature {
        r: 22129079714464775523558011975783934917393840520435129444071631645269439697677,
        s: 27718327560213575637531446285019363003048589007536457895040009294500021073956,
        y_parity: false,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            192386296451564579883986923854275433229, 65031520483123556785023737834632843808,
            174290547607613065733276908690444580900, 81456843653181943624412583030459140476, 0,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_11_link() {
    let label: ByteArray = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = link;
    let _ = (movement, revoke);
    assert(
        statement == "Link my Ethereum address to this AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA account. This does not approve asset transfers.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0x8001aa002ef8224ec6f5150a1a18701a77a49b5b842a3799aab9fca2737e91a0,
        'STATEMENT_HASH',
    );
    let request = LinkRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        account_address: 0x0100000000000000000000000000000000000000000000112233445566778899
            .try_into()
            .unwrap(),
        ethereum_nonce: 1606938044258990275541962092341162602522202993782792835301393,
        recipient_nonce: 6277101735386680763835789423207666416102355444464034512915,
        deadline: 18446744073709551615,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(393402133025997798000961, registry);
    assert(salt == 0xebb0143a1a4473f486c1882ca93c075f6350fc14777c5e949472d193a3d9187f, 'SALT');
    let domain = eip712::domain(11155111, salt);
    assert(domain == 0x35e3e193c805147b90ef21e5aa103590af08fd1fd8a208a3e91f17d5ac8867a7, 'DOMAIN');
    let message = eip712::link_hash(
        @request, eip712::hash_text(@statement), 393402133025997798000961, registry,
    );
    assert(message == 0xd0cb3caa68b54074c914f2ab7029256ed710865a3fe4195f491b9d7e20bad8ab, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0x7b5dbf07d6425a3fafa465ef53e498ff4fdbf5f73afa1938727b359b92d58d5f, 'DIGEST');
    let sig = Signature {
        r: 58259397672796921845483251434276248909031408142861435583760761062798537841910,
        s: 17182208575927667133978541424013597696005251275252643263608560431393869227688,
        y_parity: false,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            218042738385383184764626980492766141686, 171208982116704763137202312061041093654,
            266595509146695031557769392689500743336, 50493972789133085489927708306921324117, 0,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
#[test]
fn golden_12_link() {
    let label: ByteArray = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    labels::validate(@label);
    let (link, movement, revoke) = labels::statements(@label);
    let statement = link;
    let _ = (movement, revoke);
    assert(
        statement == "Link my Ethereum address to this AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA account. This does not approve asset transfers.",
        'STATEMENT',
    );
    assert(
        eip712::hash_text(
            @statement,
        ) == 0x5ad67fa530e15656c848f4ec7107342fec955762b22876838b2e876dbd0309dd,
        'STATEMENT_HASH',
    );
    let request = LinkRequest {
        ethereum_address: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf.try_into().unwrap(),
        account_address: 0x0100000000000000000000000000000000000000000000112233445566778899
            .try_into()
            .unwrap(),
        ethereum_nonce: 1606938044258990275541962092341162602522202993782792835301393,
        recipient_nonce: 6277101735386680763835789423207666416102355444464034512915,
        deadline: 18446744073709551615,
    };
    let registry = 0x0200000000000000000000000000000000000000000000000123456789abcdef
        .try_into()
        .unwrap();
    let salt = eip712::salt(23448594291968334, registry);
    assert(salt == 0x530f100dd34727e18578e9bba03257795e1c2377263264f0767ec02842ed9911, 'SALT');
    let domain = eip712::domain(1, salt);
    assert(domain == 0x3bb745f8400ed774c08562eab64d18da8eaeeae1f5e352d15bbc7059c595f972, 'DOMAIN');
    let message = eip712::link_hash(
        @request, eip712::hash_text(@statement), 23448594291968334, registry,
    );
    assert(message == 0x5ccf45474892c2b7d6f1e11aece1280c696546e269a972fdf9f6ba6a590a73fb, 'STRUCT');
    let digest = eip712::envelope(domain, message);
    assert(digest == 0x93b9134ba511231c5459a9af5215f7bd04fc2b5d58f992efac4a3bd87f13f604, 'DIGEST');
    let sig = Signature {
        r: 18235742599334492180148096121773316734021533376539552008207348615108653157649,
        s: 31790477318812221096264851284243597395365040094432423135074012234225284001636,
        y_parity: true,
    };
    let mut calldata = array![];
    Serde::serialize(@request, ref calldata);
    Serde::serialize(@sig, ref calldata);
    assert(
        calldata == array![
            721457446580647751014191829380889690493307935711,
            452312848583266388373324160190187140051835877600158453595190225338656852121, 17,
            4722366482869645213696, 19, 18446744073709551616, 18446744073709551615,
            117541539112154026267015082154642574609, 53590031021417581639623396819204770215,
            123376430487120131999811403443063467876, 93423816245519567453082202972668791335, 1,
        ],
        'CALLDATA',
    );
    signature::verify(digest, sig, request.ethereum_address);
}
