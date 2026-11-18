/*
 * This file is part of YAC - Yet Another CORDIC Core
 * Copyright (c) 2026, Author(s), All rights reserved.
 *
 * YAC is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation; either version 3.0 of the License, or
 * (at your option) any later version. YAC is distributed in the hope
 * that it will be useful, but WITHOUT ANY WARRANTY; without even the
 * implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
 * PURPOSE. See the GNU Lesser General Public License for more details.
 */

/**
 * @file cordic_pipeline.c
 * @brief Bit-accurate model of the pipelined CORDIC (circular rotation and
 * vectoring).
 */

#include "cordic_pipeline.h"

#include <stddef.h>
#include <stdint.h>

#include "cordic_pipeline_tables.h"

/* The right shifts of negative values below are arithmetic. C99 leaves this
 * implementation-defined; gcc and clang shift arithmetically. */

static int cordic_pipeline_cfg_valid(const cordic_pipeline_cfg_t* cfg) {
  int64_t word;
  if (cfg == NULL) return 0;
  if (cfg->xy_width < 2 || cfg->a_width < 3 || cfg->a_width > 32) return 0;
  if (cfg->guard_bits < 0 || cfg->lsb_bits < 0) return 0;
  if (cfg->n_iter < 1 || cfg->n_iter > CORDIC_PIPELINE_TABLE_SIZE) return 0;
  if (cfg->rm_gain < 0 || cfg->rm_gain > CORDIC_PIPELINE_MAX_RM_GAIN) return 0;
  word = (int64_t)cfg->xy_width + cfg->guard_bits + cfg->lsb_bits;
  return word <= 62;
}

/* Two's complement value of the low `width` bits of u. */
static int64_t cordic_pipeline_wrap(uint64_t u, int32_t width) {
  const uint64_t sign = UINT64_C(1) << (width - 1);
  u &= (sign << 1) - 1U;
  return (int64_t)(u ^ sign) - (int64_t)sign;
}

static void cordic_pipeline_rm_gain(const cordic_pipeline_cfg_t* cfg,
                                    int32_t width, int64_t* x, int64_t* y) {
  uint64_t sum_x = 0;
  uint64_t sum_y = 0;
  int32_t i;
  if (cfg->rm_gain == 0) return;
  for (i = 0; i < cfg->rm_gain; i++) {
    const cordic_pipeline_term_t* term =
        &cordic_pipeline_terms[cfg->rm_gain][i];
    const uint64_t vx = (uint64_t)(*x >> term->shift);
    const uint64_t vy = (uint64_t)(*y >> term->shift);
    if (term->sign > 0) {
      sum_x += vx;
      sum_y += vy;
    } else {
      sum_x -= vx;
      sum_y -= vy;
    }
  }
  *x = cordic_pipeline_wrap(sum_x, width);
  *y = cordic_pipeline_wrap(sum_y, width);
}

int32_t cordic_pipeline_latency(const cordic_pipeline_cfg_t* cfg) {
  if (!cordic_pipeline_cfg_valid(cfg)) return (int32_t)CORDIC_PIPELINE_ERR_CFG;
  return 1 + cfg->n_iter + cfg->rm_gain;
}

int32_t cordic_pipeline(const cordic_pipeline_cfg_t* cfg, int64_t x_i,
                        int64_t y_i, int64_t a_i, int64_t* x_o, int64_t* y_o) {
  int64_t limit;
  int64_t x, y, t, resid;
  uint64_t a;
  int32_t i, q, shift, width;

  if (!cordic_pipeline_cfg_valid(cfg) || x_o == NULL || y_o == NULL)
    return (int32_t)CORDIC_PIPELINE_ERR_CFG;
  width = cfg->xy_width + cfg->guard_bits + cfg->lsb_bits;
  limit = INT64_C(1) << (cfg->xy_width - 1);
  if (x_i < -limit || x_i >= limit || y_i < -limit || y_i >= limit)
    return (int32_t)CORDIC_PIPELINE_ERR_RANGE;

  a = (uint64_t)a_i & ((UINT64_C(1) << cfg->a_width) - 1U);
  q = (int32_t)(a >> (cfg->a_width - 2));
  resid = (int64_t)(a & ((UINT64_C(1) << (cfg->a_width - 2)) - 1U));

  switch (q) {
    case 0:
      x = x_i;
      y = y_i;
      break;
    case 1:
      x = -y_i;
      y = x_i;
      break;
    case 2:
      x = -x_i;
      y = -y_i;
      break;
    default:
      x = y_i;
      y = -x_i;
      break;
  }
  x = cordic_pipeline_wrap((uint64_t)(x * ((int64_t)1 << cfg->lsb_bits)),
                           width);
  y = cordic_pipeline_wrap((uint64_t)(y * ((int64_t)1 << cfg->lsb_bits)),
                           width);

  shift = 32 - cfg->a_width;
  for (i = 0; i < cfg->n_iter; i++) {
    const int64_t at = (int64_t)(cordic_pipeline_atan[i] >> shift);
    const int64_t dx = y >> i;
    const int64_t dy = x >> i;
    if (resid >= 0) {
      t = x - dx;
      y = cordic_pipeline_wrap((uint64_t)(y + dy), width);
      resid -= at;
    } else {
      t = x + dx;
      y = cordic_pipeline_wrap((uint64_t)(y - dy), width);
      resid += at;
    }
    x = cordic_pipeline_wrap((uint64_t)t, width);
  }

  cordic_pipeline_rm_gain(cfg, width, &x, &y);

  *x_o = x >> cfg->lsb_bits;
  *y_o = y >> cfg->lsb_bits;
  return (int32_t)CORDIC_PIPELINE_OK;
}

