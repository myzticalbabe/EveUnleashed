#!/usr/bin/env python3
"""baremetal_pathfinder.py -- scout probe for bare-metal Ubuntu (runs on any soil).

Stdlib only, zero third-party wheels. Every probe degrades to
{"available": false, "reason": ...} instead of raising; exit 0 always means
"the report is honest", never "the soil is bare metal". Ship this one file to
the bare-metal box (USB, scp,сюда) and run:  python3 baremetal_pathfinder.py
[--out report.json]

Prints one SOIL= verdict line plus the full JSON report on stdout.
"""

import ctypes
import ctypes.util
import glob
import json
import os
import platform
import shutil
import subprocess
import sys

PROBE = {"file": os.path.basename(__file__), "argv": sys.argv[1:]}


def ok(**kw):
    d = {"available": True}
    d.update(kw)
    return d


def na(reason):
    return {"available": False, "reason": reason}


def read1(path):
    try:
        with open(path, "r", errors="replace") as f:
            return f.read().strip()
    except OSError as e:
        return None if False else ("ERR:" + str(e))


def probe_soil():
    sysname = platform.system()
    if sysname == "Windows":
        return ok(soil="windows-host", hypervisor="unknown",
                  note="Windows host; Hyper-V role not probed from userland here")
    if sysname != "Linux":
        return ok(soil="other-" + sysname.lower(), hypervisor="unknown")
    ver = read1("/proc/version") or ""
    if "microsoft" in ver.lower() or "wsl" in ver.lower():
        flavor = "wsl2-guest" if "WSL2" in ver or "microsoft-standard" in ver.lower() else "wsl-guest"
        return ok(soil=flavor, kernel=platform.release(), proc_version=ver[:160])
    cpuinfo = read1("/proc/cpuinfo") or ""
    hyper = any(l.startswith("flags") and " hypervisor " in (" " + l + " ")
                for l in cpuinfo.splitlines())
    vendor = read1("/sys/class/dmi/id/sys_vendor") or ""
    product = read1("/sys/class/dmi/id/product_name") or ""
    vm_marks = ("qemu", "kvm", "vmware", "virtualbox", "xen", "microsoft corporation",
                "parallels", "bhyve")
    blob = (vendor + " " + product).lower()
    if hyper or any(m in blob for m in vm_marks) or os.path.exists("/.dockerenv"):
        return ok(soil="virtual-guest", hypervisor=True, sys_vendor=vendor,
                  product_name=product, kernel=platform.release())
    det = None
    if shutil.which("systemd-detect-virt"):
        try:
            det = subprocess.run(["systemd-detect-virt"], capture_output=True,
                                 text=True, timeout=10).stdout.strip()
        except OSError:
            det = None
    soil = "bare-metal-linux" if det in (None, "none") else "virtual-guest"
    return ok(soil=soil, hypervisor=False, sys_vendor=vendor,
              product_name=product, kernel=platform.release(),
              systemd_detect_virt=det,
              bios_version=read1("/sys/class/dmi/id/bios_version"))


def probe_cpu():
    sysname = platform.system()
    if sysname == "Windows":
        return ok(model=os.environ.get("PROCESSOR_IDENTIFIER", "unknown"),
                  arch=os.environ.get("PROCESSOR_ARCHITECTURE", "unknown"),
                  count=os.cpu_count())
    if sysname == "Linux":
        model, flags = "unknown", ""
        for line in (read1("/proc/cpuinfo") or "").splitlines():
            if line.startswith("model name") and model == "unknown":
                model = line.split(":", 1)[1].strip()
            if line.startswith("flags") and not flags:
                flags = line.split(":", 1)[1].strip()
        fl = set(flags.split())
        return ok(model=model, count=os.cpu_count(),
                  flags_n=len(fl), hypervisor_bit=("hypervisor" in fl),
                  avx512=("avx512f" in fl), vnni=("avx512_vnni" in fl or "avx_vnni" in fl))
    return na("cpu probe not implemented for " + sysname)


