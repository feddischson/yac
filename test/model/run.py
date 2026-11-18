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
"""Tests of the pipelined CORDIC model. Usage: run.py --out DIR"""

import sys

sys.dont_write_bytecode = True

import argparse
import math
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "c_model"))
sys.path.insert(0, str(ROOT / "test"))

import gen_tables  # noqa: E402
import numpy as np  # noqa: E402
from cordic_test_common import (  # noqa: E402
    build_library, directed_vectors, directed_vectoring_vectors)

OUT = None
LIB = None


def library():
    global LIB
    if LIB is None:
        LIB = build_library(OUT / "lib")
    return LIB


def parse_iterative_terms():
    """Reads the circular terms of cordic_int_rm_gain() in the iterative C model.

    Returns {case: [(sign, shift), ...]} for the cases 1..12. The *x and *y
    blocks must be identical.
    """
    text = (ROOT / "c_octave" / "cordic_iterative.c").read_text()
    start = text.index("void cordic_int_rm_gain(")
    body = text[start:text.index("C_MODE_HYP", start)]
    blocks = {}
    for var in ("x", "y"):
        case_re = re.compile(
            r"case (\d+): \*%s = (.*?);\s*break;" % var)
        term_re = re.compile(r"([+-]) \( \*%s >> (\d+) \)" % var)
        terms = {}
        for case, expr in case_re.findall(body):
            found = term_re.findall(expr)
            terms[int(case)] = [(1 if s == "+" else -1, int(n))
                                for s, n in found]
        blocks[var] = terms
    if blocks["x"] != blocks["y"]:
        raise AssertionError("*x and *y blocks differ")
    for case in range(1, 13):
        if case not in blocks["x"]:
            raise AssertionError("case %d missing" % case)
    return {k: v for k, v in blocks["x"].items() if 1 <= k <= 12}


class TestTables(unittest.TestCase):
    def test_atan_values(self):
        t = gen_tables.atan_table()
        self.assertEqual(len(t), 32)
        self.assertEqual(t[:4], [0x20000000, 0x12E4051E, 0x09FB385B, 0x051111D4])
        self.assertEqual(t[28:], [3, 1, 1, 0])

    def test_terms_match_iterative_model(self):
        self.assertEqual(parse_iterative_terms(), gen_tables.RM_GAIN_TERMS)

    def test_term_count(self):
        for r in range(1, 13):
            self.assertEqual(len(gen_tables.RM_GAIN_TERMS[r]), r)

    def test_generated_files_current(self):
        self.assertEqual(gen_tables.main(["--check"]), 0)


def cordic(**kw):
    from cordic_pipeline import CordicPipeline
    return CordicPipeline(library(), **kw)


def rot(c, x, y, a):
    xo, yo = c.rotate(x, y, a)
    return int(xo), int(yo)


def exact_rotation(x, y, a, a_width):
    th = 2.0 * math.pi * a / 2.0 ** a_width
    return (x * math.cos(th) - y * math.sin(th),
            x * math.sin(th) + y * math.cos(th))


def nominal_gain(n_iter=16, rm_gain=4):
    """Gain of the core: CORDIC gain of n_iter stages times the gain-removal sum."""
    g = 1.0
    for i in range(n_iter):
        g *= math.sqrt(1.0 + 4.0 ** -i)
    return g * sum(sign * 2.0 ** -shift
                   for sign, shift in gen_tables.RM_GAIN_TERMS[rm_gain]) \
        if rm_gain else g


def vec(c, x, y):
    xo, yo, ao = c.vector(x, y)
    return int(xo), int(yo), int(ao)


def vec_bounds(cfg):
    """Returns the vectoring error bounds of cfg as a function of the input.

    :param cfg: (xy_width, a_width, lsb_bits, n_iter, rm_gain)
    :return: f(x, y) giving (m, gm, x_tol, y_tol, a_tol) with the magnitude m,
        the expected magnitude gm = G*m, the tolerances of x_o - gm and y_o,
        and the angle tolerance in angle LSB (None below m = 2^(xy_width-3))
    """
    xy_width, a_width, lsb_bits, n_iter, rm_gain = cfg
    e = 2.0 ** -lsb_bits
    r = math.atan(2.0 ** -(n_iter - 1))
    gain = nominal_gain(n_iter, rm_gain)
    g_n = nominal_gain(n_iter, 0)

    def bounds(x, y):
        m = math.hypot(x, y)
        gm = gain * m
        x_tol = (n_iter + rm_gain) * e + 1 + gm * (1 - math.cos(r))
        y_tol = gm * math.sin(r) + (n_iter + rm_gain) * e + 1
        a_tol = None
        if m >= 2.0 ** (xy_width - 3):
            a_tol = ((r + (n_iter + 2) * e / (g_n * m)) * 2.0 ** a_width
                     / (2 * math.pi) + n_iter + 1)
        return m, gm, x_tol, y_tol, a_tol

    return bounds


