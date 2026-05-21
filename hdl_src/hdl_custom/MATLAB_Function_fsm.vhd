-- Hand-written replacement architecture for hdlsrc/mmn_kart/MATLAB_Function.vhd.
-- Keep the entity name and ports identical to the HDL Coder generated STDP block.
--
-- Assumption:
--   clk        : fast FPGA clock
--   enb        : one-clock sample tick, every Simulink dt = 5e-5 s
--   reset      : asynchronous reset
--
-- The original HDL Coder implementation updates all 10x100 weights in one sample
-- combinationally. This version serializes the work over FPGA clock cycles and
-- stores weights in a 1-D RAM so XST can infer block RAM instead of LUT registers.

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;
USE work.MMN_Core_Chip_pkg.ALL;

ENTITY MATLAB_Function IS
  PORT( clk                               :   IN    std_logic;
        reset                             :   IN    std_logic;
        enb                               :   IN    std_logic;
        spikes_pre                        :   IN    std_logic_vector(99 DOWNTO 0);  -- boolean [100]
        spikes_post                       :   IN    std_logic_vector(9 DOWNTO 0);  -- boolean [10]
        I_syn                             :   OUT   vector_of_std_logic_vector16(0 TO 9);  -- sfix16_En8 [10]
        weight_dbg                        :   OUT   vector_of_std_logic_vector16(0 TO 99)  -- all Mem_A row sums, Q8
        );
END MATLAB_Function;