def probe_mem():
    sysname = platform.system()
    if sysname == "Linux":
        total_kb = None
        for line in (read1("/proc/meminfo") or "").splitlines():
            if line.startswith("MemTotal:"):
                total_kb = int(line.split()[1])
        return ok(total_gb=round(total_kb / 1048576, 2) if total_kb else None)
    if sysname == "Windows":
        try:
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            st = MS()
            st.dwLength = ctypes.sizeof(MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
                return ok(total_gb=round(st.ullTotalPhys / 1073741824, 2))
            return na("GlobalMemoryStatusEx failed")
        except OSError as e:
            return na("ctypes: %s" % e)
    return na("mem probe not implemented for " + sysname)


def probe_pci():
    lspci = shutil.which("lspci")
    if not lspci:
        return na("lspci not on PATH")
    try:
        p = subprocess.run([lspci, "-nnmm"], capture_output=True, text=True, timeout=30)
    except OSError as e:
        return na("lspci exec failed: %s" % e)
    if p.returncode != 0:
        return na("lspci exit %d: %s" % (p.returncode, p.stderr[:200]))
    devs = []
    for line in p.stdout.splitlines():
        ll = line.lower()
        if any(k in ll for k in ("vga", "3d controller", "display", "npu", "neural",
                                 "vpu", "ai ", "multimedia", "signal processing")):
            devs.append(line[:220])
    return ok(count=len(devs), devices=devs, raw_lines=len(p.stdout.splitlines()))


def probe_drm():
    if platform.system() != "Linux":
        return na("sysfs DRM only exists on Linux")
    cards = []
    for uevent in sorted(glob.glob("/sys/class/drm/card*/device/uevent")):
        card = {"node": uevent.split("/device/")[0]}
        for line in (read1(uevent) or "").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                if k in ("DRIVER", "PCI_ID", "PCI_SUBSYS_ID"):
                    card[k.lower()] = v
        cards.append(card)
    dri = sorted(glob.glob("/dev/dri/*"))
    accel = sorted(glob.glob("/dev/accel*"))
    return ok(drm_cards=cards, dri_nodes=dri, accel_nodes=accel,
              npu_present=len(accel) > 0)


def probe_npu_module():
    if platform.system() != "Linux":
        return na("kernel modules only exist on Linux")
    mods = read1("/proc/modules") or ""
    loaded = [l.split()[0] for l in mods.splitlines() if "vpu" in l or "npu" in l]
    return ok(intel_vpu_loaded=any("intel_vpu" in l.split()[0] for l in mods.splitlines()),
              vpu_npu_modules=loaded)


def _cl_str(fn, handle, param):
    size = ctypes.c_size_t(0)
    if fn(handle, param, 0, None, ctypes.byref(size)) != 0 or not size.value:
        return None
    buf = ctypes.create_string_buffer(size.value)
    if fn(handle, param, size.value, buf, None) != 0:
        return None
    return buf.value.decode("utf-8", "replace").rstrip("\x00")


def probe_opencl():
    try:
        if platform.system() == "Windows":
            lib = ctypes.WinDLL("OpenCL.dll")
        else:
            name = ctypes.util.find_library("OpenCL") or "libOpenCL.so.1"
            lib = ctypes.CDLL(name)
    except OSError as e:
        return na("no OpenCL loader: %s" % e)
    try:
        lib.clGetPlatformIDs.restype = ctypes.c_int32
        lib.clGetPlatformIDs.argtypes = [ctypes.c_uint32,
                                         ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        lib.clGetPlatformInfo.restype = ctypes.c_int32
        lib.clGetDeviceIDs.restype = ctypes.c_int32
        n = ctypes.c_uint32(0)
        if lib.clGetPlatformIDs(0, None, ctypes.byref(n)) != 0 or n.value == 0:
            return ok(platforms=0, note="loader present, zero platforms")
        arr = (ctypes.c_void_p * n.value)()
        lib.clGetPlatformIDs(n.value, arr, None)
        plats = []
        for ph in arr:
            p = ctypes.c_void_p(ph)
            info = {"name": _cl_str(lib.clGetPlatformInfo, p, 0x0902),
                    "vendor": _cl_str(lib.clGetPlatformInfo, p, 0x0903),
                    "version": _cl_str(lib.clGetPlatformInfo, p, 0x0901)}
            lib.clGetDeviceIDs.restype = ctypes.c_int32
            lib.clGetDeviceIDs.argtypes = [ctypes.c_void_p, ctypes.c_uint64,
                                          ctypes.c_uint32, ctypes.c_void_p,
                                          ctypes.POINTER(ctypes.c_uint32)]
            dn = ctypes.c_uint32(0)
            devs = []
            if lib.clGetDeviceIDs(p, 0xFFFFFFFF, 0, None, ctypes.byref(dn)) == 0 and dn.value:
                darr = (ctypes.c_void_p * dn.value)()
                lib.clGetDeviceIDs(p, 0xFFFFFFFF, dn.value, darr, None)
                lib.clGetDeviceInfo = lib.clGetDeviceInfo if hasattr(lib, "clGetDeviceInfo") else None
                gdi = lib.clGetDeviceInfo
                gdi.restype = ctypes.c_int32
                for dh in darr:
                    d = ctypes.c_void_p(dh)
                    cu = ctypes.c_uint32(0)
                    sz = ctypes.c_size_t(ctypes.sizeof(cu))
                    gdi(d, 0x1002, sz, ctypes.byref(cu), None)
                    # Clock calibration (measured 2026-11-09, Intel NEO Windows
                    # drv 32.0.101.8991): 0x100C reads 2350, 0x100D reads 64,
                    # 0x100E reads 128 -- the table disagrees with the Khronos
                    # enum by one slot in this range, so sweep and pick the
                    # value in a sane MHz band instead of trusting one slot.
                    raw = {}
                    for param in (0x100C, 0x100D, 0x100E):
                        v = ctypes.c_uint32(0)
                        rc = gdi(d, param, sz, ctypes.byref(v), None)
                        raw[hex(param)] = (rc, v.value)
                    sane = [v for (rc, v) in raw.values()
                            if rc == 0 and 100 <= v <= 6000]
                    mem = ctypes.c_ulonglong(0)
                    gdi(d, 0x101F, ctypes.c_size_t(8), ctypes.byref(mem), None)
                    devs.append({"name": _cl_str(gdi, d, 0x102B),
                                 "vendor": _cl_str(gdi, d, 0x102C),
                                 "version": _cl_str(gdi, d, 0x102F),
                                 "compute_units": cu.value,
                                 "max_mhz": sane[0] if sane else None,
                                 "clock_raw": raw,
                                 "global_mem_gb": round(mem.value / 1073741824, 2),
                                 "extensions": (_cl_str(gdi, d, 0x1030) or "")[:400]})
            info["devices"] = devs
            plats.append(info)
        return ok(platforms=len(plats), detail=plats)
    except OSError as e:
        return na("OpenCL query failed: %s" % e)


def probe_secureboot():
    # Their broken promise, our detector (26.04.1 ships intel-ipu7 modules
    # unsigned: Secure Boot ON + NPU driver = refusal. Know before you boot).
    if platform.system() == "Linux":
        efivars = sorted(glob.glob("/sys/firmware/efi/efivars/SecureBoot-*"))
        if efivars:
            try:
                with open(efivars[0], "rb") as f:
                    raw = f.read()
                # efivar payload: 4-byte attrs + 1-byte value
                state = "ON" if raw and raw[-1] == 1 else "OFF"
                return ok(secure_boot=state, source=efivars[0])
            except OSError as e:
                return na("efivar unreadable: %s" % e)
        if shutil.which("mokutil"):
            try:
                p = subprocess.run(["mokutil", "--sb-state"], capture_output=True,
                                   text=True, timeout=10)
                out = (p.stdout + p.stderr).strip().lower()
                if "enabled" in out:
                    return ok(secure_boot="ON", source="mokutil")
                if "disabled" in out:
                    return ok(secure_boot="OFF", source="mokutil")
                return na("mokutil inconclusive: %s" % out[:120])
            except OSError as e:
                return na("mokutil exec failed: %s" % e)
        return na("no efivars and no mokutil (BIOS boot or no permission)")
    if platform.system() == "Windows":
        return na("SecureBoot read needs admin BCD; check msinfo32 instead")
    return na("secureboot probe not implemented for " + platform.system())


def verdict_frontier(r):
    # EVOLVE-TO-FIXED: the report judges itself. FIXED = ours, verified live.
    # DEGRADED-KNOWN = theirs, routed around with a named owner + fallback.
    # UNKNOWN = this soil cannot answer; hand to a soil that can.
    v = {}
    soil = (r.get("soil") or {}).get("soil", "unknown")
    drm = r.get("drm", {})
    npu_mod = r.get("npu_module", {})
    sb = r.get("secureboot", {})
    ocl = r.get("opencl", {})
    if drm.get("available") and drm.get("npu_present"):
        v["npu_device"] = ok(verdict="FIXED", detail="/dev/accel present")
    elif soil in ("wsl2-guest", "wsl-guest"):
        v["npu_device"] = ok(verdict="DEGRADED-KNOWN",
                               detail="NPU not paravirtualized by dxgkrnl (Microsoft); use bare metal")
    elif soil == "bare-metal-linux":
        v["npu_device"] = ok(verdict="BROKEN-UPSTREAM",
                               detail="no /dev/accel on bare metal: BIOS disabled or no intel_vpu (Intel/firmware)")
    else:
        v["npu_device"] = ok(verdict="UNKNOWN", detail="not a Linux soil")
    if npu_mod.get("available") and npu_mod.get("intel_vpu_loaded"):
        v["npu_driver"] = ok(verdict="FIXED", detail="intel_vpu loaded")
    elif soil in ("wsl2-guest", "wsl-guest"):
        v["npu_driver"] = ok(verdict="DEGRADED-KNOWN",
                               detail="no intel_vpu in guest by design; NPU lane runs on bare metal only")
    else:
        v["npu_driver"] = ok(verdict="UNKNOWN", detail="module state unreadable here")
    if sb.get("available") and sb.get("secure_boot") == "ON" and soil == "bare-metal-linux":
        v["secure_boot"] = ok(verdict="DEGRADED-KNOWN",
                               detail="Secure Boot ON + unsigned ipu7 modules (26.04.1): turn OFF or MOK-enroll or NPU refuses")
    elif sb.get("available"):
        v["secure_boot"] = ok(verdict="FIXED", detail="Secure Boot " + sb.get("secure_boot", "?"))
    else:
        v["secure_boot"] = ok(verdict="UNKNOWN", detail=sb.get("reason", "unreadable"))
    devs = [d for p in (ocl.get("detail") or []) for d in p.get("devices", [])]
    sane = [d for d in devs if d.get("max_mhz")]
    if ocl.get("available") and sane:
        v["gpu_compute"] = ok(verdict="FIXED",
                               detail="%d OpenCL device(s), clocks sane" % len(sane))
    elif ocl.get("available"):
        v["gpu_compute"] = ok(verdict="BROKEN-UPSTREAM",
                               detail="loader present, no usable devices")
    else:
        v["gpu_compute"] = ok(verdict="UNKNOWN", detail=ocl.get("reason", "unreadable"))
    return ok(subsystems=v)


def probe_rapl():
    if platform.system() != "Linux":
        return na("powercap sysfs only exists on Linux")
    zones = []
    for energy in sorted(glob.glob("/sys/class/powercap/intel-rapl*/energy_uj")):
        base = energy.rsplit("/", 1)[0]
        zones.append({"name": read1(base + "/name"),
                      "energy_uj": read1(energy),
                      "max_energy_range_uj": read1(base + "/max_energy_range_uj"),
                      "constraint0_max_power_uw": read1(base + "/constraint_0_max_power_uw")})
    if not zones:
        return na("no intel-rapl zones (not Intel, no powercap, or WSL guest)")
    return ok(zones=zones)


def main():
    out_path = None
    args = sys.argv[1:]
    if args[:1] == ["--out"] and len(args) > 1:
        out_path = args[1]
    report = {"probe": PROBE, "python": sys.version.split()[0],
              "platform": platform.platform()}
    for name, fn in (("soil", probe_soil), ("cpu", probe_cpu),
                     ("mem", probe_mem), ("pci", probe_pci),
                     ("drm", probe_drm), ("npu_module", probe_npu_module),
                     ("opencl", probe_opencl), ("rapl", probe_rapl),
                     ("secureboot", probe_secureboot)):
        try:
            report[name] = fn()
        except Exception as e:  # last-resort net: a probe never kills the report
            report[name] = na("probe crashed: %r" % e)
    report["frontier"] = verdict_frontier(report)
    soil = report["soil"].get("soil", "unknown")
    n_gpu = sum(len(p.get("devices", [])) for p in
                report["opencl"].get("detail", [])) if report["opencl"].get("available") else "?"
    drm = report.get("drm", {})
    npu = ("n/a-nonlinux" if not drm.get("available", False)
           else ("YES" if drm.get("npu_present") else "NO"))
    print("SOIL=%s CPU=%s GPU_opencl=%s NPU_accel=%s RAM_GB=%s" % (
        soil, (report["cpu"].get("model") or "?")[:60], n_gpu, npu,
        report["mem"].get("total_gb", "?")))
    text = json.dumps(report, indent=2)
    if out_path:
        with open(out_path, "w") as f:
            f.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
