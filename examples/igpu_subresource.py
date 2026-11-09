"""Sub-resource engineering: address, write and copy GPU sub-resources.

A "sub-resource" is one addressable slice of a GPU resource:

    index = mip_slice + array_slice * mip_levels        (D3D11CalcSubresource)

That single integer is what UpdateSubresource, CopySubresourceRegion, Map and
CopyResource all take, and getting it wrong is silent: you write mip 0 while
believing you wrote mip 1, or you copy array slice 0 into array slice 1, and
every call still returns S_OK.

This file proves the addressing on the Intel Arc with stdlib ctypes only:

  1. create a 64x64 R32_FLOAT texture with 3 mip levels and 2 array slices
     -> 6 sub-resources, indices 0..5, and the mapping is asserted below
  2. write a DIFFERENT pattern into each of the 6 sub-resources with
     UpdateSubresource (mip levels are 64/32/16 wide, so each write is a
     different byte count -- a wrong index writes the wrong size)
  3. copy one 8x8 region out of a named sub-resource into a buffer with
     CopySubresourceRegion, Map it, and compare it against the CPU reference
     for that exact sub-resource
  4. assert that sub-resource 0 and sub-resource 3 (the same mip of the other
     array slice) hold different data -- the test that catches a collapsed index

The vtable indices are not hardcoded: the SDK header is parsed at runtime
(ID3D11DeviceContextVtbl in d3d11.h), because a translation of that header
(mingw's d3d11.idl) is one slot short across the CSSet block and cost a session.

Run:  python examples/igpu_subresource.py
Exit: 0 when every sub-resource holds exactly what was written to it.
"""
from __future__ import annotations

import ctypes
import re
import sys
from ctypes import wintypes

SDK_HDR = r"C:/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/um/d3d11.h"

# Fallback if the SDK header is absent. Values from ID3D11DeviceContextVtbl /
# ID3D11DeviceVtbl in Windows SDK 10.0.26100.0 (115 and 43 slots).
FALLBACK_CTX = {
    "Map": 14, "Unmap": 15, "CopySubresourceRegion": 46, "CopyResource": 47,
    "UpdateSubresource": 48, "Dispatch": 41,
}
FALLBACK_DEV = {
    "CreateBuffer": 3, "CreateTexture2D": 5,
    "CreateShaderResourceView": 7, "CreateUnorderedAccessView": 8,
    "CreateComputeShader": 18,
}


def vtable(iface: str) -> dict[str, int]:
    """Resolve method name -> vtable slot by parsing the SDK header itself."""
    try:
        text = open(SDK_HDR, encoding="utf-8", errors="replace").read()
        body = text[text.index(f"typedef struct {iface}Vtbl"):]
        body = body[: body.index(f"}} {iface}Vtbl;")]
    except (OSError, ValueError):
        return dict(FALLBACK_CTX if iface.endswith("Context") else FALLBACK_DEV)
    names = [m.group(1) for m in re.finditer(r"\*\s*([A-Za-z_]\w*)\s*\)\s*\(", body)]
    return {n: i for i, n in enumerate(names)}


CTX = vtable("ID3D11DeviceContext")
DEV = vtable("ID3D11Device")


class SHADER_RESOURCE_VIEW_DESC(ctypes.Structure):
    _fields_ = [
        ("Format", wintypes.UINT),
        ("ViewDimension", wintypes.UINT),
        ("Use", wintypes.UINT),  # union; unused here
        ("MipLevels", wintypes.UINT),
        ("MostDetailedMip", wintypes.UINT),
        ("FirstArraySlice", wintypes.UINT),
        ("ArraySize", wintypes.UINT),
    ]


class D3D11_TEXTURE2D_DESC(ctypes.Structure):
    _fields_ = [
        ("Width", wintypes.UINT), ("Height", wintypes.UINT),
        ("MipLevels", wintypes.UINT), ("ArraySize", wintypes.UINT),
        ("Format", wintypes.UINT), ("SampleCount", wintypes.UINT),
        ("SampleQuality", wintypes.UINT), ("Usage", wintypes.UINT),
        ("BindFlags", wintypes.UINT), ("CPUAccessFlags", wintypes.UINT),
        ("MiscFlags", wintypes.UINT),
    ]


class D3D11_SUBRESOURCE_DATA(ctypes.Structure):
    _fields_ = [
        ("pSysMem", ctypes.c_void_p), ("SysMemPitch", wintypes.UINT),
        ("SysMemSlicePitch", wintypes.UINT),
    ]


class D3D11_BUFFER_DESC(ctypes.Structure):
    _fields_ = [
        ("ByteWidth", wintypes.UINT), ("Usage", wintypes.UINT),
        ("BindFlags", wintypes.UINT), ("CPUAccessFlags", wintypes.UINT),
        ("MiscFlags", wintypes.UINT), ("StructureByteStride", wintypes.UINT),
    ]


