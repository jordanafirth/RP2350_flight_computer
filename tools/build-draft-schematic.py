"""Build a connectivity-first KiCad draft from pinned Eagle reference netlists.

The draft uses explicit physical pad numbers and global net labels. It is a
reviewable engineering intermediate, not a production PCB or a BOM release.
Requires only Python's standard library. Never modifies upstream CAD.
"""
from __future__ import annotations
import copy
import csv
import json
import math
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from part_catalog import apply as apply_part_catalog

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hardware' / 'rev-a'
NS = uuid.UUID('95e42019-75b7-4964-b47d-4e0c293e84bb')
PROJECT = 'flight-computer'
parts: dict[str, dict] = {}


def uid(key):
    return str(uuid.uuid5(NS, key))


def q(value):
    return json.dumps(str(value), ensure_ascii=False)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def source(repo, filename):
    sch = ET.parse(ROOT / 'references' / repo / filename).getroot().find('drawing/schematic')
    libraries = {x.get('name'): x for x in sch.findall('libraries/library')}
    nets = {}
    for net in sch.findall('sheets/sheet/nets/net'):
        for pin in net.findall('segment/pinref'):
            key = (pin.get('part'), pin.get('gate'), pin.get('pin'))
            if key in nets and nets[key] != net.get('name'):
                raise ValueError(f'Conflicting source pin: {key}')
            nets[key] = net.get('name')
    result = {}
    for part in sch.findall('parts/part'):
        lib = libraries[part.get('library')]
        ds = next(x for x in lib.findall('devicesets/deviceset') if x.get('name') == part.get('deviceset'))
        device = next(x for x in ds.findall('devices/device') if x.get('name', '') == part.get('device', ''))
        package = device.get('package')
        if not package:
            continue
        gates = {x.get('name'): x.get('symbol') for x in ds.findall('gates/gate')}
        symbols = {x.get('name'): x for x in lib.findall('symbols/symbol')}
        pin_data = {}
        for connect in device.findall('connects/connect'):
            pin = next(x for x in symbols[gates[connect.get('gate')]].findall('pin') if x.get('name') == connect.get('pin'))
            direction = pin.get('direction', 'io')
            ptype = {'in': 'input', 'out': 'output', 'io': 'bidirectional', 'pas': 'passive', 'pwr': 'power_in', 'oc': 'open_collector', 'hiz': 'tri_state', 'nc': 'no_connect', 'sup': 'power_out'}.get(direction, 'passive')
            for pad in connect.get('pad', '').split():
                data = {'number': pad, 'name': connect.get('pin'), 'type': ptype, 'net': nets.get((part.get('name'), connect.get('gate'), connect.get('pin')))}
                if pad in pin_data and pin_data[pad]['net'] != data['net']:
                    raise ValueError(f'Conflicting mapped pad: {part.get("name")}.{pad}')
                pin_data[pad] = data
        if not pin_data:
            continue
        result[part.get('name')] = {
            'ref': part.get('name'), 'value': part.get('value') or part.get('deviceset'),
            'package': package, 'pins': list(pin_data.values()), 'source': f'{repo}/{filename}:{part.get("name")}',
            'mpn': '', 'dnp': False,
        }
    return result


def add(part, ref=None, page='Processor'):
    part = copy.deepcopy(part)
    part['ref'] = ref or part['ref']
    if part['ref'] in parts:
        raise ValueError(f'Duplicate reference {part["ref"]}')
    part['page'] = page
    parts[part['ref']] = part
    return part


def simple(ref, value, nets, page, package, mpn='', names=None, types=None, dnp=False):
    names = names or [str(i + 1) for i in range(len(nets))]
    types = types or ['passive'] * len(nets)
    return add({'ref': ref, 'value': value, 'pins': [{'number': str(i + 1), 'name': names[i], 'type': types[i], 'net': net} for i, net in enumerate(nets)], 'package': package, 'mpn': mpn, 'source': 'Custom integration', 'dnp': dnp}, page=page)