ARCHITECTURE rtl OF MATLAB_Function IS

  SUBTYPE s16 IS signed(15 DOWNTO 0);
  SUBTYPE s18 IS signed(17 DOWNTO 0);

  -- Use a power-of-two depth so XST's 10-bit BRAM address range matches
  -- the declared array range. Only addresses 0..999 hold active weights.
  TYPE ram_t IS ARRAY (0 TO 1023) OF s16;
  TYPE state_t IS (
    S_INIT,
    S_IDLE,
    S_DECAY_PRE,
    S_DECAY_POST,
    S_WEIGHT_READ,
    S_WEIGHT_UPDATE,
    S_INC_PRE,
    S_INC_POST,
    S_PUBLISH
  );

  CONSTANT C_ZERO16              : s16 := to_signed(0, 16);
  CONSTANT C_ZERO18              : s18 := to_signed(0, 18);
  CONSTANT C_W_INIT              : s16 := to_signed(102, 16);     -- 0.4 in sfix16_En8
  CONSTANT C_W_MIN               : s16 := to_signed(3, 16);       -- approx 0.01
  CONSTANT C_W_MAX               : s16 := to_signed(2560, 16);    -- 10.0
  CONSTANT C_A_PLUS              : s18 := to_signed(2621, 18);    -- 0.02 in sfix18_En17
  CONSTANT C_A_MINUS_NEG         : s18 := to_signed(-3932, 18);   -- -0.03 in sfix18_En17
  CONSTANT C_DECAY_PRE           : s18 := to_signed(130527, 18);  -- 0x1FDDF
  CONSTANT C_DECAY_POST          : s18 := to_signed(130799, 18);  -- 0x1FEEF
  CONSTANT C_TRACE_PRE_EPS       : s18 := to_signed(354, 18);     -- 0x00162
  CONSTANT C_TRACE_POST_EPS_NEG  : s18 := to_signed(-2110, 18);   -- -0x0083E

  SIGNAL state                   : state_t := S_INIT;
  SIGNAL weights_ram             : ram_t;
  ATTRIBUTE ram_style            : string;
  ATTRIBUTE ram_extract          : string;
  ATTRIBUTE ram_style OF weights_ram : SIGNAL IS "block";
  ATTRIBUTE ram_extract OF weights_ram : SIGNAL IS "yes";
  SIGNAL ram_addr                : integer RANGE 0 TO 999 := 0;
  SIGNAL ram_din                 : s16 := (OTHERS => '0');
  SIGNAL ram_dout                : s16 := (OTHERS => '0');
  SIGNAL ram_we                  : std_logic := '0';

  SIGNAL init_idx                : integer RANGE 0 TO 999 := 0;
  SIGNAL pre_idx                 : integer RANGE 0 TO 99 := 0;
  SIGNAL post_idx                : integer RANGE 0 TO 9 := 0;
  SIGNAL r_idx                   : integer RANGE 0 TO 9 := 0;
  SIGNAL c_idx                   : integer RANGE 0 TO 99 := 0;
  SIGNAL weight_idx              : integer RANGE 0 TO 999 := 0;

  SIGNAL pre_latched             : std_logic_vector(99 DOWNTO 0) := (OTHERS => '0');
  SIGNAL post_latched            : std_logic_vector(9 DOWNTO 0) := (OTHERS => '0');
  SIGNAL trace_pre_mem           : vector_of_signed18(0 TO 99) := (OTHERS => (OTHERS => '0'));
  SIGNAL trace_post_mem          : vector_of_signed18(0 TO 9) := (OTHERS => (OTHERS => '0'));
  SIGNAL I_syn_acc               : vector_of_signed16(0 TO 9) := (OTHERS => (OTHERS => '0'));
  SIGNAL I_syn_reg               : vector_of_signed16(0 TO 9) := (OTHERS => (OTHERS => '0'));
  SIGNAL weight_dbg_acc          : vector_of_signed16(0 TO 99) := (OTHERS => (OTHERS => '0'));
  SIGNAL weight_dbg_reg          : vector_of_signed16(0 TO 99) := (OTHERS => (OTHERS => '0'));
  SIGNAL w_update_next           : s16 := (OTHERS => '0');

  FUNCTION mul_q17(a : s18; b : s18) RETURN s18 IS
    VARIABLE prod     : signed(35 DOWNTO 0);
    VARIABLE rounded  : signed(35 DOWNTO 0);
    VARIABLE shifted  : signed(35 DOWNTO 0);
  BEGIN
    prod := a * b;
    rounded := prod + to_signed(65536, 36);
    shifted := shift_right(rounded, 17);
    RETURN resize(shifted, 18);
  END FUNCTION;

  FUNCTION trace_pre_to_w(x : s18) RETURN s16 IS
    VARIABLE tmp      : signed(31 DOWNTO 0);
    VARIABLE shifted  : signed(31 DOWNTO 0);
  BEGIN
    -- Q1.17 -> Q8, rounded. This matches trace_pre(c)(17 downto 9) + round bit.
    tmp := resize(x, 32) + to_signed(256, 32);
    shifted := shift_right(tmp, 9);
    RETURN resize(shifted, 16);
  END FUNCTION;

  FUNCTION trace_post_to_w(x : s18) RETURN s16 IS
    VARIABLE tmp      : signed(31 DOWNTO 0);
    VARIABLE shifted  : signed(31 DOWNTO 0);
  BEGIN
    -- LTD gain is 2.0, so Q1.17 -> Q8 uses net shift of 8 bits.
    tmp := resize(x, 32) + to_signed(128, 32);
    shifted := shift_right(tmp, 8);
    RETURN resize(shifted, 16);
  END FUNCTION;

  FUNCTION clip_weight(x : signed(31 DOWNTO 0)) RETURN s16 IS
  BEGIN
    IF x < resize(C_W_MIN, 32) THEN
      RETURN C_W_MIN;
    ELSIF x > resize(C_W_MAX, 32) THEN
      RETURN C_W_MAX;
    ELSE
      RETURN resize(x, 16);
    END IF;
  END FUNCTION;

  FUNCTION sat_add16(a : s16; b : s16) RETURN s16 IS
    VARIABLE sum32 : signed(31 DOWNTO 0);
  BEGIN
    sum32 := resize(a, 32) + resize(b, 32);
    IF sum32 > to_signed(32767, 32) THEN
      RETURN to_signed(32767, 16);
    ELSIF sum32 < to_signed(-32768, 32) THEN
      RETURN to_signed(-32768, 16);
    ELSE
      RETURN resize(sum32, 16);
    END IF;
  END FUNCTION;

  FUNCTION sat_add_q17(a : s18; b : s18) RETURN s18 IS
    VARIABLE sum32 : signed(31 DOWNTO 0);
  BEGIN
    sum32 := resize(a, 32) + resize(b, 32);
    IF sum32 > to_signed(131071, 32) THEN
      RETURN to_signed(131071, 18);
    ELSIF sum32 < to_signed(-131072, 32) THEN
      RETURN to_signed(-131072, 18);
    ELSE
      RETURN resize(sum32, 18);
    END IF;
  END FUNCTION;

