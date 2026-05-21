-- ML605 board top for MMN_Core_Chip.
--
-- Clocking:
--   ML605 SYSCLK_P/N = 200 MHz differential oscillator.
--   PLL generates 48 MHz for the MMN core.
--   clk_enable is asserted once every 2400 core clocks:
--     48 MHz / 2400 = 20 kHz -> dt = 50 us.
--
-- Stimulus:
--   Generates a 10 ms pulse every 200 ms internally:
--     200 samples high, period 4000 samples at dt = 50 us.
--
-- Outputs:
--   PE spikes are stretched for visibility on ML605 user LEDs.

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;

LIBRARY UNISIM;
USE UNISIM.vcomponents.ALL;

ENTITY MMN_Core_Chip_ML605_Top IS
  PORT (
    sysclk_p   : IN  std_logic;
    sysclk_n   : IN  std_logic;
    reset      : IN  std_logic;
    pe_led     : OUT std_logic_vector(9 DOWNTO 0);
    ce_20k     : OUT std_logic;
    pll_locked : OUT std_logic;
    stim_led   : OUT std_logic
  );
END MMN_Core_Chip_ML605_Top;

ARCHITECTURE rtl OF MMN_Core_Chip_ML605_Top IS

  COMPONENT MMN_Core_Chip IS
    PORT (
      clk        : IN  std_logic;
      reset      : IN  std_logic;
      clk_enable : IN  std_logic;
      In1        : IN  std_logic;
      ce_out     : OUT std_logic;
      Spike      : OUT std_logic_vector(9 DOWNTO 0);
      debug_mem_spike  : OUT std_logic;
      debug_thal_spike : OUT std_logic_vector(9 DOWNTO 0);
      debug_p_spike    : OUT std_logic_vector(9 DOWNTO 0);
      debug_i_spike    : OUT std_logic_vector(9 DOWNTO 0);
      debug_pe_spike   : OUT std_logic_vector(9 DOWNTO 0);
      debug_path_flags : OUT std_logic_vector(9 DOWNTO 0)
    );
  END COMPONENT;

  TYPE stretch_array_t IS ARRAY (0 TO 9) OF unsigned(21 DOWNTO 0);

  CONSTANT C_LED_SELF_TEST  : boolean := false;

  FUNCTION any_high(v : std_logic_vector) RETURN std_logic IS
  BEGIN
    FOR i IN v'RANGE LOOP
      IF v(i) = '1' THEN
        RETURN '1';
      END IF;
    END LOOP;
    RETURN '0';
  END FUNCTION;

  SIGNAL sysclk_ibuf       : std_logic;
  SIGNAL pll_clkfb         : std_logic;
  SIGNAL pll_clk48_unbuf   : std_logic;
  SIGNAL clk48             : std_logic;
  SIGNAL pll_locked_i      : std_logic;
  SIGNAL core_reset        : std_logic;

  SIGNAL ce_count          : unsigned(11 DOWNTO 0) := (OTHERS => '0');
  SIGNAL ce_tick           : std_logic := '0';
  SIGNAL sample_count      : unsigned(11 DOWNTO 0) := (OTHERS => '0');
  SIGNAL stim_core         : std_logic := '0';
  SIGNAL pe_spike_raw      : std_logic_vector(9 DOWNTO 0);
  SIGNAL debug_mem_spike   : std_logic;
  SIGNAL debug_thal_spike  : std_logic_vector(9 DOWNTO 0);
  SIGNAL debug_p_spike     : std_logic_vector(9 DOWNTO 0);
  SIGNAL debug_i_spike     : std_logic_vector(9 DOWNTO 0);
  SIGNAL debug_pe_spike    : std_logic_vector(9 DOWNTO 0);
  SIGNAL debug_path_flags  : std_logic_vector(9 DOWNTO 0);
  SIGNAL debug_led_src     : std_logic_vector(9 DOWNTO 0);
  SIGNAL pe_stretch_count  : stretch_array_t := (OTHERS => (OTHERS => '0'));
  SIGNAL pe_led_i          : std_logic_vector(9 DOWNTO 0) := (OTHERS => '0');
  SIGNAL led_test_count    : unsigned(23 DOWNTO 0) := (OTHERS => '0');
  SIGNAL led_test_pos      : integer RANGE 0 TO 19 := 0;
  SIGNAL led_test_i        : std_logic_vector(9 DOWNTO 0) := (OTHERS => '0');

