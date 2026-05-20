# syntax=docker/dockerfile:1
#
# Single image used by both compose services. ROS 2 Jazzy provides Python 3.12
# plus rclpy/sensor_msgs system packages; we layer the Python deps from
# pyproject.toml on top using pip.
#
# Base image pinned by digest (multi-arch manifest list covering linux/amd64
# and linux/arm64) for OSSF Scorecard Pinned-Dependencies and reproducibility.
FROM ros:jazzy-ros-base@sha256:eac11a5285beeb1e1884e71f7091c610e08452e823bfb3f43afaa334375325f6

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-rclpy \
        ros-jazzy-sensor-msgs \
        ros-jazzy-rmw-cyclonedds-cpp \
        python3-pip \
        python3-opencv \
        python3-fastapi \
        python3-uvicorn \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml /app/
COPY src/ /app/src/

# Why these are pip-installed instead of apt:
#   - pydantic: apt ships v1, we need v2.
#   - pyarrow: no apt package on Ubuntu 24.04.
#   - av:      no apt package on Ubuntu 24.04.
#
# Why --ignore-installed (load-bearing, do not remove):
# pydantic 2.x requires typing_extensions >= 4.12, but the base image's
# python3-fastapi (apt) pulls in python3-typing-extensions 4.10. Apt-installed
# wheels have no RECORD file, so pip refuses to uninstall the older copy
# ("Cannot uninstall ... no RECORD file") and aborts. --ignore-installed tells
# pip to skip the uninstall and write a fresh copy under /usr/local, which
# takes precedence on sys.path. The flag is harmless for the other packages.
#
# Why --require-hashes + heredoc: defence-in-depth against compromised PyPI
# artefacts. The full transitive closure (av, pyarrow, pydantic and the
# pydantic deps annotated-types, pydantic-core, typing-extensions,
# typing-inspection) is hash-pinned and materialised in-layer to keep the
# requirements DRY in this Dockerfile. Regenerate with:
#   uv pip compile <(printf 'av==17.0.1\npyarrow==24.0.0\npydantic==2.13.4\n') \
#       --python-version 3.12 --python-platform manylinux_2_28_x86_64 \
#       --generate-hashes --no-header --no-annotate
# The output is identical for manylinux_2_28_aarch64 (uv emits hashes for all
# PyPI distributions of the resolved versions, covering both archs).
RUN <<'EOF'
cat > /tmp/scene-aligner-requirements.txt <<'REQ'
annotated-types==0.7.0 \
    --hash=sha256:1f02e8b43a8fbbc3f3e0d4f0f4bfc8131bcb4eebe8849b8e5c773f3a1c582a53 \
    --hash=sha256:aff07c09a53a08bc8cfccb9c85b05f1aa9a2a6f23728d790723543408344ce89
