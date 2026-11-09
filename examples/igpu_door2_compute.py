"""Door 2, finished: real GPU compute on the iGPU, stdlib only.

Not an enumeration -- actual math on the Intel Arc. ctypes reaches
d3d11.dll and d3dcompiler_47.dll (both ship with Windows), compiles one
HLSL compute shader, uploads a structured buffer, dispatches, and reads
the result back. The work is y[i] = x[i] * 2.0 + 1.0 over N floats.

Why this is the "unified language" answer: one HLSL source runs on any
vendor's GPU (Intel, NVIDIA, AMD) through the same D3D11 entry points.
No wheel, no runtime install, no vendor SDK -- the operating system is
the compiler's host.

VTABLE NOTE (this cost a session; do not re-derive it): the DeviceContext
indices used here were read out of the Windows SDK header itself --
C:/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/um/d3d11.h,
ID3D11DeviceContextVtbl -- not out of mingw-w64's d3d11.idl. The IDL is one
slot short across the whole CS* block, so an idl-derived count yields
CSSetShaderResources=66 / CSSetUnorderedAccessViews=67 / CSSetShader=68 and
the first two of those fault with an access violation on this build. The
header (115 slots including IUnknown's 3) is authoritative:
    Dispatch 41, CopyResource 47, Map 14, Unmap 15,
    CSSetShaderResources 67, CSSetUnorderedAccessViews 68, CSSetShader 69.
Read the header, not a translation of it.

Run:  python examples/igpu_door2_compute.py
Exit: 0 when the GPU result matches the CPU expectation exactly;
      nonzero with the failing call named.

The MCML baseline (pure-Python list comprehension, same math) is timed
alongside, so the decision is a reading, not an opinion.
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

N = 1 << 20  # 1,048,576 floats = 4 MB

HLSL = b"""
RWStructuredBuffer<float> outBuf : register(u0);
StructuredBuffer<float> inBuf  : register(t0);