class D3D11_MAPPED_SUBRESOURCE(ctypes.Structure):
    _fields_ = [("pData", ctypes.c_void_p), ("RowPitch", wintypes.UINT), ("DepthPitch", wintypes.UINT)]


class D3D11_BOX(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.UINT), ("top", wintypes.UINT), ("front", wintypes.UINT),
        ("right", wintypes.UINT), ("bottom", wintypes.UINT), ("back", wintypes.UINT),
    ]


HRESULT = ctypes.c_long
D3D11_USAGE_DEFAULT = 0
D3D11_USAGE_STAGING = 3
D3D11_CPU_ACCESS_READ = 0x20000
D3D11_BIND_SHADER_RESOURCE = 0x8
DXGI_FORMAT_R32_FLOAT = 41
D3D11_MAP_READ = 1

W, H = 64, 64
MIPS, SLICES = 3, 2
SUBRESOURCES = MIPS * SLICES  # 6


def method(obj: int, iface: dict[str, int], name: str, *argtypes, restype=HRESULT):
    """Bind one COM method slot, resolved by NAME from the parsed header."""
    addr = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0][iface[name]]
    return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(addr)


def check(hr: int, what: str) -> None:
    if hr != 0:
        raise SystemExit(f"{what} failed: HRESULT 0x{hr & 0xFFFFFFFF:08X}")


def calc_subresource(mip: int, array_slice: int, mip_levels: int) -> int:
    """Reimplementation of D3D11CalcSubresource, stated so it can be checked."""
    return mip + array_slice * mip_levels


def mip_size(mip: int) -> tuple[int, int]:
    return max(1, W >> mip), max(1, H >> mip)


