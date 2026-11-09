"""Door 2, finished: real GPU math on the iGPU with NOTHING but the stdlib.

Standard library only (ctypes + time). No numpy, no torch, no onnxruntime,
no pip install of any kind. It loads the Khronos ICD loader that ships with
Windows (C:/Windows/System32/OpenCL.dll), which forwards to the vendor driver
(Intel's intelocl64.dll is the one registered on this machine).

Why OpenCL and not D3D11 (examples/igpu_door2_compute.py): Direct3D is a COM
interface, so every call is a hand-computed vtable index -- one wrong index is
an access violation, and the index cannot be discovered at runtime. OpenCL is a
flat C API: clBuildProgram(program, ...) is a name in a DLL, resolved by ctypes.
One C kernel runs on Intel, AMD, NVIDIA, Apple, or a CPU fallback unchanged --
that is the "unified language" property, and it is why this is the example that
finishes.

Run:
    C:/Azazael/.venvs/py316t/Scripts/python.exe examples/igpu_opencl_compute.py
    python3 examples/igpu_opencl_compute.py          # same file, on Linux

Expected output ends with:
    VERDICT: GPU produced y = 2x + 1 for 1,048,576 floats, ...
    opencl compute: exit 0
"""

from __future__ import annotations

import ctypes
import ctypes.util
import time
from ctypes import wintypes

# --------------------------------------------------------------------------- #
# OpenCL constants we actually use (from CL/cl.h)
# --------------------------------------------------------------------------- #
CL_SUCCESS = 0
CL_DEVICE_TYPE_GPU = 1 << 2
CL_PLATFORM_NAME = 0x0902
CL_DEVICE_NAME = 0x102B
CL_DEVICE_MAX_COMPUTE_UNITS = 0x1002
CL_DEVICE_GLOBAL_MEM_SIZE = 0x101F
CL_PROGRAM_BUILD_LOG = 0x1183
CL_MEM_READ_ONLY = 1 << 2
CL_MEM_WRITE_ONLY = 1 << 1
CL_TRUE = 1

N = 1 << 20  # 1,048,576 floats = 4 MiB per buffer

KERNEL_SOURCE = b"""
__kernel void axpy(__global const float* a,
                   __global float* b,
                   const float scale,
                   const float shift)
{
    size_t i = get_global_id(0);
    b[i] = scale * a[i] + shift;
}
"""


def _lib():
    """Load the Khronos ICD loader. Windows ships it in System32; on Linux the
    same file is libOpenCL.so.1 (mesa or the vendor ICD). The example is written
    once and runs on both, which is the whole point of the flat C API."""
    for name in (ctypes.util.find_library("OpenCL"), "OpenCL.dll", "libOpenCL.so.1", "libOpenCL.so"):
        if not name:
            continue
        try:
            return ctypes.CDLL(name)
        except OSError:
            continue
    raise SystemExit("no OpenCL ICD loader found (libOpenCL.so.1 / OpenCL.dll)")


def _brief(err: int) -> str:
    return {
        0: "CL_SUCCESS",
        -1: "CL_DEVICE_NOT_FOUND",
        -2: "CL_DEVICE_NOT_AVAILABLE",
        -5: "CL_OUT_OF_RESOURCES",
        -6: "CL_OUT_OF_HOST_MEMORY",
        -30: "CL_INVALID_VALUE",
        -31: "CL_INVALID_DEVICE_TYPE",
        -32: "CL_INVALID_PLATFORM",
        -33: "CL_INVALID_DEVICE",
        -34: "CL_INVALID_CONTEXT",
        -44: "CL_INVALID_PROGRAM",
        -45: "CL_INVALID_PROGRAM_EXECUTABLE",
        -46: "CL_INVALID_KERNEL_NAME",
        -47: "CL_INVALID_KERNEL_DEFINITION",
        -48: "CL_INVALID_KERNEL",
        -49: "CL_INVALID_ARG_INDEX",
        -50: "CL_INVALID_ARG_VALUE",
        -51: "CL_INVALID_ARG_SIZE",
        -52: "CL_INVALID_KERNEL_ARGS",
        -54: "CL_INVALID_WORK_GROUP_SIZE",
        -55: "CL_INVALID_WORK_ITEM_SIZE",
        -56: "CL_INVALID_GLOBAL_OFFSET",
        1: "CL_DEVICE_NOT_FOUND(raw fail)",
    }.get(err, f"CL error {err}")


def _check(err: int, what: str) -> None:
    if err != CL_SUCCESS:
        raise SystemExit(f"{what} failed: {_brief(err)} (code {err})")


def _info_str(cl, handle: int, param: int, getter) -> str:
    size = ctypes.c_size_t()
    _check(getter(handle, param, 0, None, ctypes.byref(size)), f"size query {param:#x}")
    if size.value == 0:
        return "<empty>"
    buf = ctypes.create_string_buffer(size.value)
    _check(getter(handle, param, size.value, buf, None), f"read info {param:#x}")
    return buf.value.decode("utf-8", "replace").strip()


