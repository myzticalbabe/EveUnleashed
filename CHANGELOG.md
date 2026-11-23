# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Native GGUF inference with llama-cpp-python on Python 3.16t free-threaded** — `llama-cpp-python` installed via pip with 3.16t wheel support; integrated into `eve_unleashed/engine.py` as `GGUFEngine` class with support for standard generation, streaming, and advanced features.
- **GGUF Metadata Editor CLI** — `eve edit-metadata --model <gguf> --set key=val` command in `src/eve_unleashed/commands/edit_metadata.py`, registered in `cli.py` subparsers. Uses `gguf` library to read/modify metadata fields.
- **Speculative Decoding** — Draft+verify with small draft model in `src/eve_unleashed/speculative.py`. Implements `SpeculativeEngine(draft_model, target_model, num_draft_tokens=4)` with token acceptance/rejection statistics. Added `--speculative`, `--draft-model`, `--num-draft-tokens` flags to `eve infer`.
- **KV Cache Quantization (8-bit)** — 8-bit KV cache for GGUF models in `src/eve_unleashed/kv_quant.py`. Implements `KVQuantizer` with quantization/dequantization, memory savings reporting. Added `--kv-quant 8` flag to `eve infer` and `eve serve` (also supports 4-bit).
- **Multi-modal GGUF Support (LLaVA-style)** — Vision encoder support in `GGUFEngine.load_multimodal_model()` and `infer()` with image+text input handling. Uses llama-cpp-python's chat completion with images for LLaVA-GGUF models.
- **New GGUF Framework Loaders** — `gguf-speculative`, `gguf-kv-quant`, `gguf-multimodal` frameworks in `InferenceEngine.model_loaders` with corresponding `_load_gguf_speculative_model`, `_load_gguf_kv_quant_model`, `_load_gguf_multimodal_model` methods.
- **Tests** — Added `tests/test_edit_metadata.py` and `tests/test_new_engines.py` for new functionality.

### Changed

- Updated `InferenceEngine._single_infer` to handle new GGUF framework types (`gguf-speculative`, `gguf-kv-quant`, `gguf-multimodal`).
- Updated `InferenceEngine.infer_stream` to support streaming for new GGUF frameworks.
- Updated `InferenceEngine._warmup_model` to warm up new framework types.
- Enhanced `cmd_infer` with speculative decoding, KV quantization, and multi-modal image input options.
- Enhanced `cmd_serve` with `--kv-quant` flag and per-request KV quantization override via API.

## v0.1.0 (2026-11-18)

### Added
- Initial release of Eve Unleashed — standalone desktop AI app extracted from AZAZAEL
- Local AI inference, Python REPL, system monitor, multi-backend benchmarks
- Professional governance files (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY)
- CI/CD workflows and issue templates

### Fixed
- Git health: commit-graph, fsmonitor, untrackedCache, index v4 configured