BEGIN

  u_sysclk_ibuf : IBUFGDS
    GENERIC MAP (
      DIFF_TERM    => TRUE,
      IBUF_LOW_PWR => FALSE,
      IOSTANDARD   => "LVDS_25"
    )
    PORT MAP (
      I  => sysclk_p,
      IB => sysclk_n,
      O  => sysclk_ibuf
    );

  -- 200 MHz -> 48 MHz:
  -- VCO = 200 / 5 * 24 = 960 MHz, CLKOUT0 = 960 / 20 = 48 MHz.
  u_pll_48m : PLL_BASE
    GENERIC MAP (
      BANDWIDTH          => "OPTIMIZED",
      CLKFBOUT_MULT      => 24,
      CLKFBOUT_PHASE     => 0.0,
      CLKIN_PERIOD       => 5.0,
      CLKOUT0_DIVIDE     => 20,
      CLKOUT0_DUTY_CYCLE => 0.5,
      CLKOUT0_PHASE      => 0.0,
      CLKOUT1_DIVIDE     => 1,
      CLKOUT1_DUTY_CYCLE => 0.5,
      CLKOUT1_PHASE      => 0.0,
      CLKOUT2_DIVIDE     => 1,
      CLKOUT2_DUTY_CYCLE => 0.5,
      CLKOUT2_PHASE      => 0.0,
      CLKOUT3_DIVIDE     => 1,
      CLKOUT3_DUTY_CYCLE => 0.5,
      CLKOUT3_PHASE      => 0.0,
      CLKOUT4_DIVIDE     => 1,
      CLKOUT4_DUTY_CYCLE => 0.5,
      CLKOUT4_PHASE      => 0.0,
      CLKOUT5_DIVIDE     => 1,
      CLKOUT5_DUTY_CYCLE => 0.5,
      CLKOUT5_PHASE      => 0.0,
      COMPENSATION       => "SYSTEM_SYNCHRONOUS",
      DIVCLK_DIVIDE      => 5,
      REF_JITTER         => 0.010,
      RESET_ON_LOSS_OF_LOCK => FALSE
    )
    PORT MAP (
      CLKFBOUT => pll_clkfb,
      CLKOUT0  => pll_clk48_unbuf,
      CLKOUT1  => OPEN,
      CLKOUT2  => OPEN,
      CLKOUT3  => OPEN,
      CLKOUT4  => OPEN,
      CLKOUT5  => OPEN,
      LOCKED   => pll_locked_i,
      CLKFBIN  => pll_clkfb,
      CLKIN    => sysclk_ibuf,
      RST      => reset
    );

  u_clk48_bufg : BUFG
    PORT MAP (
      I => pll_clk48_unbuf,
      O => clk48
    );

  core_reset <= reset OR (NOT pll_locked_i);

  ce_and_stim_gen : PROCESS (clk48, core_reset)
  BEGIN
    IF core_reset = '1' THEN
      ce_count <= (OTHERS => '0');
      ce_tick <= '0';
      sample_count <= (OTHERS => '0');
      stim_core <= '0';
    ELSIF clk48'EVENT AND clk48 = '1' THEN
      IF ce_count = to_unsigned(2399, ce_count'LENGTH) THEN
        ce_count <= (OTHERS => '0');
        ce_tick <= '1';

        IF sample_count = to_unsigned(3999, sample_count'LENGTH) THEN
          sample_count <= (OTHERS => '0');
        ELSE
          sample_count <= sample_count + 1;
        END IF;

        IF sample_count < to_unsigned(200, sample_count'LENGTH) THEN
          stim_core <= '1';
        ELSE
          stim_core <= '0';
        END IF;
      ELSE
        ce_count <= ce_count + 1;
        ce_tick <= '0';
      END IF;
    END IF;
  END PROCESS;

  u_core : MMN_Core_Chip
    PORT MAP (
      clk        => clk48,
      reset      => core_reset,
      clk_enable => ce_tick,
      In1        => stim_core,
      ce_out     => ce_20k,
      Spike      => pe_spike_raw,
      debug_mem_spike  => debug_mem_spike,
      debug_thal_spike => debug_thal_spike,
      debug_p_spike    => debug_p_spike,
      debug_i_spike    => debug_i_spike,
      debug_pe_spike   => debug_pe_spike,
      debug_path_flags => debug_path_flags
    );

  -- Path debug mapping:
  -- LED0 thal spike, LED1 raw PE AMPA, LED2 delayed PE AMPA,
  -- LED3 PE AMPA synapse output, LED4 PE spike, LED5 P AMPA,
  -- LED6 P spike, LED7 STDP I_syn, LED8 Mem trace, LED9 Mem spike.
  debug_led_src <= debug_path_flags;

  led_stretch : PROCESS (clk48, core_reset)
  BEGIN
    IF core_reset = '1' THEN
      pe_stretch_count <= (OTHERS => (OTHERS => '0'));
      pe_led_i <= (OTHERS => '0');
    ELSIF clk48'EVENT AND clk48 = '1' THEN
      FOR k IN 0 TO 9 LOOP
        IF debug_led_src(k) = '1' THEN
          pe_stretch_count(k) <= (OTHERS => '1');
        ELSIF pe_stretch_count(k) /= to_unsigned(0, pe_stretch_count(k)'LENGTH) THEN
          pe_stretch_count(k) <= pe_stretch_count(k) - 1;
        END IF;

        IF pe_stretch_count(k) /= to_unsigned(0, pe_stretch_count(k)'LENGTH) THEN
          pe_led_i(k) <= '1';
        ELSE
          pe_led_i(k) <= '0';
        END IF;
      END LOOP;
    END IF;
  END PROCESS;

  led_self_test : PROCESS (clk48, core_reset)
  BEGIN
    IF core_reset = '1' THEN
      led_test_count <= (OTHERS => '0');
      led_test_pos <= 0;
      led_test_i <= (OTHERS => '0');
    ELSIF clk48'EVENT AND clk48 = '1' THEN
      IF led_test_count = to_unsigned(11999999, led_test_count'LENGTH) THEN
        led_test_count <= (OTHERS => '0');
        IF led_test_pos = 19 THEN
          led_test_pos <= 0;
        ELSE
          led_test_pos <= led_test_pos + 1;
        END IF;
      ELSE
        led_test_count <= led_test_count + 1;
      END IF;

      IF led_test_pos < 10 THEN
        led_test_i <= (OTHERS => '0');
        led_test_i(led_test_pos) <= '1';
      ELSE
        led_test_i <= (OTHERS => '1');
        led_test_i(led_test_pos - 10) <= '0';
      END IF;
    END IF;
  END PROCESS;

  pe_led <= led_test_i WHEN C_LED_SELF_TEST ELSE pe_led_i;
  pll_locked <= pll_locked_i;
  stim_led <= stim_core;

END rtl;