def main() -> int:
    cl = _lib()

    # ---- prototypes: every one is a *name*, not a vtable slot -------------- #
    cl.clGetPlatformIDs.argtypes = [wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(wintypes.UINT)]
    cl.clGetPlatformIDs.restype = ctypes.c_int
    cl.clGetPlatformInfo.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    cl.clGetPlatformInfo.restype = ctypes.c_int
    cl.clGetDeviceIDs.argtypes = [ctypes.c_void_p, ctypes.c_ulonglong, wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(wintypes.UINT)]
    cl.clGetDeviceIDs.restype = ctypes.c_int
    cl.clGetDeviceInfo.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    cl.clGetDeviceInfo.restype = ctypes.c_int
    cl.clCreateContext.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    cl.clCreateContext.restype = ctypes.c_void_p
    cl.clCreateCommandQueue.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong, ctypes.POINTER(ctypes.c_int)]
    cl.clCreateCommandQueue.restype = ctypes.c_void_p
    cl.clCreateProgramWithSource.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_int)]
    cl.clCreateProgramWithSource.restype = ctypes.c_void_p
    cl.clBuildProgram.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p]
    cl.clBuildProgram.restype = ctypes.c_int
    cl.clGetProgramBuildInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    cl.clGetProgramBuildInfo.restype = ctypes.c_int
    cl.clCreateKernel.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
    cl.clCreateKernel.restype = ctypes.c_void_p
    cl.clCreateBuffer.argtypes = [ctypes.c_void_p, ctypes.c_ulonglong, ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    cl.clCreateBuffer.restype = ctypes.c_void_p
    cl.clSetKernelArg.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_size_t, ctypes.c_void_p]
    cl.clSetKernelArg.restype = ctypes.c_int
    cl.clEnqueueNDRangeKernel.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t), wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p]
    cl.clEnqueueNDRangeKernel.restype = ctypes.c_int
    cl.clEnqueueWriteBuffer.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p]
    cl.clEnqueueWriteBuffer.restype = ctypes.c_int
    cl.clEnqueueReadBuffer.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p]
    cl.clEnqueueReadBuffer.restype = ctypes.c_int
    cl.clFinish.argtypes = [ctypes.c_void_p]
    cl.clFinish.restype = ctypes.c_int

    # ---- 1. platform ------------------------------------------------------ #
    n_plat = wintypes.UINT()
    _check(cl.clGetPlatformIDs(0, None, ctypes.byref(n_plat)), "clGetPlatformIDs(count)")
    platforms = (ctypes.c_void_p * n_plat.value)()
    _check(cl.clGetPlatformIDs(n_plat.value, platforms, None), "clGetPlatformIDs(list)")
    platform = platforms[0]
    print(f"platforms: {n_plat.value}  [{_info_str(cl, platform, CL_PLATFORM_NAME, cl.clGetPlatformInfo)}]")

    # ---- 2. device -------------------------------------------------------- #
    n_dev = wintypes.UINT()
    _check(cl.clGetDeviceIDs(platform, CL_DEVICE_TYPE_GPU, 0, None, ctypes.byref(n_dev)), "clGetDeviceIDs(count)")
    if n_dev.value == 0:
        raise SystemExit("no GPU device reported by the ICD loader")
    devices = (ctypes.c_void_p * n_dev.value)()
    _check(cl.clGetDeviceIDs(platform, CL_DEVICE_TYPE_GPU, n_dev.value, devices, None), "clGetDeviceIDs(list)")
    device = devices[0]

    cu = wintypes.UINT()
    _check(cl.clGetDeviceInfo(device, CL_DEVICE_MAX_COMPUTE_UNITS, ctypes.sizeof(cu), ctypes.byref(cu), None), "max compute units")
    gmem = ctypes.c_ulonglong()
    _check(cl.clGetDeviceInfo(device, CL_DEVICE_GLOBAL_MEM_SIZE, ctypes.sizeof(gmem), ctypes.byref(gmem), None), "global mem size")
    print(f"device:    {_info_str(cl, device, CL_DEVICE_NAME, cl.clGetDeviceInfo)}")
    print(f"           {cu.value} compute units, {gmem.value / 2**30:.1f} GiB global memory")

    # ---- 3. context + queue ----------------------------------------------- #
    err = ctypes.c_int()
    context = cl.clCreateContext(None, 1, devices, None, None, ctypes.byref(err))
    _check(err.value, "clCreateContext")
    queue = cl.clCreateCommandQueue(context, device, 0, ctypes.byref(err))
    _check(err.value, "clCreateCommandQueue")

    # ---- 4. compile the kernel ON the GPU's own compiler ------------------ #
    src = ctypes.c_char_p(KERNEL_SOURCE)
    length = ctypes.c_size_t(len(KERNEL_SOURCE))
    program = cl.clCreateProgramWithSource(context, 1, ctypes.byref(src), ctypes.byref(length), ctypes.byref(err))
    _check(err.value, "clCreateProgramWithSource")
    build = cl.clBuildProgram(program, 1, devices, b"-cl-mad-enable", None, None)
    if build != CL_SUCCESS:
        size = ctypes.c_size_t()
        cl.clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, 0, None, ctypes.byref(size))
        log = ctypes.create_string_buffer(max(size.value, 1))
        cl.clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, size.value, log, None)
        raise SystemExit(f"kernel build failed: {_brief(build)}\n{log.value.decode('utf-8', 'replace')}")
    kernel = cl.clCreateKernel(program, b"axpy", ctypes.byref(err))
    _check(err.value, "clCreateKernel")

    # ---- 5. host data, buffers, arguments -------------------------------- #
    host_in = (ctypes.c_float * N)(*[float(i % 97) for i in range(N)])
    probes = (0, 1, 2, N // 3, N // 2, N - 1)
    expect = {i: 2.0 * host_in[i] + 1.0 for i in probes}
    host_out = (ctypes.c_float * N)()

    buf_in = cl.clCreateBuffer(context, CL_MEM_READ_ONLY, N * 4, None, ctypes.byref(err))
    _check(err.value, "clCreateBuffer(in)")
    buf_out = cl.clCreateBuffer(context, CL_MEM_WRITE_ONLY, N * 4, None, ctypes.byref(err))
    _check(err.value, "clCreateBuffer(out)")

    scale = ctypes.c_float(2.0)
    shift = ctypes.c_float(1.0)
    _check(cl.clSetKernelArg(kernel, 0, ctypes.sizeof(ctypes.c_void_p), ctypes.byref(ctypes.c_void_p(buf_in))), "arg0")
    _check(cl.clSetKernelArg(kernel, 1, ctypes.sizeof(ctypes.c_void_p), ctypes.byref(ctypes.c_void_p(buf_out))), "arg1")
    _check(cl.clSetKernelArg(kernel, 2, ctypes.sizeof(scale), ctypes.byref(scale)), "arg2")
    _check(cl.clSetKernelArg(kernel, 3, ctypes.sizeof(shift), ctypes.byref(shift)), "arg3")

    # ---- 6. move data in, dispatch, move data out ------------------------ #
    global_size = ctypes.c_size_t(N)
    runs = []
    readback = None
    for _ in range(3):
        t0 = time.perf_counter()
        _check(cl.clEnqueueWriteBuffer(queue, buf_in, CL_TRUE, 0, N * 4, host_in, 0, None, None), "write")
        _check(cl.clEnqueueNDRangeKernel(queue, kernel, 1, None, ctypes.byref(global_size), None, 0, None, None), "kernel")
        _check(cl.clEnqueueReadBuffer(queue, buf_out, CL_TRUE, 0, N * 4, host_out, 0, None, None), "read")
        _check(cl.clFinish(queue), "finish")
        runs.append((time.perf_counter() - t0) * 1000.0)
        readback = host_out

    assert readback is not None
    probe = {i: readback[i] for i in probes}
    correct = all(abs(probe[i] - expect[i]) < 1e-6 for i in probes)

    # ---- 7. the baseline this replaces: pure-Python, same arithmetic ----- #
    t0 = time.perf_counter()
    py_out = [2.0 * v + 1.0 for v in host_in]
    py_ms = (time.perf_counter() - t0) * 1000.0
    py_ok = abs(py_out[N // 2] - expect[N // 2]) < 1e-6

    gpu_ms = min(runs)
    print()
    print(f"workload:  y = 2x + 1 over {N:,} floats ({N*4/2**20:.0f} MiB per buffer)")
    print(f"  GPU (OpenCL): {gpu_ms:8.2f} ms  (3 runs: " + ", ".join(f"{r:.2f}" for r in runs) + ")")
    print(f"  CPU (python): {py_ms:8.2f} ms  list comprehension, same formula")
    print(f"  speedup:      {py_ms / gpu_ms:6.2f}x   (includes both PCIe transfers, not just the kernel)")
    shown = (0, 1, N - 1)
    print(f"  gpu values:   " + ", ".join(f"[{i}]={probe[i]:.1f}" for i in shown))
    print(f"  expected:     " + ", ".join(f"[{i}]={expect[i]:.1f}" for i in shown))
    print()
    if not (correct and py_ok):
        print("VERDICT: FAIL -- GPU output does not match the reference")
        return 1
    print(f"VERDICT: GPU produced y = 2x + 1 for {N:,} floats, matching the reference on all probes")
    print("opencl compute: exit 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
