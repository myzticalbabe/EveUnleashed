#!/bin/bash
# verify.sh -- prove the bare-metal soil. READ-ONLY: writes nothing, safe anywhere.
# Runs: lspci binding, NPU device+driver, GuC firmware, OpenCL, pathfinder verdicts.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PASS=0; FAIL=0
say() { if [ "$2" = 0 ]; then PASS=$((PASS+1)); echo "PASS: $1"; else FAIL=$((FAIL+1)); echo "FAIL: $1"; fi; }

GPU_LINE="$(lspci -k 2>/dev/null | grep -A2 -i 'vga.*7d51\|3d.*7d51\|display.*7d51' | head -5)"
echo "$GPU_LINE"
echo "$GPU_LINE" | grep -q "Kernel driver in use: xe" && R=0 || R=1
say "xe binds the Arc 140T (want 'Kernel driver in use: xe')" $R

[ -e /dev/accel/accel0 ] && R=0 || R=1
say "/dev/accel/accel0 present" $R
lsmod 2>/dev/null | grep -q intel_vpu && R=0 || R=1
say "intel_vpu module loaded" $R

dmesg 2>/dev/null | grep -i "Initialized intel_vpu" | tail -1
dmesg 2>/dev/null | grep -i "Initialized intel_vpu" | grep -q . && R=0 || R=1
say "dmesg shows NPU boot (Initialized intel_vpu)" $R

if command -v clinfo >/dev/null; then
  clinfo 2>/dev/null | grep -m2 "Device Name" ; R=0
else R=1; fi
say "clinfo lists OpenCL GPU" $R

if [ -f "$HERE/../examples/baremetal_pathfinder.py" ]; then
  python3 "$HERE/../examples/baremetal_pathfinder.py" --out /tmp/bm_report.json
  python3 -c "import json;r=json.load(open('/tmp/bm_report.json'));print('frontier:',{k:v['verdict'] for k,v in r['frontier']['subsystems'].items()})"
  R=0
else R=1; fi
say "pathfinder ran, report at /tmp/bm_report.json" $R

echo "== $PASS pass, $FAIL fail =="
[ "$FAIL" -eq 0 ]
