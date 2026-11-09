"""MCML GPU backend -- stdlib-native OpenCL acceleration for MellifluousML.

Additive module: imports from mcml, never modifies it. Same weight init stream
(mcml._xavier), same block semantics, f32 on device vs f64 on CPU, so results
agree to ~1e-6 and the CPU path keeps the golden digest authority.

Interop hyper-optimization (the whole point of this file -- moving bytes across
the bus is the cost, not the flops):
  1. weights/grads LIVE on the device. W, b, gW, gb are created once; the host
     never re-uploads them. step() runs on-device.
  2. per batch the bus sees only X up and Y/dX down -- O(batch), never O(params).
  3. fused forward kernel: matvec + bias + activation in ONE dispatch, so the
     B*OUT intermediate never crosses anything.
  4. grads accumulate on-device across the batch; only the loss scalar (one
     float) comes back per training step.
  5. failures are loud: build log on compile error, device name/type printed,
     CPU cross-check with a tolerance on every run of __main__.

Requires an OpenCL ICD (Intel/AMD/NVIDIA ship one with the driver; Ubuntu 26.04
carries libOpenCL.so.1 out of the box). No wheel, no NumPy, ctypes only.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import struct
import time

from .mcml import _xavier

import random

# --------------------------------------------------------------------------
# OpenCL loader (flat C API -- no COM, no vtables, hence no IDL off-by-one)


class _CL:
    """Minimal ctypes binding for exactly the entry points we use."""

    def __init__(self) -> None:
        name = ctypes.util.find_library("OpenCL")
        if not name:
            raise RuntimeError(
                "no OpenCL ICD found (find_library('OpenCL') failed). "
                "Install the GPU driver / ocl-icd-libopencl1; CPU path "
                "in mcml.py is unaffected.")
        self.lib = ctypes.CDLL(name)
        lib = self.lib
        vp = ctypes.c_void_p
        u32 = ctypes.c_uint32
        u64 = ctypes.c_uint64
        sz = ctypes.c_size_t

        def bind(fname, restype, *argtypes):
            try:
                f = getattr(lib, fname)
            except AttributeError:
                return None
            f.restype = restype
            f.argtypes = list(argtypes)
            return f

        i32 = ctypes.c_int32
        self.get_platform_ids = bind("clGetPlatformIDs", i32, u32, vp, ctypes.POINTER(u32))
        self.get_platform_info = bind("clGetPlatformInfo", i32, vp, u32, sz, vp,
                                      ctypes.POINTER(sz))
        self.get_device_ids = bind("clGetDeviceIDs", i32, vp, u64, u32, vp,
                                   ctypes.POINTER(u32))
        self.get_device_info = bind("clGetDeviceInfo", i32, vp, u32, sz, vp,
                                    ctypes.POINTER(sz))
        self.create_context = bind("clCreateContext", vp, vp, u32, vp, vp, vp,
                                   ctypes.POINTER(i32))
        self.queue_props = bind("clCreateCommandQueueWithProperties", vp, vp, vp,
                                vp, ctypes.POINTER(i32))
        self.queue_legacy = bind("clCreateCommandQueue", vp, vp, vp, u32,
                                 ctypes.POINTER(i32))
        self.create_buffer = bind("clCreateBuffer", vp, vp, u64, sz, vp,
                                  ctypes.POINTER(i32))
        self.create_program = bind("clCreateProgramWithSource", vp, vp, u32, vp, vp,
                                   ctypes.POINTER(i32))
        self.build_program = bind("clBuildProgram", i32, vp, u32, vp, vp, vp, vp)
        self.build_info = bind("clGetProgramBuildInfo", i32, vp, vp, u32, sz, vp,
                               ctypes.POINTER(sz))
        self.create_kernel = bind("clCreateKernel", vp, vp, ctypes.c_char_p,
                                  ctypes.POINTER(i32))
        self.set_arg = bind("clSetKernelArg", i32, vp, u32, sz, vp)
        self.enqueue_write = bind("clEnqueueWriteBuffer", i32, vp, vp, u32, u64,
                                  u64, vp, u32, vp, vp)
        self.enqueue_read = bind("clEnqueueReadBuffer", i32, vp, vp, u32, u64,
                                 u64, vp, u32, vp, vp)
        self.enqueue_nd = bind("clEnqueueNDRangeKernel", i32, vp, vp, u32, vp, vp,
                               vp, u32, vp, vp)
        self.finish = bind("clFinish", i32, vp)
        missing = [n for n, f in self.__dict__.items()
                   if f is None and n not in ("queue_props", "queue_legacy")]
        if missing or (self.queue_props is None and self.queue_legacy is None):
            raise RuntimeError("ICD missing entry points: %s" % (missing,))

        must = ["get_platform_ids", "get_device_ids", "create_context",
                "create_buffer", "create_program", "build_program",
                "create_kernel", "set_arg", "enqueue_write", "enqueue_read",
                "enqueue_nd", "finish"]
        absent = [n for n in must if getattr(self, n) is None]
        if absent:
            raise RuntimeError("ICD missing entry points: %s" % (absent,))


CL_DEVICE_TYPE_GPU = 1 << 2
CL_DEVICE_TYPE_CPU = 1 << 1
CL_DEVICE_TYPE_DEFAULT = 1 << 0
CL_MEM_READ_WRITE = 1
CL_BLOCKING = 1

_INFO_NAME = 0x102B
_INFO_TYPE = 0x1000
_TYPE_GPU = 1 << 2


def available() -> bool:
    """True when an OpenCL ICD with at least one device exists."""
    try:
        cl = _CL()
        n = ctypes.c_uint32()
        if cl.get_platform_ids(0, None, ctypes.byref(n)) != 0 or n.value == 0:
            return False
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# kernels: fused, batched, device-resident weights


_FWD = r"""
__kernel void fwd(__global const float* W, __global const float* b,
                  __global const float* X, __global float* Y,
                  const int IN, const int OUT, const int ACT) {
    int gid = get_global_id(0);
    int o = gid % OUT;
    int bb = gid / OUT;
    float acc = b[o];
    __global const float* w = W + (size_t)o * IN;
    __global const float* x = X + (size_t)bb * IN;
    for (int i = 0; i < IN; i++) acc += w[i] * x[i];
    float y;
    if (ACT == 0)      y = acc > 0.0f ? acc : 0.0f;   /* relu    */
    else if (ACT == 1) y = tanh(acc);                 /* tanh    */
    else               y = 1.0f / (1.0f + exp(-acc)); /* sigmoid */
    Y[gid] = y;
}
"""

_BWD_DX = r"""
__kernel void bwd_dx(__global const float* W, __global const float* dY,
                     __global const float* dAct, __global float* dX,
                     const int IN, const int OUT) {
    int gid = get_global_id(0);
    int i = gid % IN;
    int bb = gid / IN;
    float s = 0.0f;
    for (int o = 0; o < OUT; o++)
        s += W[(size_t)o * IN + i] * dY[(size_t)bb * OUT + o];
    dX[gid] = s * dAct[gid];
}
"""

_BWD_G = r"""
/* dY is grad w.r.t. the ACTIVATED output (what forward_batch returns).
   The pre-activation grad dY*df(Y) is formed on the fly so the fused block
   chains exactly like Activate.backward -> Dense.backward. */
