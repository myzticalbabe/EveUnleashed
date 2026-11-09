# Choke-point audit: one die, three engines, who taxes what (2026-11-09)

Box: Intel Core Ultra 9 285H (Arrow Lake-H, TSMC N3B) — 6P+8E+2LPE, 16T, 2.9 GHz base,
5.4 GHz P-turbo. iGPU Arc 140T (device 0x7D51, 8 Xe-cores / 128 EUs, 2.35 GHz max).
NPU Intel AI Boost (NPU 3720-class, 13 TOPS INT8). RAM 8x2GB slices @ 8533 MT/s
(LPDDR5X class, soldered, shared with the iGPU). Power plan: High performance ACTIVE.
VBS: enabled (DeviceGuard=0x1). WSL2 kernel 6.18.33.2, /dev/dxg + renderD128 present,
/dev/accel ABSENT, dxgkrnl ioctl -22 errors in dmesg.

Every number below was measured on this box or quoted from the vendor page it names.
Nothing in this file is recalled.

## 1. The silicon budget (Intel ARK 241747 + TechPowerUp + live OpenCL)

| engine | peak INT8 | notes |
|---|---|---|
| GPU Arc 140T | 77 TOPS | measured 2350 MHz, OpenCL 3.0 NEO drv 32.0.101.8991 FULL_PROFILE, fp64+fp16+subgroups, 128 CUs |
| NPU AI Boost | 13 TOPS | sparsity engine, inference-only, F16 compute, static shapes on this gen |
| CPU (DL Boost/VNNI) | 9 TOPS | AVX2+VNNI, no AVX-512 on this part |
| package total | 99 TOPS | PL1 45 W sustained / PL2 115 W burst (firmware) |

The NPU is 13% of the package's AI flops and sits idle in our whole stack. That is the
squandered part. But it is the wrong engine for dense f32 matmul (our workload): no
training, no dynamic shapes, INT8/F16-oriented, proprietary graph compiler, blobs not
portable across driver versions. Routing MCML's Dense at it would be slower AND
less exact. The GPU route (35.7x measured) was the right call; the NPU's job is
background INT8 inference offload, quarantined behind an optional OpenVINO path.

## 2. Choke-point ledger: physics vs policy, with owners

| # | choke point | kind | owner | on-box evidence |
|---|---|---|---|---|
| 1 | Shared package power: CPU+iGPU+NPU draw from one PL1 45 W / PL2 115 W envelope; sustained GPU+NPU co-load clocks one of them down | physics, arbitrated | OEM firmware sets PL1/PL2/DTT policy; Intel DTT arbitrates live | ARK PL1/PL2; DTT is OEM-configured per Intel docs 000102775/000058479 |
| 2 | Shared LPDDR5X bandwidth: iGPU has no VRAM, contends with CPU on the 128-bit bus | physics | nobody (design); Intel memory controller | 8533 MT/s soldered; zero-copy is the upside, contention the price |
| 3 | NPU has no generic compute API: OpenCL/Level-Zero-compute cannot see it; only OpenVINO/DirectML/WindowsML graph path, proprietary compiler-in-driver | policy | Intel | OpenVINO docs: graph extension API, static shapes only, blob incompatibility across versions |
| 4 | NPU invisible in WSL2: /dev/accel absent, dxgkrnl only paravirtualizes GPU; dxgkio_query_adapter_info ioctl -22 in guest dmesg | policy | Microsoft (GPU-PV scope) | `ls /dev/accel*` -> missing; dmesg dxgkrnl errors logged 2026-11-09 |
| 5 | Copilot+ 40 TOPS gate: 13-TOPS NPU locked out of Recall/local-model features by policy, not physics | policy | Microsoft | third-party confirm (cpu-monkey 2026-11-01): "too weak for Copilot+"; local AI falls back to GPU |
| 6 | VBS/HVCI tax: hypervisor-isolated code integrity on every driver load; ~2-5% typical, 11-17% outliers (MSFS-class) | policy default | Microsoft (default-on Win11); measurable per-box | DeviceGuard EnableVBS=0x1 on this box; Tom's/PCWorld benches |
| 7 | WSL2 GPU-PV launch tax: VMBus round trip per submit; small sequential kernels pay most (~6x measured here) | architecture | Microsoft dxgkrnl design; NVIDIA doc confirms mechanism | 0.66 ms native vs 3.91 ms WSL on identical kernel (2026-11-09) |
| 8 | NPU driver stack unvalidated on Ubuntu 26.04 (kernel 7.0 has intel_vpu, userspace untested; verified matrix stops at 24.04/6.14) | maturity | Intel (linux-npu-driver #134) | GitHub issue 2026-05-13, still open-format |
| 9 | First-dispatch JIT 11-35 ms vs 0.6 ms warm: quoting warm numbers as throughput | measurement trap | us (discipline) | three-run print rule in examples |

## 3. Arena verdicts (each claim judged across vendor docs + live box)

- "The NPU being on the same clip doesn't matter" -> PARTLY REFUTED. Coexistence is
  free (separate engines, DTT partitions power when both load). What is NOT free:
  one 45 W envelope and one memory bus. Run GPU+NPU hot together and physics clocks
  something. Nobody's driver bug -- arithmetic.
- "We squander full potential of limited resources" -> CONFIRMED with scope. 13 of 99
  TOPS idle, plus VBS tax running, plus WSL-only-Linux workflow paying 6x on transfers.
  But the NPU's 13 TOPS are not fungible with the GPU's 77 for our math.
- "Evolve out" -> the moves below. None requires permission; two require reboots or
  installs this shell cannot do, and they are labeled as such.

## 4. Evolve-out moves (E2R: live-measured, developed instruments, no simulation)

1. DONE -- GPU backend + hybrid tuner (`src/eve_unleashed/mcml_gpu.py`, exit 0, 35.7x).
   This is our DTT: measure per shape, pin the split. Extend it, don't fork it (E2R-9).
2. NPU lane (quarantined, needs OpenVINO wheel -- NEVER inside mcml/): background INT8
   classifiers (captcha families, studio-effect-style prefilters) via OpenVINO NPU
   plugin on Windows, where the driver is already OK. Proves the 13 TOPS without
   touching the exact path.
3. VBS measure-then-decide: run the mcml_gpu check with Memory integrity on vs off
   (reboot + admin; NOT done from here). Predict ~0-5% on our shape (kernel-bound,
   MBEC hardware); do it once, keep the faster, record both numbers.
4. Bare-metal Linux: unlocks intel_vpu + removes the 6x PV tax. Out of reach from this
   shell (no install path); the portable OpenCL file is the artifact that survives it.
5. Watch item, not action: dxgkrnl degradation-over-uptime reports (NVIDIA forum
   2026-09-25, same PV family). If WSL numbers ever drift across days without a code
   change, `wsl --shutdown` first, GPU device restart second, then record.

## 5. Standing numbers (re-measure, never recall)

GPU 2350 MHz / OpenCL 3.0 NEO 32.0.101.8991 / 128 CUs / maxAlloc ~4 GiB.
NPU: AI Boost OK, class ComputeAccelerator. RAM 16 GB-class @ 8533. PL1 45 W.
VBS on. /dev/accel missing in WSL. Tune: 0.00:123.16 ... 1.00:1.45 ms.
