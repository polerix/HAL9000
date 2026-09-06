# HAL 9000 Keypad PCB

10-button backlit keypad for the HAL 9000 terminal. Connects to a Vasiumic MCP23017 I2C GPIO expander via Dupont wires.

## Specs
- Board: 75.10 × 30.20 mm, 2-layer
- Buttons: 6×6×5mm momentary tactile, 4-pin DIP, 15mm pitch (2×5 grid)
- LEDs: 5mm through-hole, always-on, one per button in function color
- Resistors: current-limiting per LED color (330Ω red, 270Ω green, 180Ω blue, 300Ω amber)
- J1: 10-pin 2.54mm Dupont → MCP23017 GPA0–7 + GPB0–1
- J2: 2-pin power (5V + GND)

## Button Layout (row × col)
| | Col 1 | Col 2 | Col 3 | Col 4 | Col 5 |
|---|---|---|---|---|---|
| Row 1 | HIB | LIF | COM | NAV | MEM |
| Row 2 | ATM | FLX | NUC | WEA | MED |

## Files
- `hal9000-keypad/` — KiCad project (.kicad_sch, .kicad_pcb, .kicad_pro)
- `hal9000-keypad-pcb.zip` — full project archive for peer review
- `author-hal9000-keypad.mjs` — MCP authoring script that generated this design

## Notes
Resistors may need manual placement adjustment in KiCad PCB editor to clear courtyard overlaps (all nets and footprints are correct).
