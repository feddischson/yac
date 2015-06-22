library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
Library UNISIM;
use UNISIM.vcomponents.all;

entity test_sys_top is
    Port ( CLK_50M   : in  STD_LOGIC;
           BTN_NORTH : in  STD_LOGIC;
           BTN_EAST  : in  STD_LOGIC;
           BTN_SOUTH : in  STD_LOGIC;
           BTN_WEST  : in  STD_LOGIC;
           SW        : in  STD_LOGIC_VECTOR( 4-1 downto 0 );
           LED       : out STD_LOGIC_VECTOR( 8-1 downto 0 );
           RS232_DCE_RXD  : in STD_LOGIC;
           RS232_DCE_TXD  : out STD_LOGIC
           );
end test_sys_top;

architecture Behavioral of test_sys_top is

constant VPI_TAP : boolean := false;


component dbg_comm_vpi is
   Port( 
      SYS_CLK    : out STD_LOGIC;
      SYS_RST    : out STD_LOGIC;
      P_TMS      : out STD_LOGIC; 
      P_TCK      : out STD_LOGIC; 
      P_TRST     : out STD_LOGIC; 
      P_TDI      : out STD_LOGIC; 
      P_TDO      : in  STD_LOGIC
      );
end component;
signal P_TMS      : STD_LOGIC; 
signal P_TCK      : STD_LOGIC; 
signal P_TRST     : STD_LOGIC; 
signal P_TDI      : STD_LOGIC; 
signal P_TDO      : STD_LOGIC;



component yac_test_soc is 
port( 
clk_i :  in  std_logic ;
rst_i :  in  std_logic ;
tck_i :  in  std_logic ;
tdi_i :  in  std_logic ;
tdo_o :  out  std_logic ;
debug_rst_i :  in  std_logic ;
shift_dr_i :  in  std_logic ;
pause_dr_i :  in  std_logic ;
update_dr_i :  in  std_logic ;
capture_dr_i :  in  std_logic ;
debug_select_i :  in  std_logic;
stx_pad_o :  out  std_logic ;
srx_pad_i :  in  std_logic ;
rts_pad_o :  out  std_logic ;
cts_pad_i :  in  std_logic ;
dtr_pad_o :  out  std_logic ;
dsr_pad_i :  in  std_logic ;
ri_pad_i :  in  std_logic ;
dcd_pad_i :  in  std_logic 
 );
end component yac_test_soc;

component tap_top is
 port (

   -- JTAG pads
   signal tms_pad_i                 :  in std_logic; 
   signal tck_pad_i                 :  in std_logic; 
   signal trstn_pad_i               :  in std_logic; 
   signal tdi_pad_i                 :  in std_logic; 
   signal tdo_pad_o                 :  out std_logic; 
   signal tdo_padoe_o               :  out std_logic;

   -- TAP states
   signal test_logic_reset_o        :  out std_logic;
   signal run_test_idle_o           :  out std_logic;
   signal shift_dr_o                :  out std_logic;
   signal pause_dr_o                :  out std_logic; 
   signal update_dr_o               :  out std_logic;
   signal capture_dr_o              :  out std_logic;

   -- Select signals for boundary scan or mbist
   signal extest_select_o           : out std_logic; 
   signal sample_preload_select_o   : out std_logic;
   signal mbist_select_o            : out std_logic;
   signal debug_select_o            : out std_logic;

   -- TDO signal that is connected to TDI of sub-modules.
   signal tdi_o                     : out std_logic; 

   -- TDI signals from sub-modules
   signal debug_tdo_i               : in std_logic;     -- from debug module
   signal bs_chain_tdo_i            : in std_logic;  -- from Boundary Scan Chain
   signal mbist_tdo_i               : in std_logic      -- from Mbist Chain
);
end component;

component xilinx_internal_jtag is
port(
   signal tck_o                  : out std_logic;
   signal debug_tdo_i            : in  std_logic;
   signal tdi_o                  : out std_logic;
   signal test_logic_reset_o     : out std_logic;
   signal run_test_idle_o        : out std_logic;
   signal shift_dr_o             : out std_logic;
   signal capture_dr_o           : out std_logic;
   signal pause_dr_o             : out std_logic;
   signal update_dr_o            : out std_logic;
   signal debug_select_o         : out std_logic
);
end component;



signal clk_i :  std_logic ;
signal rst_i :  std_logic ;
signal n_rst_i :  std_logic ;
signal tck_i :  std_logic ;
signal tdi_i :  std_logic ;
signal tdo_o :  std_logic ;
signal shift_dr_i :  std_logic ;
signal pause_dr_i :  std_logic ;
signal update_dr_i :  std_logic ;
signal capture_dr_i :  std_logic ;
signal debug_select_i :  std_logic ;
signal debug_rst_i  :  std_logic ;
signal stx_pad_o :    std_logic ;
signal srx_pad_i :   std_logic ;
signal rts_pad_o :    std_logic ;
signal cts_pad_i :   std_logic ;
signal dtr_pad_o :    std_logic ;
signal dsr_pad_i :   std_logic ;
signal ri_pad_i :  std_logic ;
signal dcd_pad_i :   std_logic ;
signal gnd : std_logic;


