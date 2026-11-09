# Bare metal Ubuntu 26.04 — runbook (5 minutes, one boot)

Carry this folder + `../examples/baremetal_pathfinder.py` +
`../npu_lane/dist/eve_npu_lane-0.1.0-py3-none-any.whl` on USB.
Everything else is scripted. Kernel symlinks (`/boot/vmlinuz`) are used,
so kernel updates don't orphan the entry.

## Apply (inside the installed Ubuntu 26.04)

```bash
cd /media/$USER/*/baremetal   # or wherever the USB landed
sudo bash apply.sh            # auto-detects / and /boot/efi UUIDs
```

`apply.sh` backs up `/etc/default/grub` and `/etc/grub.d/40_custom` to
`*.bak-<date>`, sets menu/timeout/cmdline, writes the entries, runs
`update-grub`, `grub-install --target=x86_64-efi`, and orders `ubuntu`
ahead of Windows Boot Manager. Re-run safe. To override detection:
`sudo ROOT_UUID=<uuid> ESP_UUID=<XXXX-XXXX> bash apply.sh`.

Secure Boot must be OFF (26.04.1 ships `intel-ipu7` modules unsigned;
with SB on, the NPU driver refuses and the lane degrades).

## Verify (same boot, after reboot into Ubuntu)

```bash
sudo bash verify.sh
```

Checks: `xe` binds the Arc 140T, `/dev/accel/accel0` exists,
`dmesg` shows `Initialized intel_vpu`, `clinfo` lists the GPU, then runs
the pathfinder and prints its `frontier` verdicts. Expect
`SOIL=bare-metal-linux`, `gpu_compute FIXED`, `npu_device FIXED`
(after the v1.38.0 tarball from the recipe) or a named owner if not.

## Files

- `40_custom.template` — GRUB entries (`@ROOT_UUID@`, `@ESP_UUID@` filled by apply.sh)
- `grub-default-snippet` — the exact `/etc/default/grub` lines enforced
- `apply.sh` — land the entry, idempotent
- `verify.sh` — prove the soil, read-only (never writes, safe anywhere)
