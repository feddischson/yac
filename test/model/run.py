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
from cordic_test_common import build_library, directed_vectors  # noqa: E402

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


SWEEP_XY_WIDTH = (12, 14, 16)
SWEEP_A_WIDTH = (16, 18, 20, 22, 24)
SWEEP_LSB_BITS = (0, 2, 4, 6)
SWEEP_N_ITER = (8, 10, 12, 14, 16, 18, 20)
SWEEP_RM_GAIN = (0, 1, 2, 3, 4, 6, 8, 12)
SWEEP_COLUMNS = ("xy_width", "a_width", "lsb_bits", "n_iter", "rm_gain",
                 "latency", "nominal_gain", "fitted_gain", "rms_lsb",
                 "max_lsb")
SWEEP = None


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    global OUT
    OUT = args.out.resolve()
    global SWEEP
    SWEEP = run_sweep(OUT)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