av==17.0.1 \
    --hash=sha256:09b1f1601cc4a4d9e616d197b345c363ba6abfe567cb3d6b18e45516126692b6 \
    --hash=sha256:1229e879f4b6431bc00f69d7f8891fe9a683b0a6e0e009e6c98eb7e449f0383d \
    --hash=sha256:1d33871742d1e71562db3c8e752cacc5a62766d7efc3ae408bff1c3e26ebb46e \
    --hash=sha256:3a3f33bbfed2bcc65be37941bfeb6cc20bbe9cb7afc4ef1ac8d330972df098f9 \
    --hash=sha256:3d0a7d45d9599bf9df9f8249827113d4f36df1cd6b5356227b997f0552dbc98e \
    --hash=sha256:3d3a36204cb1f1e7691e6446afa8d6b7097b09946dae732c71c5d05ce09e506e \
    --hash=sha256:3ed6bcd7021fe55832f95b8ef78dd01a4cb21faf3cd71f1e1bf4f20bf100b278 \
    --hash=sha256:42d6745d30a410ec9b22aef79a52a7ab5a001eb8f5adfd952946606a30983318 \
    --hash=sha256:4744837f4116964280bcc72285e3cdd51361e98a696205aadd924203440ef511 \
    --hash=sha256:50e58a473d65ea29b645e45c9fd8518a6783737135683ecc40571a91592bdfe4 \
    --hash=sha256:50f9dd53a8ebef77606dca3b21710f660f9a6478484e79b9abda7c787b4f2403 \
    --hash=sha256:8270634c409f8efc9a24216e5dd90313d873b26ea4b5f172b14de52cbd15121c \
    --hash=sha256:985c21095bfb9c4bb7ba362fbef7bf0194bd72b1d7d3c46e30d1f47c5d38b4df \
    --hash=sha256:987f4f46ceae4da6c614dcbd2b8149be9dbf680c3bb7a6841c58af9cff4d9230 \
    --hash=sha256:9acd0b6a6e02af2b37f63d97a03ee2c47936d58e82425c3cd075a95245937c59 \
    --hash=sha256:9af524e8632a54032e361d6b88895bd3e7c6212ca560de60f5ccc525323c764c \
    --hash=sha256:a87a42c36e29f75e7dff7281944f2a6876a2c8875e225ccbf6c1ae62748b4caa \
    --hash=sha256:b87b98afe971cde123953073bc9c95ab0b7efd2ecc082dd2dbd11f9d9abf190e \
    --hash=sha256:c58c71bffd9383908c85695ac61d3184c668accb04a5bd1b262e0fb8d09f60a5 \
    --hash=sha256:d97f54e55b18a74912f479c1978aadd1341d38d892dee95bb5c2f2dccfa72f32 \
    --hash=sha256:e6eee84afa48d0e9321047cd3e4facd44b401493f6bdc753e2e1d1e7c9e6d13e \
    --hash=sha256:f585358fe0127990aea7887e940de4cdd745a2770605c31e54b2418fd0fdd8bd \
    --hash=sha256:f63b30067e6d88a3cce0d73d01ecfc0e6f091ad2bcf689db5dc305b0b4e8348c \
    --hash=sha256:fbcbd4aa43bca6a8691816283112d1659a27f407bbeb66d1397023691339f5d4
