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
 * @file cordic_pipeline.h
 * @brief Bit-accurate model of the pipelined CORDIC (circular rotation).
 */

#ifndef CORDIC_PIPELINE_H_
#define CORDIC_PIPELINE_H_

#include <stddef.h>
#include <stdint.h>

/** Generics of the core. */
typedef struct {
  int32_t xy_width;   /**< input width, >= 2 */
  int32_t a_width;    /**< angle width, 3 to 32 */
  int32_t guard_bits; /**< MSB guard bits, >= 0 */
  int32_t lsb_bits;   /**< internal fraction bits, >= 0 */
  int32_t n_iter;     /**< CORDIC iterations, 1 to 32 */
  int32_t rm_gain;    /**< gain-removal terms, 0 to 12 */
} cordic_pipeline_cfg_t;

/** Success. */
#define CORDIC_PIPELINE_OK 0L
/** Invalid configuration, or a NULL pointer argument. */
#define CORDIC_PIPELINE_ERR_CFG (-1L)
/** x or y outside the signed range of xy_width bits. */
#define CORDIC_PIPELINE_ERR_RANGE (-2L)

/**
 * @brief Latency in clocks: 1 + n_iter + rm_gain.
 * @param cfg Configuration.
 * @return The latency, or CORDIC_PIPELINE_ERR_CFG.
 */
int32_t cordic_pipeline_latency(const cordic_pipeline_cfg_t* cfg);

/**
 * @brief Rotates one sample.
 * @param cfg Configuration.
 * @param x_i Real part, signed xy_width bits.
 * @param y_i Imaginary part, signed xy_width bits.
 * @param a_i Angle, wrapped to a_width bits as a fraction of a full circle.
 * @param x_o Result, signed xy_width + guard_bits bits.
 * @param y_o Result, signed xy_width + guard_bits bits.
 * @return CORDIC_PIPELINE_OK or an error code. The outputs are written only on
 * success.
 */
int32_t cordic_pipeline(const cordic_pipeline_cfg_t* cfg, int64_t x_i,
                        int64_t y_i, int64_t a_i, int64_t* x_o, int64_t* y_o);

/**
 * @brief Rotates n samples with cordic_pipeline().
 * @param cfg Configuration, see cordic_pipeline().
 * @param x_i Input x of n samples.
 * @param y_i Input y of n samples.
 * @param a_i Input angle of n samples.
 * @param x_o Result x of n samples, signed xy_width + guard_bits bits.
 * @param y_o Result y of n samples, signed xy_width + guard_bits bits.
 * @param n Number of samples.
 * @return CORDIC_PIPELINE_OK or the first error code. The outputs of the
 * samples before the error are written.
 */
int32_t cordic_pipeline_array(const cordic_pipeline_cfg_t* cfg,
                              const int64_t* x_i, const int64_t* y_i,
                              const int64_t* a_i, int64_t* x_o, int64_t* y_o,
                              size_t n);

#endif /* CORDIC_PIPELINE_H_ */
