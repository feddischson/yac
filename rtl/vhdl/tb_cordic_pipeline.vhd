----------------------------------------------------------------------------
----                                                                    ----
----  File           : tb_cordic_pipeline.vhd                           ----
----  Project        : YAC (Yet Another CORDIC Core)                    ----
----  Creation       : Oct. 2026                                        ----
----  Limitations    :                                                  ----
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
----        VUnit testbench of cordic_pipeline_int: compares the core   ----
----        with the C model data from test/pipeline/run.py             ----
----                                                                    ----
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
library std;
library vunit_lib;
use std.textio.all;
use ieee.std_logic_1164.ALL;
use ieee.math_real.ALL;
use work.cordic_pipeline_pkg.ALL;
context vunit_lib.vunit_context;

entity tb_cordic_pipeline is
generic(
   runner_cfg       : string;
   XY_WIDTH         : natural;
   A_WIDTH          : natural;
   GUARD_BITS       : natural;
   LSB_BITS         : natural;
   N_ITER           : natural;
   RM_GAIN          : natural;
   EXPECTED_LATENCY : natural;
   N_SAMPLES        : natural
       );
end entity tb_cordic_pipeline;


architecture BEHAVIORAL of tb_cordic_pipeline is

   constant CLK_PERIOD : time := 10 ns;

   -- Samples of a reset test: fills the pipeline and delivers some outputs.
   constant N_RESET : natural := minimum( N_SAMPLES, EXPECTED_LATENCY+4 );

   signal clk     : std_logic := '0';
   signal rst     : std_logic := '1';
   signal en      : std_logic;
   signal valid_i : std_logic := '0';
   signal x_i     : std_logic_vector( XY_WIDTH-1 downto 0 ) := ( others => 'X' );
   signal y_i     : std_logic_vector( XY_WIDTH-1 downto 0 ) := ( others => 'X' );
   signal a_i     : std_logic_vector( A_WIDTH-1  downto 0 ) := ( others => 'X' );
   signal valid_o : std_logic;
   signal x_o     : std_logic_vector( XY_WIDTH+GUARD_BITS-1 downto 0 );
   signal y_o     : std_logic_vector( XY_WIDTH+GUARD_BITS-1 downto 0 );

   signal en_main      : std_logic := '1';
   signal en_rand      : std_logic := '1';
   signal en_rand_on   : boolean   := false;
   signal started      : boolean   := false;
   signal samples_seen : natural   := 0;
   signal restart      : natural   := 0;

