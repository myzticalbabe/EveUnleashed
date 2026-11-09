# Frontier Recovery Technique (enshrined 2026-11-09)

Earned on a Core Ultra 9 285H (Arc 140T + AI Boost NPU) across one day:
stdlib GPU proof, NPU illumination, wiped-GRUB recovery from the Windows side.
Each pattern carries its proof command. A pattern without a command is a wish.

## T1 — Judge, don't hope (verdict layer over probes)

A probe that only describes broken upstream stacks inherits them. Add a
`verdict_frontier()` that classifies every subsystem:
FIXED (ours, live-verified) / DEGRADED-KNOWN (theirs, owner + fallback named) /
BROKEN-UPSTREAM / UNKNOWN (wrong soil to answer — never a guess).
Key discipline: verdicts key off soil FIRST (WSL's missing NPU is by-design,
never BROKEN).
Proof: `baremetal_pathfinder.py` → `report["frontier"]`; green both soils, exit 0.

## T2 — Locate by file, identify by firmware (never guessed UUIDs)

Kernels/initrds: GRUB `search --no-floppy --file /boot/vmlinuz --set=root`.
Root identity: PARTUUID queried live from GPT
(`(Get-Partition -DiskNumber 0 -PartitionNumber 8).Guid`), braces stripped —
Linux PARTUUID takes none. Fallback: raw device path (`/dev/nvme0n1p8`).
Proof: `baremetal/elevated_recover.ps1` + `esp_recovery_grub.template`;
recovery grub.cfg 806 B live on ESP with 2 backups.

## T3 — Quarantine the dependency (stdlib core, dirty lanes outside)

`mcml/` stays stdlib-only, zero wheels — the rule that made the GPU backend
portable (Windows + WSL2 unmodified, 28x). Everything with a third-party dep
lives outside: `npu_lane/` (openvino+numpy declared, `eve-npu-probe` entry).
A lane that cannot import its dep degrades to a verdict (exit 2), never an ImportError.
Proof: `npu_lane/dist/*.whl` installed into a clean target, ran FIXED.

## T4 — Elevate read-only first (UAC + report-file polling)

From an unprivileged shell: `Start-Process powershell -Verb RunAs -File <script>`;
the elevated child writes ONLY a report file; the caller polls for it.
First run is always inspection (BCD + ESP trees); mutation runs only after eyes.
Proof: `baremetal/elevated_inspect.ps1` → shim-first displayorder found;
`elevated_recover.ps1` → menu rebuilt.

## T5 — Never strand the box

Every bootloader menu ships a working Windows chainload entry; every fallback
entry exists before the primary is trusted. A Linux-only menu on a shared box
is a stranding, not a fix.
Proof: recovery grub.cfg items 1–3 (recovered, fallback, Windows 11).

## T6 — Quote warmed numbers, calibrate live

First dispatch pays upload/compile (NPU 333 ms → 0.55 ms warmed; OpenCL clock
at 0x100C not 0x100D on NEO Windows drv 32.0.101.8991 — sweep the slots, pick
the sane band, record raw). Quote p50 warmed or say nothing.
Proof: `examples/igpu_opencl_compute.py` (3-run rule), `mcml_gpu` tune table,
NPU probe `runs.{min,p50,max}_ms`.
