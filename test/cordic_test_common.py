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
"""Shared helpers of the pipelined CORDIC tests."""

import subprocess
from pathlib import Path

import numpy as np
import numpy.typing as npt

Vectors = tuple[npt.NDArray[np.int64], npt.NDArray[np.int64], npt.NDArray[np.int64]]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def build_library(out_dir: Path) -> Path:
    """Builds the C model as a shared library in out_dir and returns its path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    lib = out_dir / "libcordic_pipeline.so"
    src = repo_root() / "c_model" / "cordic_pipeline.c"
    subprocess.run(
        ["gcc", "-Wall", "-Wextra", "-Werror", "-O2", "-fPIC", "-shared",
         str(src), "-o", str(lib)],
        check=True)
    return lib


def directed_vectors(xy_width: int, a_width: int) -> Vectors:
    """Returns the directed test inputs: every input with every angle.

    Inputs are the four full-scale corners and (0, 0). Angles are 0, one LSB
    either side of 0, and each quadrant boundary with one LSB either side.

    :param xy_width: input width in bits
    :type xy_width: int
    :param a_width: angle width in bits
    :type a_width: int
    :return: x, y and a, of equal length
    :rtype: Vectors
    """
    low = -(2 ** (xy_width - 1))
    high = 2 ** (xy_width - 1) - 1
    inputs = [(low, low), (low, high), (high, low), (high, high), (0, 0)]
    angles = {0, 1, 2**a_width - 1}
    for q in range(1, 4):
        boundary = q * 2 ** (a_width - 2)
        angles |= {boundary - 1, boundary, boundary + 1}
    rows = [(x, y, a) for x, y in inputs for a in sorted(angles)]
    x, y, a = np.array(rows, dtype=np.int64).T
    return x, y, a


def directed_vectoring_vectors(
    xy_width: int,
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.int64]]:
    """Returns the directed vectoring inputs, each pair once.

    Inputs are the four full-scale corners, (0, 0), the four axis points at
    full scale and the pairs next to the origin on the half-plane boundary.

    :param xy_width: input width in bits
    :type xy_width: int
    :return: x and y, of equal length
    :rtype: tuple[npt.NDArray[np.int64], npt.NDArray[np.int64]]
    """
    low = -(2 ** (xy_width - 1))
    high = 2 ** (xy_width - 1) - 1
    pairs = [(low, low), (low, high), (high, low), (high, high), (0, 0),
             (high, 0), (low, 0), (0, high), (0, low),
             (-1, 0), (-1, -1), (-1, 1), (0, -1), (0, 1), (1, 0)]
    x, y = np.array(sorted(set(pairs)), dtype=np.int64).T
    return x, y
