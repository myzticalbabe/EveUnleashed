"""eve_npu_lane -- quarantined Intel AI Boost (NPU) probe lane.

Lives OUTSIDE mcml/ by design (mcml is stdlib-only; this lane owns the
single third-party dependency: openvino). Offline: the probe model is built
from opset ops, nothing is downloaded.

CLI:  eve-npu-probe [--out report.json]
Exit 0 = NPU present, inference exact vs CPU, report honest.
Exit 2 = no NPU in this soil (expected in WSL2 guests / non-Intel boxes).
Exit 1 = real failure (compile error, wrong numerics).
"""

import json
import sys
import time

try:
    import numpy as np
except ImportError:
    np = None

try:
    import openvino as ov
    from openvino import opset8 as ops
except ImportError:
    ov, ops = None, None

EXPECTED = 15.75  # sum([0..63]/64) * 0.5, per output element


def _tiny_model():
    p = ops.parameter([1, 64], dtype=np.float16, name="x")
    w = ops.constant(np.ones((64, 32), dtype=np.float16) * 0.5, dtype=np.float16)
    y = ops.relu(ops.matmul(p, w, False, False), name="y")
    return ov.Model([y], [p], "tiny")


def _infer(cm, x, iters=50):
    ts = []
    out = None
    for _ in range(iters):
        t = time.perf_counter()
        out = cm(x)[0]
        ts.append((time.perf_counter() - t) * 1000.0)
    ts.sort()
    return float(np.asarray(out).ravel()[0]), ts[0], ts[len(ts) // 2], ts[-1]


def probe(out_path=None):
    report = {"lane": "eve-npu-lane", "version": "0.1.0"}
    if ov is None or np is None:
        report["error"] = "openvino/numpy not importable in this interpreter"
        return 1, report
    core = ov.Core()
    devs = core.available_devices
    report["devices"] = devs
    report["names"] = {}
    for d in devs:
        try:
            report["names"][d] = core.get_property(d, "FULL_DEVICE_NAME")
        except Exception as e:
            report["names"][d] = "name query failed: %s" % str(e)[:100]
    if "NPU" not in devs:
        report["verdict"] = "NO-NPU-HERE"
        report["note"] = ("expected in WSL2 guests (dxgkrnl never paravirtualizes "
                          "the NPU) and non-Intel boxes; run on bare metal Windows/Linux")
        return 2, report
    m = _tiny_model()
    x = (np.arange(64, dtype=np.float16).reshape(1, 64) / 64.0)
    got = {}
    for dev in ("CPU", "NPU"):
        cm = core.compile_model(m, dev)
        val, mn, p50, mx = _infer(cm, x)
        got[dev] = {"out": val, "min_ms": round(mn, 3),
                    "p50_ms": round(p50, 3), "max_ms": round(mx, 3)}
    report["runs"] = got
    ok_npu = abs(got["NPU"]["out"] - EXPECTED) < 1e-2
    ok_cpu = abs(got["CPU"]["out"] - EXPECTED) < 1e-2
    agree = abs(got["NPU"]["out"] - got["CPU"]["out"]) < 1e-2
    report["verdict"] = "FIXED" if (ok_npu and ok_cpu and agree) else "WRONG-NUMERICS"
    report["expected"] = EXPECTED
    return (0 if report["verdict"] == "FIXED" else 1), report


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    out_path = args[1] if args[:1] == ["--out"] and len(args) > 1 else None
    code, report = probe(out_path)
    npu = report.get("runs", {}).get("NPU", {})
    print("NPU_LANE verdict=%s devices=%s npu_p50_ms=%s out=%s" % (
        report.get("verdict"), report.get("devices"),
        npu.get("p50_ms", "?"), npu.get("out", "?")))
    text = json.dumps(report, indent=2)
    if out_path:
        with open(out_path, "w") as f:
            f.write(text + "\n")
    else:
        print(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