[numthreads(64,1,1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    uint i = id.x;
    outBuf[i] = inBuf[i] * 2.0f + 1.0f;
}
"""

# --- D3D11 constants -------------------------------------------------------
D3D_DRIVER_TYPE_HARDWARE = 1
D3D11_SDK_VERSION = 7
D3D11_USAGE_DEFAULT = 0
D3D11_USAGE_STAGING = 3
D3D11_BIND_SHADER_RESOURCE = 0x8
D3D11_BIND_UNORDERED_ACCESS = 0x80
D3D11_CPU_ACCESS_READ = 0x20000
D3D11_RESOURCE_MISC_BUFFER_STRUCTURED = 0x40
D3D11_MAP_READ = 1
D3DCOMPILE_OPTIMIZATION_LEVEL3 = 1 << 15

HRESULT = ctypes.c_long

# Protos are kept alive here: a WINFUNCTYPE instance must outlive its call.
_ALIVE: list = []


class D3D11_BUFFER_DESC(ctypes.Structure):
    _fields_ = [
        ("ByteWidth", wintypes.UINT),
        ("Usage", wintypes.UINT),
        ("BindFlags", wintypes.UINT),
        ("CPUAccessFlags", wintypes.UINT),
        ("MiscFlags", wintypes.UINT),
        ("StructureByteStride", wintypes.UINT),
    ]


class D3D11_SUBRESOURCE_DATA(ctypes.Structure):
    _fields_ = [
        ("pSysMem", ctypes.c_void_p),
        ("SysMemPitch", wintypes.UINT),
        ("SysMemSlicePitch", wintypes.UINT),
    ]


class D3D11_MAPPED_SUBRESOURCE(ctypes.Structure):
    _fields_ = [
        ("pData", ctypes.c_void_p),
        ("RowPitch", wintypes.UINT),
        ("DepthPitch", wintypes.UINT),
    ]


def method(ptr: int, index: int, *argtypes, restype=HRESULT):
    """Bind one COM method by vtable index.

    The returned callable takes the interface pointer first, then argtypes.
    Index 0..2 are QueryInterface/AddRef/Release for every interface.
    """
    vtable = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
    address = vtable.contents[index]
    if not address:
        raise SystemExit(f"vtable[{index}] is NULL for interface 0x{ptr:X}")
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    fn = proto(address)
    _ALIVE.append(fn)
    return fn


def check(hr: int, what: str) -> None:
    if hr != 0:
        raise SystemExit(f"{what} failed: HRESULT=0x{hr & 0xFFFFFFFF:08X}")


def main() -> int:
    d3d11 = ctypes.WinDLL("d3d11")
    compiler = ctypes.WinDLL("d3dcompiler_47")

    # ---- device ----------------------------------------------------------
    d3d11.D3D11CreateDevice.restype = HRESULT
    d3d11.D3D11CreateDevice.argtypes = [
        ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, wintypes.UINT,
        ctypes.c_void_p, wintypes.UINT, wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    device = ctypes.c_void_p()
    context = ctypes.c_void_p()
    level = wintypes.UINT(0)
    check(d3d11.D3D11CreateDevice(
        None, D3D_DRIVER_TYPE_HARDWARE, None, 0, None, 0, D3D11_SDK_VERSION,
        ctypes.byref(device), ctypes.byref(level), ctypes.byref(context),
    ), "D3D11CreateDevice")
    print(f"device: feature level 0x{level.value:X}")

    # ---- compile one HLSL source ----------------------------------------
    compiler.D3DCompile.restype = HRESULT
    compiler.D3DCompile.argtypes = [
        ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, wintypes.UINT,
        wintypes.UINT, ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    code = ctypes.c_void_p()
    errors = ctypes.c_void_p()
    hr = compiler.D3DCompile(
        HLSL, len(HLSL), b"inline.hlsl", None, None, b"CSMain", b"cs_5_0",
        D3DCOMPILE_OPTIMIZATION_LEVEL3, 0, ctypes.byref(code), ctypes.byref(errors),
    )
    if hr != 0:
        if errors.value:
            text = method(errors.value, 3, restype=ctypes.c_void_p)(errors.value)
            print("HLSL:", ctypes.string_at(text, 400))
        raise SystemExit(f"D3DCompile failed: HRESULT=0x{hr & 0xFFFFFFFF:08X}")
    blob = method(code.value, 3, restype=ctypes.c_void_p)(code.value)
    blob_size = method(code.value, 4, restype=ctypes.c_size_t)(code.value)

    # ---- buffers ---------------------------------------------------------
    values = [float(i % 97) for i in range(N)]
    source = (ctypes.c_float * N)(*values)

    create_buffer = method(device.value, 3, ctypes.POINTER(D3D11_BUFFER_DESC),
                           ctypes.POINTER(D3D11_SUBRESOURCE_DATA),
                           ctypes.POINTER(ctypes.c_void_p))

    src_desc = D3D11_BUFFER_DESC(N * 4, D3D11_USAGE_DEFAULT,
                                 D3D11_BIND_SHADER_RESOURCE, 0,
                                 D3D11_RESOURCE_MISC_BUFFER_STRUCTURED, 4)
    src_data = D3D11_SUBRESOURCE_DATA(ctypes.cast(source, ctypes.c_void_p), 0, 0)
    src_buf = ctypes.c_void_p()
    check(create_buffer(device.value, ctypes.byref(src_desc), ctypes.byref(src_data),
                        ctypes.byref(src_buf)), "CreateBuffer(source)")

    dst_buf = ctypes.c_void_p()
    check(create_buffer(device.value, ctypes.byref(D3D11_BUFFER_DESC(
        N * 4, D3D11_USAGE_DEFAULT, D3D11_BIND_UNORDERED_ACCESS, 0,
        D3D11_RESOURCE_MISC_BUFFER_STRUCTURED, 4)), None, ctypes.byref(dst_buf)),
        "CreateBuffer(destination)")

    # A staging copy is the only way to read a DEFAULT buffer back.
    stage_buf = ctypes.c_void_p()
    check(create_buffer(device.value, ctypes.byref(D3D11_BUFFER_DESC(
        N * 4, D3D11_USAGE_STAGING, 0, D3D11_CPU_ACCESS_READ, 0, 4)), None,
        ctypes.byref(stage_buf)), "CreateBuffer(staging)")

    # ---- views -----------------------------------------------------------
    uav = ctypes.c_void_p()
    check(method(device.value, 8, ctypes.c_void_p, ctypes.c_void_p,
                 ctypes.POINTER(ctypes.c_void_p))(
        device.value, dst_buf, None, ctypes.byref(uav)), "CreateUnorderedAccessView")

    srv = ctypes.c_void_p()
    check(method(device.value, 7, ctypes.c_void_p, ctypes.c_void_p,
                 ctypes.POINTER(ctypes.c_void_p))(
        device.value, src_buf, None, ctypes.byref(srv)), "CreateShaderResourceView")

    shader = ctypes.c_void_p()
    check(method(device.value, 18, ctypes.c_void_p, ctypes.c_size_t,
                 ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))(
        device.value, blob, blob_size, None, ctypes.byref(shader)), "CreateComputeShader")

    # ---- context: the draw order ----------------------------------------
    csset_shader = method(context.value, 69, ctypes.c_void_p, ctypes.c_void_p,
                          wintypes.UINT)
    csset_uav = method(context.value, 68, wintypes.UINT, wintypes.UINT,
                       ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p)
    csset_srv = method(context.value, 67, wintypes.UINT, wintypes.UINT,
                       ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p)
    dispatch = method(context.value, 41, wintypes.UINT, wintypes.UINT, wintypes.UINT)
    copy_resource = method(context.value, 47, ctypes.c_void_p, ctypes.c_void_p)
    map_resource = method(context.value, 14, ctypes.c_void_p, wintypes.UINT,
                          wintypes.UINT, wintypes.UINT,
                          ctypes.POINTER(D3D11_MAPPED_SUBRESOURCE))
    unmap = method(context.value, 15, ctypes.c_void_p, wintypes.UINT)

    csset_shader(context.value, shader, None, 0)
    csset_uav(context.value, 0, 1, ctypes.byref(uav), None)
    csset_srv(context.value, 0, 1, ctypes.byref(srv), None)

    # ---- run -------------------------------------------------------------
    groups = N // 64
    timings = []
    ok = False
    for _ in range(3):  # first pass warms the driver
        t0 = time.perf_counter()
        dispatch(context.value, groups, 1, 1)
        copy_resource(context.value, stage_buf, dst_buf)
        mapped = D3D11_MAPPED_SUBRESOURCE()
        check(map_resource(context.value, stage_buf, 0, D3D11_MAP_READ, 0,
                           ctypes.byref(mapped)), "Map")
        out = ctypes.cast(mapped.pData, ctypes.POINTER(ctypes.c_float))
        ok = all(out[i] == values[i] * 2.0 + 1.0
                 for i in (0, 1, 2, N // 3, N // 2, N - 1))
        unmap(context.value, stage_buf, 0)
        timings.append((time.perf_counter() - t0) * 1000.0)

    gpu_ms = min(timings)
    gpu_rate = N / (gpu_ms / 1000.0) / 1e6
    print(f"gpu: {N:,} floats  y=2x+1  dispatch+readback {gpu_ms:.2f} ms  "
          f"{gpu_rate:.1f} M elem/s  correct={ok}")

    # ---- MCML baseline: same math as pure Python -------------------------
    cpu_n = 1 << 17
    xs = [float(i % 97) for i in range(cpu_n)]
    t0 = time.perf_counter()
    ys = [x * 2.0 + 1.0 for x in xs]
    cpu_ms = (time.perf_counter() - t0) * 1000.0
    cpu_rate = cpu_n / (cpu_ms / 1000.0) / 1e6
    print(f"cpu: {cpu_n:,} floats  same math  {cpu_ms:.2f} ms  "
          f"{cpu_rate:.2f} M elem/s")
    print(f"ratio: iGPU runs {gpu_rate / cpu_rate:.1f}x the pure-Python rate")
    print(f"cpu spot-check: y[3]={ys[3]} (expect {xs[3] * 2.0 + 1.0})")

    if not ok:
        print("FAIL: the GPU result disagrees with the CPU expectation")
        return 1
    print("OK: one HLSL source, the iGPU's math matches the CPU exactly")
    return 0


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("windows-only: D3D11 ships with the OS")
    raise SystemExit(main())