def set_pin(part, name, net):
    matches = [pin for pin in part['pins'] if pin['name'] == name]
    if not matches:
        raise ValueError(f'Pin {name} missing from {part["ref"]}')
    for pin in matches:
        pin['net'] = net


def prepare_model():
    base = source('Adafruit-Feather-RP2350-PCB', 'Adafruit Feather RP2350.sch')
    gpio_nets = {0: 'UART_TX', 1: 'UART_RX', 2: 'SDA', 3: 'SCL', 4: 'GPIO4', 5: 'SERVO1', 6: 'SERVO2', 7: 'STATUS_LED', 8: 'GPIO8', 9: 'SERVO3', 10: 'SERVO4', 11: 'GPIO11', 12: 'SD_MISO', 13: 'SD_CS', 14: 'SD_CLK', 15: 'SD_MOSI', 16: 'BNO_INT_N', 17: 'BNO_RESET_N', 18: 'SD_DETECT_N', 19: 'BMP_INT', 20: 'EXP_MISO', 21: 'NEOPIXEL', 22: 'EXP_SCK', 23: 'EXP_MOSI', 24: 'GPIO24', 25: 'GPIO25', 26: 'A0', 27: 'A1', 28: 'A2', 29: 'A3'}
    aliases = {'3.3V': '+3V3', '1.2V': 'VCORE', 'EN': 'ENABLE', 'VHI': 'VSYS', 'N$8': 'VBAT'}
    for pin in base['X2']['pins']:
        match = re.search(r'GPIO(\d+)(?:/|$)', pin['name'])
        if match:
            aliases[pin['net']] = gpio_nets[int(match.group(1))]
    for i in range(4):
        aliases[f'QSPI_DATA[{i}]'] = f'QSPI_IO{i}'
    excluded = {'CN2', 'U4', 'R15', 'C22', 'DEBUG', 'SJ1', 'D+1', 'D-1'}
    rename = {'X2': 'U4', 'X1': 'JBAT1', 'X6': 'JUSB1', 'JP1': 'J1', 'JP3': 'J2', 'CONN1': 'JQT1', 'L': 'D1', 'CHG': 'D2', 'LED1': 'D5', 'D+1': 'TP1', 'D-1': 'TP2', 'TP3': 'TP3', 'SWD': 'TP4', 'SWC': 'TP5'}
    power = {'JBAT1', 'JUSB1', 'U2', 'U3', 'Q3', 'D4', 'D2', 'R2', 'R3', 'R4', 'R8', 'R9', 'R10', 'R12', 'R13', 'C1', 'C4', 'C20', 'TP1', 'TP2'}
    interfaces = {'J1', 'J2', 'JQT1', 'R16', 'R17'}
    for old_ref, part in base.items():
        if old_ref in excluded:
            continue
        ref = rename.get(old_ref, old_ref)
        page = 'Power' if ref in power else 'Interfaces' if ref in interfaces else 'Processor'
        new = add(part, ref, page)
        for pin in new['pins']:
            net = pin['net']
            pin['net'] = aliases.get(net, f'BASE_{net.replace("$", "_")}' if net and net.startswith('N$') else net)
            match = re.search(r'GPIO(\d+)(?:/|$)', pin['name'])
            if match:
                pin['name'] = f'GPIO{match.group(1)}'
        if ref in {'R16', 'R17'}:
            new['value'] = '4.7k'
        if ref == 'U4':
            new['value'] = 'RP2350A (A4)'
            new['mpn'] = 'RP2350A0A4'
        if ref == 'U2':
            new['mpn'] = 'RT9080-33GJ5'
            for pin in new['pins']:
                if pin['name'] == 'OUT':
                    pin['type'] = 'power_out'
        if ref == 'U3':
            new['mpn'] = 'MCP73831T-2ACI/OT'
        if ref == 'U1':
            for pin in new['pins']:
                if pin['name'] in {'VCC', 'VSS'}:
                    pin['type'] = 'power_in'
        if ref == 'R8':
            new['value'] = '5.1k'
            new['mpn'] = 'RC0402FR-075K1L'
        if ref == 'JBAT1':
            new['mpn'] = 'S2B-PH-SM4-TB(LF)(SN)'
        if ref.startswith(('J', 'TP')):
            for pin in new['pins']:
                pin['type'] = 'passive'
        if ref in {'J1', 'J2'}:
            new['dnp'] = True  # Retain GPIO pads without adding assembled headers.

    # The sensor core keeps its reference crystal and CAP circuit, but omits
    # breakout regulator, interface buffer and level translation.
    imu = source('Adafruit-BNO08x-PCB', 'Adafruit_BNO08x.sch')
    sensor = add(imu['U1'], 'U5', 'Sensors')
    sensor['value'] = sensor['mpn'] = 'BNO085'
    sensor_nets = {'BOOTN': 'BNO_BOOT_N', 'CAP': 'BNO_CAP', 'CLKSEL0': 'GND', 'CLKSEL1/XOUT32': 'BNO_XOUT', 'GND': 'GND', 'GNDIO': 'GND', 'H_CSN': 'BNO_CS_N', 'H_INTN': 'BNO_INT_N', 'H_SA0/MOSI': 'GND', 'H_SCL/SCLK/RX': 'SCL', 'H_SDA/MISO/TX': 'SDA', 'NRST': 'BNO_RESET_N', 'PS0/WAKE': 'GND', 'PS1': 'GND', 'S_SCL': 'BNO_AUX_SCL', 'S_SDA': 'BNO_AUX_SDA', 'VDD': '+3V3', 'VDDIO': '+3V3', 'XIN32': 'BNO_XIN'}
    for name, net in sensor_nets.items():
        set_pin(sensor, name, net)
    for pin in sensor['pins']:
        if pin['name'] == 'H_SA0/MOSI':
            pin['type'] = 'input'  # I2C address strap, not SPI data direction.
    for number in (1, 7, 8, 12, 13, 21, 22, 23, 24):
        sensor['pins'].append({'number': str(number), 'name': 'RESV_NC', 'type': 'no_connect', 'net': None})
    crystal = add(imu['X1'], 'Y2', 'Sensors')
    crystal['value'] = '32.768kHz'
    for pin in crystal['pins']:
        pin['net'] = {'XIN': 'BNO_XIN', 'XOUT': 'BNO_XOUT'}.get(pin['net'], pin['net'])
    cap = 'Capacitor_SMD:C_0603_1608Metric'
    resistor = 'Resistor_SMD:R_0603_1608Metric'
    for ref, value, net in [('C31', '100nF', 'BNO_CAP'), ('C32', '100nF', '+3V3'), ('C33', '22pF', 'BNO_XIN'), ('C34', '22pF', 'BNO_XOUT'), ('C35', '100nF', '+3V3')]:
        simple(ref, value, [net, 'GND'], 'Sensors', cap)
    for ref, net in [('R41', 'BNO_BOOT_N'), ('R42', 'BNO_RESET_N'), ('R43', 'BNO_CS_N'), ('R44', 'BNO_AUX_SCL'), ('R45', 'BNO_AUX_SDA')]:
        simple(ref, '10k', ['+3V3', net], 'Sensors', resistor)

    baro = source('Adafruit-BMP5xx-Temperature-and-Pressure-Sensor-PCB', 'Adafruit BMP581 Temperature and Pressure Sensor rev B.sch')
    pressure = add(baro['IC1'], 'U6', 'Sensors')
    pressure['value'] = pressure['mpn'] = 'BMP581'
    for name, net in {'CSB': '+3V3', 'GND': 'GND', 'INT': 'BMP_INT', 'SCK': 'SCL', 'SDI': 'SDA', 'SDO': 'GND', 'VDD': '+3V3', 'VDDIO': '+3V3'}.items():
        set_pin(pressure, name, net)
    for pin in pressure['pins']:
        if pin['name'] == 'SDO':
            pin['type'] = 'input'  # I2C address strap.
    for ref in ['C36', 'C37']:
        simple(ref, '100nF', ['+3V3', 'GND'], 'Sensors', cap)

    logger = source('Adafruit-Feather-RP2040-Adalogger-PCB', 'Adafruit Feather RP2040 Adalogger.sch')
    sd = add(logger['X2'], 'JSD1', 'Interfaces')
    for name, net in {'SD_VDD': '+3V3', 'SD_VSS': 'GND', 'MOUNTING': 'GND', 'DATA_OUT': 'SD_MISO', 'DATA_IN': 'SD_MOSI', 'SCLK': 'SD_CLK', 'CS': 'SD_CS', 'DAT1': 'SD_DAT1_UNUSED', 'DAT2': 'SD_DAT2_UNUSED', 'CARD_DETECT': 'SD_DETECT_N'}.items():
        set_pin(sd, name, net)
    for index, net in enumerate(['SD_MISO', 'SD_MOSI', 'SD_CS', 'SD_DAT1_UNUSED', 'SD_DAT2_UNUSED', 'SD_DETECT_N'], 31):
        simple(f'R{index}', '47k', ['+3V3', net], 'Interfaces', resistor)
    simple('C38', '10uF', ['+3V3', 'GND'], 'Interfaces', 'Capacitor_SMD:C_0805_2012Metric')
    simple('JTAG1', 'REMOVE BEFORE FLIGHT', ['ENABLE', 'GND'], 'Power', 'Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical', 'BM02B-SRSS-TB(LF)(SN)')
    servo_pins = [net for i in range(1, 5) for net in (f'SERVO{i}', 'VBAT_SERVO', 'GND')]
    simple('JSERVO1', '4 x servo: S / BAT / GND', servo_pins, 'Interfaces', 'FlightComputer:Servo_RA_3x04_P2.54mm_TSW10408', 'TSW-104-08-T-T-RA')
    for i in range(1, 5):
        simple(f'R{50+i}', '100k', [f'SERVO{i}', 'GND'], 'Interfaces', resistor)
    simple('U7', 'TPS22919', ['VBAT', 'GND', 'ENABLE', None, 'SERVO_QOD', 'VBAT_SERVO'], 'Power', 'Package_TO_SOT_SMD:SOT-363_SC-70-6', 'TPS22919DCKR', ['VIN', 'GND', 'ON', 'NC', 'QOD', 'VOUT'], ['power_in', 'power_in', 'input', 'no_connect', 'passive', 'power_out'])
    simple('R55', '1k', ['VBAT_SERVO', 'SERVO_QOD'], 'Power', resistor)
    simple('C39', '10uF', ['VBAT_SERVO', 'GND'], 'Power', 'Capacitor_SMD:C_0805_2012Metric')
    simple('C40', '1uF', ['VBAT', 'GND'], 'Power', cap)
    # ERC cannot propagate power through diodes, FETs, inductors and filter
    # resistors. These flags declare real sources and passive supply paths.
    for index, net in enumerate(['VBUS', 'VBAT', 'VSYS', 'GND', 'VCORE', 'ADC_AVDD', 'VREG_AVDD'], 1):
        simple(f'#FLG{index:02d}', 'PWR_FLAG', [net], 'Power', '', names=['pwr'], types=['power_out'])

    # Specify an orderable USB connector and its physical pad numbering.
    # The reference footprint uses combined pads; GCT has separate contacts.
    usb = parts['JUSB1']
    usb['package'] = 'Connector_USB:USB_C_Receptacle_GCT_USB4110'
    usb['mpn'] = 'USB4110-GF-A'
    parts['JQT1']['mpn'] = 'SM04B-SRSS-TB(LF)(SN)'
    usb_map = {
        'A1':'GND', 'A12':'GND', 'B1':'GND', 'B12':'GND', 'SH':'GND',
        'A4':'VBUS', 'A9':'VBUS', 'B4':'VBUS', 'B9':'VBUS',
        'A5':'CC1', 'B5':'CC2', 'A6':'USB_D+', 'B6':'USB_D+',
        'A7':'USB_D-', 'B7':'USB_D-', 'A8':None, 'B8':None,
    }
    usb['pins'] = [{'number':pad, 'name':pad, 'type':'passive', 'net':net} for pad,net in usb_map.items()]
    sd['package'] = 'Connector_Card:microSD_HC_Molex_104031-0811'
    sd['mpn'] = '1040310811'
    sd_map = {'1':'SD_DAT2_UNUSED', '2':'SD_CS', '3':'SD_MOSI', '4':'+3V3',
              '5':'SD_CLK', '6':'GND', '7':'SD_MISO', '8':'SD_DAT1_UNUSED',
              '9':'SD_DETECT_N', '10':'GND', 'SH':'GND'}
    sd['pins'] = [{'number':pad, 'name':pad, 'type':'passive', 'net':net} for pad,net in sd_map.items()]
    # Manufacturer-approved RP235x crystal; explicitly ground the case pads.
    parts['Y1']['package'] = 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm'
    parts['Y1']['mpn'] = 'ABM8-272-T3'
    parts['Y1']['pins'].extend([{'number':str(n),'name':'GND','type':'passive','net':'GND'} for n in (2,4)])
    parts['Y2']['package'] = 'Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm'
    parts['Y2']['mpn'] = 'ABS07-32.768KHZ-T'
    for n,pin in enumerate(parts['Y2']['pins'],1):
        pin['number'] = str(n)
    parts['U1']['mpn'] = 'W25Q64JVXGIQ'
    apply_part_catalog(parts)

    # Source-specific anonymous nets are namespaced; no accidental joins across
    # the merged projects are permitted. Every physical pad has one assignment.
    for part in parts.values():
        numbers = [pin['number'] for pin in part['pins']]
        if len(numbers) != len(set(numbers)):
            raise ValueError(f'Duplicate physical pad in {part["ref"]}')
        if part['package'] and ':' not in part['package']:
            part['footprint'] = 'FlightComputer:' + re.sub(r'[^A-Za-z0-9_.+-]', '_', part['package'])
        else:
            part['footprint'] = part['package']