begin

   clk <= not clk after CLK_PERIOD/2;
   en  <= en_main and en_rand;

   DUT : entity work.cordic_pipeline_int
   generic map(
      XY_WIDTH   => XY_WIDTH,
      A_WIDTH    => A_WIDTH,
      GUARD_BITS => GUARD_BITS,
      LSB_BITS   => LSB_BITS,
      N_ITER     => N_ITER,
      RM_GAIN    => RM_GAIN
              )
   port map(
      clk     => clk,
      rst     => rst,
      en      => en,
      valid_i => valid_i,
      x_i     => x_i,
      y_i     => y_i,
      a_i     => a_i,
      valid_o => valid_o,
      x_o     => x_o,
      y_o     => y_o
           );


   en_generator : process
      variable seed1 : positive := 7;
      variable seed2 : positive := 11;
      variable r     : real;
   begin
      wait until rising_edge( clk );
      uniform( seed1, seed2, r );
      if en_rand_on and r < 0.3 then
         en_rand <= '0';
      else
         en_rand <= '1';
      end if;
   end process en_generator;


   checker : process
      file expected       : text;
      variable l          : line;
      variable x_e        : std_logic_vector( x_o'range );
      variable y_e        : std_logic_vector( y_o'range );
      variable count      : natural   := 0;
      variable frozen     : boolean   := false;
      variable valid_last : std_logic := '0';
      variable restart_seen : natural := 0;
   begin
      file_open( expected, output_path( runner_cfg ) & "expected.txt", read_mode );
      wait until started;
      loop
         wait until rising_edge( clk );
         if restart /= restart_seen then
            file_close( expected );
            file_open( expected, output_path( runner_cfg ) & "expected.txt", read_mode );
            count        := 0;
            samples_seen <= 0;
            restart_seen := restart;
         end if;
         check_not_unknown( valid_o, "valid_o" );
         if frozen then
            check_equal( valid_o, valid_last, "valid_o changed across a frozen edge" );
         end if;
         frozen     := en = '0' and rst = '0';
         valid_last := valid_o;
         if valid_o = '1' and en = '1' then
            check( not endfile( expected ), "more samples than expected" );
            readline( expected, l );
            read( l, x_e );
            read( l, y_e );
            check_equal( x_o, x_e, "x_o of sample " & to_string( count ) );
            check_equal( y_o, y_e, "y_o of sample " & to_string( count ) );
            count        := count + 1;
            samples_seen <= count;
         end if;
      end loop;
   end process checker;


   main : process
      file stimulus      : text;
      variable seed1     : positive := 3;
      variable seed2     : positive := 5;
      variable r         : real;
      variable gap       : natural;
      variable edges     : natural;
      variable sent      : natural;

      procedure drive_idle is
      begin
         valid_i <= '0';
         x_i     <= ( others => 'X' );
         y_i     <= ( others => 'X' );
         a_i     <= ( others => 'X' );
      end procedure drive_idle;

      procedure drive_next is
         variable l : line;
         variable x : std_logic_vector( x_i'range );
         variable y : std_logic_vector( y_i'range );
         variable a : std_logic_vector( a_i'range );
      begin
         readline( stimulus, l );
         read( l, x );
         read( l, y );
         read( l, a );
         x_i     <= x;
         y_i     <= y;
         a_i     <= a;
         valid_i <= '1';
      end procedure drive_next;

      -- Returns after the edge which took the driven sample.
      procedure wait_taken is
      begin
         loop
            wait until rising_edge( clk );
            exit when en = '1';
         end loop;
      end procedure wait_taken;

      procedure stream( n : natural ) is
      begin
         for k in 1 to n loop
            drive_next;
            wait_taken;
         end loop;
         drive_idle;
      end procedure stream;

      procedure check_valid_stays_low is
      begin
         for k in 1 to EXPECTED_LATENCY+2 loop
            wait until rising_edge( clk );
            check_equal( valid_o, '0', "valid_o after the last sample" );
         end loop;
      end procedure check_valid_stays_low;

      procedure wait_all_arrived( n : natural ) is
      begin
         while samples_seen < n loop
            wait until rising_edge( clk );
         end loop;
         en_rand_on <= false;
         en_main    <= '1';
         check_valid_stays_low;
         check_equal( samples_seen, n, "number of samples" );
         info( "compared " & to_string( samples_seen ) & " samples" );
      end procedure wait_all_arrived;

      -- Streams, resets for one clock with en = reset_en, and expects that the
      -- samples reaching the output by the reset edge are the only ones.
      procedure reset_test( reset_en : std_logic ) is
         variable reset_edge_counts : natural := 0;
      begin
         if reset_en = '1' then
            reset_edge_counts := 1;
         end if;
         stream( N_RESET );
         rst     <= '1';
         en_main <= reset_en;
         wait until rising_edge( clk );
         rst     <= '0';
         en_main <= '1';
         check_valid_stays_low;
         check_equal( samples_seen, maximum( 0, N_RESET + reset_edge_counts - EXPECTED_LATENCY ),
                      "number of samples before the reset" );
         info( "compared " & to_string( samples_seen ) & " samples" );
      end procedure reset_test;

      -- Resets while a sample is offered with valid_i = '1', which must be
      -- dropped, then streams the whole stimulus file again from its start.
      procedure resume_test is
      begin
         stream( N_RESET );
         drive_next;
         rst <= '1';
         wait until rising_edge( clk );
         rst <= '0';
         drive_idle;
         check_valid_stays_low;
         restart <= restart + 1;
         file_close( stimulus );
         file_open( stimulus, output_path( runner_cfg ) & "stimulus.txt", read_mode );
         wait until rising_edge( clk );
         en_rand_on <= true;
         stream( N_SAMPLES );
         wait_all_arrived( N_SAMPLES );
      end procedure resume_test;

   begin
      test_runner_setup( runner, runner_cfg );
      file_open( stimulus, output_path( runner_cfg ) & "stimulus.txt", read_mode );

      wait until rising_edge( clk );
      wait until rising_edge( clk );
      wait until rising_edge( clk );
      rst     <= '0';
      started <= true;
      wait until rising_edge( clk );

      while test_suite loop
         if run( "test_consecutive" ) then
            stream( N_SAMPLES );
            wait_all_arrived( N_SAMPLES );

         elsif run( "test_latency" ) then
            check_equal( cordic_pipeline_latency( N_ITER, RM_GAIN ), EXPECTED_LATENCY,
                         "cordic_pipeline_latency" );
            for k in 1 to 3 loop
               wait until rising_edge( clk );
               check_equal( valid_o, '0', "valid_o while idle" );
            end loop;
            stream( 1 );
            edges := 0;
            loop
               wait until rising_edge( clk );
               edges := edges + 1;
               exit when valid_o /= '0' or edges > EXPECTED_LATENCY;
            end loop;
            check_equal( valid_o, '1', "valid_o at the end of the latency" );
            check_equal( edges, EXPECTED_LATENCY, "measured latency" );
            wait_all_arrived( 1 );

         elsif run( "test_gaps" ) then
            for k in 1 to N_SAMPLES loop
               drive_next;
               wait_taken;
               uniform( seed1, seed2, r );
               gap := integer( floor( r * 4.0 ) );
               if gap > 0 then
                  drive_idle;
                  for g in 1 to gap loop
                     wait until rising_edge( clk );
                  end loop;
               end if;
            end loop;
            drive_idle;
            wait_all_arrived( N_SAMPLES );

         elsif run( "test_en_toggle" ) then
            en_rand_on <= true;
            stream( N_SAMPLES );
            wait_all_arrived( N_SAMPLES );

         elsif run( "test_reset_mid_stream" ) then
            reset_test( '1' );

         elsif run( "test_reset_while_frozen" ) then
            reset_test( '0' );

         elsif run( "test_reset_resume" ) then
            resume_test;

         end if;
      end loop;

      test_runner_cleanup( runner );
   end process main;

   test_runner_watchdog( runner, 1 ms );

end architecture BEHAVIORAL;
