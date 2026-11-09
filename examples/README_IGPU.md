# iGPU compute, three finished examples — measured 2026-11-09

Everything here is **stdlib only**: `ctypes`, `time`, nothing else. No numpy, no
torch, no onnxruntime, no pip install, no vendor SDK. The Python on both
platforms was 3.14+/3.16 free-threaded, unmodified.

The question these examples answer: *can this box do ML-shaped math on the Intel
Arc 140T without buying into CUDA, a wheel, or a runtime?* The answer measured
here is yes, and the price is one C kernel plus the numbers below.

## What runs

| file | what it proves | command | result |
| --- | --- | --- | --- |
| `igpu_door2_ctypes_dxgi.py` | the iGPU is reachable at all from Python: DXGI adapter enumeration through raw COM | `python examples/igpu_door2_ctypes_dxgi.py` | `adapter 0: Intel(R) Arc(TM) 140T GPU (8GB) vendor=0x8086 device=0x7D51` — exit 0 |
| `igpu_door2_compute.py` | real compute on D3D11: one HLSL `cs_5_0` kernel, structured buffer, dispatch, readback | `python examples/igpu_door2_compute.py` | 1,048,576 floats `y=2x+1` in **0.66 ms** = 1590.4 M elem/s, `correct=True`, exit 0 |
| `igpu_opencl_compute.py` | the same work through a **flat C API**, which is the portable one | `python examples/igpu_opencl_compute.py` | GPU **0.60 ms** vs pure-Python **119.70 ms** = **199×**, exit 0 |
| `igpu_subresource.py` | sub-resource engineering: 3 mips × 2 array slices, a distinct pattern written into each of the 6 sub-resources, then read back through a named region copy | `python examples/igpu_subresource.py` | 6/6 sub-resources byte-exact, `collapsed-index test -> distinct`, exit 0 |

Two independent GPU paths, two different compilers (D3DCompile/HLSL and the
Intel OpenCL JIT), both agreeing with the CPU reference on the same probe
indices. That agreement is the verification — not the timing.

## Same file, Ubuntu 26.04

`igpu_opencl_compute.py` is platform-portable (it resolves the loader by name:
`libOpenCL.so.1` on Linux, `OpenCL.dll` on Windows). Copied nowhere, edited
not at all:

```
wsl -d Ubuntu-26.04 -- python3 /mnt/c/Azazael/EveUnleashed/examples/igpu_opencl_compute.py
  device:  Intel(R) Graphics [0x7d51]      128 compute units, 7.8 GiB
  GPU (OpenCL): 3.91 ms      CPU (python): 111.40 ms      speedup 28.48x
  VERDICT: GPU produced y = 2x + 1 for 1,048,576 floats ... exit 0
```

`[0x7d51]` is the same Arc 140T the Windows run names. Ubuntu shipped
`libOpenCL.so.1`, the Intel ICDs (`/etc/OpenCL/vendors/intel*.icd`) and
`/dev/dxg` — nothing was installed to make this run.

**That is WSL2, not bare metal.** The GPU arrives through `/dev/dxg`
virtualization, which is why the same kernel costs 3.91 ms there against 0.60 ms
on Windows: the transfers pay the VM boundary. A bare-metal install would remove
that tax, and nothing in this repo can install an OS on hardware this session
cannot touch.

## Did this functionally bypass CUDA?

For this workload, yes, literally: GPU math executed on this box with zero CUDA
artifacts present. But the scope matters, so in the same breath:

- **This silicon never had CUDA.** Arc 140T is Intel; `nvidia-smi` is not the
  gate here. "Bypassing CUDA" here means "not needing NVIDIA's stack to do
  compute", which on this box was never an option to begin with.
- **What is bypassed is the dependency, not the capability ceiling.** cuBLAS,
  cuDNN and cuSPARSE are hand-tuned BLAS/conv libraries. A hand-written OpenCL
  kernel on an Arc will not match an H100 running cuDNN for transformer training.
  For elementwise math, reductions, matvec and image work — the shapes MCML
  actually has — the gap is the 77–199× measured above, because the comparison
  is against pure-Python lists, not against BLAS.