int32_t cordic_pipeline_vec(const cordic_pipeline_cfg_t* cfg, int64_t x_i,
                            int64_t y_i, int64_t* x_o, int64_t* y_o,
                            int64_t* a_o) {
  int64_t limit;
  int64_t x, y, t;
  uint64_t a, amask;
  int32_t i, shift, width;

  if (!cordic_pipeline_cfg_valid(cfg) || x_o == NULL || y_o == NULL ||
      a_o == NULL)
    return (int32_t)CORDIC_PIPELINE_ERR_CFG;
  width = cfg->xy_width + cfg->guard_bits + cfg->lsb_bits;
  limit = INT64_C(1) << (cfg->xy_width - 1);
  if (x_i < -limit || x_i >= limit || y_i < -limit || y_i >= limit)
    return (int32_t)CORDIC_PIPELINE_ERR_RANGE;

  amask = (UINT64_C(1) << cfg->a_width) - 1U;
  x = cordic_pipeline_wrap((uint64_t)(x_i * ((int64_t)1 << cfg->lsb_bits)),
                           width);
  y = cordic_pipeline_wrap((uint64_t)(y_i * ((int64_t)1 << cfg->lsb_bits)),
                           width);

  if (x >= 0) {
    a = 0;
  } else if (y >= 0) {
    t = x;
    x = y;
    y = cordic_pipeline_wrap((uint64_t)(-t), width);
    a = UINT64_C(1) << (cfg->a_width - 2);
  } else {
    t = x;
    x = cordic_pipeline_wrap((uint64_t)(-y), width);
    y = t;
    a = UINT64_C(3) << (cfg->a_width - 2);
  }

  shift = 32 - cfg->a_width;
  for (i = 0; i < cfg->n_iter; i++) {
    const uint64_t at = cordic_pipeline_atan[i] >> shift;
    const int64_t dx = y >> i;
    const int64_t dy = x >> i;
    if (y >= 0) {
      t = x + dx;
      y = cordic_pipeline_wrap((uint64_t)(y - dy), width);
      a = (a + at) & amask;
    } else {
      t = x - dx;
      y = cordic_pipeline_wrap((uint64_t)(y + dy), width);
      a = (a - at) & amask;
    }
    x = cordic_pipeline_wrap((uint64_t)t, width);
  }

  cordic_pipeline_rm_gain(cfg, width, &x, &y);

  *x_o = x >> cfg->lsb_bits;
  *y_o = y >> cfg->lsb_bits;
  *a_o = (int64_t)a;
  return (int32_t)CORDIC_PIPELINE_OK;
}

int32_t cordic_pipeline_array(const cordic_pipeline_cfg_t* cfg,
                              const int64_t* x_i, const int64_t* y_i,
                              const int64_t* a_i, int64_t* x_o, int64_t* y_o,
                              size_t n) {
  size_t k;
  int32_t err;
  if (n > 0 &&
      (x_i == NULL || y_i == NULL || a_i == NULL || x_o == NULL || y_o == NULL))
    return (int32_t)CORDIC_PIPELINE_ERR_CFG;
  if (!cordic_pipeline_cfg_valid(cfg)) return (int32_t)CORDIC_PIPELINE_ERR_CFG;
  for (k = 0; k < n; k++) {
    err = cordic_pipeline(cfg, x_i[k], y_i[k], a_i[k], &x_o[k], &y_o[k]);
    if (err != CORDIC_PIPELINE_OK) return err;
  }
  return (int32_t)CORDIC_PIPELINE_OK;
}

int32_t cordic_pipeline_vec_array(const cordic_pipeline_cfg_t* cfg,
                                  const int64_t* x_i, const int64_t* y_i,
                                  int64_t* x_o, int64_t* y_o, int64_t* a_o,
                                  size_t n) {
  size_t k;
  int32_t err;
  if (n > 0 &&
      (x_i == NULL || y_i == NULL || x_o == NULL || y_o == NULL || a_o == NULL))
    return (int32_t)CORDIC_PIPELINE_ERR_CFG;
  if (!cordic_pipeline_cfg_valid(cfg)) return (int32_t)CORDIC_PIPELINE_ERR_CFG;
  for (k = 0; k < n; k++) {
    err = cordic_pipeline_vec(cfg, x_i[k], y_i[k], &x_o[k], &y_o[k], &a_o[k]);
    if (err != CORDIC_PIPELINE_OK) return err;
  }
  return (int32_t)CORDIC_PIPELINE_OK;
}
