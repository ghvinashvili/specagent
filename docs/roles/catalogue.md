# Role catalogue

What a role session loads, in bytes and tokens (about four bytes per token of English Markdown), as printed by
`python3 -I .claude/skills/running-specagent-pipelines/scripts/manager/catalogue.py table` on the tree of the commit
that last changed this page (`git log -1 --format=%h -- docs/roles/catalogue.md`). The bounds the manager chooses by: a
role's start-up prefix within 10,000 tokens, near up to 13,000, over above (manager spec 3.8); an item half the
sessions of a type use only up to 2,500 tokens (`over` in the `half-use` column). How the numbers are used: the
pipeline skill's `references/choosing-roles-and-skills.md`. No column names a model: the model is each role's setting,
which no role reads.

### type (21)
| name | bytes | tokens | half-use |
| --- | ---: | ---: | --- |
| advisor | 3748 | 937 |  |
| analyst | 5519 | 1380 |  |
| classifier | 2789 | 697 |  |
| comparator | 3888 | 972 |  |
| critic | 14154 | 3539 | over |
| judge | 6955 | 1739 |  |
| librarian | 7002 | 1751 |  |
| manager | 10797 | 2699 | over |
| plan-fixer | 1998 | 500 |  |
| planner | 15229 | 3807 | over |
| quarantine-reader | 3532 | 883 |  |
| reader | 11842 | 2961 | over |
| researcher | 5782 | 1446 |  |
| spec-writer | 6592 | 1648 |  |
| story-writer | 5019 | 1255 |  |
| synthesizer | 5040 | 1260 |  |
| test-verifier | 6719 | 1680 |  |
| translator | 1637 | 409 |  |
| validator | 6369 | 1592 |  |
| verifier | 11965 | 2991 | over |
| writer | 11785 | 2946 | over |
| total | 148361 | 37090 |  |

### contract (21)
| name | bytes | tokens | half-use |
| --- | ---: | ---: | --- |
| advisor | 598 | 150 |  |
| analyst | 745 | 186 |  |
| classifier | 562 | 141 |  |
| comparator | 642 | 161 |  |
| critic | 1225 | 306 |  |
| judge | 826 | 207 |  |
| librarian | 784 | 196 |  |
| manager | 182 | 46 |  |
| plan-fixer | 488 | 122 |  |
| planner | 1639 | 410 |  |
| quarantine-reader | 724 | 181 |  |
| reader | 1986 | 497 |  |
| researcher | 781 | 195 |  |
| spec-writer | 860 | 215 |  |
| story-writer | 637 | 159 |  |
| synthesizer | 652 | 163 |  |
| test-verifier | 714 | 179 |  |
| translator | 465 | 116 |  |
| validator | 627 | 157 |  |
| verifier | 1270 | 318 |  |
| writer | 1798 | 450 |  |
| total | 18205 | 4551 |  |

### brief (12)
| name | bytes | tokens | half-use |
| --- | ---: | ---: | --- |
| builder-a-assignment | 5641 | 1410 |  |
| builder-b-assignment | 5641 | 1410 |  |
| common | 11941 | 2985 | over |
| critic-assignment | 5682 | 1421 |  |
| first-pass-rules | 2192 | 548 |  |
| handoff-rule | 3428 | 857 |  |
| judge-assignment | 8012 | 2003 |  |
| launch | 2734 | 684 |  |
| lessons | 5190 | 1298 |  |
| plan-fixer-assignment | 6454 | 1614 |  |
| planner-assignment | 9334 | 2334 |  |
| verifier-assignment | 6443 | 1611 |  |
| total | 72692 | 18173 |  |

### skill (27)
| name | bytes | tokens | half-use |
| --- | ---: | ---: | --- |
| adr | 744 | 186 |  |
| agent-eval | 4383 | 1096 |  |
| agent-security-hardening | 10152 | 2538 | over |
| agent-self-evaluation | 7236 | 1809 |  |
| checkpoint | 1298 | 325 |  |
| commit-style | 772 | 193 |  |
| conventional-commit-review | 4397 | 1099 |  |
| council | 1493 | 373 |  |
| cpp-coding-standards | 2188 | 547 |  |
| cpp-testing | 9161 | 2290 |  |
| doc-gardening | 628 | 157 |  |
| docs-governance | 3777 | 944 |  |
| escalate | 1382 | 346 |  |
| eval-harness | 6491 | 1623 |  |
| handoff | 546 | 137 |  |
| intake | 1630 | 408 |  |
| loop-tick | 1353 | 338 |  |
| new-role-type | 1273 | 318 |  |
| postgres-patterns | 3407 | 852 |  |
| python-patterns | 1358 | 340 |  |
| python-testing | 1384 | 346 |  |
| release | 729 | 182 |  |
| resume-stage | 2097 | 524 |  |
| run-stage | 5675 | 1419 |  |
| running-specagent-pipelines | 11973 | 2993 | over |
| spec | 623 | 156 |  |
| wiki-ingest | 1535 | 384 |  |
| total | 87685 | 21921 |  |