def effects(size=1.0, extra=''):
    return f'(effects (font (size {size} {size})) {extra})'


def symbol_geometry(part):
    pins = sorted(part['pins'], key=lambda p: (not p['number'].isdigit(), int(p['number']) if p['number'].isdigit() else p['number']))
    ref = part['ref']
    two = len(pins) == 2 and ref[0] in 'RC'
    if two:
        return [(-5.08, 0, 0, pins[0]), (5.08, 0, 180, pins[1])], 12.7, 5.08
    if len(pins) == 1:
        return [(-5.08, 0, 0, pins[0])], 10.16, 5.08
    split = math.ceil(len(pins) / 2)
    half_height = max(2.54, (split - 1) * 1.27 + 2.54)
    width = 45.72 if len(pins) > 40 else 30.48 if len(pins) > 14 else 20.32
    out = []
    for i, pin in enumerate(pins):
        side = 0 if i < split else 1
        row = i if side == 0 else i - split
        y = (split - 1) * 1.27 - row * 2.54
        out.append(((-width / 2 - 5.08) if side == 0 else (width / 2 + 5.08), y, 0 if side == 0 else 180, pin))
    return out, width, half_height * 2


def library_symbol(part):
    ref = part['ref']
    geom, width, height = symbol_geometry(part)
    passive = len(geom) == 2 and ref[0] in 'RC'
    if passive and ref[0] == 'R':
        graphic = '(rectangle (start -2.54 1.016) (end 2.54 -1.016) (stroke (width 0.254) (type default)) (fill (type none)))'
    elif passive:
        graphic = ''.join(f'(polyline (pts (xy {x} -2.032) (xy {x} 2.032)) (stroke (width 0.254) (type default)) (fill (type none)))' for x in (-0.762, 0.762))
        graphic += '(polyline (pts (xy -2.54 0) (xy -0.762 0)) (stroke (width 0.254) (type default)) (fill (type none)))'
        graphic += '(polyline (pts (xy 0.762 0) (xy 2.54 0)) (stroke (width 0.254) (type default)) (fill (type none)))'
    else:
        graphic = f'(rectangle (start {-width/2} {height/2}) (end {width/2} {-height/2}) (stroke (width 0.254) (type default)) (fill (type background)))'
    pin_text = []
    for x, y, angle, pin in geom:
        length = 2.54 if passive else 5.08
        name = '~' if passive else pin['name']
        pin_text.append(f'(pin {pin["type"]} line (at {x} {y} {angle}) (length {length}) (name {q(name)} {effects(.95)}) (number {q(pin["number"])} {effects(.95)}))')
    return f'''(symbol {q('FlightComputer:'+ref)} (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
      (property "Reference" {q(re.sub(r'[0-9]+$', '', ref))} (at 0 {height/2+2.54} 0) {effects()})
      (property "Value" {q(part['value'])} (at 0 {-height/2-2.54} 0) {effects()})
      (symbol {q(ref+'_0_1')} {graphic})
      (symbol {q(ref+'_1_1')} {''.join(pin_text)}))'''


