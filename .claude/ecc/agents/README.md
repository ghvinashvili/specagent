# ECC agents

ECC's agent definitions at the pin, kept as text a chat-role brief may borrow from; no file here is an agent
of this repository (`../sources.md`, "Agents"). Each line: the copy, the upstream file's sha256, and
the upstream lines dropped besides the frontmatter's `tools:` and `model:` lines (4 and 5 in every file).
A copy over 12,000 bytes ends its line in `; <bytes> bytes: read by outline`: run `python3 ops/outline.py <copy>`,
then read only the sections needed (`--show "<heading>"`), never the whole file.

- [a11y-architect](a11y-architect.md): `88e684476cbc449a2444a1218a79034d275465f375ce45b6d86ab99958bf45e7`; 148-149 K1
- [agent-evaluator](agent-evaluator.md): `7ef0739152e7bbc837e9bab4fbae7164f29719a4d1dbdaa1e3b62b4f34358e3c`; 25 K1; 55-56 K1
- [architect](architect.md): `6b8e1e8bd274995f3949691731f4334820c061d3054eaea3be2ce163386d1f24`; none
- [bengali-reviewer](bengali-reviewer.md): `ad93abe7b04a2606b671fe7a86e3980565a55bee939b4eccedfccfea7107fd5a`; none
- [build-error-resolver](build-error-resolver.md): `acc9e14df59dd28d00f966b3a6cf0d9aeeda7e8a9ab7f1bc442466c0219c35ec`; none
- [chief-of-staff](chief-of-staff.md): `d3dca9a474011410256dfcd0cc553f926bd30b4efdaaf6ec41b4f6ec86e88e6f`; 112-113 K1
- [code-architect](code-architect.md): `1a2ce1d231b7427ff863522f6f19e7738cd668279ac60af520aa0c45ac14772b`; none
- [code-explorer](code-explorer.md): `3dbb33769147f6c7ffb739c550b7b8867e1b8ea84f1179197fdbc3028dc34fb7`; none
- [code-reviewer](code-reviewer.md): `9dd23be23d65f18126e10f7680fc1eb2576ec54a427d076ff2f870bd0bafd5d2`; none; 13833 bytes: read by outline
- [code-simplifier](code-simplifier.md): `4020b1466f4a635ed33b87a3d734bda45363514defc7d1613b81d5c59e426c6b`; none
- [comment-analyzer](comment-analyzer.md): `ce7fdf759885ba9ef5ee1bdc9da4ce88d78ba65501facf53e581082fcf402b07`; none
- [commit-reviewer](commit-reviewer.md): `b6e8bb0a3bab270ef6c53f68f829e5c86f2725c159b790962a6cd2dc648d2a26`; none
- [conversation-analyzer](conversation-analyzer.md): `f86fcf4317a41158dc55641f606c97a8d4d3ccacf7157ff70e0811ca7b42ba75`; none
- [cpp-build-resolver](cpp-build-resolver.md): `0a06faff0f6be85989a22c79647743d872c3348ca772ee860f048035473c1675`; none
- [cpp-reviewer](cpp-reviewer.md): `c34ee3291505ea66d4330268babbd9cbc899e32b7869ca71cca1690b4ce3cf22`; none
- [csharp-reviewer](csharp-reviewer.md): `34652d6a39387d0d008a90804b1b271ae62bba77abaf9537b79bd7705b1724e0`; 105-107 K1
- [dart-build-resolver](dart-build-resolver.md): `2715aa7b58fae3667493a089afbfa891dfe20d24e555e90ddfdd732d10104d1f`; 209-210 K1
- [database-reviewer](database-reviewer.md): `945c107dea01ca74e3e9bc3a5841e79e744673e8f14697e88cf1cfd9c01a1cc5`; 94-95 K1
- [django-build-resolver](django-build-resolver.md): `643f1445336ef801f49cc56a00ad09af3435124ef841f4b023be19ee50662b29`; 250-252 K1
- [django-reviewer](django-reviewer.md): `d116bccee67db3d1f52f54f819a04467fe7dd2b0004ec85d21f218a6aacf6346`; 163-166 K1
- [doc-updater](doc-updater.md): `5018d3a0bf740d2263fd4b7a92412d53a62d4be151a71221d6549cacba62d72c`; none
- [docs-lookup](docs-lookup.md): `11560171e4535419e7917158d0de3bc7bbbf0408f83f61f0f3558b356802419e`; none
- [e2e-runner](e2e-runner.md): `94811f4bbc491c351cdf220ab103d6bd251fb1d88d9d46ba4c8162637a236a5b`; 112-113 K1
- [fastapi-reviewer](fastapi-reviewer.md): `d8704e52fda045fa72cfc51de7937aa4e313b2161279ff8e11d878f6ab8a0d81`; none
- [flutter-reviewer](flutter-reviewer.md): `26a78d27db9a035204c9c517314c880a5ea4419500da319acdb643b84d59b0b8`; 251-252 K1; 15108 bytes: read by outline
- [fsharp-reviewer](fsharp-reviewer.md): `24200e4814ddbdb32ed2eeb5b6aecabbb3d655d5ba0de7b2a054638fe12e7c5a`; 104-106 K1
- [gan-evaluator](gan-evaluator.md): `e5c8e6ab245ce97502472ae5223e529cc3d1c4c84527f4c19bcca3d362513322`; none
- [gan-generator](gan-generator.md): `52411e8bb705284ef0be36a86b9df69d7365cda84a2780d5e3c2d64e6019a352`; none
- [gan-planner](gan-planner.md): `852f8ac7cc1761186ec6f48e1b1be65cc32307a182062e0cebb84aae2d3ca901`; none
- [go-build-resolver](go-build-resolver.md): `fa191d2a3c66915402b343a8f2da21090bb330968e62a8615739acccfce90424`; 102-103 K1
- [go-reviewer](go-reviewer.md): `be174fc66f6be1ade25f496548ba7040c00894aec81da163863b046d44233e39`; 84-85 K1
- [harmonyos-app-resolver](harmonyos-app-resolver.md): `2385d05160744130f6f5fadbae0314a7500db92da13719779dac41eb53ae1202`; 181-182 K1
- [harness-optimizer](harness-optimizer.md): `54444fd46afdfacb87a885bef4dcef129915740d35b5fe6f07a5a7e804f2b053`; 23-24 K1; 29-32 K1; 37-40 K1; 48-55 K1
- [healthcare-reviewer](healthcare-reviewer.md): `ffe0855862276f94bd47fbbdeba0d233b7ca2c8647bce784c94f61c382e3cc69`; none
- [homelab-architect](homelab-architect.md): `d851727c8d07d2c44ea953d1ccab812865de3ba4b693d0392e86ba52187664bc`; none
- [java-build-resolver](java-build-resolver.md): `6dc1da9c6ac9f39671dcf1013a8e8ab30cccf3604808d7da1b0a21935c1ac537`; 272-275 K1
- [java-reviewer](java-reviewer.md): `e768811020978d62930e8a1de33d674f07fbd479073de570df57c143b8eb33b6`; 187-190 K1; 13156 bytes: read by outline
- [kotlin-build-resolver](kotlin-build-resolver.md): `db6796bdc2294d795bac286f7c04f4e6048af8acb3faf80edfc110285172e16b`; 126-127 K1
- [kotlin-reviewer](kotlin-reviewer.md): `be82de3435c4b7b48e4ff9589e8c211d80fafa5c8c9ac98d6572c88004519858`; none
- [loop-operator](loop-operator.md): `51f8283a56b799c2bd2c2455b3480e949656cbf997ea2feb34a972d3d6400f22`; none
- [marketing-agent](marketing-agent.md): `9d9cdcde2f90ba36ac488065beaa4fc3b74ff5a91507e504b9ea2cc608213cf8`; 40 K1; 70-71 K1; 152-159 K1
- [mle-reviewer](mle-reviewer.md): `c505be5fccea9d067775b86fed76bc4b84e63e17090855ac135694adbc83a7f8`; 161-162 K1
- [network-architect](network-architect.md): `1b434aa8496a1cb8c39add08d0c68a4b27af8378de725f370d7682c02a56997e`; none
- [network-config-reviewer](network-config-reviewer.md): `12b2b04d8235941f6a9a0d42a679c581ce89963172d5fb0f63abb4202521593f`; none
- [network-troubleshooter](network-troubleshooter.md): `64528c41b59eea2cb4ac642bd3197bbadc8c456f3601520e410cf606e848fb07`; none
- [opensource-forker](opensource-forker.md): `3cbe7f04a15fe67355ded13103e3b961c51678ba93c2db1b25b4f88aa0a3dee6`; none
- [opensource-packager](opensource-packager.md): `996f528ac789b3c19ded6bf7c25217a3e9e7c1e6d320a4f9d69f17252815cb16`; none
- [opensource-sanitizer](opensource-sanitizer.md): `89bee8676c1004b4b88d0513edda1835c3738503ba7fbef07b55bf9ba12a347b`; none; 18093 bytes: read by outline
- [performance-optimizer](performance-optimizer.md): `76d00a70fcc07a0b207f6b517d54078fa7a59f29e157fea72bf5f1d9cab8f9b2`; none; 13397 bytes: read by outline
- [planner](planner.md): `63aba865206bac9cb5887542fb01b97656e7701faff98e091aa77057ba9860bc`; none
- [pr-test-analyzer](pr-test-analyzer.md): `5432aaf7e5fcb0813ac21828382971cc00f17d56ee95eac6d0ce180fc5d58016`; none
- [python-reviewer](python-reviewer.md): `d2180b115f5840383268c13d5d075b0541fe7ef2a1ac8ecd5d835266ca1b27ce`; none
- [pytorch-build-resolver](pytorch-build-resolver.md): `5ec08de6c6b616b068e7075be4496edd3e4ef3b041f0095a2e073131a58a9f7c`; none
- [rag-pipeline-reviewer](rag-pipeline-reviewer.md): `793432a0c4e44aa4c640cb85ec24b47062ed044782852b0ba67323d860154fec`; none
- [react-build-resolver](react-build-resolver.md): `a29dec6de18ac3d7b65c746f8133c1f14de5886592fa340c5c2a62fe7c4584e0`; 209-215 K1
- [react-reviewer](react-reviewer.md): `17d0286b4f101e27b818cad026a6bfc1f9fd3e7f9b52c8414e6ea2a05481995a`; 34-35 M; 158-164 K1
- [refactor-cleaner](refactor-cleaner.md): `13704c3aee163bcbf6bcbf7a7933630a70d6c312ff3ee5a29bff63b8800484cc`; none
- [ruby-reviewer](ruby-reviewer.md): `3ba715e19b0f776fbd63128f6f79a0c2c0e846896ce1c20f603dc8f5971e5d0c`; 108-109 K1
- [rust-build-resolver](rust-build-resolver.md): `78c75c6be38ff376963b3c5b26d60dce0491064481d1a61e842a6d2879534e82`; 156-157 K1
- [rust-reviewer](rust-reviewer.md): `10af67c5764677596d43f32a952d8ec28662bb353fd986d726daefd3382ebeca`; 102-103 K1
- [security-reviewer](security-reviewer.md): `813e4062bed5f42ab25dd02a0070f682058ffe9508198fcfdbb2c31296f93b7b`; 113-114 K1
- [seo-specialist](seo-specialist.md): `40a66d601113669585cf6abbf4c9ae2bf134ef23ffdb78c45223733dbde90a2c`; 70-71 K1
- [silent-failure-hunter](silent-failure-hunter.md): `e5e2094c6f50cc515a77376331c78e4955d5ff16c7a0e5d8f6edec692b7ebd8d`; none
- [spec-miner](spec-miner.md): `a9270c2012e2dc979f153a481cdfdc7c5413e8774f579ada0319c00ea8903ba2`; none; 15059 bytes: read by outline
- [swift-build-resolver](swift-build-resolver.md): `219e9e37151e385c0eae69b28306897e2a21ba1dbad5ed3077801c822c98b156`; 169-170 K1
- [swift-reviewer](swift-reviewer.md): `b8de7f16fafef82645aca3923b0c4fdbe619433c5df9386b3737fb6591545e8b`; 114-115 K1
- [tdd-guide](tdd-guide.md): `979afbb40c42bfdd02fc308c130d7e257f5d6dd5f6531ef2562644862f6b7771`; 89-90 K1
- [type-design-analyzer](type-design-analyzer.md): `753908aadd759d4710e07ac1a0ba8a6fbc0bc35fe369cadd3ede9655da5d1c49`; none
- [typescript-reviewer](typescript-reviewer.md): `6b012db1a9039870c4f040975144a0d4e3592510d6332e2d260f02859ec66da1`; 80-81 K1; 118-121 K1
- [vue-reviewer](vue-reviewer.md): `c675814544f06703cf34347c24c630267073d6ee605e70820fc1c1a74e71358a`; 36-37 M; 197-203 K1; 14827 bytes: read by outline