pyarrow==24.0.0 \
    --hash=sha256:02b001b3ed4723caa44f6cd1af2d5c86aa2cf9971dacc2ffa55b21237713dfba \
    --hash=sha256:04920d6a71aabd08a0417709efce97d45ea8e6fb733d9ca9ecffb13c67839f68 \
    --hash=sha256:0b3537c00fb8d384f15ac1e79b6eb6db04a16514c8c1d22e59a9b95c8ba42868 \
    --hash=sha256:1183baeb14c5f587b1ec52831e665718ce632caab84b7cd6b85fd44f96114495 \
    --hash=sha256:14e31a3c9e35f1ab6356c6378f6f72830e6d2d5f1791df3774a7b097d18a6a1e \
    --hash=sha256:1617043b99bd33e5318ae18eb2919af09c71322ef1ca46566cdafc6e6712fb66 \
    --hash=sha256:1a4e45017efbf115032e4475ee876d525e0e36c742214fbe405332480ecd6275 \
    --hash=sha256:1b2fe7f9a5566401a0ef2571f197eb92358925c1f0c8dba305d6e43ea0871bb3 \
    --hash=sha256:1cc9057f0319e26333b357e17f3c2c022f1a83739b48a88b25bfd5fa2dc18838 \
    --hash=sha256:2392d954fcb920f42d230284b677605e4e2fbb11f2821e823e642abd67fbb491 \
    --hash=sha256:25ea65d868eb04015cd18e6df2fbe98f07e5bda2abefabcb88fce39a947716f6 \
    --hash=sha256:295f0a7f2e242dabd513737cf076007dc5b2d59237e3eca37b05c0c6446f3826 \
    --hash=sha256:2f16197705a230a78270cdd4ea8a1d57e86b2fdcbc34a1f6aebc72e65c986f9a \
    --hash=sha256:35405aecb474e683fb36af650618fd5340ee5471fc65a21b36076a18bbc6c981 \
    --hash=sha256:38be1808cdd068605b787e6ca9119b27eb275a0234e50212c3492331680c3b1e \
    --hash=sha256:3a577bd840ca83f646f0a625dbc571dba7044c43c2d1503afc378b570954345c \
    --hash=sha256:3b13dedfe76a0ad2d1d859b0811b53827a4e9d93a0bcb05cf59333ab4980cc7e \
    --hash=sha256:418e48ce50a45a6a6c73c454677203a9c75c966cb1e92ca3370959185f197a05 \
    --hash=sha256:55a3bc1e3df3b5567b7d27ef551b2283f0c68a5e86f1cd56abc569da4f31335b \
    --hash=sha256:6165461f55ef6314f026de6638d661188e3455d3ec49834556a0ebbdbace18bb \
    --hash=sha256:61a3d7eaa97a14768b542f3d284dc6400dd2470d9f080708b13cd46b6ae18136 \
    --hash=sha256:6233c9ed9ab9d1db47de57d9753256d9dcffbf42db341576099f0fd9f6bf4810 \
    --hash=sha256:641f795b361874ac9da5294f8f443dfdbee355cf2bd9e3b8d97aaac2306b9b37 \
    --hash=sha256:644a246325b8c69c595ad1dd4b463eba4b0cdb731370e4a86137d433208d6147 \
    --hash=sha256:6f066b179d68c413374294bc1735f68475457c933258df594443bb9d88ddc2a0 \
    --hash=sha256:7986f1fa71cee060ad00758bcc79d3a93bab8559bf978fab9e53472a2e25a17b \
    --hash=sha256:7c2b98645d576a0b9616892ead22b64a83a5f043c5e2ca15ebcefcb5b70c80cb \
    --hash=sha256:806f24b4085453c197a5078218d1ee08783ebbba271badd153d1ae22a3ee804f \
    --hash=sha256:85fe721a14dd823aca09127acbb06c3ca723efbd436c004f16bca601b04dcc83 \
    --hash=sha256:8adc8e6ce5fccf5dc707046ae4914fd537def529709cc0d285d37a7f9cd442ca \
    --hash=sha256:9700ebd9a51f5895ce75ff4ac4b3c47a7d4b42bc618be8e713e5d56bacf5f931 \
    --hash=sha256:9b18371ad2f44044b81a8d23bc2d8a9b6a6226dca775e8e16cfee640473d6c5d \
    --hash=sha256:a964266397740257f16f7bb2e4f08a0c81454004beab8ff59dd531b73610e9f2 \
    --hash=sha256:adbbedc55506cbdabb830890444fb856bfb0060c46c6f8026c6c2f2cf86ae795 \
    --hash=sha256:ae8a1145af31d903fa9bb166824d7abe9b4681a000b0159c9fb99c11bc11ad26 \
    --hash=sha256:b0e131f880cda8d04e076cee175a46fc0e8bc8b65c99c6c09dff6669335fde74 \
    --hash=sha256:b196eb3f931862af3fa84c2a253514d859c08e0d8fe020e07be12e75a5a9780c \
    --hash=sha256:b7d9a514e73bc42711e6a35aaccf3587c520024fe0a25d830a1a8a27c15f4f57 \
    --hash=sha256:bec9373df11544592b0ba7ec2af0e35059e5f0e7647c6183a854dedd193298f1 \
    --hash=sha256:c42ab9439498270139cc63e18847a02afe5c8b3ed9c931266533cfe378bd3591 \
    --hash=sha256:c91d00057f23b8d353039520dc3a6c09d8608164c692e9f59a175a42b2ae0c19 \
    --hash=sha256:d3e0b61e8efb24ed38898e5cdc5fffa9124be480008d401a1f8071500494ae42 \
    --hash=sha256:d7027eba1df3b2069e2e8d80f644fa0918b68c46432af3d088ddd390d063ecde \
    --hash=sha256:d8ddd2768da81d3ee08cfea9b597f4abb4e8e1dc8ae7e204b608d23a0d3ab699 \
    --hash=sha256:e3268e43984d0b1a185c89b4cfff282a7ead12fc93f56cfd7088bdbcbe727041 \
    --hash=sha256:e4505fc6583f7b05ab854934896bcac8253b04ac1171a77dfb73efef92076d91 \
    --hash=sha256:e56a1ffe9bf7b727432b89104cc0849c21582949dd7bdcb34f17b2001a351a76 \
    --hash=sha256:e6f1278ee4785b6db21229374a1c9e54ec7c549de5d1efc9630b6207de7e170b \
    --hash=sha256:f7616236ec1bc2b15bfdec22a71ab38851c86f8f05ff64f379e1278cf20c634a \
    --hash=sha256:fb24ac194bfc5e86839d7dcd52092ee31e5fe6733fe11f5e3b06ef0812b20072
pydantic==2.13.4 \
    --hash=sha256:45a282cde31d808236fd7ea9d919b128653c8b38b393d1c4ab335c62924d9aba \
    --hash=sha256:c40756b57adaa8b1efeeced5c196f3f3b7c435f90e84ea7f443901bec8099ef6
