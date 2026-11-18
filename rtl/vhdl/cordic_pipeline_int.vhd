----------------------------------------------------------------------------
----                                                                    ----
----  File           : cordic_pipeline_int.vhd                          ----
----  Project        : YAC (Yet Another CORDIC Core)                    ----
----  Creation       : Oct. 2026                                        ----
----  Limitations    : Circular rotation and vectoring                  ----
----  Synthesizer    :                                                  ----
----  Target         :                                                  ----
----                                                                    ----
----  Author(s):     : Christian Haettich                               ----
----  Email          : feddischson@gmail.com                            ----
----                                                                    ----
----                                                                    ----
-----                                                                  -----
----                                                                    ----
----  Description                                                       ----
----        Pipelined CORDIC rotation with a binary angle: one sample   ----
----        per clock, fixed latency. c_model/cordic_pipeline.c is its  ----
----        bit-accurate model.                                         ----
----                                                                    ----
-----                                                                  -----
----                                                                    ----
----                  Copyright Notice                                  ----
----                                                                    ----
---- This file is part of YAC - Yet Another CORDIC Core                 ----
---- Copyright (c) 2026, Author(s), All rights reserved.                ----
----                                                                    ----
---- YAC is free software; you can redistribute it and/or               ----
---- modify it under the terms of the GNU Lesser General Public         ----
---- License as published by the Free Software Foundation; either       ----
---- version 3.0 of the License, or (at your option) any later version. ----
----                                                                    ----
---- YAC is distributed in the hope that it will be useful,             ----
---- but WITHOUT ANY WARRANTY; without even the implied warranty of     ----
---- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU  ----
---- Lesser General Public License for more details.                    ----
----                                                                    ----
---- You should have received a copy of the GNU Lesser General Public   ----
---- License along with this library. If not, download it from          ----
---- http://www.gnu.org/licenses/lgpl                                   ----
----                                                                    ----
----------------------------------------------------------------------------


library ieee;
use ieee.std_logic_1164.ALL;
use ieee.numeric_std.ALL;
use work.cordic_pipeline_pkg.ALL;

entity cordic_pipeline_int is
generic(
   XY_WIDTH    : natural := 16;  -- input width
   A_WIDTH     : natural := 18;  -- angle width, 2**A_WIDTH is a full circle
   GUARD_BITS  : natural :=  2;  -- MSB guard bits
   LSB_BITS    : natural :=  0;  -- internal fraction bits
   N_ITER      : natural := 16;  -- CORDIC iterations
   RM_GAIN     : natural :=  4;  -- gain-removal terms, 0 to 12
   VECTORING   : boolean := false -- true: vectoring, a_i ignored, a_o is the angle
       );
port(
   clk, rst  : in  std_logic;
   en        : in  std_logic;
   valid_i   : in  std_logic;
   x_i       : in  std_logic_vector( XY_WIDTH-1 downto 0 );
   y_i       : in  std_logic_vector( XY_WIDTH-1 downto 0 );
   a_i       : in  std_logic_vector( A_WIDTH-1  downto 0 );
   valid_o   : out std_logic;
   x_o       : out std_logic_vector( XY_WIDTH+GUARD_BITS-1 downto 0 );
   y_o       : out std_logic_vector( XY_WIDTH+GUARD_BITS-1 downto 0 );
   a_o       : out std_logic_vector( A_WIDTH-1 downto 0 )
    );
end entity cordic_pipeline_int;