signal VPI_CLK       : std_logic;

begin

gnd <= '0';
srx_pad_i <= RS232_DCE_RXD;
RS232_DCE_TXD <= stx_pad_o;
cts_pad_i <= '0';
dsr_pad_i <= '0';
dcd_pad_i <= '0';
ri_pad_i  <= '0';


-- led_p : process( clk_i )
-- begin
--   if clk_i'event and clk_i='1' then
--     LED <= SW & BTN_NORTH & BTN_EAST & BTN_SOUTH & BTN_WEST;
--   end if;
-- end process;

--LED <= SW & BTN_NORTH & BTN_EAST & BTN_SOUTH & BTN_WEST;
LED <= "10101100";





--
-- Simulation Part:
-- The VPI and Standard JTAG TAP is used
--
VPI_SEL : if  VPI_TAP = true generate


-- clk_i    <= CLK_50M;
rst_i    <= BTN_SOUTH;
n_rst_i  <= not rst_i;

--
-- Debug VPI
--
vpi : dbg_comm_vpi 
   port map(
     SYS_CLK  => clk_i,
     P_TMS    => P_TMS  ,
     P_TCK    => P_TCK  ,
     P_TRST   => P_TRST ,
     P_TDI    => P_TDI  ,
     P_TDO    => P_TDO ); 

--
-- Standard JTAG TAP
--
tap_inst : tap_top
 port map(

   -- JTAG pads: this 6 signals simulates
   -- the physical connection to the tap
   tms_pad_i                 =>  P_TMS,
   tck_pad_i                 =>  P_TCK,
   trstn_pad_i               =>  n_rst_i,
   tdi_pad_i                 =>  P_TDI,
   tdo_pad_o                 =>  P_TDO,
   tdo_padoe_o               =>  open,

   -- TAP states
   test_logic_reset_o        =>  debug_rst_i,
   run_test_idle_o           =>  open,
   shift_dr_o                =>  shift_dr_i,
   pause_dr_o                =>  pause_dr_i,
   update_dr_o               =>  update_dr_i,
   capture_dr_o              =>  capture_dr_i,

   -- Select signals for boundary scan or mbist
   extest_select_o           =>  open,
   sample_preload_select_o   =>  open,
   mbist_select_o            =>  open,
   debug_select_o            =>  debug_select_i,

   -- TDO signal that is connected to TDI of sub-modules.
   tdi_o                     =>  tdi_i,

   -- TDI signals from sub-modules
   debug_tdo_i               =>  tdo_o,
   bs_chain_tdo_i            =>  gnd,
   mbist_tdo_i               =>  gnd
);

tck_i <= P_TCK;



end generate VPI_SEL;

--
-- Synthesis Part:
-- The FPGA internal Xilinx TAP is used
--
NO_VPI_SEL : if  VPI_TAP  = false generate

   clk_i    <= CLK_50M;
   rst_i    <= BTN_SOUTH;
   n_rst_i  <= not rst_i;

   tap_inst_xilinx : xilinx_internal_jtag 
   port map(
      tck_o                => tck_i,
      debug_tdo_i          => tdo_o,
      tdi_o                => tdi_i,
      test_logic_reset_o   => debug_rst_i,
      run_test_idle_o      => open,
      shift_dr_o           => shift_dr_i,
      capture_dr_o         => capture_dr_i,
      pause_dr_o           => pause_dr_i,
      update_dr_o          => update_dr_i,
      debug_select_o       => debug_select_i
   );

end generate NO_VPI_SEL;


--
-- The SOC instance
--
top : yac_test_soc
port map(
clk_i          => clk_i         ,
rst_i          => rst_i         ,
tck_i          => tck_i         ,
tdi_i          => tdi_i         ,
tdo_o          => tdo_o         ,
debug_rst_i    => debug_rst_i     ,
shift_dr_i     => shift_dr_i    ,
pause_dr_i     => pause_dr_i    ,
update_dr_i    => update_dr_i   ,
capture_dr_i   => capture_dr_i  ,
debug_select_i => debug_select_i ,
stx_pad_o   => stx_pad_o  ,
srx_pad_i   => srx_pad_i ,
rts_pad_o   => rts_pad_o ,
cts_pad_i   => cts_pad_i ,
dtr_pad_o   => dtr_pad_o ,
dsr_pad_i   => dsr_pad_i ,
ri_pad_i    => ri_pad_i  ,
dcd_pad_i   => dcd_pad_i
);


end Behavioral;

