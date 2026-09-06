/**
 * HAL 9000 Keypad PCB — MCP Schematic + Board Authoring Script
 *
 * Board: 75.10 × 30.20 mm, 2-layer
 * 10 momentary switches (6×6mm, 4-pin DIP) in a 2×5 grid at 15mm pitch
 * 10 indicator LEDs (5mm THT), one per button, always-on
 * 10 current-limiting resistors (THT axial)
 * J1: 10-pin 2.54mm header  (button signal outputs → MCP23017)
 * J2:  2-pin 2.54mm header  (+5V / GND power in)
 *
 * Follows the exact pattern of author-vk-power-carrier.mjs.
 */

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

// ─── Paths ────────────────────────────────────────────────────────────────────
const serverRoot  = "/Users/polerixsys/Documents/kicad9-mcp-backend";
const projectRoot = "/Users/polerixsys/Documents/hal9000-keypad";
const projectName = "hal9000-keypad";
const schematicPath = path.join(projectRoot, `${projectName}.kicad_sch`);
const boardPath     = path.join(projectRoot, `${projectName}.kicad_pcb`);
const reportPath    = path.join(projectRoot, "mcp-authoring.json");
const venvPython    = "/Users/polerixsys/Documents/kicad-mcp-server/venv/bin/python3";

// ─── MCP client setup ─────────────────────────────────────────────────────────
const transcript = { projectRoot, schematicPath, boardPath, kicad: "9.0.9", steps: [] };
const client     = new Client({ name: "hal9000-keypad-author", version: "1.0.0" });
const transport  = new StdioClientTransport({
  command: process.execPath,
  args:    [path.join(serverRoot, "dist/index.js")],
  cwd:     serverRoot,
  stderr:  "pipe",
  env: {
    ...process.env,
    KICAD_PYTHON: venvPython,
    PATH: `/Applications/KiCad9/KiCad.app/Contents/MacOS:${process.env.PATH}`,
    LOG_LEVEL: "info",
  },
});

transport.stderr?.on("data", (chunk) => process.stderr.write(chunk));

async function call(toolName, args) {
  const result = await client.callTool({ name: toolName, arguments: args });
  transcript.steps.push({ name: toolName, args, result });
  const text = result.content?.find((item) => item.type === "text")?.text?.trim() ?? "";
  if (result.isError || text.startsWith("Failed")) {
    throw new Error(`${toolName}: ${text}`);
  }
  if (text.startsWith("{")) {
    const payload = JSON.parse(text);
    if (payload.success === false) throw new Error(`${toolName}: ${payload.message ?? text}`);
  }
  return result;
}

// ─── Button circuit definitions ───────────────────────────────────────────────
// Columns: [code, btnNet, resistorValue(Ω), schX, schY, pcbSWx, pcbSWy]
//
// LED resistor values (Vcc=5V, I=10mA):
//   Green/Teal (Vf≈2.2V):  (5-2.2)/0.010 = 280Ω → 270Ω
//   Red/Magenta (Vf≈2.0V): (5-2.0)/0.010 = 300Ω → 330Ω
//   Blue/Purple (Vf≈3.2V): (5-3.2)/0.010 = 180Ω → 180Ω
//   Amber/Yellow (Vf≈2.1V):(5-2.1)/0.010 = 290Ω → 300Ω
const BUTTONS = [
  // ── Row 1 (PCB y = 7.60 mm) ──
  ["HIB", "BTN_HIB", "270",   20, 40,  7.55,  7.60],  // Dark Teal  → Green
  ["LIF", "BTN_LIF", "330",   40, 40, 22.55,  7.60],  // Rose Magenta → Red
  ["COM", "BTN_COM", "180",   60, 40, 37.55,  7.60],  // Plum Magenta → Blue
  ["NAV", "BTN_NAV", "180",   80, 40, 52.55,  7.60],  // Deep Violet  → Blue
  ["MEM", "BTN_MEM", "180",  100, 40, 67.55,  7.60],  // Slate Steel Blue → Blue
  // ── Row 2 (PCB y = 22.60 mm) ──
  ["ATM", "BTN_ATM", "330",   20, 80,  7.55, 22.60],  // Crimson Red → Red
  ["FLX", "BTN_FLX", "180",   40, 80, 22.55, 22.60],  // Royal Blue  → Blue
  ["NUC", "BTN_NUC", "180",   60, 80, 37.55, 22.60],  // Midnight Navy → Blue
  ["WEA", "BTN_WEA", "300",   80, 80, 52.55, 22.60],  // Amber → Amber
  ["MED", "BTN_MED", "300",  100, 80, 67.55, 22.60],  // Amber → Amber
];