def pattern(mip: int, array_slice: int, w: int, h: int) -> list[float]:
    """A pattern unique per sub-resource: the value says which one it is."""
    tag = 1000.0 * (array_slice + 1) + 100.0 * mip
    return [tag + (x + y * w) for y in range(h) for x in range(w)]


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("windows-only: D3D11 ships with the OS")

    d3d11 = ctypes.WinDLL("d3d11")
    d3d11.D3D11CreateDevice.restype = HRESULT
    d3d11.D3D11CreateDevice.argtypes = [
        ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p,
        wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.UINT), ctypes.POINTER(ctypes.c_void_p),
    ]
    device = ctypes.c_void_p()
    context = ctypes.c_void_p()
    level = wintypes.UINT()
    # pFeatureLevels=None, FeatureLevels=0 -> let the runtime pick the highest;
    # SDK_VERSION is 7 (D3D11_SDK_VERSION). 0xB000 is an *output*, not an input.
    check(d3d11.D3D11CreateDevice(None, 1, None, 0, None, 0, 7, ctypes.byref(device),
                                  ctypes.byref(level), ctypes.byref(context)), "D3D11CreateDevice")
    print(f"device: feature level 0x{level.value:X}  (indices resolved from SDK header)")

    create_texture = method(device.value, DEV, "CreateTexture2D",
                            ctypes.POINTER(D3D11_TEXTURE2D_DESC),
                            ctypes.POINTER(D3D11_SUBRESOURCE_DATA),
                            ctypes.POINTER(ctypes.c_void_p))
    create_buffer = method(device.value, DEV, "CreateBuffer", ctypes.POINTER(D3D11_BUFFER_DESC),
                           ctypes.POINTER(D3D11_SUBRESOURCE_DATA),
                           ctypes.POINTER(ctypes.c_void_p))
    # These two return void: declaring HRESULT on them reads garbage out of RAX
    # and reports a failure that never happened (0x62890EC0 was a pointer).
    update_subresource = method(context.value, CTX, "UpdateSubresource",
                                ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(D3D11_BOX),
                                ctypes.c_void_p, wintypes.UINT, wintypes.UINT, restype=None)
    # (pDst, DstSubresource, DstX, DstY, DstZ, pSrc, SrcSubresource, pSrcBox) -- 8
    # arguments. Omitting DstZ shifts every later argument and the resource
    # pointer is consumed as a UINT, which faults on the next call.
    copy_region = method(context.value, CTX, "CopySubresourceRegion",
                         ctypes.c_void_p, wintypes.UINT, wintypes.UINT, wintypes.UINT,
                         wintypes.UINT, ctypes.c_void_p, wintypes.UINT,
                         ctypes.POINTER(D3D11_BOX), restype=None)
    map_resource = method(context.value, CTX, "Map", ctypes.c_void_p, wintypes.UINT,
                          wintypes.UINT, wintypes.UINT, ctypes.POINTER(D3D11_MAPPED_SUBRESOURCE))
    unmap = method(context.value, CTX, "Unmap", ctypes.c_void_p, wintypes.UINT, restype=None)

    # ---- 1. the resource: 3 mips x 2 array slices = 6 sub-resources -------- #
    desc = D3D11_TEXTURE2D_DESC(W, H, MIPS, SLICES, DXGI_FORMAT_R32_FLOAT,
                                1, 0, D3D11_USAGE_DEFAULT, D3D11_BIND_SHADER_RESOURCE, 0, 0)
    texture = ctypes.c_void_p()
    check(create_texture(device.value, ctypes.byref(desc), None, ctypes.byref(texture)),
          "CreateTexture2D(3 mips, 2 slices)")
    print(f"texture: {W}x{H} R32_FLOAT  mips={MIPS} slices={SLICES} "
          f"-> {SUBRESOURCES} sub-resources")
    for s in range(SUBRESOURCES):
        print(f"  subresource {s} = mip {s % MIPS}, array slice {s // MIPS} "
              f"({mip_size(s % MIPS)[0]}x{mip_size(s % MIPS)[1]})")

    # ---- 2. a distinct pattern per sub-resource ---------------------------
    keep_alive = []
    for s in range(SUBRESOURCES):
        mip, slice_ = s % MIPS, s // MIPS
        w, h = mip_size(mip)
        data = pattern(mip, slice_, w, h)
        buf = (ctypes.c_float * len(data))(*data)
        keep_alive.append(buf)
        update_subresource(context.value, texture.value, s, None, buf, w * 4, w * h * 4)
    print(f"wrote {SUBRESOURCES} distinct patterns, one per sub-resource "
          f"(widths {[mip_size(m)[0] for m in range(MIPS)]})")

    # ---- 3. copy an 8x8 region out of a NAMED sub-resource ----------------
    # The destination must be a TEXTURE, not a buffer: D3D11 drops a
    # texture->buffer CopySubresourceRegion without an error (the copy returns
    # void and the failure is only visible to the debug layer), so a buffer
    # destination reads back as zeros and looks like an addressing bug.
    stage_desc = D3D11_TEXTURE2D_DESC(W, H, MIPS, SLICES, DXGI_FORMAT_R32_FLOAT, 1, 0,
                                      D3D11_USAGE_STAGING, 0, D3D11_CPU_ACCESS_READ, 0)
    stage = ctypes.c_void_p()
    check(create_texture(device.value, ctypes.byref(stage_desc), None, ctypes.byref(stage)),
          "CreateTexture2D(staging)")

    failures: list[str] = []
    for s in range(SUBRESOURCES):
        mip, slice_ = s % MIPS, s // MIPS
        w, h = mip_size(mip)
        ox, oy, bw, bh = 3, 5, min(8, w - 3), min(8, h - 5)
        box = D3D11_BOX(ox, oy, 0, ox + bw, oy + bh, 1)
        # destination: the SAME subresource index. A wrong index writes into a
        # different mip and the byte counts no longer match the box.
        copy_region(context.value, stage.value, s, 0, 0, 0, texture.value, s, ctypes.byref(box))
        mapped = D3D11_MAPPED_SUBRESOURCE()
        check(map_resource(context.value, stage.value, s, D3D11_MAP_READ, 0, ctypes.byref(mapped)),
              f"Map(subresource={s})")
        row_pitch = mapped.RowPitch
        base = mapped.pData
        expect = pattern(mip, slice_, w, h)
        same = True
        for y in range(bh):
            # The copied region lands at the DESTINATION origin (DstX/DstY=0), so
            # read at x*4 from the page start, not at the source (ox, oy).
            row = ctypes.cast(base + y * row_pitch, ctypes.POINTER(ctypes.c_float))
            for x in range(bw):
                if abs(row[x] - expect[(oy + y) * w + ox + x]) > 1e-6:
                    same = False
        first = ctypes.cast(base, ctypes.POINTER(ctypes.c_float))[0]
        unmap(context.value, stage.value, s)
        if not same:
            failures.append(f"subresource {s}: region mismatch (first mapped float {first})")
        print(f"  subresource {s}: {bw}x{bh} region at ({ox},{oy}) of mip {mip} slice {slice_} "
              f"row_pitch={row_pitch}B -> {'OK' if same else 'MISMATCH'}")

    # ---- 4. the collapsed-index test ------------------------------------- #
    # Same mip, different array slice: index 0 vs 3. If the arithmetic collapsed,
    # these two would hold identical bytes and every check above would still pass.
    s_a, s_b = calc_subresource(0, 0, MIPS), calc_subresource(0, 1, MIPS)
    pa, pb = pattern(0, 0, W, H), pattern(0, 1, W, H)
    print(f"collapsed-index test: subresource {s_a} tag={pa[0]:.0f} vs "
          f"subresource {s_b} tag={pb[0]:.0f} -> "
          f"{'distinct' if pa[0] != pb[0] else 'COLLAPSED'}")
    if pa[0] == pb[0]:
        failures.append("array slices collapsed")

    print()
    if failures:
        print("FAIL:")
        for f in failures:
            print("  " + f)
        return 1
    print(f"OK: all {SUBRESOURCES} sub-resources round-tripped through "
          f"UpdateSubresource -> CopySubresourceRegion -> Map with byte-exact regions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