architecture BEHAVIORAL of cordic_pipeline_int is

   constant WORD_WIDTH  : natural := XY_WIDTH + GUARD_BITS + LSB_BITS;
   constant RESID_WIDTH : natural := A_WIDTH - 1;
   constant LATENCY     : natural := cordic_pipeline_latency( N_ITER, RM_GAIN );

   subtype word_t  is signed( WORD_WIDTH-1  downto 0 );
   subtype resid_t is signed( RESID_WIDTH-1 downto 0 );

   type iter_stage_t is record
      x : word_t;
      y : word_t;
      a   : resid_t;
      acc : unsigned( A_WIDTH-1 downto 0 );
   end record iter_stage_t;
   type iter_stages_t is array( 0 to N_ITER ) of iter_stage_t;

   type gain_stage_t is record
      x     : word_t;
      y     : word_t;
      x_sum : word_t;
      y_sum : word_t;
      acc   : unsigned( A_WIDTH-1 downto 0 );
   end record gain_stage_t;
   type gain_stages_t is array( 1 to RM_GAIN ) of gain_stage_t;

   signal iter  : iter_stages_t;
   signal gain  : gain_stages_t;
   signal valid : std_logic_vector( LATENCY-1 downto 0 );

   signal x_word : word_t;
   signal y_word : word_t;
   signal a_word : unsigned( A_WIDTH-1 downto 0 );