// ─── Build parts list and net map ─────────────────────────────────────────────
// parts: [reference, symbolLib:name, value, footprint, schX, schY, angle?]
const parts = [];

// nets: { netName: [[componentRef, pinName], ...] }
const nets = {
  "+5V": [],
  GND:   [],
};

for (let i = 0; i < BUTTONS.length; i++) {
  const [code, btnNet, rVal, schX, schY] = BUTTONS[i];
  const n   = i + 1;
  const sw  = `SW${n}`;
  const led = `D${n}`;
  const res = `R${n}`;

  // Schematic placement: switch at (schX, schY), LED 10mm above, resistor 20mm above
  parts.push([
    sw, "Switch:SW_Push", `SW_${code}`,
    "Button_Switch_THT:SW_PUSH_6mm",
    schX, schY,
  ]);
  parts.push([
    led, "Device:LED", `LED_${code}`,
    "LED_THT:LED_D5.0mm",
    schX, schY - 10,
  ]);
  parts.push([
    res, "Device:R", rVal,
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    schX, schY - 20,
  ]);

  // Switch: pin 1 → BTN_* net, pin 2 → GND
  // (SW_Push 4-pin DIP: pins 1+3 are common, pins 2+4 are common;
  //  the KiCad SW_Push symbol exposes them as pins "1" and "2")
  nets[btnNet] = nets[btnNet] ?? [];
  nets[btnNet].push([sw, "1"]);
  nets.GND.push([sw, "2"]);

  // LED circuit: R pin1 → +5V, R pin2 → LED anode, LED cathode → GND
  const ledAnode = `LED_A_${code}`;
  nets[ledAnode] = [[res, "2"], [led, "A"]];
  nets["+5V"].push([res, "1"]);
  nets.GND.push([led, "K"]);
}

// J1 — 10-pin button header (one pin per button signal)
//   Connector_Generic:Conn_01x10  pins 1-10
parts.push([
  "J1",
  "Connector_Generic:Conn_01x10", "BTN_HDR_10P",
  "Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical",
  130, 60,
]);

const BTN_NET_ORDER = [
  "BTN_HIB", "BTN_LIF", "BTN_COM", "BTN_NAV", "BTN_MEM",
  "BTN_ATM", "BTN_FLX", "BTN_NUC", "BTN_WEA", "BTN_MED",
];
for (let i = 0; i < BTN_NET_ORDER.length; i++) {
  const net = BTN_NET_ORDER[i];
  nets[net] = nets[net] ?? [];
  nets[net].push(["J1", String(i + 1)]);
}

// J2 — 2-pin power header (+5V pin1, GND pin2)
parts.push([
  "J2",
  "Connector_Generic:Conn_01x02", "PWR_HDR_5V_GND",
  "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
  130, 90,
]);
nets["+5V"].push(["J2", "1"]);
nets.GND.push(["J2", "2"]);

// PWR_FLAG — required so KiCad ERC can identify the GND power driver
parts.push(["#FLG01", "power:PWR_FLAG", "PWR_FLAG", "", 140, 100]);
nets.GND.push(["#FLG01", "1"]);

// ─── PCB placements (all mm) ──────────────────────────────────────────────────
// pcbPlacements: { reference: [x, y, rotationDeg] }
const pcbPlacements = {};

for (let i = 0; i < BUTTONS.length; i++) {
  const [code, , , , , swX, swY] = BUTTONS[i];
  const n    = i + 1;
  const ledY = swY - 5;   // 5 mm above switch center (per spec)
  // Resistors: all placed mid-board (y=15) to fit between the two switch rows.
  // Row 1 centre = 7.60, Row 2 centre = 22.60; mid ≈ 15 mm.
  // Horizontal footprint (10.16 mm pad-to-pad) fits within 15 mm column pitch.
  const resY = 15;

  pcbPlacements[`SW${n}`] = [swX, swY,   0];
  pcbPlacements[`D${n}`]  = [swX, ledY,  90];  // 90° → LED faces board top edge
  pcbPlacements[`R${n}`]  = [swX, resY,   0];
}