def vec_angle_error(a_o, x, y, a_width):
    """Returns |a_o - atan2(y, x)| in angle LSB, wrapped to (-2^(A-1), 2^(A-1)]."""
    exact = np.arctan2(y, x) / (2 * np.pi) * 2.0**a_width
    d = np.mod(a_o - exact, 2.0**a_width)
    d = np.where(d > 2.0**(a_width - 1), d - 2.0**a_width, d)
    return np.abs(d)


def vec_exact_error(cfg, n=20000):
    """Compares the vectoring model with the exact magnitude and angle.

    :param cfg: (xy_width, a_width, lsb_bits, n_iter, rm_gain)
    :param n: number of random full-scale samples, seed 12345
    :return: (rms_mag, max_mag, fitted_gain, max_angle_excess): rms and maximum
        of |x_o - G*M| in output LSB, the least-squares gain of x_o against M,
        and the largest angle error minus its bound over the samples with a
        bound
    """
    xy_width, a_width, lsb_bits, n_iter, rm_gain = cfg
    c = cordic(xy_width=xy_width, a_width=a_width, lsb_bits=lsb_bits,
               n_iter=n_iter, rm_gain=rm_gain)
    rng = np.random.default_rng(12345)
    x = rng.integers(-2**(xy_width - 1), 2**(xy_width - 1), n)
    y = rng.integers(-2**(xy_width - 1), 2**(xy_width - 1), n)
    xo, _, ao = c.vector(x, y)
    m = np.hypot(x, y)
    err = np.abs(xo - nominal_gain(n_iter, rm_gain) * m)
    fitted = float(np.dot(xo, m) / np.dot(m, m))
    bounds = vec_bounds(cfg)
    ang = vec_angle_error(ao, x, y, a_width)
    excess = [ang[k] - bounds(int(x[k]), int(y[k]))[4] for k in range(n)
              if bounds(int(x[k]), int(y[k]))[4] is not None]
    return (float(np.sqrt(np.mean(err**2))), float(np.max(err)), fitted,
            float(max(excess)))


def vec_sweep_row(cfg, n=20000):
    """Measures the vectoring model against the exact magnitude and angle.

    :param cfg: (xy_width, a_width, lsb_bits, n_iter, rm_gain)
    :param n: number of random full-scale samples, seed 12345
    :return: (rms_mag, max_mag, fitted_gain, rms_ang, max_ang): rms and maximum
        of |x_o - G*M| in output LSB, the least-squares gain of x_o against M,
        and rms and maximum of the angle error in angle LSB over the samples
        with M >= 2^(xy_width-3)
    """
    xy_width, a_width, lsb_bits, n_iter, rm_gain = cfg
    c = cordic(xy_width=xy_width, a_width=a_width, lsb_bits=lsb_bits,
               n_iter=n_iter, rm_gain=rm_gain)
    rng = np.random.default_rng(12345)
    x = rng.integers(-2**(xy_width - 1), 2**(xy_width - 1), n)
    y = rng.integers(-2**(xy_width - 1), 2**(xy_width - 1), n)
    xo, _, ao = c.vector(x, y)
    m = np.hypot(x, y)
    err = np.abs(xo - nominal_gain(n_iter, rm_gain) * m)
    fitted = float(np.dot(xo, m) / np.dot(m, m))
    ang = vec_angle_error(ao, x, y, a_width)[m >= 2.0 ** (xy_width - 3)]
    return (float(np.sqrt(np.mean(err**2))), float(np.max(err)), fitted,
            float(np.sqrt(np.mean(ang**2))), float(np.max(ang)))