pydantic-core==2.46.4 \
    --hash=sha256:00c603d540afdd6b80eb39f078f33ebd46211f02f33e34a32d9f053bba711de0 \
    --hash=sha256:0186750b482eefa11d7f435892b09c5c606193ef3375bcf94aa00ae6bfb66262 \
    --hash=sha256:041bde0a48fd37cf71cab1c9d56d3e8625a3793fef1f7dd232b3ff37e978ecda \
    --hash=sha256:0c563b08bca408dc7f65f700633d8442fffb2421fc47b8101377e9fd65051ff0 \
    --hash=sha256:0cbe8b01f948de4286c74cdd6c667aceb38f5c1e26f0693b3983d9d74887c65e \
    --hash=sha256:0ce40cd7b21210e99342afafbd4d0f76d784eb5b1d60f3bdc566be4983c6c73b \
    --hash=sha256:0e96592440881c74a213e5ad528e2b24d3d4f940de2766bed9010ab1d9e51594 \
    --hash=sha256:10e17cbb10a330363733efc4d7c4d0dd827ac0909b8f6a6542298fed1ea62f29 \
    --hash=sha256:133878133d271ade3d41d1bfb2a45ec38dbdbda40bc065921c6b04e4630127e2 \
    --hash=sha256:14d4edf427bdcf950a8a02d7cb44a08614388dd6e1bdcbf4f67504fa7887da9c \
    --hash=sha256:14f4c5d6db102bd796a627bbb3a17b4cf4574b9ae861d8b7c9a9661c6dd3362d \
    --hash=sha256:17299feefe090f2caa5b8e37222bb5f663e4935a8bfa6931d4102e5df1a9f398 \
    --hash=sha256:184c081504d17f1c1066e430e117142b2c77d9448a97f7b65c6ac9fd9aee238d \
    --hash=sha256:18e5ceec2ab67e6d5f1a9085e5a24c9c4e2ac4545730bfe668680bca05e555f3 \
    --hash=sha256:19e51f073cd3df251856a8a4189fbdf1de4012c3ebacfb1884f94f1eb406079f \
    --hash=sha256:1a7dd0b3ee80d90150e3495a3a13ac34dbcbfd4f012996a6a1d8900e91b5c0fb \
    --hash=sha256:1d8ba486450b14f3b1d63bc521d410ec7565e52f887b9fb671791886436a42f7 \
    --hash=sha256:2108ba5c1c1eca18030634489dc544844144ee36357f2f9f780b93e7ddbb44b5 \
    --hash=sha256:228ee9bae8bef5b1e97ec58302f80357c37199e0d0a99174e138d28e6957b9d9 \
    --hash=sha256:23ace664830ee0bfe014a0c7bc248b1f7f25ed7ad103852c317624a1083af462 \
    --hash=sha256:2412e734dcb48da14d4e4006b82b46b74f2518b8a26ee7e58c6844a6cd6d03c4 \
    --hash=sha256:29c61fc04a3d840155ff08e475a04809278972fe6aef51e2720554e96367e34b \
    --hash=sha256:2f84c03c8607173d16b5a854ec68a2f9079ae03237a54fb506d13af47e1d018d \
    --hash=sha256:3009f12e4e90b7f88b4f9adb1b0c4a3d58fe7820f3238c190047209d148026df \
    --hash=sha256:3245406455a5d98187ec35530fd772b1d799b26667980872c8d4614991e2c4a2 \
    --hash=sha256:3447661d99f75a3683a4cf5c87da72f2161964611864dbbeac7fbb118bb4bfc0 \
    --hash=sha256:372429a130e469c9cd698925ce5fc50940b7a1336b0d82038e63d5bbc4edc519 \
    --hash=sha256:395aebd9183f9d112f569aeb5b2214d1a10a33bec8456447f7fbdfa51d38d4cd \
    --hash=sha256:3a233125ac121aa3ffba9a2b59edfc4a985a76092dc8279586ab4b71390875e7 \
    --hash=sha256:3be77f45df024d789a672ae34f8b06fb346c4f9f46ea714956660ea4862e89ac \
    --hash=sha256:3bf92c5d0e00fefaab325a4d27828fe6b6e2a21848686b5b60d2d9eeb09d76c6 \
    --hash=sha256:3ecbc122d18468d06ca279dc26a8c2e2d5acb10943bb35e36ae92096dc3b5565 \
    --hash=sha256:3fb702cd90b0446a3a1c5e470bfa0dd23c0233b676a9099ddcc964fa6ca13898 \
    --hash=sha256:428e04521a40150c85216fc8b85e8d39fece235a9cf5e383761238c7fa9b96fb \
    --hash=sha256:432c179df7874eeb73307aad2df0755e1ae0efa61ff0ea89b93e194411ae3928 \
    --hash=sha256:4a05d69cba51d852c5c3e92758653245a50c0b646ced0cf05bd793ed592839d6 \
    --hash=sha256:4c63ebc82684aa89d9a3bcbd13d515b3be44250dc68dd3bd81526c1cb31286c3 \
    --hash=sha256:4fc73cb559bdb54b1134a706a2802a4cddd27a0633f5abb7e53056268751ac6a \
    --hash=sha256:4fcbe087dbc2068af7eda3aa87634eba216dbda64d1ae73c8684b621d33f6596 \
    --hash=sha256:56cb4851bcaf3d117eddcef4fe66afd750a50274b0da8e22be256d10e5611987 \
    --hash=sha256:5855698a4856556d86e8e6cd8434bc3ac0314ee8e12089ae0e143f64c6256e4e \
    --hash=sha256:5a4330cdbc57162e4b3aa303f588ba752257694c9c9be3e7ebb11b4aca659b5d \
    --hash=sha256:5b712b53160b79a5850310b912a5ef8e57e56947c8ad690c227f5c9d7e561712 \
    --hash=sha256:5d5902252db0d3cedf8d4a1bc68f70eeb430f7e4c7104c8c476753519b423008 \
    --hash=sha256:617d7e2ca7dcb8c5cf6bcb8c59b8832c94b36196bbf1cbd1bfb56ed341905edd \
    --hash=sha256:62f875393d7f270851f20523dd2e29f082bcc82292d66db2b64ea71f64b6e1c1 \
    --hash=sha256:633147d34cf4550417f12e2b1a0383973bdf5cdfde212cb09e9a581cf10820be \
    --hash=sha256:66ce7632c22d837c95301830e111ad0128a32b8207533b60896a96c4915192ea \
    --hash=sha256:6b3ace8194b0e5204818c92802dcdca7fc6d88aabbb799d7c795540d9cd6d292 \
    --hash=sha256:6f2eeda33a839975441c86a4119e1383c50b47faf0cbb5176985565c6bb02c33 \
    --hash=sha256:7027560ee92211647d0d34e3f7cd6f50da56399d26a9c8ad0da286d3869a53f3 \
    --hash=sha256:7283d57845ecf5a163403eb0702dfc220cc4fbdd18919cb5ccea4f95ee1cdab4 \
    --hash=sha256:7a5f930472650a82629163023e630d160863fce524c616f4e5186e5de9d9a49b \
    --hash=sha256:7bfb192b3f4b9e8a89b6277b6ce787564f62cfd272055f6e685726b111dc7826 \
    --hash=sha256:811ff8e9c313ab425368bcbb36e5c4ebd7108c2bbf4e4089cfbb0b01eff63fac \
    --hash=sha256:8233f2947cf85404441fd7e0085f53b10c93e0ee78611099b5c7237e36aacbf7 \
    --hash=sha256:82cf5301172168103724d49a1444d3378cb20cdee30b116a1bd6031236298a5d \
    --hash=sha256:8358a950c8909158e3df31538a7e4edc2d7265a7c54b47f0864d9e5bae9dcebf \
    --hash=sha256:85bb3611ff1802f3ee7fdd7dbff26b56f343fb432d57a4728fdd49b6ef35e2f4 \
    --hash=sha256:86e1a4418c6cd97d60c95c71164158eaf7324fae7b0923264016baa993eba6fc \
    --hash=sha256:8b9bab013d1c7a79d3501ff86d0bc9c31bf587db4551677b96bec07df78c6b15 \
    --hash=sha256:8c5dac79fa1614d1e06ca695109c6105923bd9c7d1d6c918d4e637b7e6b32fd3 \
    --hash=sha256:8d0820e8192167f80d88d64038e609c31452eeca865b4e1d9950a27a4609b00b \
    --hash=sha256:8daafc69c93ee8a0204506a3b6b30f586ef54028f52aeeeb5c4cfc5184fd5914 \
    --hash=sha256:9037063db01f09b09e237c282b6792bd4da634b5402c4e7f0c61effed7701a04 \
    --hash=sha256:905a0ed8ea6f2d61c1738835f99b699348d7857379083e5fc497fa0c967a407c \
    --hash=sha256:90884113d8b48f760e9587002789ddd741e76ab9f89518cd1e43b1f1a52ec44b \
    --hash=sha256:91a06d2e259ecfbd8c901d70c3c507900458498142b3026a296b7de4d1322cc9 \
    --hash=sha256:926c9541b14b12b1681dca8a0b75feb510b06c6341b70a8e500c2fdcff837cce \
    --hash=sha256:9401557acd873c3a7f3eb9383edef8ac4968f9510e340f4808d427e75667e7b4 \
    --hash=sha256:9551187363ffc0de2a00b2e47c25aeaeb1020b69b668762966df15fc5659dd5a \
    --hash=sha256:962ccbab7b642487b1d8b7df90ef677e03134cf1fd8880bf698649b22a69371f \
    --hash=sha256:97e7cf2be5c77b7d1a9713a05605d49460d02c6078d38d8bef3cbe323c548424 \
    --hash=sha256:9aa768456404a8bf48a4406685ac2bec8e72b62c69313734fa3b73cf33b3a894 \
    --hash=sha256:9bc519fbf2b7578398853d815009ae5e4d4603d12f4e3f91da8c06852d3da3e9 \
    --hash=sha256:9d56801be94b86a9da183e5f3766e6310752b99ff647e38b09a9500d88e46e76 \
    --hash=sha256:9f444c499b3eefd3a92e348059471ea0c3a6e303d9c1cec09fa748fd9f895201 \
    --hash=sha256:9fa8ae11da9e2b3126c6426f147e0fba88d96d65921799bb30c6abd1cb2c97fb \
    --hash=sha256:a0f62d0a58f4e7da165457e995725421e0064f2255d8eccebc49f41bbc23b109 \
    --hash=sha256:a396dcc17e5a0b164dbe026896245a4fa9ff402edca1dff0be3d53a517f74de4 \
    --hash=sha256:aaa2a54443eff1950ba5ddc6b6ccda0d9c84a364276a62f969bdf2a390650848 \
    --hash=sha256:ad785e92e6dc634c21555edc8bd6b64957ab844541bcb96a1366c202951ae526 \
    --hash=sha256:af8244b2bef6aaad6d92cda81372de7f8c8d36c9f0c3ea36e827c60e7d9467a0 \
    --hash=sha256:b078afbc25f3a1436c7a1d2cd3e322497ee99615ba97c563566fdf46aff1ee01 \
    --hash=sha256:b2f69dec1725e79a012d920df1707de5caf7ed5e08f3be4435e25803efc47458 \
    --hash=sha256:b8458003118a712e66286df6a707db01c52c0f52f7db8e4a38f0da1d3b94fc4e \
    --hash=sha256:bb63e0198ca18aad131c089b9204c23079c3afa95487e561f4c522d519e55aba \
    --hash=sha256:bfec22eab3c8cc2ceec0248aec886624116dc079afa027ecc8ad4a7e62010f8a \
    --hash=sha256:c1747f85cee84c26985853c6f3d9bd3e75da5212912443fa111c113b9c246f39 \
    --hash=sha256:c1b3f518abeca3aa13c712fd202306e145abf59a18b094a6bafb2d2bbf59192c \
    --hash=sha256:c50f2528cf200c5eed56faf3f4e22fcd5f38c157a8b78576e6ba3168ec35f000 \
    --hash=sha256:c68fcd102d71ea85c5b2dfac3f4f8476eff42a9e078fd5faefff6d145063536b \
    --hash=sha256:c7a7bd4e39e8e4c12c39cd480356842b6a8a06e41b23a55a5e3e191718838ddf \
    --hash=sha256:c94f0688e7b8d0a67abf40e57a7eaaecd17cc9586706a31b76c031f63df052b4 \
    --hash=sha256:cbaf13819775b7f769bf4a1f066cb6df7a28d4480081a589828ef190226881cd \
    --hash=sha256:cd2213145bcc2ba85884d0ac63d222fece9209678f77b9b4d76f054c561adb28 \
    --hash=sha256:ce5c1d2a8b27468f433ca974829c44060b8097eedc39933e3c206a90ee49c4a9 \
    --hash=sha256:d396ec2b979760aaf3218e76c24e65bd0aca24983298653b3a9d7a45f9e47b30 \
    --hash=sha256:d51026d73fcfd93610abc7b27789c26b313920fcfb20e27462d74a7f8b06e983 \
    --hash=sha256:d80ee3d731373b24cebbc10d689ca4ee1875caf0d5703a245db18efd4dd37fc1 \
    --hash=sha256:d995260fdf4e1db774581b4900e0f832abe3c7c84996726bbc161b19c8f29e76 \
    --hash=sha256:da4b951fe36dc7c3a1ccb4e3cd1747c3542b8c9ceede8fc86cae054e764485f5 \
    --hash=sha256:daa27d92c36f24388fe3ad306b174781c747627f134452e4f128ea00ce1fe8c4 \
    --hash=sha256:db06ffe51636ffe9ca531fe9023dd64bdd794be8754cb5df57c5498ae5b518a7 \
    --hash=sha256:e0d65b8c354be7fb5f720c3caa8bc940bc2d20ce749c8e06135f07f8ed95dd7c \
    --hash=sha256:e68b7a074f65a2fd746c52a7ce6142ab7006074ac269ace0c25cd8ba171f8066 \
    --hash=sha256:e739fee756ba1010f8bcccb534252e85a35fe45ae92c295a06059ce58b74ccd3 \
    --hash=sha256:e846ae7835bf0703ae43f534ab79a867146dadd59dc9ca5c8b53d5c8f7c9ef02 \
    --hash=sha256:e9c26f834c65f5752f3f06cb08cb86a913ceb7274d0db6e267808a708b46bc89 \
    --hash=sha256:ea793e075b70290d89d8142074262885d3f7da19634845135751bd6344f73b50 \
    --hash=sha256:f027324c56cd5406ca49c124b0db10e56c69064fec039acc571c29020cc87c76 \
    --hash=sha256:f13a646d65d09fbf1bc6b3a9635d30095c8e7e5cc419ff35ecc563c5fd04cd49 \
    --hash=sha256:f47286a97f0bc9b8859519809077b91b2cefe4ae47fcbf5e466a009c1c5d742b \
    --hash=sha256:f747929cf940cddb5b3668a390056ddd5ba2e5010615ea2dcf4f9c4f3ab8791d \
    --hash=sha256:f99626688942fb746e545232e7726926f3be91b5975f8b55327665fafda991c7 \
    --hash=sha256:f9fa868638bf362d3d138ea55829cefb3d5f4b0d7f142234382a15e2485dbec4 \
    --hash=sha256:fbdb89b3e1c94a30cc5edfce477c6e6a5dc4d8f84665b455c27582f211a1c72c \
    --hash=sha256:fc010ab034c8c7452522748bf937df58020d256ccae0874463d1f4d01758af8e \
    --hash=sha256:fc3e9034a63de20e15e8ade85358bc6efc614008cab72898b4b4952bea0509ff \
    --hash=sha256:fd8b3d9fd264be37976686c7f65cd52a83f5e84f4bfd2adf9c1d469676bbb6ae
typing-extensions==4.15.0 \
    --hash=sha256:0cea48d173cc12fa28ecabc3b837ea3cf6f38c6d1136f85cbaaf598984861466 \
    --hash=sha256:f0fa19c6845758ab08074a0cfa8b7aecb71c999ca73d62883bc25cc018c4e548
typing-inspection==0.4.2 \
    --hash=sha256:4ed1cacbdc298c220f1bd249ed5287caa16f34d44ef4e9c3d0cbad5b521545e7 \
    --hash=sha256:ba561c48a67c5958007083d386c3295464928b01faa735ab8547c5692e87f464
REQ
pip3 install --no-cache-dir --break-system-packages --ignore-installed \
    --require-hashes -r /tmp/scene-aligner-requirements.txt
rm /tmp/scene-aligner-requirements.txt
EOF

# Install the package itself (no deps; everything was hash-pinned above).
RUN pip3 install --no-cache-dir --break-system-packages --no-deps -e .

EXPOSE 8080

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["python3", "-m", "uvicorn", "scene_aligner.aligner:app", "--host", "0.0.0.0", "--port", "8080"]