- **Portability is real.** One kernel source ran unchanged on Windows and on
  Ubuntu 26.04 and would run on an NVIDIA or AMD part through that vendor's ICD.
  That is the "unified language" property, and it is the thing CUDA does not have.

## Where this belongs on this box (ranked, by shape not by enthusiasm)

1. **MCML's numeric core.** `src/eve_unleashed/mcml.py` is pure-Python lists and
   already has Cython siblings (`_replay_cy`, `_forensic_cy`). These examples are
   the measured argument for a third backend: same "stdlib only" rule, ~100×
   on elementwise passes.
2. **The memory store's similarity work.** Cosine distance across the DirectMemory
   store is dense vector math over GBs — the one workload here that looks like
   BLAS and would benefit most.
3. **Frame compositing in the render lanes** (CODEX/CAIN, PIL → ffmpeg). Frame
   math is per-pixel elementwise, which is exactly the measured shape.
4. **Not** the AST/audit sweeps (`ast_audit.py`, `golden_arrow`): parse-bound and
   I/O-bound, the GPU would idle while Python tokenizes.
5. **Not** the wasm/mp4 playback crate: it is already 3.5× cheaper streamed than
   baked, and GPU encode is not reachable through this API.

## The walls hit (the brick list)

1. **The mingw IDL is one slot short.** `d3d11.idl` counts
   `CSSetShaderResources=66 / CSSetUnorderedAccessViews=67 / CSSetShader=68`;
   the shipping runtime wants **67 / 68 / 69**. Two of the IDL-derived indices
   fault with `access violation reading 0x4`, and the third silently no-ops —
   which is worse, because Dispatch then returns zeros with no error at all.
   The authoritative source is the Windows SDK header
   `.../Windows Kits/10/Include/10.0.26100.0/um/d3d11.h`, `ID3D11DeviceContextVtbl`,
   115 slots. Both examples now carry that note.
2. **Door 1 is dead on py316t.** `pip install onnxruntime-directml` and
   `torch-directml` both return `No matching distribution found`; and either
   would break the MCML stdlib rule anyway.
3. **First call is not the steady state.** The driver JIT costs 11–35 ms on the
   first dispatch (both APIs, both platforms); the 0.6 ms figure is the third
   run. Quoting the warm number without saying so would be a lie of the HED-9
   kind, so it is printed as `3 runs: 12.26, 0.73, 0.60`.
4. **WSL2 taxes the transfers ~6×.** 3.91 ms vs 0.66 ms for identical work.
   Useful for capability proof, not for a performance claim.
5. **Bare metal is out of reach from here.** No OS install, no second machine.
   The portable example is the deliverable that *survives* a bare-metal install;
   the install itself is not something this session can do.
6. **D3D11 silently drops a texture→buffer `CopySubresourceRegion`.** The method
   returns `void`, so the failure is only visible to the debug layer; the staging
   buffer then reads back as zeros and looks exactly like a broken sub-resource
   index. Copy into a STAGING **texture** and `Map` the same subresource instead.
7. **A `void` method must not be declared `HRESULT`.** `UpdateSubresource` and
   `CopySubresourceRegion` return nothing, so reading RAX reports a failure that
   never happened — `0x62890EC0`, which was really a pointer.
8. **A copied region lands at the destination origin.** Read the mapped page at
   `y * RowPitch + x * 4`, not at the source `(x, y)`; the source coordinates
   only select what was copied, not where it lands.
9. **`0xB000` is an output, not an input.** Passing feature level 0xB000 as the
   `FeatureLevels` count in `D3D11CreateDevice` returns `E_INVALIDARG
   0x80070057`; pass `pFeatureLevels=NULL, FeatureLevels=0, SDKVersion=7`.
