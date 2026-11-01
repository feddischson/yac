# This file is part of YAC - Yet Another CORDIC Core
# Copyright (c) 2026, Author(s), All rights reserved.
#
# YAC is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 3.0 of the License, or (at your option)
# any later version. YAC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details.
"""ctypes wrapper of the C model of the pipelined CORDIC (cordic_pipeline.c)."""

import ctypes

import numpy as np

_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1


class _Cfg(ctypes.Structure):
    _fields_ = [(n, ctypes.c_int32)
                for n in ("xy_width", "a_width", "guard_bits", "lsb_bits",
                          "n_iter", "rm_gain")]


def _as_int64(value, name):
    """Returns value as an int64 array; rejects non-integers and values beyond int64."""
    arr = np.asarray(value)
    if arr.dtype == object:
        for v in arr.flat:
            if isinstance(v, (bool, np.bool_)) or not isinstance(v, int):
                raise TypeError("%s must be an integer" % name)
            if not _INT64_MIN <= v <= _INT64_MAX:
                raise ValueError("%s is outside the int64 range" % name)
        return arr.astype(np.int64)
    if arr.dtype.kind not in "iu":
        raise TypeError("%s must be an integer, not %s" % (name, arr.dtype))
    if arr.dtype.kind == "u" and arr.size and int(arr.max()) > _INT64_MAX:
        raise ValueError("%s is outside the int64 range" % name)
    return arr.astype(np.int64)


class CordicPipeline:
    """Bit-accurate model of cordic_pipeline_int, loaded from a shared library."""

    def __init__(self, library_path, *, xy_width=16, a_width=18, guard_bits=2,
                 lsb_bits=0, n_iter=16, rm_gain=4):
        self._lib = ctypes.CDLL(str(library_path))
        p64 = ctypes.POINTER(ctypes.c_int64)
        self._lib.cordic_pipeline_latency.argtypes = [ctypes.POINTER(_Cfg)]
        self._lib.cordic_pipeline_latency.restype = ctypes.c_int32
        self._lib.cordic_pipeline_array.argtypes = [
            ctypes.POINTER(_Cfg), p64, p64, p64, p64, p64, ctypes.c_size_t]
        self._lib.cordic_pipeline_array.restype = ctypes.c_int32
        self._cfg = _Cfg(xy_width, a_width, guard_bits, lsb_bits, n_iter,
                         rm_gain)
        latency = self._lib.cordic_pipeline_latency(ctypes.byref(self._cfg))
        if latency < 0:
            raise ValueError("invalid configuration")
        self._latency = latency

    @property
    def latency(self):
        return self._latency

    def rotate(self, x, y, a):
        """Rotates x + jy by the binary angle a. Returns (x_o, y_o) as int64 arrays."""
        xs, ys, az = np.broadcast_arrays(
            _as_int64(x, "x"), _as_int64(y, "y"), _as_int64(a, "a"))
        shape = xs.shape
        xs = np.ascontiguousarray(xs, dtype=np.int64).ravel()
        ys = np.ascontiguousarray(ys, dtype=np.int64).ravel()
        az = np.ascontiguousarray(az, dtype=np.int64).ravel()
        xo = np.zeros(xs.size, dtype=np.int64)
        yo = np.zeros(xs.size, dtype=np.int64)
        if xs.size:
            p64 = ctypes.POINTER(ctypes.c_int64)
            err = self._lib.cordic_pipeline_array(
                ctypes.byref(self._cfg), xs.ctypes.data_as(p64),
                ys.ctypes.data_as(p64), az.ctypes.data_as(p64),
                xo.ctypes.data_as(p64), yo.ctypes.data_as(p64), xs.size)
            if err == -2:
                raise ValueError("x or y outside the signed xy_width range")
            if err < 0:
                raise ValueError("invalid configuration or argument")
        return xo.reshape(shape), yo.reshape(shape)
