# LinkedIn technical post — DRAFT (post manually; no autoposter here)

Weekend project: I stopped assuming my laptop's NPU was useless and measured it instead.

The box: Core Ultra 9 285H — 99 package TOPS split 77 GPU / 13 NPU / 9 CPU under
one 45W envelope. The NPU (Intel AI Boost) sat at 0% while my GPU path did all
the work. So:

1. GPU first, stdlib only. A ctypes OpenCL backend (no CUDA, no wheels) moved a
dense layer 35.7x vs CPU, verified bit-near (5e-7) with the CPU kept as
golden-digest authority, plus a tunable CPU/GPU split that pins itself per shape.
Same file runs unmodified on WSL2 Ubuntu 26.04 (28x there — the 6x gap is the
GPU-PV launch tax, measured, not guessed).

2. Then the NPU. OpenVINO enumerated CPU/GPU/NPU; an offline-built static f16
matmul+relu compiled to the NPU and returned exact results (15.75, matching CPU
to 1e-2), warmed p50 0.55ms. First dispatch paid 333ms — quote warmed numbers
or say nothing. The 13 TOPS were never broken; the software promise around them
was. Lesson: treat vendor stacks as weather, not terrain.

3. Then the hard reset wiped my GRUB menu. Rebuilt it from the Windows side:
elevated script, backup first, root PARTUUID queried live from GPT (strip the
braces — Linux takes none), kernel located by GRUB file-search so nothing rots,
Windows chainload kept so the box is never stranded. Reboot lands on a menu.

The reusable bit: put a verdict layer over your probes —
FIXED / DEGRADED-KNOWN / BROKEN-UPSTREAM / UNKNOWN-by-soil — so your tooling
judges broken upstream instead of inheriting it.

Numbers above are measured on my box today, not benchmarketing. The probe files
are stdlib-only; the NPU lane is quarantined behind OpenVINO and out of the
exact path. Happy to share the technique doc with anyone fighting the same
Arrow Lake frontier.
