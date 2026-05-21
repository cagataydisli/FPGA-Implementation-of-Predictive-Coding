LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;

ENTITY uart_tx_core IS
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
END uart_tx_core;

ARCHITECTURE rtl OF uart_tx_core IS
  TYPE state_t IS (IDLE, START_BIT, DATA_BITS, STOP_BIT);

  SIGNAL state      : state_t := IDLE;
  SIGNAL clk_count  : integer RANGE 0 TO G_CLKS_PER_BIT - 1 := 0;
  SIGNAL bit_index  : integer RANGE 0 TO 7 := 0;
  SIGNAL tx_shift   : std_logic_vector(7 DOWNTO 0) := (OTHERS => '0');
  SIGNAL txd_i      : std_logic := '1';
  SIGNAL tx_busy_i  : std_logic := '0';
BEGIN

  PROCESS (clk, reset)
  BEGIN
    IF reset = '1' THEN
      state <= IDLE;
      clk_count <= 0;
      bit_index <= 0;
      tx_shift <= (OTHERS => '0');
      txd_i <= '1';
      tx_busy_i <= '0';
    ELSIF clk'EVENT AND clk = '1' THEN
      CASE state IS
        WHEN IDLE =>
          txd_i <= '1';
          tx_busy_i <= '0';
          clk_count <= 0;
          bit_index <= 0;

          IF tx_valid = '1' THEN
            tx_shift <= tx_data;
            tx_busy_i <= '1';
            state <= START_BIT;
          END IF;

        WHEN START_BIT =>
          txd_i <= '0';
          tx_busy_i <= '1';

          IF clk_count = G_CLKS_PER_BIT - 1 THEN
            clk_count <= 0;
            state <= DATA_BITS;
          ELSE
            clk_count <= clk_count + 1;
          END IF;

        WHEN DATA_BITS =>
          txd_i <= tx_shift(bit_index);
          tx_busy_i <= '1';

          IF clk_count = G_CLKS_PER_BIT - 1 THEN
            clk_count <= 0;
            IF bit_index = 7 THEN
              bit_index <= 0;
              state <= STOP_BIT;
            ELSE
              bit_index <= bit_index + 1;
            END IF;
          ELSE
            clk_count <= clk_count + 1;
          END IF;

        WHEN STOP_BIT =>
          txd_i <= '1';
          tx_busy_i <= '1';

          IF clk_count = G_CLKS_PER_BIT - 1 THEN
            clk_count <= 0;
            state <= IDLE;
          ELSE
            clk_count <= clk_count + 1;
          END IF;
      END CASE;
    END IF;
  END PROCESS;

  txd <= txd_i;
  tx_busy <= tx_busy_i;

END rtl;
