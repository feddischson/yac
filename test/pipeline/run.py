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
"""VUnit run of cordic_pipeline_int against the C model."""

import sys

sys.dont_write_bytecode = True

import tempfile  # noqa: E402
from collections.abc import Callable  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import NamedTuple  # noqa: E402

import numpy as np  # noqa: E402
from vunit import VUnit  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "c_model"))
sys.path.insert(0, str(ROOT / "test"))

from cordic_pipeline import CordicPipeline  # noqa: E402
from cordic_test_common import Vectors, build_library, directed_vectors  # noqa: E402

RTL = ROOT / "rtl" / "vhdl"
N_RANDOM = 1000
SEED = 20261031


class Config(NamedTuple):
    """Generics of one testbench configuration, identified by its name."""

    name: str
    xy_width: int
    a_width: int
    guard_bits: int
    lsb_bits: int
    n_iter: int
    rm_gain: int


CONFIGS = (
    Config("default", 16, 18, 2, 0, 16, 4),
    Config("rm0", 16, 18, 2, 0, 16, 0),
    Config("rm12", 16, 18, 2, 0, 16, 12),
    Config("lsb4", 16, 18, 2, 4, 16, 4),
    Config("reference", 14, 18, 2, 0, 10, 4),
    Config("wide", 24, 32, 2, 8, 32, 12),
    Config("small", 6, 8, 2, 0, 8, 1),
    Config("guard3", 12, 14, 3, 2, 14, 6),
    Config("min_angle", 8, 3, 2, 0, 4, 2),
    Config("guard1", 8, 10, 1, 0, 12, 4),
    Config("narrow", 4, 8, 2, 0, 32, 0),
)


def inputs(cfg: Config) -> Vectors:
    """Returns the directed samples followed by the random samples of cfg.

    :param cfg: configuration
    :type cfg: Config
    :return: x, y and a, of equal length
    :rtype: Vectors
    """
    x, y, a = directed_vectors(cfg.xy_width, cfg.a_width)
    rng = np.random.default_rng(SEED)
    limit = 2 ** (cfg.xy_width - 1)
    return (
        np.concatenate((x, rng.integers(-limit, limit, N_RANDOM))),
        np.concatenate((y, rng.integers(-limit, limit, N_RANDOM))),
        np.concatenate((a, rng.integers(0, 2**cfg.a_width, N_RANDOM))),
    )


def model(library: Path, cfg: Config) -> CordicPipeline:
    """Returns the C model of cfg.

    :param library: path of the shared library
    :type library: Path
    :param cfg: configuration
    :type cfg: Config
    :return: the model
    :rtype: CordicPipeline
    """
    return CordicPipeline(
        library,
        xy_width=cfg.xy_width,
        a_width=cfg.a_width,
        guard_bits=cfg.guard_bits,
        lsb_bits=cfg.lsb_bits,
        n_iter=cfg.n_iter,
        rm_gain=cfg.rm_gain,
    )


def binary(value: int, width: int) -> str:
    """Returns the two's complement of value as a binary string of width bits.

    :param value: value
    :type value: int
    :param width: number of bits
    :type width: int
    :return: binary string
    :rtype: str
    """
    return format(value & (2**width - 1), f"0{width}b")


def make_hook(cfg: Config) -> Callable[[str], bool]:
    """Returns the pre_config hook, which writes the data files of cfg.

    :param cfg: configuration
    :type cfg: Config
    :return: hook taking the VUnit output path
    :rtype: Callable[[str], bool]
    """

    def hook(output_path: str) -> bool:
        out = Path(output_path)
        x, y, a = inputs(cfg)
        x_o, y_o = model(build_library(out), cfg).rotate(x, y, a)
        with (out / "stimulus.txt").open("w") as stimulus:
            for xv, yv, av in zip(x.tolist(), y.tolist(), a.tolist()):
                stimulus.write(
                    f"{binary(xv, cfg.xy_width)} {binary(yv, cfg.xy_width)} "
                    f"{binary(av, cfg.a_width)}\n")
        width = cfg.xy_width + cfg.guard_bits
        with (out / "expected.txt").open("w") as expected:
            for xv, yv in zip(x_o.tolist(), y_o.tolist()):
                expected.write(f"{binary(xv, width)} {binary(yv, width)}\n")
        return True

    return hook


def main() -> None:
    """Runs the testbench once per entry of CONFIGS."""
    ui = VUnit.from_argv(compile_builtins=False)
    ui.add_vhdl_builtins()
    lib = ui.add_library("yac_lib")
    for name in ("cordic_pipeline_pkg.vhd", "cordic_pipeline_int.vhd",
                 "tb_cordic_pipeline.vhd"):
        lib.add_source_file(RTL / name)
    tb = lib.test_bench("tb_cordic_pipeline")
    tb.set_sim_option("disable_ieee_warnings", True)
    with tempfile.TemporaryDirectory() as tmp:
        library = build_library(Path(tmp))
        for cfg in CONFIGS:
            tb.add_config(
                cfg.name,
                generics={
                    "XY_WIDTH": cfg.xy_width,
                    "A_WIDTH": cfg.a_width,
                    "GUARD_BITS": cfg.guard_bits,
                    "LSB_BITS": cfg.lsb_bits,
                    "N_ITER": cfg.n_iter,
                    "RM_GAIN": cfg.rm_gain,
                    "EXPECTED_LATENCY": model(library, cfg).latency,
                    "N_SAMPLES": inputs(cfg)[0].size,
                },
                pre_config=make_hook(cfg))
    ui.main()


if __name__ == "__main__":
    main()