SWEEP_XY_WIDTH = (12, 14, 16)
SWEEP_A_WIDTH = (16, 18, 20, 22, 24)
SWEEP_LSB_BITS = (0, 2, 4, 6)
SWEEP_N_ITER = (8, 10, 12, 14, 16, 18, 20)
SWEEP_RM_GAIN = (0, 1, 2, 3, 4, 6, 8, 12)
SWEEP_COLUMNS = ("xy_width", "a_width", "lsb_bits", "n_iter", "rm_gain",
                 "latency", "nominal_gain", "fitted_gain", "rms_lsb",
                 "max_lsb")
SWEEP_VEC_COLUMNS = ("xy_width", "a_width", "lsb_bits", "n_iter", "rm_gain",
                     "latency", "nominal_gain", "fitted_gain", "rms_mag_lsb",
                     "max_mag_lsb", "rms_ang_lsb", "max_ang_lsb")
SWEEP = None
SWEEP_VEC = None


def exact_error(cfg, n=20000):
    """Compares the model with the exact rotation scaled by the nominal gain.

    :param cfg: (xy_width, a_width, lsb_bits, n_iter, rm_gain)
    :param n: number of random full-scale samples, fixed seed
    :return: (rms, max, fitted_gain): rms and maximum of the complex error
        magnitude |dx + i*dy| in output LSB, and the least-squares gain of the
        model output against the unscaled exact rotation
    """
    xy_width, a_width, lsb_bits, n_iter, rm_gain = cfg
    c = cordic(xy_width=xy_width, a_width=a_width, lsb_bits=lsb_bits,
               n_iter=n_iter, rm_gain=rm_gain)
    rng = np.random.default_rng(12345)
    x = rng.integers(-2**(xy_width - 1), 2**(xy_width - 1), n)
    y = rng.integers(-2**(xy_width - 1), 2**(xy_width - 1), n)
    a = rng.integers(0, 2**a_width, n)
    xo, yo = c.rotate(x, y, a)
    z = (x + 1j * y) * np.exp(2j * np.pi * a / 2.0**a_width)
    out = xo + 1j * yo
    err = out - z * nominal_gain(n_iter, rm_gain)
    mag = np.abs(err)
    fitted = np.vdot(z, out).real / np.vdot(z, z).real
    return (float(np.sqrt(np.mean(mag**2))), float(np.max(mag)),
            float(fitted))


def run_sweep(out):
    """Writes the accuracy sweep over the generic grid to out/sweep.csv.

    :param out: output directory
    :return: path of sweep.csv
    """
    path = out / "sweep.csv"
    with path.open("w") as f:
        f.write(",".join(SWEEP_COLUMNS) + "\n")
        for xw in SWEEP_XY_WIDTH:
            for aw in SWEEP_A_WIDTH:
                for lsb in SWEEP_LSB_BITS:
                    for n_iter in SWEEP_N_ITER:
                        for r in SWEEP_RM_GAIN:
                            rms, mx, fit = exact_error((xw, aw, lsb, n_iter, r))
                            lat = cordic(xy_width=xw, a_width=aw, lsb_bits=lsb,
                                         n_iter=n_iter, rm_gain=r).latency
                            f.write("%d,%d,%d,%d,%d,%d,%.6f,%.6f,%.4f,%.4f\n"
                                    % (xw, aw, lsb, n_iter, r, lat,
                                       nominal_gain(n_iter, r), fit, rms, mx))
    return path


def run_sweep_vec(out):
    """Writes the vectoring accuracy sweep over the generic grid to out/sweep_vec.csv.

    :param out: output directory
    :return: path of sweep_vec.csv
    """
    path = out / "sweep_vec.csv"
    with path.open("w") as f:
        f.write(",".join(SWEEP_VEC_COLUMNS) + "\n")
        for xw in SWEEP_XY_WIDTH:
            for aw in SWEEP_A_WIDTH:
                for lsb in SWEEP_LSB_BITS:
                    for n_iter in SWEEP_N_ITER:
                        for r in SWEEP_RM_GAIN:
                            rms, mx, fit, arms, amx = vec_sweep_row(
                                (xw, aw, lsb, n_iter, r))
                            lat = cordic(xy_width=xw, a_width=aw, lsb_bits=lsb,
                                         n_iter=n_iter, rm_gain=r).latency
                            f.write("%d,%d,%d,%d,%d,%d,%.6f,%.6f,%.4f,%.4f,"
                                    "%.4f,%.4f\n"
                                    % (xw, aw, lsb, n_iter, r, lat,
                                       nominal_gain(n_iter, r), fit, rms, mx,
                                       arms, amx))
    return path