begin

   assert XY_WIDTH >= 2
      report "XY_WIDTH must be at least 2" severity failure;
   assert A_WIDTH >= 3 and A_WIDTH <= ATAN_TABLE_WIDTH
      report "A_WIDTH must be 3 to 32" severity failure;
   assert N_ITER >= 1 and N_ITER <= ATAN_TABLE_SIZE
      report "N_ITER must be 1 to 32" severity failure;
   assert RM_GAIN <= MAX_RM_GAIN
      report "RM_GAIN must be 0 to 12" severity failure;
   assert WORD_WIDTH <= 62
      report "XY_WIDTH+GUARD_BITS+LSB_BITS must be at most 62" severity failure;


   data_pipeline : process( clk )
      variable x_scaled : word_t;
      variable y_scaled : word_t;
      variable at       : resid_t;
      variable at_acc   : unsigned( A_WIDTH-1 downto 0 );
      variable x_sh     : word_t;
      variable y_sh     : word_t;
      variable prev     : gain_stage_t;
   begin
      if rising_edge( clk ) then
         if en = '1' then

            x_scaled := shift_left( resize( signed( x_i ), WORD_WIDTH ), LSB_BITS );
            y_scaled := shift_left( resize( signed( y_i ), WORD_WIDTH ), LSB_BITS );
            if VECTORING then
               if x_scaled( WORD_WIDTH-1 ) = '0' then
                  iter( 0 ).x   <= x_scaled;
                  iter( 0 ).y   <= y_scaled;
                  iter( 0 ).acc <= ( others => '0' );
               elsif y_scaled( WORD_WIDTH-1 ) = '0' then
                  iter( 0 ).x   <= y_scaled;
                  iter( 0 ).y   <= -x_scaled;
                  iter( 0 ).acc <= "01" & to_unsigned( 0, A_WIDTH-2 );
               else
                  iter( 0 ).x   <= -y_scaled;
                  iter( 0 ).y   <= x_scaled;
                  iter( 0 ).acc <= "11" & to_unsigned( 0, A_WIDTH-2 );
               end if;
            else
               case a_i( A_WIDTH-1 downto A_WIDTH-2 ) is
                  when "00" =>
                     iter( 0 ).x <= x_scaled;
                     iter( 0 ).y <= y_scaled;
                  when "01" =>
                     iter( 0 ).x <= -y_scaled;
                     iter( 0 ).y <= x_scaled;
                  when "10" =>
                     iter( 0 ).x <= -x_scaled;
                     iter( 0 ).y <= -y_scaled;
                  when others =>
                     iter( 0 ).x <= y_scaled;
                     iter( 0 ).y <= -x_scaled;
               end case;
               iter( 0 ).a <= signed( resize( unsigned( a_i( A_WIDTH-3 downto 0 ) ), RESID_WIDTH ) );
            end if;

            for i in 0 to N_ITER-1 loop
               at     := signed( resize( shift_right( ATAN_TABLE( i ),
                                                      ATAN_TABLE_WIDTH-A_WIDTH ), RESID_WIDTH ) );
               at_acc := resize( shift_right( ATAN_TABLE( i ), ATAN_TABLE_WIDTH-A_WIDTH ), A_WIDTH );
               x_sh   := shift_right( iter( i ).x, i );
               y_sh   := shift_right( iter( i ).y, i );
               if VECTORING then
                  if iter( i ).y( WORD_WIDTH-1 ) = '0' then
                     iter( i+1 ).x   <= iter( i ).x + y_sh;
                     iter( i+1 ).y   <= iter( i ).y - x_sh;
                     iter( i+1 ).acc <= iter( i ).acc + at_acc;
                  else
                     iter( i+1 ).x   <= iter( i ).x - y_sh;
                     iter( i+1 ).y   <= iter( i ).y + x_sh;
                     iter( i+1 ).acc <= iter( i ).acc - at_acc;
                  end if;
               else
                  -- The sign bit, because a comparison warns on an unknown value in a gap.
                  if iter( i ).a( RESID_WIDTH-1 ) = '0' then
                     iter( i+1 ).x <= iter( i ).x - y_sh;
                     iter( i+1 ).y <= iter( i ).y + x_sh;
                     iter( i+1 ).a <= iter( i ).a - at;
                  else
                     iter( i+1 ).x <= iter( i ).x + y_sh;
                     iter( i+1 ).y <= iter( i ).y - x_sh;
                     iter( i+1 ).a <= iter( i ).a + at;
                  end if;
               end if;
            end loop;

            for i in 1 to RM_GAIN loop
               if i = 1 then
                  prev := ( x     => iter( N_ITER ).x,
                            y     => iter( N_ITER ).y,
                            x_sum => ( others => '0' ),
                            y_sum => ( others => '0' ),
                            acc   => iter( N_ITER ).acc );
               else
                  prev := gain( i-1 );
               end if;
               x_sh := shift_right( prev.x, RM_GAIN_TERMS( RM_GAIN, i ).shift );
               y_sh := shift_right( prev.y, RM_GAIN_TERMS( RM_GAIN, i ).shift );
               gain( i ).x <= prev.x;
               gain( i ).y <= prev.y;
               gain( i ).acc <= prev.acc;
               if RM_GAIN_TERMS( RM_GAIN, i ).add then
                  gain( i ).x_sum <= prev.x_sum + x_sh;
                  gain( i ).y_sum <= prev.y_sum + y_sh;
               else
                  gain( i ).x_sum <= prev.x_sum - x_sh;
                  gain( i ).y_sum <= prev.y_sum - y_sh;
               end if;
            end loop;

         end if;
      end if;
   end process data_pipeline;


   valid_chain : process( clk )
   begin
      if rising_edge( clk ) then
         if rst = '1' then
            valid <= ( others => '0' );
         elsif en = '1' then
            valid <= valid( LATENCY-2 downto 0 ) & valid_i;
         end if;
      end if;
   end process valid_chain;


   gen_no_gain : if RM_GAIN = 0 generate
      x_word <= iter( N_ITER ).x;
      y_word <= iter( N_ITER ).y;
      a_word <= iter( N_ITER ).acc;
   end generate gen_no_gain;

   gen_gain : if RM_GAIN > 0 generate
      x_word <= gain( RM_GAIN ).x_sum;
      y_word <= gain( RM_GAIN ).y_sum;
      a_word <= gain( RM_GAIN ).acc;
   end generate gen_gain;

   valid_o <= valid( LATENCY-1 );
   x_o     <= std_logic_vector( x_word( WORD_WIDTH-1 downto LSB_BITS ) );
   y_o     <= std_logic_vector( y_word( WORD_WIDTH-1 downto LSB_BITS ) );

   gen_a_vec : if VECTORING generate
      a_o <= std_logic_vector( a_word );
   end generate gen_a_vec;

   gen_a_rot : if not VECTORING generate
      a_o <= ( others => '0' );
   end generate gen_a_rot;

end architecture BEHAVIORAL;
