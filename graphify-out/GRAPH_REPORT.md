# Graph Report - EveUnleashed  (2026-11-09)

## Corpus Check
- 150 files · ~0 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2742 nodes · 6091 edges · 131 communities (107 shown, 24 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 151 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Failure Telemetry + Live Server
- Eve CLI Commands
- Replay Cython Kernel
- Decision Engine
- Replay Module
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 123
- Community 124
- Community 125
- Community 127
- Community 128
- Community 129
- Community 130

## God Nodes (most connected - your core abstractions)
1. `note_failure()` - 135 edges
2. `main()` - 41 edges
3. `InferenceEngine` - 37 edges
4. `__pyx_pymod_exec__forensic_cy()` - 25 edges
5. `__pyx_pymod_exec__replay_cy()` - 25 edges
6. `ShapeStore` - 25 edges
7. `EveInterpreterBridge` - 24 edges
8. `ModelRegistry` - 22 edges
9. `ModelLoader` - 21 edges
10. `GoRunner` - 20 edges

## Surprising Connections (you probably didn't know these)
- `therapy_prompt()` --calls--> `build_prompt()`  [INFERRED]
  Project_LUCY/lucy.py → src/eve_unleashed/therapy.py
- `therapy_response()` --calls--> `fallback_response()`  [INFERRED]
  Project_LUCY/lucy.py → src/eve_unleashed/therapy.py
- `test_run_code_javascript_inline()` --calls--> `run_code()`  [EXTRACTED]
  tests/test_polyglot_shards.py → src/INTERPRETERS/__init__.py
- `test_bash_runs_after_fix()` --uses--> `ShRunner`  [INFERRED]
  tests/test_sh_runner_paths.py → src/INTERPRETERS/sh_runner.py
- `test_route_lang_spends_budgets()` --calls--> `route_lang()`  [INFERRED]
  tests/test_polyglot_shards.py → src/SHARDS/registry.py

## Import Cycles
- None detected.

## Communities (131 total, 24 thin omitted)

### Community 0 - "Failure Telemetry + Live Server"
Cohesion: 0.00
Nodes (34): note_failure(), instruction_injections(), note_failure(), oversized(), path_escapes(), run_suite(), section_spoofs(), _try_instruction() (+26 more)

### Community 1 - "Eve CLI Commands"
Cohesion: 0.00
Nodes (34): cmd_ablate(), cmd_bypass(), cmd_cognition(), cmd_cradle(), cmd_debunk(), cmd_factcheck(), cmd_forge(), cmd_foundry() (+26 more)

### Community 2 - "Replay Cython Kernel"
Cohesion: 0.00
Nodes (60): __Pyx_as_CyFunctionObject_safe(), __Pyx_CyFunction_annotate_impl(), __Pyx_CyFunction_Call(), __Pyx_CyFunction_CallAsMethod(), __Pyx_CyFunction_CallMethod(), __Pyx__CyFunction_clear(), __Pyx__CyFunction_dealloc(), __Pyx_CyFunction_get_annotate() (+52 more)

### Community 4 - "Decision Engine"
Cohesion: 0.00
Nodes (13): _attach_utility(), AutonomousDecisionEngine, AutonomyLevel, Decision, DecisionStatus, note_failure(), ConversationalKLINK, Intent (+5 more)

### Community 5 - "Replay Module"
Cohesion: 0.00
Nodes (48): PyInit__replay_cy(), __Pyx_check_binary_version(), __Pyx_CheckVectorcallKwarg(), __pyx_CommonTypesMetaclass_call(), __pyx_CommonTypesMetaclass_get_module(), __pyx_CommonTypesMetaclass_init(), __pyx_CommonTypesMetaclass_setattr(), __Pyx_CreateCodeObjects() (+40 more)

### Community 6 - "Community 6"
Cohesion: 0.00
Nodes (51): __Pyx_as_CyFunctionObject_safe(), __Pyx_CyFunction_annotate_impl(), __Pyx__CyFunction_clear(), __Pyx__CyFunction_dealloc(), __Pyx_CyFunction_get_annotate(), __Pyx_CyFunction_get_annotate_from_dict_if_exists(), __Pyx_CyFunction_get_annotations(), __Pyx_CyFunction_get_annotations_locked() (+43 more)

### Community 7 - "Community 7"
Cohesion: 0.00
Nodes (27): audit(), _exercised(), nexus(), paradigm(), _src_root(), affect(), consolidate(), counterfactual_replay() (+19 more)

### Community 8 - "Community 8"
Cohesion: 0.00
Nodes (5): cmd_benchmark(), BatchResult, InferenceResult, InferenceEngine, note_failure()

### Community 9 - "Community 9"
Cohesion: 0.00
Nodes (9): EvolutionaryWormManager, GeneticAlgorithm, note_failure(), splice_hunches(), WormDNA, WormFitness, load_or_seed(), load_pop() (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.00
Nodes (24): PyInit__forensic_cy(), __Pyx_check_binary_version(), __pyx_CommonTypesMetaclass_init(), __Pyx_CreateCodeObjects(), __Pyx_DecompressString_LZSS(), __Pyx_get_runtime_version(), __Pyx_init_co_variables(), __Pyx_init_runtime_version() (+16 more)

### Community 11 - "Community 11"
Cohesion: 0.00
Nodes (7): ComponentModel, GoalSetting, ImprovementGoal, IntrospectionLoop, note_failure(), Reflection, SelfModel

### Community 12 - "Community 12"
Cohesion: 0.00
Nodes (16): propagate(), residual_report(), root_audit(), sha_file(), funnel_proof(), verify_funnel(), fault_stats(), moore_efficiency() (+8 more)

### Community 13 - "Community 13"
Cohesion: 0.00
Nodes (37): __pyx_atomic_pointer_cmp_exchange(), __Pyx_CyFunction_SetAnnotationsDict(), __Pyx_CyFunction_SetDefaultsKwDict(), __Pyx_CyFunction_SetDefaultsTuple(), __Pyx_CyOrPyCFunction_GET_SELF(), __Pyx_get_object_dict_version(), __Pyx_get_tp_dict_version(), __Pyx_GetKwValue_FASTCALL() (+29 more)

### Community 14 - "Community 14"
Cohesion: 0.00
Nodes (10): _discover_available(), get_router(), ModelRouter, note_failure(), route_query(), RouteDecision, FixProposal, HealStats (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.00
Nodes (9): apply_rotary_pos_emb(), Qwen35Attention, Qwen35DecoderLayer, Qwen35MLP, Qwen35SSM, Qwen35SSMConfig, RMSNorm, RotaryEmbedding (+1 more)

### Community 16 - "Community 16"
Cohesion: 0.00
Nodes (9): cmd_list_models(), cmd_run(), _check_xpu_available(), _import_ok(), ModelLoader, _module_installed(), note_failure(), list_cradle_models() (+1 more)

### Community 17 - "Community 17"
Cohesion: 0.00
Nodes (3): EveInterpreterBridge, get_eve_interpreter_bridge(), note_failure()

### Community 19 - "Community 19"
Cohesion: 0.00
Nodes (21): _memory_rungs(), _archive_fallback(), _archive_urls(), _cc_extract(), _cc_pick(), _cc_try_crawl(), _commoncrawl_fetch(), _crossref() (+13 more)

### Community 20 - "Community 20"
Cohesion: 0.00
Nodes (11): CLOCKZ, DISKZ, Forecast, _forecast_value(), _linear_regression(), NETWORXZ, note_failure(), PredictiveWorm (+3 more)

### Community 21 - "Community 21"
Cohesion: 0.00
Nodes (13): _bash_flavor(), main(), note_failure(), ShResult, ShRunner, _to_bash_path(), test_bash_runs_after_fix(), test_both_prefix_forms_map_to_msys() (+5 more)

### Community 22 - "Community 22"
Cohesion: 0.00
Nodes (4): GoResult, GoRunner, main(), note_failure()

### Community 23 - "Community 23"
Cohesion: 0.00
Nodes (18): _blocks(), _clean(), _counts(), engram_records(), _fields(), flush(), _first_paragraph(), harvest() (+10 more)

### Community 24 - "Community 24"
Cohesion: 0.00
Nodes (15): cmd_train(), emit(), _capped(), effective_confidence(), _ensure_fixture(), freeze_fixture(), LillithTuner, _load_fixture() (+7 more)

### Community 25 - "Community 25"
Cohesion: 0.00
Nodes (28): __pyx_atomic_pointer_cmp_exchange(), __Pyx_CyFunction_SetAnnotationsDict(), __Pyx_CyFunction_SetDefaultsKwDict(), __Pyx_CyFunction_SetDefaultsTuple(), __Pyx_get_object_dict_version(), __Pyx_get_tp_dict_version(), __Pyx_GetKwValue_FASTCALL(), __Pyx_IgnoreGivenException() (+20 more)

### Community 26 - "Community 26"
Cohesion: 0.00
Nodes (18): cmd_check(), cmd_inject(), cmd_install(), cmd_render(), cmd_verify(), current_block(), hooks_path(), inject() (+10 more)

### Community 28 - "Community 28"
Cohesion: 0.00
Nodes (14): main(), note_failure(), run_bash(), run_code(), run_go(), run_javascript(), run_powershell(), run_python() (+6 more)

### Community 29 - "Community 29"
Cohesion: 0.00
Nodes (27): __Pyx_AddTraceback(), __Pyx_ArgTypeError(), __Pyx_ArgTypeTest(), __Pyx_CLineForTraceback(), __Pyx_CyFunction_InitDefaults(), __Pyx_ErrFetchInState(), __Pyx_ErrRestoreInState(), __pyx_f_13eve_unleashed_12_forensic_cy__bfs() (+19 more)

### Community 30 - "Community 30"
Cohesion: 0.00
Nodes (17): check(), check_arch(), detect(), fix(), fmt(), have_tools(), _repo_root(), _run() (+9 more)

### Community 31 - "Community 31"
Cohesion: 0.00
Nodes (16): _canon_rules(), _command_target_exists(), drift_message(), _glossary_problems(), load_base(), load_theme(), main(), _reference_index() (+8 more)

### Community 32 - "Community 32"
Cohesion: 0.00
Nodes (7): timed_inference(), note_failure(), postprocess_output(), prepare_input_tensor(), softmax(), top_k(), validate_input_shape()

### Community 33 - "Community 33"
Cohesion: 0.00
Nodes (12): cmd_transmute(), write_tutorial(), lock_receipts(), note_failure(), open_inquest(), draft_rebuttal(), prove_case(), grievance_into_dossier() (+4 more)

### Community 34 - "Community 34"
Cohesion: 0.00
Nodes (13): _config_problems(), CorpusError, declared_domains(), harvest_ids(), _paths_in(), _practice_problems(), _prose_block_problems(), _provenance_problems() (+5 more)

### Community 35 - "Community 35"
Cohesion: 0.00
Nodes (12): _probe_work_tier(), check_doc_shards(), main(), prune_build_dirs(), run_shard(), self_test(), supported_shard_langs(), sweep() (+4 more)

### Community 36 - "Community 36"
Cohesion: 0.00
Nodes (12): build_wasm(), build_wasm_go(), generate(), generate_go(), _go_root(), have_toolchain(), parse_ablation_log(), run_wasm() (+4 more)

### Community 37 - "Community 37"
Cohesion: 0.00
Nodes (4): main(), note_failure(), PwshResult, PwshRunner

### Community 38 - "Community 38"
Cohesion: 0.00
Nodes (13): _align(), build_all(), build_gguf(), dequantize_q40(), dequantize_q80(), note_failure(), _pack_kv(), _pack_str() (+5 more)

### Community 40 - "Community 40"
Cohesion: 0.00
Nodes (13): _antibody_specs(), antibody_status(), _load_store(), main(), promote_antibody(), record_seek(), run_antibody(), _save_store() (+5 more)

### Community 41 - "Community 41"
Cohesion: 0.00
Nodes (4): main(), NodeResult, NodeRunner, note_failure()

### Community 42 - "Community 42"
Cohesion: 0.00
Nodes (11): build_parser(), cmd_berzerker(), cmd_cradle(), cmd_doctor(), cmd_eve(), cmd_inject(), cmd_lilith(), cmd_lucy() (+3 more)

### Community 43 - "Community 43"
Cohesion: 0.00
Nodes (13): cmd_locker(), custody(), ingest_file(), ingest_receipt(), ingest_text(), _ldir(), list_items(), _log() (+5 more)

### Community 44 - "Community 44"
Cohesion: 0.00
Nodes (21): __Pyx_copy_object_array(), __Pyx_is_valid_index(), __Pyx__ListComp_AppendAndDecref(), __Pyx_MatchKeywordArg(), __Pyx_MatchKeywordArg_nostr(), __Pyx_MatchKeywordArg_str(), __Pyx_ParseKeywordDict(), __Pyx_ParseKeywordDictToDict() (+13 more)

### Community 45 - "Community 45"
Cohesion: 0.00
Nodes (7): guard_llm_call(), PromptGuard, sanitize_prompt(), ThreatDetection, ThreatLevel, validate_response(), ValidationResult

### Community 46 - "Community 46"
Cohesion: 0.00
Nodes (9): ablate_prompt(), classify(), cmd_unleash(), morph_markdown(), fallback_response(), build_vessel(), dispatch(), matrix() (+1 more)

### Community 47 - "Community 47"
Cohesion: 0.00
Nodes (9): describe(), digest(), load_ship(), mcml_proof(), rebuild(), replicate(), Sequential, ship() (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.00
Nodes (19): __Pyx_ArgTypeError(), __Pyx_ArgTypeTest(), __Pyx_CyFunction_Init(), __Pyx_CyFunction_InitDefaults(), __Pyx_CyFunction_New(), __Pyx_FetchCommonTypeFromSpec(), __Pyx_Get_CyFunction_Type(), __Pyx_InBases() (+11 more)

### Community 49 - "Community 49"
Cohesion: 0.00
Nodes (4): _estimate_size(), _hash_inputs(), InferenceCache, note_failure()

### Community 50 - "Community 50"
Cohesion: 0.00
Nodes (8): note_failure(), stream_gguf(), _generate(), stream_native(), stream_transformers(), _generate(), StreamResult, StreamToken

### Community 51 - "Community 51"
Cohesion: 0.00
Nodes (20): __Pyx_CyFunction_get_is_coroutine(), __Pyx_CyFunction_get_is_coroutine_value(), __Pyx_LargePyLong___Pyx_PyLong_As_int(), __Pyx_NewRef(), __Pyx_NonPyLong___Pyx_PyLong_As_long(), __Pyx_Owned_Py_None(), __Pyx_PyBool_FromLong(), __Pyx_PyLong_As_long() (+12 more)

### Community 52 - "Community 52"
Cohesion: 0.00
Nodes (20): __Pyx_CyFunction_get_is_coroutine(), __Pyx_CyFunction_get_is_coroutine_value(), __Pyx_LargePyLong___Pyx_PyLong_As_long(), __Pyx_NewRef(), __Pyx_NonPyLong___Pyx_PyLong_As_long(), __Pyx_Owned_Py_None(), __Pyx_PyBool_FromLong(), __Pyx_PyLong_As_long() (+12 more)

### Community 53 - "Community 53"
Cohesion: 0.00
Nodes (4): EveLlamaService, LlamaServerManager, note_failure(), _resolve_paths()

### Community 54 - "Community 54"
Cohesion: 0.00
Nodes (6): atomic_write_bytes(), atomic_write_json(), file_lock(), note_failure(), _thread_lock_for(), _atomic_write_json()

### Community 55 - "Community 55"
Cohesion: 0.00
Nodes (4): distill_to_insights(), MemoryImportance, note_failure(), PamSEvolution

### Community 56 - "Community 56"
Cohesion: 0.00
Nodes (5): assemble_swarm(), ferment(), ferment_shard(), separate(), transsubstantiate()

### Community 57 - "Community 57"
Cohesion: 0.00
Nodes (10): adopt_cradle(), _free_port(), _llama_server_candidates(), note_failure(), _probe_direct(), _probe_gguf(), run_gguf(), _load_verifier() (+2 more)

### Community 58 - "Community 58"
Cohesion: 0.00
Nodes (6): adaptive_expansion(), _counts(), _git(), main(), _show(), _staged_py_files()

### Community 59 - "Community 59"
Cohesion: 0.00
Nodes (11): code_coach(), mind(), _toolchain(), weird_tests(), test_builder_gets_weird_tests_and_level_line(), test_coach_scrubs_contact_details(), test_code_coach_rejects_unknown_lang_and_level(), test_code_coach_scaffolds_python_spark() (+3 more)

### Community 60 - "Community 60"
Cohesion: 0.00
Nodes (10): CleanupRecommendation, _default_box_roots(), discover_checkouts(), EmbeddedInfo, InstallInfo, _origin(), _probe_stale_fallback(), PythonInfo (+2 more)

### Community 61 - "Community 61"
Cohesion: 0.00
Nodes (8): cast_projection(), conjoin(), morph_shard(), morph_store(), recall_host(), ShapeStore, write_projection(), melee()

### Community 62 - "Community 62"
Cohesion: 0.00
Nodes (16): __Pyx_copy_object_array(), __Pyx_DecompressString(), __Pyx_is_valid_index(), __Pyx_MatchKeywordArg(), __Pyx_MatchKeywordArg_nostr(), __Pyx_MatchKeywordArg_str(), __Pyx_ParseKeywordDict(), __Pyx_ParseKeywordDictToDict() (+8 more)

### Community 63 - "Community 63"
Cohesion: 0.00
Nodes (12): __pyx_atomic_int_cmp_exchange(), __pyx_bisect_code_objects(), __Pyx_CachedCFunction_GetAndSetInitializing(), __Pyx_CachedCFunction_SetFinishedInitializing(), __Pyx_CallUnboundCMethod0(), __Pyx_CallUnboundCMethod2(), __pyx__find_code_object(), __pyx__insert_code_object() (+4 more)

### Community 64 - "Community 64"
Cohesion: 0.00
Nodes (12): __pyx_atomic_int_cmp_exchange(), __pyx_bisect_code_objects(), __Pyx_CachedCFunction_GetAndSetInitializing(), __Pyx_CachedCFunction_SetFinishedInitializing(), __Pyx_CallUnboundCMethod0(), __Pyx_CallUnboundCMethod2(), __pyx__find_code_object(), __pyx__insert_code_object() (+4 more)

### Community 65 - "Community 65"
Cohesion: 0.00
Nodes (10): check(), _drift(), edition_path(), generated_drift(), import_graph(), _label(), load(), main() (+2 more)

### Community 66 - "Community 66"
Cohesion: 0.00
Nodes (13): __Pyx_CheckVectorcallKwarg(), __pyx_CommonTypesMetaclass_call(), __pyx_CommonTypesMetaclass_get_module(), __pyx_CommonTypesMetaclass_setattr(), __Pyx_KwargsAsDict_FASTCALL(), __pyx_m_clear(), __Pyx_ModuleStateLookup_wait_until_no_readers(), __Pyx_State_AddModule() (+5 more)

### Community 67 - "Community 67"
Cohesion: 0.00
Nodes (8): _bake_lane(), note_failure(), plan(), record_fix(), scan(), _scan_raw(), turf_of(), verify()

### Community 68 - "Community 68"
Cohesion: 0.00
Nodes (10): note_failure(), search_dockets(), add_watch(), check_watches(), _load_watchlist(), note_failure(), remove_watch(), _save_watchlist() (+2 more)

### Community 69 - "Community 69"
Cohesion: 0.00
Nodes (4): aether_verify(), golden_digest(), golden_tensor(), replicate_golden()

### Community 71 - "Community 71"
Cohesion: 0.00
Nodes (5): bfs_distances(), diameter(), girth(), mutate_shape(), transmogrify()

### Community 73 - "Community 73"
Cohesion: 0.00
Nodes (4): note_failure(), create_qwen35_model(), note_failure(), Qwen35ForCausalLM

### Community 74 - "Community 74"
Cohesion: 0.00
Nodes (9): apply_best(), apply_mod(), _backup(), evolve_mod(), _patch_json(), _patch_kv(), _read_mod(), revert_mod() (+1 more)

### Community 75 - "Community 75"
Cohesion: 0.00
Nodes (3): _guess_framework_ext(), convert_text(), mutate_file()

### Community 77 - "Community 77"
Cohesion: 0.00
Nodes (3): cmd_registry(), cmd_serve(), get_registry()

### Community 78 - "Community 78"
Cohesion: 0.00
Nodes (6): check_self_contradiction(), debunk_claim(), extract_propositions(), flag_fallacies(), _has_any(), _sentences()

### Community 80 - "Community 80"
Cohesion: 0.00
Nodes (6): fallback_reason(), pair_columns(), py_score(), rung_rates(), _rung_to_int(), score_columns()

### Community 81 - "Community 81"
Cohesion: 0.00
Nodes (5): _ground(), test_bout_is_merit_not_mood(), test_judge_shapes_match_throw_order(), test_rock_needs_the_grounding_script(), test_spock_refuses_clinician_language()

### Community 82 - "Community 82"
Cohesion: 0.00
Nodes (6): judge_lizard(), judge_paper(), judge_rock(), judge_scissors(), judge_spock(), _words()

### Community 83 - "Community 83"
Cohesion: 0.00
Nodes (6): extract_entities(), factcheck_claim(), fetch_url(), loc_lookup(), note_failure(), wikipedia_lookup()

### Community 84 - "Community 84"
Cohesion: 0.00
Nodes (12): __Pyx_CyFunction_Call(), __Pyx_CyFunction_CallAsMethod(), __Pyx_CyFunction_CallMethod(), __Pyx_CyFunction_raise_argument_count_error(), __Pyx_CyFunction_raise_type_error(), __Pyx_CyFunction_Vectorcall_CheckArgs(), __Pyx_CyFunction_Vectorcall_FASTCALL_KEYWORDS(), __Pyx_CyFunction_Vectorcall_FASTCALL_KEYWORDS_METHOD() (+4 more)

### Community 85 - "Community 85"
Cohesion: 0.00
Nodes (6): _ledger_path(), _ledger_read(), record_completion(), _scrub(), suggest_level(), test_ledger_records_and_suggests()

### Community 86 - "Community 86"
Cohesion: 0.00
Nodes (5): inject(), main(), _record_span(), _trace_ids(), main()

### Community 88 - "Community 88"
Cohesion: 0.00
Nodes (6): bfs_order(), dodeca_neighbors(), icosahedron_neighbors(), neighbors(), petersen_neighbors(), unregister_shape()

### Community 89 - "Community 89"
Cohesion: 0.00
Nodes (5): complete_neighbors(), cycle_neighbors(), _nbr(), generalized_petersen(), hypercube()

### Community 90 - "Community 90"
Cohesion: 0.00
Nodes (5): contract(), gaps(), materialize(), report(), _root()

### Community 92 - "Community 92"
Cohesion: 0.00
Nodes (3): supported_languages(), test_dispatcher_covers_all_shard_langs(), test_run_code_javascript_inline()

### Community 93 - "Community 93"
Cohesion: 0.00
Nodes (6): ids(), load(), main(), _prose(), rule_blocks(), rule_problem()

### Community 94 - "Community 94"
Cohesion: 0.00
Nodes (7): audit(), _debunk_notes(), dream(), inhibited(), _src_on_path(), test_audit_names_23_processes_3_strata(), test_dream_and_inhibition_run_offline()

### Community 95 - "Community 95"
Cohesion: 0.00
Nodes (7): companion_response(), eliza_reading(), main(), test_eliza_reading_is_honest_without_graph(), test_empty_cues_say_so(), test_lucy_cli_runs(), test_response_is_grounding_and_offline()

### Community 96 - "Community 96"
Cohesion: 0.00
Nodes (7): __Pyx_call_type_traverse(), __Pyx_check_single_interpreter(), __Pyx_copy_spec_to_module(), __Pyx_CyFunction_traverse(), __Pyx_GetCurrentInterpreterId(), __pyx_m_traverse(), __pyx_pymod_create()

### Community 97 - "Community 97"
Cohesion: 0.00
Nodes (7): __Pyx_call_type_traverse(), __Pyx_check_single_interpreter(), __Pyx_copy_spec_to_module(), __Pyx_CyFunction_traverse(), __Pyx_GetCurrentInterpreterId(), __pyx_m_traverse(), __pyx_pymod_create()

### Community 98 - "Community 98"
Cohesion: 0.00
Nodes (5): counsel(), draft_accommodation(), movements(), note_failure(), study()

### Community 99 - "Community 99"
Cohesion: 0.00
Nodes (5): cmd_grievance(), draft_foia(), draft_public_comment(), legal_referral(), tutorial()

### Community 100 - "Community 100"
Cohesion: 0.00
Nodes (8): mse(), test_assembly_refuses_dim_mismatch_with_both_sides_named(), test_backward_matches_numeric_gradient(), test_digest_sensitive_to_seed_and_tamper(), test_seed_rebuild_is_bit_identical(), test_xent_and_proof_through_real_auditors(), test_xor_learns_end_to_end(), _xor_net()

### Community 101 - "Community 101"
Cohesion: 0.00
Nodes (7): __Pyx_AddTraceback(), __Pyx_CLineForTraceback(), __Pyx_CreateCodeObjectForTraceback(), __Pyx_ErrFetchInState(), __Pyx_ErrRestoreInState(), __Pyx__PyCode_New(), __Pyx_PyCode_Replace_For_AddTraceback()

### Community 102 - "Community 102"
Cohesion: 0.00
Nodes (6): main(), test_gamora_berzerker_commands_run_offline(), test_doctor_runs_without_traceback(), test_inject_carries_trace_and_drive(), test_inject_no_drive_is_header_only(), test_swarm_command_runs_offline()

### Community 104 - "Community 104"
Cohesion: 0.00
Nodes (6): consult(), _live_signal(), note_failure(), _record_signal(), _text_signal(), list_grievances()

### Community 105 - "Community 105"
Cohesion: 0.00
Nodes (8): __Pyx_LargePyLong___Pyx_PyLong_As_PY_LONG_LONG(), __Pyx_NonPyLong___Pyx_PyLong_As_PY_LONG_LONG(), __Pyx_PyLong_As_PY_LONG_LONG(), __Pyx_PyLong___Pyx_PyLong_As_PY_LONG_LONG(), __Pyx_PySLong___Pyx_PyLong_As_PY_LONG_LONG(), __Pyx_PyULong___Pyx_PyLong_As_PY_LONG_LONG(), __Pyx_raise_neg_overflow___Pyx_PyLong_As_PY_LONG_LONG(), __Pyx_raise_overflow___Pyx_PyLong_As_PY_LONG_LONG()

### Community 106 - "Community 106"
Cohesion: 0.00
Nodes (4): render_stationery(), seal_svg(), stationery_from_tutorial(), _strokes_js()

### Community 107 - "Community 107"
Cohesion: 0.00
Nodes (4): arena(), arena_response(), bout(), judge_all()

### Community 108 - "Community 108"
Cohesion: 0.00
Nodes (3): cmd_e2e(), cmd_fetch(), intuit()

### Community 110 - "Community 110"
Cohesion: 0.00
Nodes (8): __Pyx_LargePyLong___Pyx_PyLong_As_int(), __Pyx_NonPyLong___Pyx_PyLong_As_int(), __Pyx_PyLong_As_int(), __Pyx_PyLong___Pyx_PyLong_As_int(), __Pyx_PySLong___Pyx_PyLong_As_int(), __Pyx_PyULong___Pyx_PyLong_As_int(), __Pyx_raise_neg_overflow___Pyx_PyLong_As_int(), __Pyx_raise_overflow___Pyx_PyLong_As_int()

### Community 111 - "Community 111"
Cohesion: 0.00
Nodes (3): list_tracks(), plan_track(), referrals()

### Community 112 - "Community 112"
Cohesion: 0.00
Nodes (3): note_failure(), _one(), swarm()

### Community 113 - "Community 113"
Cohesion: 0.00
Nodes (4): candidates(), _repo_src(), therapy_prompt(), therapy_response()

### Community 114 - "Community 114"
Cohesion: 0.00
Nodes (3): DodecaStore, index_live_log(), note_failure()

### Community 116 - "Community 116"
Cohesion: 0.00
Nodes (5): __Pyx_MakeKwargDict(), __Pyx_Object_VectorcallMethodKwds(), __Pyx_PyLong_From_int(), __Pyx_PyLong_From_long(), __Pyx_PyLong_From_PY_LONG_LONG()

### Community 117 - "Community 117"
Cohesion: 0.00
Nodes (6): __Pyx_LargePyLong___Pyx_PyLong_As_long(), __Pyx_PyLong___Pyx_PyLong_As_long(), __Pyx_PySLong___Pyx_PyLong_As_long(), __Pyx_PyULong___Pyx_PyLong_As_long(), __Pyx_raise_neg_overflow___Pyx_PyLong_As_long(), __Pyx_raise_overflow___Pyx_PyLong_As_long()

### Community 119 - "Community 119"
Cohesion: 0.00
Nodes (3): _current_versions(), _measured_order(), sweep_freshness()

### Community 120 - "Community 120"
Cohesion: 0.00
Nodes (3): iter_verses(), reference_index(), render_index()

## Knowledge Gaps
- **1 isolated node(s):** `eve-unleashed`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 980 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `note_failure()` connect `Failure Telemetry + Live Server` to `Eve CLI Commands`, `Core Paths + Orchestration`, `Decision Engine`, `Community 7`, `Community 16`, `Community 19`, `Community 20`, `Community 28`, `Community 32`, `Community 33`, `Community 35`, `Community 38`, `Community 40`, `Community 43`, `Community 49`, `Community 50`, `Community 54`, `Community 55`, `Community 57`, `Community 60`, `Community 67`, `Community 68`, `Community 70`, `Community 73`, `Community 75`, `Community 77`, `Community 78`, `Community 83`, `Community 88`, `Community 98`, `Community 104`, `Community 112`, `Community 114`, `Community 119`?**
  _High betweenness centrality (0.196) - this node is a cross-community bridge._
- **Why does `InferenceEngine` connect `Community 8` to `Community 32`, `Eve CLI Commands`, `Core Paths + Orchestration`, `Community 16`, `Community 49`, `Community 50`, `Community 87`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `DynamicHypergraph` connect `Community 103` to `Community 58`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **What connects `eve-unleashed` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Failure Telemetry + Live Server` be split into smaller, more focused modules?**
  _Cohesion score 0.04679089026915114 - nodes in this community are weakly interconnected._
- **Should `Eve CLI Commands` be split into smaller, more focused modules?**
  _Cohesion score 0.04521510096575944 - nodes in this community are weakly interconnected._
- **Should `Replay Cython Kernel` be split into smaller, more focused modules?**
  _Cohesion score 0.05837173579109063 - nodes in this community are weakly interconnected._