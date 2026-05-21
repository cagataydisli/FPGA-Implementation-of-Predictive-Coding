-- Board-level wrapper for MMN_Core_Chip when a 48 MHz clock is available.
--
-- It generates a one-clock clk_enable pulse every 2400 fast-clock cycles:
--   48 MHz / 2400 = 20 kHz -> dt = 50 us
--
-- reset is active-high here, matching the HDL Coder generated core.

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;

ENTITY MMN_Core_Chip_Top_48MHz IS
  PORT (
    clk_48    : IN  std_logic;
    reset     : IN  std_logic;
    stim_in   : IN  std_logic;
    ce_20k    : OUT std_logic;
    pe_spike  : OUT std_logic_vector(9 DOWNTO 0)
  );
END MMN_Core_Chip_Top_48MHz;

ARCHITECTURE rtl OF MMN_Core_Chip_Top_48MHz IS

  COMPONENT MMN_Core_Chip IS
    PORT (
      clk        : IN  std_logic;
      reset      : IN  std_logic;
      clk_enable : IN  std_logic;
      In1        : IN  std_logic;
      ce_out     : OUT std_logic;
      Spike      : OUT std_logic_vector(9 DOWNTO 0)
    );
  END COMPONENT;

  SIGNAL ce_count : unsigned(11 DOWNTO 0) := (OTHERS => '0');
  SIGNAL ce_tick  : std_logic := '0';

BEGIN

  ce_gen : PROCESS (clk_48, reset)
  BEGIN
    IF reset = '1' THEN
      ce_count <= (OTHERS => '0');
      ce_tick <= '0';
    ELSIF clk_48'EVENT AND clk_48 = '1' THEN
      IF ce_count = to_unsigned(2399, ce_count'LENGTH) THEN
        ce_count <= (OTHERS => '0');
        ce_tick <= '1';
      ELSE
        ce_count <= ce_count + 1;
        ce_tick <= '0';
      END IF;
    END IF;
  END PROCESS;

  u_core : MMN_Core_Chip
    PORT MAP (
      clk        => clk_48,
      reset      => reset,
      clk_enable => ce_tick,
      In1        => stim_in,
      ce_out     => ce_20k,
      Spike      => pe_spike
    );

END rtl;