__kernel void bwd_g(__global const float* X, __global const float* dY,
                    __global const float* dAct,
                    __global float* gW, __global float* gb,
                    const int IN, const int OUT, const int B) {
    int gid = get_global_id(0);
    int nW = OUT * IN;
    if (gid < nW) {
        int o = gid / IN, i = gid % IN;
        float s = 0.0f;
        for (int bb = 0; bb < B; bb++)
            s += dY[(size_t)bb * OUT + o] * dAct[(size_t)bb * OUT + o]
                 * X[(size_t)bb * IN + i];
        gW[gid] += s;
    } else {
        int o = gid - nW;
        float s = 0.0f;
        for (int bb = 0; bb < B; bb++)
            s += dY[(size_t)bb * OUT + o] * dAct[(size_t)bb * OUT + o];
        gb[o] += s;
    }
}
"""

_SGD = r"""
__kernel void sgd(__global float* W, __global const float* gW,
                  __global float* b, __global const float* gb,
                  const float lr, const int NW, const int NB) {
    int gid = get_global_id(0);
    if (gid < NW) W[gid] -= lr * gW[gid];
    else if (gid - NW < NB) b[gid - NW] -= lr * gb[gid - NW];
}
"""

_ZERO = r"""
__kernel void zero(__global float* gW, __global float* gb,
                   const int NW, const int NB) {
    int gid = get_global_id(0);
    if (gid < NW) gW[gid] = 0.0f;
    else if (gid - NW < NB) gb[gid - NW] = 0.0f;
}
"""

_ACTS = {"relu": 0, "tanh": 1, "sigmoid": 2}


class GpuDense:
    """Device-resident Dense block. Mirrors mcml.Dense semantics in f32.

    Weights are uploaded once; X goes up and Y/dX come down per batch; the
    loss scalar is the only per-step readback the training loop needs.
    """

    def __init__(self, in_dim: int, out_dim: int, seed: int = 7,
                 activation: str = "tanh", devtype: int = CL_DEVICE_TYPE_GPU) -> None:
        if in_dim < 1 or out_dim < 1:
            raise ValueError("dense dims must be >= 1, got %d -> %d"
                             % (in_dim, out_dim))
        if activation not in _ACTS:
            raise ValueError("activations: %s (got %r)"
                             % (sorted(_ACTS), activation))
        self.in_dim, self.out_dim, self.seed = in_dim, out_dim, seed
        self.act = _ACTS[activation]

        cl = self.cl = _CL()
        n = ctypes.c_uint32()
        self._ok(cl.get_platform_ids(0, None, ctypes.byref(n)))
        plats = (ctypes.c_void_p * n.value)()
        self._ok(cl.get_platform_ids(n.value, plats, None))

        self.device, self.devname, self.is_gpu = None, "?", False
        for p in plats:
            for want in (devtype, CL_DEVICE_TYPE_DEFAULT):
                m = ctypes.c_uint32()
                if cl.get_device_ids(p, want, 0, None, ctypes.byref(m)) != 0 \
                        or m.value == 0:
                    continue
                devs = (ctypes.c_void_p * m.value)()
                self._ok(cl.get_device_ids(p, want, m.value, devs, None))
                self.device = devs[0]
                if want == CL_DEVICE_TYPE_GPU:
                    self.is_gpu = True
                break
            if self.device:
                break
        if not self.device:
            raise RuntimeError("OpenCL ICD present but no usable device found")

        ln = ctypes.c_size_t()
        cl.get_device_info(self.device, _INFO_NAME, 0, None, ctypes.byref(ln))
        buf = ctypes.create_string_buffer(ln.value)
        cl.get_device_info(self.device, _INFO_NAME, ln.value, buf, None)
        self.devname = buf.value.decode("utf-8", "replace")

        err = ctypes.c_int32()
        # NOTE: with restype=c_void_p, ctypes returns the handle as a plain
        # int -- wrap it, or _arg() mistakes a buffer for an int32 kernel arg
        # and clSetKernelArg fails with -51 (CL_INVALID_ARG_SIZE).
        self.ctx = ctypes.c_void_p(cl.create_context(
            None, 1, ctypes.byref(ctypes.c_void_p(self.device)),
            None, None, ctypes.byref(err)))
        self._ok(err.value)
        if cl.queue_props is not None:
            self.queue = ctypes.c_void_p(cl.queue_props(
                self.ctx, self.device, None, ctypes.byref(err)))
        else:
            self.queue = ctypes.c_void_p(cl.queue_legacy(
                self.ctx, self.device, 0, ctypes.byref(err)))
        self._ok(err.value)

        src = (_FWD + _BWD_DX + _BWD_G + _SGD + _ZERO).encode()
        prog = ctypes.c_void_p(cl.create_program(
            self.ctx, 1, ctypes.byref(ctypes.c_char_p(src)),
            ctypes.byref(ctypes.c_size_t(len(src))), ctypes.byref(err)))
        self._ok(err.value)
        rc = cl.build_program(prog, 1,
                              ctypes.byref(ctypes.c_void_p(self.device)),
                              None, None, None)
        if rc != 0:
            ln2 = ctypes.c_size_t()
            cl.build_info(prog, self.device, 0x1183, 0, None, ctypes.byref(ln2))
            log = ctypes.create_string_buffer(max(ln2.value, 1))
            cl.build_info(prog, self.device, 0x1183, ln2.value, log, None)
            raise RuntimeError("kernel build failed:\n%s"
                               % log.value.decode("utf-8", "replace"))
        self.k = {}
        for n_ in ("fwd", "bwd_dx", "bwd_g", "sgd", "zero"):
            h = ctypes.c_void_p(cl.create_kernel(prog, n_.encode(),
                                                  ctypes.byref(err)))
            self._ok(err.value)
            if not h:
                raise RuntimeError("clCreateKernel(%s) returned NULL" % n_)
            self.k[n_] = h

        rng = random.Random(seed)
        w = [_xavier(rng, in_dim, out_dim) for _ in range(out_dim * in_dim)]
        b = [_xavier(rng, in_dim, out_dim) for _ in range(out_dim)]
        self._nw, self._nb = len(w), len(b)
        self.W = self._buf(w)
        self.b = self._buf(b)
        self.gW = self._buf([0.0] * self._nw)
        self.gb = self._buf([0.0] * self._nb)

    # -- plumbing ---------------------------------------------------------
    @staticmethod
    def _ok(rc: int) -> None:
        if rc != 0:
            raise RuntimeError("OpenCL call failed: %d" % rc)

    def _buf(self, vals) -> ctypes.c_void_p:
        raw = struct.pack("<%df" % len(vals), *vals)
        err = ctypes.c_int32()
        h = ctypes.c_void_p(self.cl.create_buffer(
            self.ctx, CL_MEM_READ_WRITE, len(raw), None, ctypes.byref(err)))
        self._ok(err.value)
        data = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        self._ok(self.cl.enqueue_write(self.queue, h, CL_BLOCKING, 0, len(raw),
                                       data, 0, None, None))
        return h

    def _new(self, nfloats: int) -> ctypes.c_void_p:
        err = ctypes.c_int32()
        h = ctypes.c_void_p(self.cl.create_buffer(
            self.ctx, CL_MEM_READ_WRITE, nfloats * 4, None, ctypes.byref(err)))
        self._ok(err.value)
        return h

    def _arg(self, k, i: int, val) -> None:
        cl = self.cl
        if isinstance(val, ctypes.c_void_p):
            h = val
            self._ok(cl.set_arg(k, i, ctypes.sizeof(ctypes.c_void_p),
                                ctypes.byref(h)))
        elif isinstance(val, int):
            v = ctypes.c_int32(val)
            self._ok(cl.set_arg(k, i, ctypes.sizeof(v), ctypes.byref(v)))
        else:
            v = ctypes.c_float(val)
            self._ok(cl.set_arg(k, i, ctypes.sizeof(v), ctypes.byref(v)))

    def _run(self, k, n: int) -> None:
        g = ctypes.c_size_t(n)
        self._ok(self.cl.enqueue_nd(self.queue, k, 1, None,
                                    ctypes.byref(g), None, 0, None, None))

    def _read(self, h, nfloats: int):
        out = (ctypes.c_ubyte * (nfloats * 4))()
        self._ok(self.cl.enqueue_read(self.queue, h, CL_BLOCKING, 0,
                                      nfloats * 4, out, 0, None, None))
        return list(struct.unpack("<%df" % nfloats, bytes(out)))

    def _write(self, h, vals) -> None:
        raw = struct.pack("<%df" % len(vals), *vals)
        data = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        self._ok(self.cl.enqueue_write(self.queue, h, CL_BLOCKING, 0,
                                       len(raw), data, 0, None, None))

    # -- block API (mirrors mcml.Dense, batched) --------------------------
    def forward_batch(self, X):
        B = len(X)
        flat = [v for row in X for v in row]
        xb = self._buf(flat)
        yb = self._new(B * self.out_dim)
        k = self.k["fwd"]
        self._arg(k, 0, self.W)
        self._arg(k, 1, self.b)
        self._arg(k, 2, xb)
        self._arg(k, 3, yb)
        self._arg(k, 4, self.in_dim)
        self._arg(k, 5, self.out_dim)
        self._arg(k, 6, self.act)
        t0 = time.perf_counter()
        self._run(k, B * self.out_dim)
        self._ok(self.cl.finish(self.queue))
        kt = (time.perf_counter() - t0) * 1e3
        y = self._read(yb, B * self.out_dim)
        return ([y[i * self.out_dim:(i + 1) * self.out_dim]
                 for i in range(B)], kt)

    def _dact(self, Y):
        if self.act == 0:
            return [1.0 if v > 0.0 else 0.0 for v in Y]
        if self.act == 1:
            return [1.0 - v * v for v in Y]
        return [v * (1.0 - v) for v in Y]

    def backward_batch(self, X, dY):
        """dY is grad w.r.t. the ACTIVATED output (what forward_batch
        returned), i.e. the loss grad -- df(Y) is applied inside, exactly
        chaining Activate.backward -> Dense.backward."""
        B = len(X)
        flatx = [v for row in X for v in row]
        flatd = [v for row in dY for v in row]
        xb, dyb = self._buf(flatx), self._buf(flatd)
        Y, _ = self.forward_batch(X)
        dab = self._buf(self._dact([v for row in Y for v in row]))
        dxb = self._new(B * self.in_dim)
        k = self.k["bwd_dx"]
        self._arg(k, 0, self.W)
        self._arg(k, 1, dyb)
        self._arg(k, 2, dab)
        self._arg(k, 3, dxb)
        self._arg(k, 4, self.in_dim)
        self._arg(k, 5, self.out_dim)
        t0 = time.perf_counter()
        self._run(k, B * self.in_dim)
        k2 = self.k["bwd_g"]
        self._arg(k2, 0, xb)
        self._arg(k2, 1, dyb)
        self._arg(k2, 2, dab)
        self._arg(k2, 3, self.gW)
        self._arg(k2, 4, self.gb)
        self._arg(k2, 5, self.in_dim)
        self._arg(k2, 6, self.out_dim)
        self._arg(k2, 7, B)
        self._run(k2, self._nw + self._nb)
        self._ok(self.cl.finish(self.queue))
        kt = (time.perf_counter() - t0) * 1e3
        dx = self._read(dxb, B * self.in_dim)
        return ([dx[i * self.in_dim:(i + 1) * self.in_dim]
                 for i in range(B)], kt)

    def zero_grad(self) -> None:
        k = self.k["zero"]
        self._arg(k, 0, self.gW)
        self._arg(k, 1, self.gb)
        self._arg(k, 2, self._nw)
        self._arg(k, 3, self._nb)
        self._run(k, self._nw + self._nb)
        self._ok(self.cl.finish(self.queue))

    def step(self, lr: float) -> None:
        k = self.k["sgd"]
        self._arg(k, 0, self.W)
        self._arg(k, 1, self.gW)
        self._arg(k, 2, self.b)
        self._arg(k, 3, self.gb)
        self._arg(k, 4, float(lr))
        self._arg(k, 5, self._nw)
        self._arg(k, 6, self._nb)
        self._run(k, self._nw + self._nb)
        self._ok(self.cl.finish(self.queue))

    def weights(self):
        w = self._read(self.W, self._nw)
        b = self._read(self.b, self._nb)
        return ([w[i * self.in_dim:(i + 1) * self.in_dim]
                 for i in range(self.out_dim)], b)


def _cpu_dense(in_dim, out_dim, seed, act_name):
    from . import mcml as _m
    d = _m.Dense(in_dim, out_dim, seed=seed)
    a = _m.Activate(act_name)
    return d, a


class HybridDense:
    """Data-parallel Dense over ALL backends, tunable by percentage.

    backends = {"gpu": GpuDense | None, "cpu": (Dense, Activate)}.
    split = fraction of batch rows on the GPU (0.0 = CPU only, 1.0 = GPU
    only); tune() measures the box and pins the fastest split for THIS shape
    (the optimum moves with batch size -- the GPU's upload overhead is fixed,
    the CPU's cost is linear, so small batches belong to the CPU).
    Replicas stay identical: sync_grads() sums the per-shard grads and deals
    the SAME total to both backends before step().
    """

    def __init__(self, in_dim: int, out_dim: int, seed: int = 7,
                 activation: str = "tanh") -> None:
        self.in_dim, self.out_dim = in_dim, out_dim
        self.cpu_d, self.cpu_a = _cpu_dense(in_dim, out_dim, seed, activation)
        try:
            self.gpu = GpuDense(in_dim, out_dim, seed=seed,
                                activation=activation)
        except Exception as e:
            self.gpu = None
            self._gpu_err = str(e)
        self.split = 1.0 if self.gpu is not None else 0.0

    @property
    def backends(self):
        return {"gpu": self.gpu is not None, "cpu": True}

    def _parts(self, rows, split):
        k = min(len(rows), max(0, int(len(rows) * split)))
        return rows[:k], rows[k:], k

    def forward_batch(self, X, split=None):
        split = self.split if split is None else split
        if self.gpu is None:
            split = 0.0
        gx, cx, k = self._parts(X, split)
        Y = [None] * len(X)
        if gx:
            gy, _ = self.gpu.forward_batch(gx)
            Y[:k] = gy
        for i, x in enumerate(cx, start=k):
            Y[i] = self.cpu_a.forward(self.cpu_d.forward(x))
        return Y

    def backward_batch(self, X, dY, split=None):
        split = self.split if split is None else split
        if self.gpu is None:
            split = 0.0
        gx, cx, k = self._parts(X, split)
        gd, cd, _ = self._parts(dY, split)
        dX = [None] * len(X)
        if gx:
            gdx, _ = self.gpu.backward_batch(gx, gd)
            dX[:k] = gdx
        for i, (x, my) in enumerate(zip(cx, cd), start=k):
            y = self.cpu_a.forward(self.cpu_d.forward(x))
            d = self.cpu_a.backward(y, my)
            dX[i] = self.cpu_d.backward(x, d)
        return dX

    def zero_grad(self) -> None:
        d = self.cpu_d
        d.gW = [[0.0] * d.in_dim for _ in range(d.out_dim)]
        d.gb = [0.0] * d.out_dim
        if self.gpu is not None:
            self.gpu.zero_grad()

    def sync_grads(self) -> None:
        """Sum per-shard grads; deal the identical total to both replicas."""
        if self.gpu is None:
            return
        g = self.gpu
        gw = g._read(g.gW, g._nw)
        gb = g._read(g.gb, g._nb)
        d = self.cpu_d
        flat = [v for row in d.gW for v in row] + list(d.gb)
        total = [a_ + b_ for a_, b_ in zip(gw + gb, flat)]
        g._write(g.gW, total[:g._nw])
        g._write(g.gb, total[g._nw:])
        d.gW = [total[i * d.in_dim:(i + 1) * d.in_dim]
                for i in range(d.out_dim)]
        d.gb = total[g._nw:]

    def step(self, lr: float) -> None:
        self.sync_grads()
        d = self.cpu_d
        d.W = [[w - lr * gw for w, gw in zip(row, grow)]
               for row, grow in zip(d.W, d.gW)]
        d.b = [x - lr * gb for x, gb in zip(d.b, d.gb)]
        if self.gpu is not None:
            self.gpu.step(lr)

    def tune(self, X, splits=(0.0, 0.25, 0.5, 0.75, 1.0), reps=3):
        """Measure each split, pin the fastest. Returns (best, table)."""
        import time as _t
        table = []
        for s in splits:
            if s > 0.0 and self.gpu is None:
                continue
            self.forward_batch(X, split=s)  # warm
            t0 = _t.perf_counter()
            for _ in range(reps):
                self.forward_batch(X, split=s)
            ms = (_t.perf_counter() - t0) * 1e3 / reps
            table.append((s, ms))
        best = min(table, key=lambda r: r[1])[0]
        self.split = best
        return best, table


def main() -> int:
    print("mcml_gpu backend check (stdlib ctypes OpenCL, additive -- mcml.py untouched)")
    if not available():
        print("FAIL: no OpenCL ICD on this box; CPU path in mcml.py is unaffected")
        return 1
    IN, OUT, B = 128, 64, 256
    rng = random.Random(11)
    X = [[rng.uniform(-1, 1) for _ in range(IN)] for _ in range(B)]
    T = [[rng.uniform(-1, 1) for _ in range(OUT)] for _ in range(B)]

    g = GpuDense(IN, OUT, seed=7, activation="tanh")
    print("device: %s%s" % (g.devname, "  [GPU]" if g.is_gpu else "  [non-GPU device]"))

    # -- exactness vs the CPU blocks -------------------------------------
    d, a = _cpu_dense(IN, OUT, 7, "tanh")
    Y, fwd_kt = g.forward_batch(X)
    cpu_Y = [a.forward(d.forward(x)) for x in X]
    fwd_err = max(abs(yv - cv) for yr, cr in zip(Y, cpu_Y)
                  for yv, cv in zip(yr, cr))
    d.gW = [[0.0] * IN for _ in range(OUT)]
    d.gb = [0.0] * OUT
    gY = [row[:] for row in Y]
    mse_g = [[2.0 * (yv - tv) / OUT for yv, tv in zip(yr, tr)]
             for yr, tr in zip(gY, T)]
    dX, bwd_kt = g.backward_batch(X, mse_g)
    for x, my in zip(X, mse_g):
        y = a.forward(d.forward(x))
        dy = [m * _d for m, _d in
              zip(my, [1.0 - v * v for v in y])]
        d.backward(x, dy)
    cpu_dW = [v for row in d.gW for v in row]
    gpu_dW = g._read(g.gW, g._nw)
    bwd_err = max(abs(a_ - b_) for a_, b_ in zip(gpu_dW, cpu_dW))

    # one SGD step on both, compare weights
    g.step(0.01)
    d.W = [[w - 0.01 * gw for w, gw in zip(row, grow)]
           for row, grow in zip(d.W, d.gW)]
    d.b = [x - 0.01 * gb for x, gb in zip(d.b, d.gb)]
    gWm, gbm = g.weights()
    w_err = max([abs(gv - cv) for gr, cr in zip(gWm, d.W)
                 for gv, cv in zip(gr, cr)] + [abs(gv - cv) for gv, cv in
                                                zip(gbm, d.b)])

    # -- speed: same batch, CPU wall vs GPU wall --------------------------
    t0 = time.perf_counter()
    for x in X:
        a.forward(d.forward(x))
    cpu_ms = (time.perf_counter() - t0) * 1e3
    t0 = time.perf_counter()
    Y2, _ = g.forward_batch(X)
    gpu_ms = (time.perf_counter() - t0) * 1e3

    print("shape: batch=%d in=%d out=%d  params=%d" % (B, IN, OUT, g._nw + g._nb))
    print("forward kernel: %.2f ms | backward kernels: %.2f ms" % (fwd_kt, bwd_kt))
    print("CPU batch forward: %.2f ms | GPU batch wall (up+run+down): %.2f ms | %.1fx"
          % (cpu_ms, gpu_ms, cpu_ms / max(gpu_ms, 1e-9)))
    print("exactness: forward max|d|=%.2e  grads max|d|=%.2e  post-step weights max|d|=%.2e"
          % (fwd_err, bwd_err, w_err))
    ok = fwd_err < 2e-5 and bwd_err < 2e-5 and w_err < 2e-5
    print("OK: GpuDense matches mcml.Dense to f32 tolerance; weights live on-device, "
          "bus sees only X/Y per batch" if ok else "FAIL: tolerance exceeded")
    if not ok:
        return 1

    # -- hybrid: tunable percentages of ALL backends ----------------------
    h = HybridDense(IN, OUT, seed=7, activation="tanh")
    print("backends: %s" % h.backends)
    best, table = h.tune(X)
    print("tune (fraction of %d rows on GPU -> ms): %s" %
          (B, "  ".join("%.2f:%.2f" % (s, ms) for s, ms in table)))
    print("pinned split: %.2f of batch on GPU" % best)
    hY = h.forward_batch(X)
    herr = max(abs(yv - cv) for yr, cr in zip(hY, cpu_Y)
               for yv, cv in zip(yr, cr))
    h.zero_grad()
    h.backward_batch(X, mse_g)
    h.step(0.01)
    if h.gpu is not None:
        hw, hb = h.gpu.weights()
        rep_err = max([abs(gv - cv) for gr, cr in zip(hw, h.cpu_d.W)
                       for gv, cv in zip(gr, cr)] +
                      [abs(gv - cv) for gv, cv in zip(hb, h.cpu_d.b)])
    else:
        rep_err = 0.0
    print("hybrid: routing max|d|=%.2e  replica-agreement max|d|=%.2e"
          % (herr, rep_err))
    hok = herr < 2e-5 and rep_err < 1e-6
    print("OK: hybrid split %.2f routes rows across backends with identical "
          "replicas" % best if hok else "FAIL: hybrid mismatch")
    return 0 if hok else 1


if __name__ == "__main__":
    raise SystemExit(main())