class TestModel(unittest.TestCase):
    def test_reference_vectors(self):
        c = cordic()
        self.assertEqual(rot(c, 10000, 0, 0), (9972, 0))
        self.assertEqual(rot(c, 10000, 0, 2**16), (0, 9974))
        self.assertEqual(rot(c, -1, -1, 0), (-2, 1))

    def test_quadrants_ccw(self):
        c = cordic(rm_gain=0)
        for q, (ex, ey) in enumerate(
                [(1647, 0), (0, 1647), (-1647, 0), (0, -1647)]):
            xo, yo = rot(c, 1000, 0, q * 2**16)
            self.assertLessEqual(abs(xo - ex), 4, (q, xo, yo))
            self.assertLessEqual(abs(yo - ey), 4, (q, xo, yo))

    def test_angle_wraps(self):
        c = cordic()
        self.assertEqual(rot(c, 12345, -6789, 2**18 + 5),
                         rot(c, 12345, -6789, 5))
        self.assertEqual(rot(c, 12345, -6789, -1),
                         rot(c, 12345, -6789, 2**18 - 1))

    def test_zero_input(self):
        c = cordic()
        for a in range(0, 2**18, 2**18 // 64):
            self.assertEqual(rot(c, 0, 0, a), (0, 0))

    def test_most_negative_input(self):
        c = cordic()
        g = nominal_gain()
        m = -2**15
        for k in range(4):
            for d in (-1, 0, 1):
                a = (k * 2**16 + d) % 2**18
                xo, yo = rot(c, m, m, a)
                ex, ey = [g * v for v in exact_rotation(m, m, a, 18)]
                self.assertLessEqual(abs(xo - ex), 8, (a, xo, ex))
                self.assertLessEqual(abs(yo - ey), 8, (a, yo, ey))
                self.assertLess(abs(xo), 2**17)
                self.assertLess(abs(yo), 2**17)

    def test_all_rm_gain(self):
        big = 2**22
        for r, gain in [(0, 1.64676), (1, .82338), (2, .72046),
                        (3, .97776), (4, .99706), (8, 1.0)]:
            c = cordic(xy_width=24, rm_gain=r)
            xo, yo = rot(c, big, 0, 0)
            self.assertAlmostEqual(xo / big, gain, delta=1e-3, msg=r)

    def test_array_equals_scalar(self):
        c = cordic()
        rng = np.random.default_rng(1)
        x = rng.integers(-2**15, 2**15, 1000)
        y = rng.integers(-2**15, 2**15, 1000)
        a = rng.integers(0, 2**18, 1000)
        xo, yo = c.rotate(x, y, a)
        for i in range(1000):
            self.assertEqual((int(xo[i]), int(yo[i])),
                             rot(c, int(x[i]), int(y[i]), int(a[i])))

    def test_word_overflow_wraps(self):
        kw = dict(xy_width=4, lsb_bits=0, n_iter=1, rm_gain=0)
        self.assertEqual(rot(cordic(guard_bits=0, **kw), -8, -8, 0), (0, 0))
        self.assertEqual(rot(cordic(guard_bits=2, **kw), -8, -8, 0), (0, -16))

    def test_invalid_config(self):
        for kw in [dict(rm_gain=13), dict(n_iter=0), dict(n_iter=33),
                   dict(a_width=2), dict(a_width=33), dict(xy_width=1),
                   dict(xy_width=50, lsb_bits=11), dict(rm_gain=-1),
                   dict(guard_bits=-1), dict(lsb_bits=-1)]:
            with self.assertRaises(ValueError, msg=str(kw)):
                cordic(**kw)

    def test_latency(self):
        self.assertEqual(cordic().latency, 1 + 16 + 4)
        self.assertEqual(cordic(n_iter=3, rm_gain=12).latency, 16)

    def test_input_range(self):
        c = cordic()
        with self.assertRaises(ValueError):
            c.rotate(2**15, 0, 0)
        with self.assertRaises(ValueError):
            c.rotate(0, -2**15 - 1, 0)
        c.rotate(-2**15, 0, 0)

    def test_wrapper_unequal_lengths(self):
        c = cordic()
        with self.assertRaises(ValueError):
            c.rotate([1, 2, 3], [1, 2, 3, 4], [0, 0, 0])

    def test_wrapper_float_input(self):
        c = cordic()
        with self.assertRaises(TypeError):
            c.rotate(1.5, 0, 0)
        with self.assertRaises(TypeError):
            c.rotate(0, 0, np.array([1.0]))

    def test_wrapper_bool_input(self):
        c = cordic()
        with self.assertRaises(TypeError):
            c.rotate(True, 0, 0)
        with self.assertRaises(TypeError):
            c.rotate(np.array([True]), 0, 0)

    def test_wrapper_huge_integers(self):
        c = cordic()
        with self.assertRaises(ValueError):
            c.rotate(np.array([2**63], dtype=np.uint64), 0, 0)
        with self.assertRaises(ValueError):
            c.rotate(0, 0, np.array([2**63 + 5], dtype=np.uint64))
        with self.assertRaises(ValueError):
            c.rotate(2**70, 0, 0)
        with self.assertRaises(ValueError):
            c.rotate(0, 0, 2**70)
        self.assertEqual(rot(c, 100, 0, np.uint64(2**18 + 5)),
                         rot(c, 100, 0, 5))

    def test_wrapper_empty(self):
        c = cordic()
        xo, yo = c.rotate(*[np.array([], dtype=np.int64)] * 3)
        self.assertEqual((xo.shape, yo.shape, xo.dtype), ((0,), (0,), np.int64))

    def test_wrapper_scalar_and_shape(self):
        c = cordic()
        xo, yo = c.rotate(1000, 0, 0)
        self.assertEqual(xo.shape, ())
        rng = np.random.default_rng(2)
        x = rng.integers(-2000, 2000, (3, 5))
        y = rng.integers(-2000, 2000, (3, 5))
        a = rng.integers(0, 2**18, (3, 5))
        xo, yo = c.rotate(x, y, a)
        self.assertEqual((xo.shape, xo.dtype), ((3, 5), np.int64))
        xf, yf = c.rotate(np.asfortranarray(x), np.asfortranarray(y),
                          np.asfortranarray(a))
        self.assertTrue(np.array_equal(xo, xf) and np.array_equal(yo, yf))
        xb, yb = c.rotate(x, 7, 3)
        self.assertEqual(xb.shape, (3, 5))

    def test_c99_build(self):
        src = ROOT / "c_model" / "cordic_pipeline.c"
        subprocess.run(
            ["gcc", "-std=c99", "-pedantic", "-Wall", "-Wextra", "-Werror",
             "-c", str(src), "-o", str(OUT / "c99_check.o")], check=True)


class TestDirectedVectors(unittest.TestCase):
    def check_vectors(self, xy_width, a_width, angles):
        x, y, a = directed_vectors(xy_width, a_width)
        m = 2**(xy_width - 1)
        self.assertEqual((x.dtype, y.dtype, a.dtype), (np.int64,) * 3)
        pairs = set(zip(x.tolist(), y.tolist()))
        self.assertEqual(pairs, {(-m, -m), (-m, m - 1), (m - 1, -m),
                                 (m - 1, m - 1), (0, 0)})
        self.assertEqual(set(a.tolist()), angles)
        triples = set(zip(x.tolist(), y.tolist(), a.tolist()))
        self.assertEqual(len(triples), len(x))
        self.assertEqual(len(x), len(pairs) * len(angles))

    def test_values_apart(self):
        q = 2**16
        self.check_vectors(16, 18, {
            0, 1, 2**18 - 1,
            q - 1, q, q + 1,
            2 * q - 1, 2 * q, 2 * q + 1,
            3 * q - 1, 3 * q, 3 * q + 1})

    def test_values_overlap(self):
        self.check_vectors(8, 3, set(range(8)))

    def test_vectoring_vectors(self):
        x, y = directed_vectoring_vectors(16)
        m = 2**15
        self.assertEqual((x.dtype, y.dtype), (np.int64, np.int64))
        pairs = list(zip(x.tolist(), y.tolist()))
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertEqual(set(pairs), {
            (-m, -m), (-m, m - 1), (m - 1, -m), (m - 1, m - 1), (0, 0),
            (m - 1, 0), (-m, 0), (0, m - 1), (0, -m),
            (-1, 0), (-1, -1), (-1, 1), (0, -1), (0, 1), (1, 0)})


class TestVectoring(unittest.TestCase):
    DEFAULT = (16, 18, 0, 16, 4)

    def check_bounds(self, cfg, x, y, xo, yo, ao):
        xy_width, a_width = cfg[0], cfg[1]
        bounds = vec_bounds(cfg)
        ang = vec_angle_error(np.asarray(ao), np.asarray(x), np.asarray(y),
                              a_width)
        for k in range(len(x)):
            m, gm, x_tol, y_tol, a_tol = bounds(int(x[k]), int(y[k]))
            msg = (cfg, int(x[k]), int(y[k]), int(xo[k]), int(yo[k]),
                   int(ao[k]))
            self.assertLessEqual(abs(xo[k] - gm), x_tol, msg)
            self.assertLessEqual(abs(yo[k]), y_tol, msg)
            self.assertGreaterEqual(xo[k], 0, msg)
            self.assertTrue(0 <= ao[k] < 2**a_width, msg)
            if a_tol is not None:
                self.assertLessEqual(ang[k], a_tol, msg)

    def test_vec_axes(self):
        cfg = (16, 18, 0, 16, 0)
        c = cordic(rm_gain=0)
        bounds = vec_bounds(cfg)
        v = 2**15 - 1
        for (x, y), a in [((v, 0), 0), ((0, v), 2**16), ((-v, 0), 2**17),
                          ((0, -v), 3 * 2**16)]:
            xo, yo, ao = vec(c, x, y)
            m, gm, x_tol, y_tol, a_tol = bounds(x, y)
            self.assertLessEqual(abs(xo - gm), x_tol, (x, y, xo))
            diff = (ao - a + 2**17) % 2**18 - 2**17
            self.assertLessEqual(abs(diff), a_tol, (x, y, ao))

    def test_vec_halfplane_boundary(self):
        c = cordic()
        bounds = vec_bounds(self.DEFAULT)
        s = 2**14
        for (x, y), a in [((-s, 0), 2**17), ((-s, -s), 2**17 + 2**15),
                          ((-s, s), 2**17 - 2**15),
                          ((-s, -1), 2**17 + round(
                              math.atan(2.0**-14) / (2 * math.pi) * 2**18))]:
            _, _, ao = vec(c, x, y)
            self.assertLessEqual(abs(ao - a), bounds(x, y)[4], (x, y, ao))

    def test_vec_most_negative(self):
        c = cordic()
        m, h = -2**15, 2**15 - 1
        x, y = np.array([m, m, h, h]), np.array([m, h, m, h])
        xo, yo, ao = c.vector(x, y)
        self.check_bounds(self.DEFAULT, x, y, xo, yo, ao)
        self.assertTrue(np.all(np.abs(xo) < 2**17))
        self.assertTrue(np.all(np.abs(yo) < 2**17))

    def test_vec_zero(self):
        xo, yo, ao = vec(cordic(), 0, 0)
        self.assertEqual((xo, yo), (0, 0))
        self.assertTrue(0 <= ao < 2**18)

    def test_vec_bounds_random(self):
        for cfg in [(16, 18, 0, 16, 4), (12, 18, 0, 10, 0), (16, 24, 6, 20, 12),
                    (8, 10, 0, 12, 4)]:
            xy_width, a_width, lsb_bits, n_iter, rm_gain = cfg
            c = cordic(xy_width=xy_width, a_width=a_width, lsb_bits=lsb_bits,
                       n_iter=n_iter, rm_gain=rm_gain)
            rng = np.random.default_rng(12345)
            x = rng.integers(-2**(xy_width - 1), 2**(xy_width - 1), 20000)
            y = rng.integers(-2**(xy_width - 1), 2**(xy_width - 1), 20000)
            dx, dy = directed_vectoring_vectors(xy_width)
            x, y = np.concatenate([x, dx]), np.concatenate([y, dy])
            xo, yo, ao = c.vector(x, y)
            self.check_bounds(cfg, x, y, xo, yo, ao)
            self.assertLessEqual(vec_exact_error(cfg)[3], 0.0, cfg)

    def test_vec_fsa_gain(self):
        cfg = (12, 18, 0, 10, 0)
        rms, mx, fitted, _ = vec_exact_error(cfg)
        self.assertAlmostEqual(fitted, nominal_gain(10, 0), delta=1e-3)
        self.assertLess(rms, 3.0)
        self.assertLess(mx, 16)

    def test_vec_guard_bits(self):
        def differing(xy_width, a_width, n_iter, rm_gain, lsb_bits):
            kw = dict(xy_width=xy_width, a_width=a_width, n_iter=n_iter,
                      rm_gain=rm_gain, lsb_bits=lsb_bits)
            v = np.arange(-2**(xy_width - 1), 2**(xy_width - 1))
            x, y = np.meshgrid(v, v)
            r2 = cordic(guard_bits=2, **kw).vector(x, y)
            r8 = cordic(guard_bits=8, **kw).vector(x, y)
            return not all(np.array_equal(p, q) for p, q in zip(r2, r8))

        grid = [(a, n, r, lsb) for a in (6, 8) for n in (8, 16, 32)
                for r in (0, 4, 12) for lsb in (0, 1, 4)]
        for xy_width in (6, 7, 8):
            for g in grid:
                self.assertFalse(differing(xy_width, *g), (xy_width, g))
        diff5 = [g for g in grid if differing(5, *g)]
        print("\nvectoring guard bits, XY_WIDTH=5, (A,N,RM,LSB) differing "
              "at 2 against 8 guard bits: %d of %d: %s"
              % (len(diff5), len(grid), diff5))

    def test_vec_array_equals_scalar(self):
        c = cordic()
        rng = np.random.default_rng(1)
        x = rng.integers(-2**15, 2**15, 1000)
        y = rng.integers(-2**15, 2**15, 1000)
        xo, yo, ao = c.vector(x, y)
        for i in range(1000):
            self.assertEqual((int(xo[i]), int(yo[i]), int(ao[i])),
                             vec(c, int(x[i]), int(y[i])))

    def test_vec_input_range(self):
        c = cordic()
        with self.assertRaises(ValueError):
            c.vector(2**15, 0)
        with self.assertRaises(ValueError):
            c.vector(0, -2**15 - 1)
        c.vector(-2**15, 0)

    def test_vec_wrapper_float_input(self):
        c = cordic()
        with self.assertRaises(TypeError):
            c.vector(1.5, 0)
        with self.assertRaises(TypeError):
            c.vector(0, np.array([1.0]))

    def test_vec_wrapper_scalar_and_shape(self):
        c = cordic()
        xo, yo, ao = c.vector(1000, 5)
        self.assertEqual((xo.shape, yo.shape, ao.shape), ((), (), ()))
        rng = np.random.default_rng(2)
        x = rng.integers(-2000, 2000, (3, 5))
        y = rng.integers(-2000, 2000, (3, 5))
        xo, yo, ao = c.vector(x, y)
        self.assertEqual((xo.shape, yo.shape, ao.shape), ((3, 5),) * 3)
        self.assertEqual((xo.dtype, yo.dtype, ao.dtype), (np.int64,) * 3)


class TestAccuracy(unittest.TestCase):
    def test_high_precision(self):
        rms, mx, _ = exact_error((16, 24, 6, 20, 12))
        self.assertLess(rms, 1.0)
        self.assertLess(mx, 2.0)

    def test_defaults(self):
        rms, mx, _ = exact_error((16, 18, 0, 16, 4))
        self.assertLess(rms, 3.0)
        self.assertLess(mx, 16)

    def test_lsb_bits_help(self):
        rms0 = exact_error((16, 24, 0, 20, 12))[0]
        rms4 = exact_error((16, 24, 4, 20, 12))[0]
        self.assertLess(rms4, rms0)

    def test_iterations_help(self):
        rms = {n: exact_error((16, 24, 6, n, 12))[0] for n in (10, 14, 20)}
        self.assertLess(rms[20], rms[14])
        self.assertLess(rms[14], rms[10])

    def test_gain_matches_nominal(self):
        for r in SWEEP_RM_GAIN:
            fitted = exact_error((16, 24, 6, 20, r))[2]
            self.assertAlmostEqual(fitted, nominal_gain(20, r), delta=1e-3,
                                   msg=r)

    def test_sweep_csv(self):
        lines = SWEEP.read_text().splitlines()
        self.assertEqual(lines[0], ",".join(SWEEP_COLUMNS))
        self.assertEqual(len(lines) - 1, 3360)

    def test_sweep_vec_csv(self):
        lines = SWEEP_VEC.read_text().splitlines()
        self.assertEqual(lines[0], ",".join(SWEEP_VEC_COLUMNS))
        self.assertEqual(len(lines) - 1, 3360)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    global OUT
    OUT = args.out.resolve()
    global SWEEP, SWEEP_VEC
    SWEEP = run_sweep(OUT)
    SWEEP_VEC = run_sweep_vec(OUT)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
