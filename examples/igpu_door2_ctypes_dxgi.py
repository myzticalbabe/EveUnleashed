"""Door 2 finished example: reach the iGPU with stdlib only.

No numpy, no torch, no onnxruntime, no OpenVINO -- ctypes + dxgi.dll,
which ships with Windows. Enumerates every GPU adapter through DXGI,
names it, and reports its dedicated video memory.

Run:  python examples/igpu_door2_ctypes_dxgi.py
Exit: 0 with the adapter table; nonzero with the HRESULT that stopped it.
Rule: this file imports ctypes only. That is the whole point.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

if sys.platform != "win32":
    raise SystemExit("windows-only: this demo calls dxgi.dll")


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class DXGI_ADAPTER_DESC(ctypes.Structure):
    _fields_ = [
        ("Description", wintypes.WCHAR * 128),
        ("VendorId", wintypes.UINT),
        ("DeviceId", wintypes.UINT),
        ("SubSysId", wintypes.UINT),
        ("Revision", wintypes.UINT),
        ("DedicatedVideoMemory", ctypes.c_size_t),
        ("DedicatedSystemMemory", ctypes.c_size_t),
        ("SharedSystemMemory", ctypes.c_size_t),
        ("AdapterLuid", LUID),
    ]


def _vtable_fn(ptr: int, index: int, restype, *argtypes):
    """Pull one COM method off a vtable by index. No comtypes, no pywin32."""
    vtable = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
    addr = vtable.contents[index]
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(addr)


def main() -> int:
    dxgi = ctypes.WinDLL("dxgi")
    dxgi.CreateDXGIFactory.argtypes = [ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    dxgi.CreateDXGIFactory.restype = ctypes.c_long  # HRESULT

    # IID_IDXGIFactory = 7b7166ec-21c7-44ae-b21a-c9ae321ae369
    iid = GUID(
        0x7B7166EC, 0x21C7, 0x44AE,
        (wintypes.BYTE * 8)(0xB2, 0x1A, 0xC9, 0xAE, 0x32, 0x1A, 0xE3, 0x69),
    )
    factory = ctypes.c_void_p()
    hr = dxgi.CreateDXGIFactory(ctypes.byref(iid), ctypes.byref(factory))
    if hr != 0:
        print(f"CreateDXGIFactory failed: HRESULT=0x{hr & 0xFFFFFFFF:08X}")
        return 1
    try:
        # IDXGIFactory vtable: 3 IUnknown + 4 IDXGIObject, EnumAdapters is [7].
        enum_adapters = _vtable_fn(factory.value, 7, ctypes.c_long, wintypes.UINT,
                                  ctypes.POINTER(ctypes.c_void_p))
        # IDXGIAdapter vtable: ... , GetDesc is [8].
        found = 0
        i = 0
        while True:
            adapter = ctypes.c_void_p()
            hr = enum_adapters(factory.value, i, ctypes.byref(adapter))
            if hr != 0:
                break  # DXGI_ERROR_NOT_FOUND: list exhausted, normal ending
            try:
                get_desc = _vtable_fn(adapter.value, 8, ctypes.c_long,
                                      ctypes.POINTER(DXGI_ADAPTER_DESC))
                desc = DXGI_ADAPTER_DESC()
                hr = get_desc(adapter.value, ctypes.byref(desc))
                if hr != 0:
                    print(f"adapter {i}: GetDesc HRESULT=0x{hr & 0xFFFFFFFF:08X}")
                else:
                    vram_gb = desc.DedicatedVideoMemory / (1024 ** 3)
                    shared_gb = desc.SharedSystemMemory / (1024 ** 3)
                    print(f"adapter {i}: {desc.Description} "
                          f"vendor=0x{desc.VendorId:04X} device=0x{desc.DeviceId:04X} "
                          f"dedicated={vram_gb:.2f} GB shared={shared_gb:.2f} GB")
                    found += 1
            finally:
                release = _vtable_fn(adapter.value, 2, ctypes.c_ulong)
                release(adapter.value)
            i += 1
        print(f"OK: {found} adapter(s) enumerated with stdlib ctypes only")
        return 0 if found else 2
    finally:
        release = _vtable_fn(factory.value, 2, ctypes.c_ulong)
        release(factory.value)


if __name__ == "__main__":
    raise SystemExit(main())
