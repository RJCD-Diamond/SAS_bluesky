library ieee;
use ieee.std_logic_1164.all;

entity sync_bit is
port (
    clk_i       : in std_logic;
    bit_i       : in std_logic;
    bit_o       : out std_logic
);
end entity;

architecture rtl of sync_bit is

signal bit_meta : std_logic;

attribute async_reg             : string;
attribute async_reg of bit_meta : signal is "TRUE";
attribute async_reg of bit_o    : signal is "TRUE";

begin

sync_io : process (clk_i) begin
    if rising_edge(clk_i) then
        bit_meta <= bit_i;
        bit_o <= bit_meta;
    end if;
end process;

end;