### description (27)
| name | bytes | tokens | half-use |
| --- | ---: | ---: | --- |
| adr | 139 | 35 |  |
| agent-eval | 144 | 36 |  |
| agent-security-hardening | 150 | 38 |  |
| agent-self-evaluation | 134 | 34 |  |
| checkpoint | 146 | 37 |  |
| commit-style | 121 | 30 |  |
| conventional-commit-review | 144 | 36 |  |
| council | 146 | 37 |  |
| cpp-coding-standards | 141 | 35 |  |
| cpp-testing | 144 | 36 |  |
| doc-gardening | 142 | 36 |  |
| docs-governance | 142 | 36 |  |
| escalate | 149 | 37 |  |
| eval-harness | 148 | 37 |  |
| handoff | 138 | 35 |  |
| intake | 147 | 37 |  |
| loop-tick | 138 | 35 |  |
| new-role-type | 144 | 36 |  |
| postgres-patterns | 150 | 38 |  |
| python-patterns | 145 | 36 |  |
| python-testing | 137 | 34 |  |
| release | 145 | 36 |  |
| resume-stage | 135 | 34 |  |
| run-stage | 146 | 37 |  |
| running-specagent-pipelines | 148 | 37 |  |
| spec | 144 | 36 |  |
| wiki-ingest | 141 | 35 |  |
| total | 3848 | 962 |  |

### ecc (70)
| name | bytes | tokens | half-use |
| --- | ---: | ---: | --- |
| a11y-architect | 7119 | 1780 |  |
| agent-evaluator | 8760 | 2190 |  |
| architect | 7240 | 1810 |  |
| bengali-reviewer | 10996 | 2749 | over |
| build-error-resolver | 4692 | 1173 |  |
| chief-of-staff | 6331 | 1583 |  |
| code-architect | 2481 | 620 |  |
| code-explorer | 2547 | 637 |  |
| code-reviewer | 13833 | 3458 | over |
| code-simplifier | 2208 | 552 |  |
| comment-analyzer | 1997 | 499 |  |
| commit-reviewer | 4441 | 1110 |  |
| conversation-analyzer | 2404 | 601 |  |
| cpp-build-resolver | 4051 | 1013 |  |
| cpp-reviewer | 3928 | 982 |  |
| csharp-reviewer | 5538 | 1385 |  |
| dart-build-resolver | 7528 | 1882 |  |
| database-reviewer | 5072 | 1268 |  |
| django-build-resolver | 9329 | 2332 |  |
| django-reviewer | 7730 | 1933 |  |
| doc-updater | 4320 | 1080 |  |
| docs-lookup | 4473 | 1118 |  |
| e2e-runner | 4855 | 1214 |  |
| fastapi-reviewer | 3470 | 868 |  |
| flutter-reviewer | 15108 | 3777 | over |
| fsharp-reviewer | 5462 | 1366 |  |
| gan-evaluator | 8491 | 2123 |  |
| gan-generator | 5834 | 1459 |  |
| gan-planner | 4457 | 1114 |  |
| go-build-resolver | 4107 | 1027 |  |
| go-reviewer | 3647 | 912 |  |
| harmonyos-app-resolver | 9235 | 2309 |  |
| harness-optimizer | 2462 | 616 |  |
| healthcare-reviewer | 4268 | 1067 |  |
| homelab-architect | 4473 | 1118 |  |
| java-build-resolver | 11991 | 2998 | over |
| java-reviewer | 13156 | 3289 | over |
| kotlin-build-resolver | 5067 | 1267 |  |
| kotlin-reviewer | 7635 | 1909 |  |
| loop-operator | 1853 | 463 |  |
| marketing-agent | 6675 | 1669 |  |
| mle-reviewer | 10175 | 2544 | over |
| network-architect | 4791 | 1198 |  |
| network-config-reviewer | 4319 | 1080 |  |
| network-troubleshooter | 4254 | 1064 |  |
| opensource-forker | 7991 | 1998 |  |
| opensource-packager | 7884 | 1971 |  |
| opensource-sanitizer | 18093 | 4523 | over |
| performance-optimizer | 13397 | 3349 | over |
| planner | 8019 | 2005 |  |
| pr-test-analyzer | 1893 | 473 |  |
| python-reviewer | 4347 | 1087 |  |
| pytorch-build-resolver | 6442 | 1611 |  |
| rag-pipeline-reviewer | 6205 | 1551 |  |
| react-build-resolver | 10880 | 2720 | over |
| react-reviewer | 10820 | 2705 | over |
| refactor-cleaner | 3629 | 907 |  |
| ruby-reviewer | 7409 | 1852 |  |
| rust-build-resolver | 6719 | 1680 |  |
| rust-reviewer | 5532 | 1383 |  |
| security-reviewer | 5276 | 1319 |  |
| seo-specialist | 2705 | 676 |  |
| silent-failure-hunter | 1945 | 486 |  |
| spec-miner | 15059 | 3765 | over |
| swift-build-resolver | 7000 | 1750 |  |
| swift-reviewer | 7065 | 1766 |  |
| tdd-guide | 3723 | 931 |  |
| type-design-analyzer | 1843 | 461 |  |
| typescript-reviewer | 8416 | 2104 |  |
| vue-reviewer | 14827 | 3707 | over |
| total | 459922 | 114981 |  |