// J1 (10-pin, 2.54 mm pitch) — right edge, centred vertically
// 10 pins at 2.54 mm span 22.86 mm; centre at y=14.3 → pins 2.87–25.73 ✓
pcbPlacements.J1 = [73.6, 14.3, 0];

// J2 (2-pin) — immediately below J1's last pin
pcbPlacements.J2 = [73.6, 27.7, 0];

// ─── Main ─────────────────────────────────────────────────────────────────────
let ercText = "not run";

try {
  await mkdir(projectRoot, { recursive: true });
  await client.connect(transport);
  await new Promise((resolve) => setTimeout(resolve, 3500));

  // 1 ── Create project
  console.log("▶ create_project");
  await call("create_project", { path: projectRoot, name: projectName });

  // 2 ── Add all schematic components
  console.log("▶ add_schematic_component (×" + parts.length + ")");
  for (const [reference, symbol, value, footprint, x, y, angle = 0] of parts) {
    await call("add_schematic_component", {
      schematicPath, symbol, reference, value, footprint,
      position: { x, y }, angle,
    });
  }

  // 3 ── Wire up all nets
  const netEntries = Object.entries(nets);
  const pinCount   = netEntries.reduce((s, [, pins]) => s + pins.length, 0);
  console.log(`▶ connect_to_net (${netEntries.length} nets, ${pinCount} pins)`);
  for (const [netName, pins] of netEntries) {
    for (const [componentRef, pinName] of pins) {
      await call("connect_to_net", { schematicPath, componentRef, pinName, netName });
    }
  }

  // 4 ── Annotate schematic
  console.log("▶ annotate_schematic");
  await call("annotate_schematic", { schematicPath });

  // 5 ── ERC
  console.log("▶ run_erc");
  const ercResult = await call("run_erc", { schematicPath });
  ercText = ercResult.content?.find((i) => i.type === "text")?.text?.trim() ?? "no output";
  console.log("ERC:", ercText);

  // 6 ── Sync schematic → board
  console.log("▶ create_board_from_schematic");
  await call("create_board_from_schematic", {
    schematicPath, boardPath, overwrite: true,
  });

  // 7 ── Board design rules
  console.log("▶ set_design_rules");
  await call("set_design_rules", {
    clearance:      0.25,
    trackWidth:     0.5,
    minTrackWidth:  0.25,
    viaDiameter:    0.6,
    viaDrill:       0.3,
    minViaDiameter: 0.6,
    minViaDrill:    0.3,
  });

  // 8 ── Board outline  75.10 × 30.20 mm
  console.log("▶ replace_board_outline");
  await call("replace_board_outline", {
    shape:  "rectangle",
    params: { x: 0, y: 0, width: 75.10, height: 30.20, unit: "mm" },
  });

  // 9 ── Place components
  console.log("▶ open_board");
  await call("open_board", { boardPath });

  console.log("▶ batch_move_components (×" + Object.keys(pcbPlacements).length + ")");
  const moves = Object.fromEntries(
    Object.entries(pcbPlacements).map(([ref, [x, y, rotation]]) => [
      ref, { position: { x, y, unit: "mm" }, rotation },
    ]),
  );
  await call("batch_move_components", { moves, save: true });

  // 10 ── Save
  console.log("▶ save_board");
  await call("save_board", { boardPath, force: true });

  transcript.success = true;

  // Summary
  const distinctNets = Object.keys(nets);
  console.log(JSON.stringify({
    success:      true,
    schematicPath,
    boardPath,
    reportPath,
    ercSummary:   ercText,
    netCount:     distinctNets.length,
    nets:         distinctNets,
  }, null, 2));

} catch (error) {
  transcript.success = false;
  transcript.error   = error instanceof Error ? error.message : String(error);
  console.error("FATAL:", error.message);
  process.exitCode = 1;
} finally {
  await writeFile(reportPath, JSON.stringify(transcript, null, 2));
  await transport.close();
}