def page_header(page_id, title):
    return f'''(kicad_sch (version 20260306) (generator "flight_computer_generator")
      (uuid {q(page_id)}) (paper "A2")
      (title_block (title {q(title)}) (date "2026-11-18") (rev "A-draft")
      (comment 1 "DEVELOPMENT DRAFT - NOT FOR MANUFACTURING")
      (comment 2 "Adafruit-derived circuits; CC BY-SA 3.0; see references and hardware/README.md"))'''


def build():
    prepare_model()
    OUT.mkdir(parents=True, exist_ok=True)
    root_id = uid('root')
    root = [page_header(root_id, 'RP2350 teaching flight computer')]
    root.append(f'(lib_symbols) (text "Integrated hardware draft\\nNo display connector. No optional PSRAM.\\nApplication firmware is supplied separately.\\nExact BOM, independent circuit/footprint review and physical fit remain open." (at 30 30 0) {effects(2, "(justify left top)")} (uuid {q(uid("root-note"))}))')
    root.append('(sheet_instances (path "/" (page "1")))')
    pin_count = 0
    for page_num, name in enumerate(['Power', 'Processor', 'Sensors', 'Interfaces'], 2):
        sheet_id = uid('sheet-'+name)
        child_id = uid('child-'+name)
        filename = name.lower()+'.kicad_sch'
        group = [p for p in parts.values() if p['page'] == name]
        symbols = '\n'.join(library_symbol(p) for p in group)
        page = [page_header(child_id, name), f'(lib_symbols {symbols})']
        page.append(f'(text "DRAFT: labels with identical names connect across sheets. Review notes: ../../docs/schematic-review.md" (at 20 14 0) {effects(1.5,"(justify left)")} (uuid {q(uid(name+"-note"))}))')
        # Shelf-pack symbols by actual pin rows. Keep space for net-label text.
        column, y = 0, 35.0
        for part in sorted(group, key=lambda p: -len(p['pins'])):
            geom, width, height = symbol_geometry(part)
            box_height = max(25.4, height + 20.32)
            if y + box_height > 380:
                column += 1
                y = 35.0
            if column > 3:
                raise ValueError(f'Sheet overflow: {name}')
            x = 78.74 + column * 139.7
            cy = round((y + box_height / 2) / 1.27) * 1.27
            ref = part['ref']
            page.append(f'''(symbol (lib_id {q('FlightComputer:'+ref)}) (at {x} {cy} 0) (unit 1)
              (in_bom {'no' if ref.startswith(('#', 'TP')) else 'yes'}) (on_board {'no' if ref.startswith('#') else 'yes'}) (dnp {'yes' if part['dnp'] else 'no'}) (uuid {q(uid('part-'+ref))})
              (property "Reference" {q(ref)} (at {x} {cy-height/2-3.81} 0) {effects(1.27)})
              (property "Value" {q(part['value'])} (at {x} {cy+height/2+3.81} 0) {effects(1.0)})
              (property "Footprint" {q(part['footprint'])} (at {x} {cy} 0) {effects(1.0,'(hide yes)')})
              (property "MPN" {q(part['mpn'])} (at {x} {cy} 0) {effects(1.0,'(hide yes)')})
              (instances (project {q(PROJECT)} (path {q('/'+root_id+'/'+sheet_id)} (reference {q(ref)}) (unit 1)))))''')
            for dx, dy, angle, pin in geom:
                pin_count += 1
                px, py = round(x+dx, 6), round(cy-dy, 6)
                key = ref+'-'+pin['number']
                if pin['net'] is None:
                    page.append(f'(no_connect (at {px} {py}) (uuid {q(uid("nc-"+key))}))')
                    continue
                end_x = round(px+(-6.35 if dx < 0 else 6.35), 6)
                page.append(f'(wire (pts (xy {px} {py}) (xy {end_x} {py})) (stroke (width 0) (type default)) (uuid {q(uid("wire-"+key))}))')
                page.append(f'(global_label {q(pin["net"])} (shape bidirectional) (at {end_x} {py} {180 if dx<0 else 0}) {effects(.95)} (uuid {q(uid("label-"+key))}))')
            y += box_height
        page.append('(embedded_fonts no))')
        write(OUT / filename, '\n'.join(page)+'\n')
        sy = 95+(page_num-2)*45
        root.append(f'''(sheet (at 35 {sy}) (size 95 30) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0))
          (uuid {q(sheet_id)}) (property "Sheetname" {q(name)} (at 35 {sy-1.27} 0) {effects(1.27,'(justify left bottom)')})
          (property "Sheetfile" {q(filename)} (at 35 {sy+31.27} 0) {effects(1.27,'(justify left top)')})
          (instances (project {q(PROJECT)} (path {q('/'+root_id)} (page {q(page_num)})))))''')
    root.append('(embedded_fonts no))')
    write(OUT / (PROJECT+'.kicad_sch'), '\n'.join(root)+'\n')
    project_path = OUT / (PROJECT+'.kicad_pro')
    project_settings = json.loads(project_path.read_text(encoding='utf-8')) if project_path.exists() else {}
    project_settings['meta'] = {'filename': PROJECT+'.kicad_pro', 'version': 3}
    write(project_path, json.dumps(project_settings, indent=2)+'\n')
    write(OUT / 'sym-lib-table', '(sym_lib_table (version 7) (lib (name "FlightComputer") (type "KiCad") (uri "${KIPRJMOD}/FlightComputer.kicad_sym") (options "") (descr "Project-local symbols with physical pad numbering from pinned references")))\n')
    # Library names are unqualified outside an embedded schematic cache.
    lib = '\n'.join(library_symbol(p).replace(q('FlightComputer:'+p['ref']), q(p['ref']), 1) for p in parts.values())
    write(OUT / 'FlightComputer.kicad_sym', '(kicad_symbol_lib (version 20241209) (generator "flight_computer_generator")\n'+lib+'\n)\n')
    write(OUT / 'connectivity.json', json.dumps({'status': 'development draft', 'parts': list(parts.values())}, indent=2)+'\n')
    with (OUT / 'draft-bom.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['Reference','Value','Manufacturer','MPN','Footprint','DNP','Source'])
        for part in parts.values():
            if part['ref'].startswith(('#', 'TP')):
                continue
            writer.writerow([part['ref'],part['value'],part.get('manufacturer',''),part['mpn'],part['footprint'],part['dnp'],part['source']])
    print(f'Generated draft: {len(parts)} parts, {pin_count} physical pad assignments, four functional sheets plus root.')


if __name__ == '__main__':
    build()