BEGIN

  outputgen: FOR k IN 0 TO 9 GENERATE
    I_syn(k) <= std_logic_vector(I_syn_reg(k));
  END GENERATE;

  dbg_outputgen: FOR k IN 0 TO 99 GENERATE
    weight_dbg(k) <= std_logic_vector(weight_dbg_reg(k));
  END GENERATE;

  -- XST-friendly single-port block RAM template:
  -- no reset, no read enable, one conditional write, one unconditional sync read.
  bram_process : PROCESS (clk)
  BEGIN
    IF clk'EVENT AND clk = '1' THEN
      IF ram_we = '1' THEN
        weights_ram(ram_addr) <= ram_din;
      END IF;
      ram_dout <= weights_ram(ram_addr);
    END IF;
  END PROCESS;

  weight_update_calc : PROCESS (
    ram_dout,
    post_latched,
    pre_latched,
    trace_pre_mem,
    trace_post_mem,
    r_idx,
    c_idx
  )
    VARIABLE w32 : signed(31 DOWNTO 0);
  BEGIN
    w32 := resize(ram_dout, 32);

    IF post_latched(r_idx) = '1' THEN
      w32 := w32 + resize(trace_pre_to_w(trace_pre_mem(c_idx)), 32);
    END IF;

    IF pre_latched(c_idx) = '1' THEN
      w32 := w32 + resize(trace_post_to_w(trace_post_mem(r_idx)), 32);
    END IF;

    w_update_next <= clip_weight(w32);
  END PROCESS;

  ram_ctrl : PROCESS (state, init_idx, weight_idx, w_update_next)
  BEGIN
    ram_addr <= weight_idx;
    ram_din <= C_ZERO16;
    ram_we <= '0';

    CASE state IS
      WHEN S_INIT =>
        ram_addr <= init_idx;
        ram_din <= C_W_INIT;
        ram_we <= '1';

      WHEN S_WEIGHT_UPDATE =>
        ram_addr <= weight_idx;
        ram_din <= w_update_next;
        ram_we <= '1';

      WHEN OTHERS =>
        ram_addr <= weight_idx;
        ram_din <= C_ZERO16;
        ram_we <= '0';
    END CASE;
  END PROCESS;

  stdp_fsm : PROCESS (clk, reset)
    VARIABLE decayed      : s18;
    VARIABLE dbg_acc_next : vector_of_signed16(0 TO 99);
  BEGIN
    IF reset = '1' THEN
      state <= S_INIT;
      init_idx <= 0;
      pre_idx <= 0;
      post_idx <= 0;
      r_idx <= 0;
      c_idx <= 0;
      weight_idx <= 0;
      pre_latched <= (OTHERS => '0');
      post_latched <= (OTHERS => '0');
      trace_pre_mem <= (OTHERS => C_ZERO18);
      trace_post_mem <= (OTHERS => C_ZERO18);
      I_syn_acc <= (OTHERS => C_ZERO16);
      I_syn_reg <= (OTHERS => C_ZERO16);
      weight_dbg_acc <= (OTHERS => C_ZERO16);
      weight_dbg_reg <= (OTHERS => C_ZERO16);

    ELSIF clk'EVENT AND clk = '1' THEN
      CASE state IS

        WHEN S_INIT =>
          IF init_idx = 999 THEN
            init_idx <= 0;
            state <= S_IDLE;
          ELSE
            init_idx <= init_idx + 1;
          END IF;

        WHEN S_IDLE =>
          IF enb = '1' THEN
            pre_latched <= spikes_pre;
            post_latched <= spikes_post;
            I_syn_acc <= (OTHERS => C_ZERO16);
            pre_idx <= 0;
            post_idx <= 0;
            r_idx <= 0;
            c_idx <= 0;
            weight_idx <= 0;
            weight_dbg_acc <= (OTHERS => C_ZERO16);
            state <= S_DECAY_PRE;
          END IF;

        WHEN S_DECAY_PRE =>
          decayed := mul_q17(trace_pre_mem(pre_idx), C_DECAY_PRE);
          IF decayed < C_TRACE_PRE_EPS THEN
            trace_pre_mem(pre_idx) <= C_ZERO18;
          ELSE
            trace_pre_mem(pre_idx) <= decayed;
          END IF;

          IF pre_idx = 99 THEN
            pre_idx <= 0;
            post_idx <= 0;
            state <= S_DECAY_POST;
          ELSE
            pre_idx <= pre_idx + 1;
          END IF;

        WHEN S_DECAY_POST =>
          decayed := mul_q17(trace_post_mem(post_idx), C_DECAY_POST);
          IF decayed > C_TRACE_POST_EPS_NEG THEN
            trace_post_mem(post_idx) <= C_ZERO18;
          ELSE
            trace_post_mem(post_idx) <= decayed;
          END IF;

          IF post_idx = 9 THEN
            post_idx <= 0;
            r_idx <= 0;
            c_idx <= 0;
            weight_idx <= 0;
            state <= S_WEIGHT_READ;
          ELSE
            post_idx <= post_idx + 1;
          END IF;

        WHEN S_WEIGHT_READ =>
          state <= S_WEIGHT_UPDATE;

        WHEN S_WEIGHT_UPDATE =>
          dbg_acc_next := weight_dbg_acc;
          dbg_acc_next(c_idx) := sat_add16(weight_dbg_acc(c_idx), w_update_next);
          weight_dbg_acc <= dbg_acc_next;

          IF pre_latched(c_idx) = '1' THEN
            I_syn_acc(r_idx) <= sat_add16(I_syn_acc(r_idx), w_update_next);
          END IF;

          IF weight_idx = 999 THEN
            weight_dbg_reg <= dbg_acc_next;
            pre_idx <= 0;
            state <= S_INC_PRE;
          ELSE
            weight_idx <= weight_idx + 1;
            IF c_idx = 99 THEN
              c_idx <= 0;
              IF r_idx = 9 THEN
                r_idx <= 0;
              ELSE
                r_idx <= r_idx + 1;
              END IF;
            ELSE
              c_idx <= c_idx + 1;
            END IF;
            state <= S_WEIGHT_READ;
          END IF;

        WHEN S_INC_PRE =>
          IF pre_latched(pre_idx) = '1' THEN
            trace_pre_mem(pre_idx) <= sat_add_q17(trace_pre_mem(pre_idx), C_A_PLUS);
          END IF;

          IF pre_idx = 99 THEN
            pre_idx <= 0;
            post_idx <= 0;
            state <= S_INC_POST;
          ELSE
            pre_idx <= pre_idx + 1;
          END IF;

        WHEN S_INC_POST =>
          IF post_latched(post_idx) = '1' THEN
            trace_post_mem(post_idx) <= sat_add_q17(trace_post_mem(post_idx), C_A_MINUS_NEG);
          END IF;

          IF post_idx = 9 THEN
            post_idx <= 0;
            state <= S_PUBLISH;
          ELSE
            post_idx <= post_idx + 1;
          END IF;

        WHEN S_PUBLISH =>
          I_syn_reg <= I_syn_acc;
          state <= S_IDLE;

      END CASE;
    END IF;
  END PROCESS;

END rtl;
