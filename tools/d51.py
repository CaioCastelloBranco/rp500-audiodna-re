"""Minimal but complete MCS-51 (8051) disassembler."""

def _s8(b):
    return b - 256 if b > 127 else b

def disasm(d, base=0, start=0, end=None, max_ins=100000):
    """Disassemble d[start:end] assuming code address = base + index."""
    if end is None:
        end = len(d)
    out = []
    i = start
    n = 0
    while i < end and n < max_ins:
        a = base + i
        op = d[i]
        def b(k):
            return d[i + k] if i + k < len(d) else 0
        text = None
        size = 1
        # helper tables
        if op == 0x00:
            text = 'NOP'
        elif op in (0x01, 0x21, 0x41, 0x61, 0x81, 0xA1, 0xC1, 0xE1):
            size = 2
            target = ((a + 2) & 0xF800) | ((op & 0xE0) << 3) | b(1)
            text = f'AJMP {target:04X}'
        elif op == 0x02:
            size = 3
            text = f'LJMP {(b(1) << 8) | b(2):04X}'
        elif op in (0x11, 0x31, 0x51, 0x71, 0x91, 0xB1, 0xD1, 0xF1):
            size = 2
            target = ((a + 2) & 0xF800) | ((op & 0xE0) << 3) | b(1)
            text = f'ACALL {target:04X}'
        elif op == 0x03:
            text = 'RR A'
        elif op == 0x04:
            text = 'INC A'
        elif op in (0x05, 0x15):
            size = 2
            text = f'{"INC" if op == 5 else "DEC"} {b(1):02X}h'
        elif op in (0x06, 0x07, 0x16, 0x17):
            size = 1
            reg = '@R0' if op & 1 == 0 else '@R1'
            text = f'{"INC" if op < 0x10 else "DEC"} {reg}'
        elif 0x08 <= op <= 0x0F:
            text = f'INC R{op - 8}'
        elif 0x18 <= op <= 0x1F:
            text = f'DEC R{op - 0x18}'
        elif op in (0x10, 0x20, 0x30):
            size = 3
            m = {0x10: 'JBC', 0x20: 'JB', 0x30: 'JNB'}[op]
            text = f'{m} {b(1):02X}h,{a + 3 + _s8(b(2)):04X}'
        elif op == 0x12:
            size = 3
            text = f'LCALL {(b(1) << 8) | b(2):04X}'
        elif op == 0x13:
            text = 'RRC A'
        elif op == 0x14:
            text = 'DEC A'
        elif op == 0x22:
            text = 'RET'
        elif op == 0x23:
            text = 'RL A'
        elif op in (0x24, 0x34, 0x44, 0x54, 0x64, 0x74, 0x94, 0xB4):
            size = 2
            m = {0x24: 'ADD', 0x34: 'ADDC', 0x44: 'ORL', 0x54: 'ANL',
                 0x64: 'XRL', 0x74: 'MOV', 0x94: 'SUBB', 0xB4: 'CJNE'}[op]
            if op == 0xB4:
                text = f'CJNE A,#{b(1):02X}h,{a + 3 + _s8(b(2)):04X}'
                size = 3
            else:
                text = f'{m} A,#{b(1):02X}h'
        elif op in (0x25, 0x35, 0x45, 0x55, 0x65, 0x95, 0xB5):
            size = 2 if op != 0xB5 else 3
            m = {0x25: 'ADD', 0x35: 'ADDC', 0x45: 'ORL', 0x55: 'ANL',
                 0x65: 'XRL', 0x95: 'SUBB', 0xB5: 'CJNE'}[op]
            if op == 0xB5:
                text = f'CJNE A,{b(1):02X}h,{a + 3 + _s8(b(2)):04X}'
            else:
                text = f'{m} A,{b(1):02X}h'
        elif op in (0x26, 0x27, 0x36, 0x37, 0x46, 0x47, 0x56, 0x57,
                    0x66, 0x67, 0x96, 0x97):
            reg = '@R0' if op & 1 == 0 else '@R1'
            m = {0x2: 'ADD', 0x3: 'ADDC', 0x4: 'ORL', 0x5: 'ANL', 0x6: 'XRL', 0x9: 'SUBB'}
            text = f'{m[op >> 4]} A,{reg}'
        elif 0x28 <= op <= 0x2F:
            text = f'ADD A,R{op - 0x28}'
        elif op == 0x32:
            text = 'RETI'
        elif op == 0x33:
            text = 'RLC A'
        elif 0x38 <= op <= 0x3F:
            text = f'ADDC A,R{op - 0x38}'
        elif 0x40 <= op <= 0x7F and (op & 0x0F) == 0:
            # conditional jumps
            size = 2
            m = {0x40: 'JC', 0x50: 'JNC', 0x60: 'JZ', 0x70: 'JNZ'}[op]
            text = f'{m} {a + 2 + _s8(b(1)):04X}'
        elif 0x48 <= op <= 0x4F:
            text = f'ORL A,R{op - 0x48}'
        elif op == 0x42:
            size = 2
            text = f'ORL {b(1):02X}h,A'
        elif op == 0x43:
            size = 3
            text = f'ORL {b(1):02X}h,#{b(2):02X}h'
        elif 0x58 <= op <= 0x5F:
            text = f'ANL A,R{op - 0x58}'
        elif op == 0x52:
            size = 2
            text = f'ANL {b(1):02X}h,A'
        elif op == 0x53:
            size = 3
            text = f'ANL {b(1):02X}h,#{b(2):02X}h'
        elif 0x68 <= op <= 0x6F:
            text = f'XRL A,R{op - 0x68}'
        elif op == 0x62:
            size = 2
            text = f'XRL {b(1):02X}h,A'
        elif op == 0x63:
            size = 3
            text = f'XRL {b(1):02X}h,#{b(2):02X}h'
        elif op == 0x72:
            size = 2
            text = f'ORL C,/{b(1):02X}h'
        elif op == 0x73:
            text = 'JMP @A+DPTR'
        elif op == 0x75:
            size = 3
            text = f'MOV {b(1):02X}h,#{b(2):02X}h'
        elif op == 0x76:
            size = 2
            text = f'MOV @R0,#{b(1):02X}h'
        elif op == 0x77:
            size = 2
            text = f'MOV @R1,#{b(1):02X}h'
        elif 0x78 <= op <= 0x7F:
            size = 2
            text = f'MOV R{op - 0x78},#{b(1):02X}h'
        elif op == 0x80:
            size = 2
            text = f'SJMP {a + 2 + _s8(b(1)):04X}'
        elif op == 0x82:
            size = 2
            text = f'ANL C,{b(1):02X}h'
        elif op == 0x83:
            text = 'MOVC A,@A+PC'
        elif op == 0x84:
            text = 'DIV AB'
        elif op == 0x85:
            size = 3
            text = f'MOV {b(2):02X}h,{b(1):02X}h'
        elif op == 0x86:
            size = 2
            text = f'MOV {b(1):02X}h,@R0'
        elif op == 0x87:
            size = 2
            text = f'MOV {b(1):02X}h,@R1'
        elif 0x88 <= op <= 0x8F:
            size = 2
            text = f'MOV {b(1):02X}h,R{op - 0x88}'
        elif op == 0x90:
            size = 3
            text = f'MOV DPTR,#{(b(1) << 8) | b(2):04X}h'
        elif op == 0x92:
            size = 2
            text = f'MOV {b(1):02X}h,C'
        elif op == 0x93:
            text = 'MOVC A,@A+DPTR'
        elif 0x98 <= op <= 0x9F:
            text = f'SUBB A,R{op - 0x98}'
        elif op == 0xA0:
            size = 2
            text = f'ORL C,/{b(1):02X}h'
        elif op == 0xA2:
            size = 2
            text = f'MOV C,{b(1):02X}h'
        elif op == 0xA3:
            text = 'INC DPTR'
        elif op == 0xA4:
            text = 'MUL AB'
        elif op == 0xA5:
            text = 'DB A5h (reserved)'
        elif op == 0xA6:
            size = 2
            text = f'MOV @R0,{b(1):02X}h'
        elif op == 0xA7:
            size = 2
            text = f'MOV @R1,{b(1):02X}h'
        elif 0xA8 <= op <= 0xAF:
            size = 2
            text = f'MOV R{op - 0xA8},{b(1):02X}h'
        elif op == 0xB0:
            size = 2
            text = f'ANL C,/{b(1):02X}h'
        elif op == 0xB2:
            size = 2
            text = f'CPL {b(1):02X}h'
        elif op == 0xB3:
            text = 'CPL C'
        elif op in (0xB6, 0xB7):
            size = 3
            reg = '@R0' if op == 0xB6 else '@R1'
            text = f'CJNE {reg},#{b(1):02X}h,{a + 3 + _s8(b(2)):04X}'
        elif 0xB8 <= op <= 0xBF:
            size = 3
            text = f'CJNE R{op - 0xB8},#{b(1):02X}h,{a + 3 + _s8(b(2)):04X}'
        elif op == 0xC0:
            size = 2
            text = f'PUSH {b(1):02X}h'
        elif op == 0xC2:
            size = 2
            text = f'CLR {b(1):02X}h'
        elif op == 0xC3:
            text = 'CLR C'
        elif op == 0xC4:
            text = 'SWAP A'
        elif op == 0xC5:
            size = 2
            text = f'XCH A,{b(1):02X}h'
        elif op == 0xC6:
            text = 'XCH A,@R0'
        elif op == 0xC7:
            text = 'XCH A,@R1'
        elif 0xC8 <= op <= 0xCF:
            text = f'XCH A,R{op - 0xC8}'
        elif op == 0xD0:
            size = 2
            text = f'POP {b(1):02X}h'
        elif op == 0xD2:
            size = 2
            text = f'SETB {b(1):02X}h'
        elif op == 0xD3:
            text = 'SETB C'
        elif op == 0xD4:
            text = 'DA A'
        elif op == 0xD5:
            size = 3
            text = f'DJNZ {b(1):02X}h,{a + 3 + _s8(b(2)):04X}'
        elif op == 0xD6:
            text = 'XCHD A,@R0'
        elif op == 0xD7:
            text = 'XCHD A,@R1'
        elif 0xD8 <= op <= 0xDF:
            size = 2
            text = f'DJNZ R{op - 0xD8},{a + 2 + _s8(b(1)):04X}'
        elif op == 0xE0:
            text = 'MOVX A,@DPTR'
        elif op == 0xE2:
            text = 'MOVX A,@R0'
        elif op == 0xE3:
            text = 'MOVX A,@R1'
        elif op == 0xE4:
            text = 'CLR A'
        elif op == 0xE5:
            size = 2
            text = f'MOV A,{b(1):02X}h'
        elif op == 0xE6:
            text = 'MOV A,@R0'
        elif op == 0xE7:
            text = 'MOV A,@R1'
        elif 0xE8 <= op <= 0xEF:
            text = f'MOV A,R{op - 0xE8}'
        elif op == 0xF0:
            text = 'MOVX @DPTR,A'
        elif op == 0xF2:
            text = 'MOVX @R0,A'
        elif op == 0xF3:
            text = 'MOVX @R1,A'
        elif op == 0xF4:
            text = 'CPL A'
        elif op == 0xF5:
            size = 2
            text = f'MOV {b(1):02X}h,A'
        elif op == 0xF6:
            text = 'MOV @R0,A'
        elif op == 0xF7:
            text = 'MOV @R1,A'
        elif 0xF8 <= op <= 0xFF:
            text = f'MOV R{op - 0xF8},A'
        elif 0x86 == op:
            pass
        else:
            text = f'DB {op:02X}h'

        if text is None:
            text = f'DB {op:02X}h'
        out.append((a, d[i:i + size].hex(' '), text))
        i += size
        n += 1
    return out


if __name__ == '__main__':
    import sys
    data = open(sys.argv[1], 'rb').read()
    base = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
    start = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0
    end = int(sys.argv[4], 16) if len(sys.argv) > 4 else len(data)
    for a, raw, txt in disasm(data, base, start, end):
        print(f'{a:04X}: {raw:<9} {txt}')
