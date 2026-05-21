-- ML605 board top for candidate1 MMN_Core_Chip.
--
-- This is the same board wrapper strategy as MMN_Core_Chip_ML605_Top.vhd,
-- but it matches the candidate1 HDL Coder entity, which has no debug ports.
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
--   Core Spike[9:0] is stretched for visibility on ML605 user LEDs.
--   UART sends a low-rate ASCII telemetry line for PC-side debug.

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;
USE work.MMN_Core_Chip_pkg.ALL;

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
    stim_led   : OUT std_logic;
    uart_tx    : OUT std_logic
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
      Weight_dbg : OUT vector_of_std_logic_vector16(0 TO 99)
    );
  END COMPONENT;

  COMPONENT uart_tx_core IS
    GENERIC (
      G_CLKS_PER_BIT : positive := 417
    );
    PORT (
      clk      : IN  std_logic;
      reset    : IN  std_logic;
      tx_valid : IN  std_logic;
      tx_data  : IN  std_logic_vector(7 DOWNTO 0);
      tx_busy  : OUT std_logic;
      txd      : OUT std_logic
    );
  END COMPONENT;

  SUBTYPE stretch_count_t IS unsigned(21 DOWNTO 0);
  SUBTYPE pe_count_t IS unsigned(11 DOWNTO 0);
  TYPE stretch_array_t IS ARRAY (0 TO 9) OF stretch_count_t;
  TYPE pe_count_array_t IS ARRAY (0 TO 9) OF pe_count_t;

  CONSTANT C_LED_SELF_TEST   : boolean := false;
  CONSTANT C_LED_LATCH_MODE  : boolean := false;
  CONSTANT C_UART_ENABLE     : boolean := true;
  -- 4000 Simulink steps * 50 us = 200 ms per full 100-row UART frame.
  CONSTANT C_UART_FRAME_LAST : unsigned(11 DOWNTO 0) := to_unsigned(3999, 12);

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
  SIGNAL pe_stretch_count  : stretch_array_t := (OTHERS => (OTHERS => '0'));
  SIGNAL pe_led_i          : std_logic_vector(9 DOWNTO 0) := (OTHERS => '0');
  SIGNAL led_test_count    : unsigned(23 DOWNTO 0) := (OTHERS => '0');
  SIGNAL led_test_pos      : integer RANGE 0 TO 19 := 0;
  SIGNAL led_test_i        : std_logic_vector(9 DOWNTO 0) := (OTHERS => '0');
  SIGNAL uart_frame_sample : unsigned(11 DOWNTO 0) := (OTHERS => '0');
  SIGNAL uart_frame_count  : unsigned(7 DOWNTO 0) := (OTHERS => '0');
  SIGNAL pe_window_mask    : std_logic_vector(9 DOWNTO 0) := (OTHERS => '0');
  SIGNAL pe_snapshot       : std_logic_vector(9 DOWNTO 0) := (OTHERS => '0');
  SIGNAL stim_window_seen  : std_logic := '0';
  SIGNAL stim_snapshot     : std_logic := '0';
  SIGNAL weight_dbg_raw    : vector_of_std_logic_vector16(0 TO 99) := (OTHERS => (OTHERS => '0'));
  SIGNAL weight_dbg_snapshot : vector_of_std_logic_vector16(0 TO 99) := (OTHERS => (OTHERS => '0'));
  SIGNAL tele_pending      : std_logic := '0';
  SIGNAL tele_sending      : std_logic := '0';
  SIGNAL pe_spike_counts   : pe_count_array_t := (OTHERS => (OTHERS => '0'));
  SIGNAL pe_count_snapshot : pe_count_array_t := (OTHERS => (OTHERS => '0'));
  SIGNAL pe_total_count    : unsigned(15 DOWNTO 0) := (OTHERS => '0');
  SIGNAL pe_total_snapshot : unsigned(15 DOWNTO 0) := (OTHERS => '0');
  SIGNAL tele_byte_index   : integer RANGE 0 TO 561 := 0;
  SIGNAL uart_tx_valid     : std_logic := '0';
  SIGNAL uart_tx_data      : std_logic_vector(7 DOWNTO 0) := (OTHERS => '0');
  SIGNAL uart_tx_busy      : std_logic := '0';
  SIGNAL uart_tx_i         : std_logic := '1';

  FUNCTION hex_char(nibble : unsigned(3 DOWNTO 0)) RETURN std_logic_vector IS
    VARIABLE result : unsigned(7 DOWNTO 0);
  BEGIN
    IF nibble < to_unsigned(10, 4) THEN
      result := to_unsigned(48, 8) + resize(nibble, 8);
    ELSE
      result := to_unsigned(55, 8) + resize(nibble, 8);
    END IF;
    RETURN std_logic_vector(result);
  END FUNCTION;

  FUNCTION hex_word_nibble(
    word         : std_logic_vector(15 DOWNTO 0);
    nibble_index : integer
  ) RETURN std_logic_vector IS
  BEGIN
    CASE nibble_index IS
      WHEN 0 => RETURN hex_char(unsigned(word(15 DOWNTO 12)));
      WHEN 1 => RETURN hex_char(unsigned(word(11 DOWNTO 8)));
      WHEN 2 => RETURN hex_char(unsigned(word(7 DOWNTO 4)));
      WHEN OTHERS => RETURN hex_char(unsigned(word(3 DOWNTO 0)));
    END CASE;
  END FUNCTION;

  FUNCTION hex_count12_nibble(
    count        : unsigned(11 DOWNTO 0);
    nibble_index : integer
  ) RETURN std_logic_vector IS
  BEGIN
    CASE nibble_index IS
      WHEN 0 => RETURN hex_char(count(11 DOWNTO 8));
      WHEN 1 => RETURN hex_char(count(7 DOWNTO 4));
      WHEN OTHERS => RETURN hex_char(count(3 DOWNTO 0));
    END CASE;
  END FUNCTION;

  FUNCTION hex_count16_nibble(
    count        : unsigned(15 DOWNTO 0);
    nibble_index : integer
  ) RETURN std_logic_vector IS
  BEGIN
    CASE nibble_index IS
      WHEN 0 => RETURN hex_char(count(15 DOWNTO 12));
      WHEN 1 => RETURN hex_char(count(11 DOWNTO 8));
      WHEN 2 => RETURN hex_char(count(7 DOWNTO 4));
      WHEN OTHERS => RETURN hex_char(count(3 DOWNTO 0));
    END CASE;
  END FUNCTION;

  FUNCTION tele_byte(
    byte_index : integer;
    frame      : unsigned(7 DOWNTO 0);
    stim_seen  : std_logic;
    pe_mask    : std_logic_vector(9 DOWNTO 0);
    w_dbg      : vector_of_std_logic_vector16(0 TO 99);
    pe_counts  : pe_count_array_t;
    pe_total   : unsigned(15 DOWNTO 0)
  ) RETURN std_logic_vector IS
    VARIABLE w_rel         : integer;
    VARIABLE w_row_index   : integer;
    VARIABLE c_rel         : integer;
    VARIABLE c_count_index : integer;
    VARIABLE hex_idx       : integer;
  BEGIN
    CASE byte_index IS
      WHEN 0  => RETURN x"4D"; -- M
      WHEN 1  => RETURN x"20"; -- space
      WHEN 2  => RETURN hex_char(frame(7 DOWNTO 4));
      WHEN 3  => RETURN hex_char(frame(3 DOWNTO 0));
      WHEN 4  => RETURN x"20"; -- space
      WHEN 5  => RETURN x"53"; -- S
      WHEN 6  =>
        IF stim_seen = '1' THEN
          RETURN x"31"; -- 1
        ELSE
          RETURN x"30"; -- 0
        END IF;
      WHEN 7  => RETURN x"20"; -- space
      WHEN 8  => RETURN x"50"; -- P
      WHEN 9  => RETURN hex_char(to_unsigned(0, 2) & unsigned(pe_mask(9 DOWNTO 8)));
      WHEN 10 => RETURN hex_char(unsigned(pe_mask(7 DOWNTO 4)));
      WHEN 11 => RETURN hex_char(unsigned(pe_mask(3 DOWNTO 0)));
      WHEN 12 => RETURN x"20"; -- space
      WHEN 13 => RETURN x"57"; -- W
      WHEN OTHERS =>
        IF byte_index >= 14 AND byte_index <= 512 THEN
          w_rel := byte_index - 14;

          IF w_rel < 4 THEN
            w_row_index := 0;
            hex_idx := w_rel;
            RETURN hex_word_nibble(w_dbg(w_row_index), hex_idx);
          ELSE
            w_rel := w_rel - 4;
            w_row_index := 1 + (w_rel / 5);
            hex_idx := w_rel MOD 5;

            IF w_row_index <= 99 THEN
              IF hex_idx = 0 THEN
                RETURN x"20"; -- space between row-sum values
              ELSE
                RETURN hex_word_nibble(w_dbg(w_row_index), hex_idx - 1);
              END IF;
            ELSIF byte_index = 513 THEN
              RETURN x"0D"; -- CR
            ELSE
              RETURN x"0A"; -- LF
            END IF;
          END IF;
        ELSIF byte_index = 513 THEN
          RETURN x"20"; -- space
        ELSIF byte_index = 514 THEN
          RETURN x"43"; -- C, PE spike counts per neuron
        ELSIF byte_index >= 515 AND byte_index <= 553 THEN
          c_rel := byte_index - 515;

          IF c_rel < 3 THEN
            c_count_index := 0;
            hex_idx := c_rel;
            RETURN hex_count12_nibble(pe_counts(c_count_index), hex_idx);
          ELSE
            c_rel := c_rel - 3;
            c_count_index := 1 + (c_rel / 4);
            hex_idx := c_rel MOD 4;

            IF c_count_index <= 9 THEN
              IF hex_idx = 0 THEN
                RETURN x"20"; -- space between PE count values
              ELSE
                RETURN hex_count12_nibble(pe_counts(c_count_index), hex_idx - 1);
              END IF;
            ELSE
              RETURN x"20";
            END IF;
          END IF;
        ELSIF byte_index = 554 THEN
          RETURN x"20"; -- space
        ELSIF byte_index = 555 THEN
          RETURN x"45"; -- E, activity-cost proxy = total PE spikes
        ELSIF byte_index >= 556 AND byte_index <= 559 THEN
          RETURN hex_count16_nibble(pe_total, byte_index - 556);
        ELSIF byte_index = 560 THEN
          RETURN x"0D"; -- CR
        ELSE
          RETURN x"0A"; -- LF
        END IF;
    END CASE;
  END FUNCTION;

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
      Weight_dbg => weight_dbg_raw
    );

  led_stretch : PROCESS (clk48, core_reset)
  BEGIN
    IF core_reset = '1' THEN
      pe_stretch_count <= (OTHERS => (OTHERS => '0'));
      pe_led_i <= (OTHERS => '0');
    ELSIF clk48'EVENT AND clk48 = '1' THEN
      FOR k IN 0 TO 9 LOOP
        IF pe_spike_raw(k) = '1' THEN
          pe_stretch_count(k) <= (OTHERS => '1');
          pe_led_i(k) <= '1';
        ELSIF (NOT C_LED_LATCH_MODE) AND pe_stretch_count(k) /= to_unsigned(0, pe_stretch_count(k)'LENGTH) THEN
          pe_stretch_count(k) <= pe_stretch_count(k) - 1;
        END IF;

        IF NOT C_LED_LATCH_MODE THEN
          IF pe_stretch_count(k) /= to_unsigned(0, pe_stretch_count(k)'LENGTH) THEN
            pe_led_i(k) <= '1';
          ELSE
            pe_led_i(k) <= '0';
          END IF;
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

  uart_window_capture : PROCESS (clk48, core_reset)
    VARIABLE next_counts : pe_count_array_t;
    VARIABLE next_total  : unsigned(15 DOWNTO 0);
  BEGIN
    IF core_reset = '1' THEN
      uart_frame_sample <= (OTHERS => '0');
      uart_frame_count <= (OTHERS => '0');
      pe_window_mask <= (OTHERS => '0');
      pe_snapshot <= (OTHERS => '0');
      pe_spike_counts <= (OTHERS => (OTHERS => '0'));
      pe_count_snapshot <= (OTHERS => (OTHERS => '0'));
      pe_total_count <= (OTHERS => '0');
      pe_total_snapshot <= (OTHERS => '0');
      stim_window_seen <= '0';
      stim_snapshot <= '0';
      weight_dbg_snapshot <= (OTHERS => (OTHERS => '0'));
      tele_pending <= '0';
    ELSIF clk48'EVENT AND clk48 = '1' THEN
      IF ce_tick = '1' THEN
        next_counts := pe_spike_counts;
        next_total := pe_total_count;

        FOR k IN 0 TO 9 LOOP
          IF pe_spike_raw(k) = '1' THEN
            IF next_counts(k) /= to_unsigned(4095, next_counts(k)'LENGTH) THEN
              next_counts(k) := next_counts(k) + 1;
            END IF;

            IF next_total /= to_unsigned(65535, next_total'LENGTH) THEN
              next_total := next_total + 1;
            END IF;
          END IF;
        END LOOP;

        pe_window_mask <= pe_window_mask OR pe_spike_raw;
        stim_window_seen <= stim_window_seen OR stim_core;

        IF uart_frame_sample = C_UART_FRAME_LAST THEN
          uart_frame_sample <= (OTHERS => '0');
          uart_frame_count <= uart_frame_count + 1;
          pe_snapshot <= pe_window_mask OR pe_spike_raw;
          pe_count_snapshot <= next_counts;
          pe_total_snapshot <= next_total;
          stim_snapshot <= stim_window_seen OR stim_core;
          weight_dbg_snapshot <= weight_dbg_raw;
          pe_window_mask <= (OTHERS => '0');
          pe_spike_counts <= (OTHERS => (OTHERS => '0'));
          pe_total_count <= (OTHERS => '0');
          stim_window_seen <= '0';
          tele_pending <= '1';
        ELSE
          uart_frame_sample <= uart_frame_sample + 1;
          pe_spike_counts <= next_counts;
          pe_total_count <= next_total;
        END IF;
      END IF;

      IF tele_sending = '1' THEN
        tele_pending <= '0';
      END IF;
    END IF;
  END PROCESS;

  uart_packet_sender : PROCESS (clk48, core_reset)
  BEGIN
    IF core_reset = '1' THEN
      tele_sending <= '0';
      tele_byte_index <= 0;
      uart_tx_valid <= '0';
      uart_tx_data <= (OTHERS => '0');
    ELSIF clk48'EVENT AND clk48 = '1' THEN
      uart_tx_valid <= '0';

      IF C_UART_ENABLE THEN
        IF tele_sending = '0' AND tele_pending = '1' THEN
          tele_sending <= '1';
          tele_byte_index <= 0;
        ELSIF tele_sending = '1' AND uart_tx_busy = '0' AND uart_tx_valid = '0' THEN
          uart_tx_data <= tele_byte(
            tele_byte_index,
            uart_frame_count,
            stim_snapshot,
            pe_snapshot,
            weight_dbg_snapshot,
            pe_count_snapshot,
            pe_total_snapshot
          );
          uart_tx_valid <= '1';

          IF tele_byte_index = 561 THEN
            tele_sending <= '0';
            tele_byte_index <= 0;
          ELSE
            tele_byte_index <= tele_byte_index + 1;
          END IF;
        END IF;
      END IF;
    END IF;
  END PROCESS;

  u_uart_tx : uart_tx_core
    GENERIC MAP (
      G_CLKS_PER_BIT => 417
    )
    PORT MAP (
      clk      => clk48,
      reset    => core_reset,
      tx_valid => uart_tx_valid,
      tx_data  => uart_tx_data,
      tx_busy  => uart_tx_busy,
      txd      => uart_tx_i
    );

  pe_led <= led_test_i WHEN C_LED_SELF_TEST ELSE pe_led_i;
  pll_locked <= pll_locked_i;
  stim_led <= stim_core;
  uart_tx <= uart_tx_i;

END rtl;
