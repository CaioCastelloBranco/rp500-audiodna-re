"""Minimal 8051 disassembler for static firmware reading."""
SFR = {
    0x80:'P0',0x81:'SP',0x82:'DPL',0x83:'DPH',0x87:'PCON',0x88:'TCON',0x89:'TMOD',
    0x8A:'TL0',0x8B:'TL1',0x8C:'TH0',0x8D:'TH1',0x90:'P1',0x98:'SCON',0x99:'SBUF',
    0xA0:'P2',0xA8:'IE',0xB0:'P3',0xB8:'IP',0xD0:'PSW',0xE0:'ACC',0xF0:'B',
}

def sfr(n):
    return SFR.get(n, '0x%02X'%n)

def bitname(n):
    # bit address decode
    if n < 0x80:
        return '0x%02X'%n
    reg = n & 0xF8
    idx = n & 7
    r = SFR.get(reg)
    if r: return '%s.%d'%(r,idx)
    return '0x%02X'%n

def operands(op, b1, b2, pc):
    """Return (mnemonic, len) for opcode op with following bytes."""
    Rn = 'R%d'%(op & 7)
    # helper
    def rel8(x):
        return x-256 if x>127 else x
    if op == 0x00: return 'NOP',1
    if op == 0x01: 
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'AJMP 0x%04X'%target,2
    if op == 0x02:
        return 'LJMP 0x%04X'%((b1<<8)|b2),3
    if op == 0x03: return 'RR A',1
    if op == 0x04: return 'INC A',1
    if op == 0x05: return 'INC %s'%sfr(b1),2
    if op == 0x06: return 'INC @R0',1
    if op == 0x07: return 'INC @R1',1
    if 0x08 <= op <= 0x0F: return 'INC %s'%Rn,1
    if op == 0x10:
        t=(pc+3)+rel8(b2); return 'JBC %s,0x%04X'%(bitname(b1),t),3
    if op == 0x11:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'ACALL 0x%04X'%target,2
    if op == 0x12:
        return 'LCALL 0x%04X'%((b1<<8)|b2),3
    if op == 0x13: return 'RRC A',1
    if op == 0x14: return 'DEC A',1
    if op == 0x15: return 'DEC %s'%sfr(b1),2
    if op == 0x16: return 'DEC @R0',1
    if op == 0x17: return 'DEC @R1',1
    if 0x18 <= op <= 0x1F: return 'DEC %s'%Rn,1
    if op == 0x20:
        t=(pc+3)+rel8(b2); return 'JB %s,0x%04X'%(bitname(b1),t),3
    if op == 0x21:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'AJMP 0x%04X'%target,2
    if op == 0x22: return 'RET',1
    if op == 0x23: return 'RL A',1
    if op == 0x24: return 'ADD A,#0x%02X'%b1,2
    if op == 0x25: return 'ADD A,%s'%sfr(b1),2
    if op == 0x26: return 'ADD A,@R0',1
    if op == 0x27: return 'ADD A,@R1',1
    if 0x28 <= op <= 0x2F: return 'ADD A,%s'%Rn,1
    if op == 0x30:
        t=(pc+3)+rel8(b2); return 'JNB %s,0x%04X'%(bitname(b1),t),3
    if op == 0x31:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'ACALL 0x%04X'%target,2
    if op == 0x32: return 'RETI',1
    if op == 0x33: return 'RLC A',1
    if op == 0x34: return 'ADDC A,#0x%02X'%b1,2
    if op == 0x35: return 'ADDC A,%s'%sfr(b1),2
    if op == 0x36: return 'ADDC A,@R0',1
    if op == 0x37: return 'ADDC A,@R1',1
    if 0x38 <= op <= 0x3F: return 'ADDC A,%s'%Rn,1
    if op == 0x40:
        t=(pc+2)+rel8(b1); return 'JC 0x%04X'%t,2
    if op == 0x41:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'AJMP 0x%04X'%target,2
    if op == 0x42: return 'ORL %s,A'%sfr(b1),2
    if op == 0x43: return 'ORL %s,#0x%02X'%(sfr(b1),b2),3
    if op == 0x44: return 'ORL A,#0x%02X'%b1,2
    if op == 0x45: return 'ORL A,%s'%sfr(b1),2
    if op == 0x46: return 'ORL A,@R0',1
    if op == 0x47: return 'ORL A,@R1',1
    if 0x48 <= op <= 0x4F: return 'ORL A,%s'%Rn,1
    if op == 0x50:
        t=(pc+2)+rel8(b1); return 'JNC 0x%04X'%t,2
    if op == 0x51:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'ACALL 0x%04X'%target,2
    if op == 0x52: return 'ANL %s,A'%sfr(b1),2
    if op == 0x53: return 'ANL %s,#0x%02X'%(sfr(b1),b2),3
    if op == 0x54: return 'ANL A,#0x%02X'%b1,2
    if op == 0x55: return 'ANL A,%s'%sfr(b1),2
    if op == 0x56: return 'ANL A,@R0',1
    if op == 0x57: return 'ANL A,@R1',1
    if 0x58 <= op <= 0x5F: return 'ANL A,%s'%Rn,1
    if op == 0x60:
        t=(pc+2)+rel8(b1); return 'JZ 0x%04X'%t,2
    if op == 0x61:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'AJMP 0x%04X'%target,2
    if op == 0x62: return 'XRL %s,A'%sfr(b1),2
    if op == 0x63: return 'XRL %s,#0x%02X'%(sfr(b1),b2),3
    if op == 0x64: return 'XRL A,#0x%02X'%b1,2
    if op == 0x65: return 'XRL A,%s'%sfr(b1),2
    if op == 0x66: return 'XRL A,@R0',1
    if op == 0x67: return 'XRL A,@R1',1
    if 0x68 <= op <= 0x6F: return 'XRL A,%s'%Rn,1
    if op == 0x70:
        t=(pc+2)+rel8(b1); return 'JNZ 0x%04X'%t,2
    if op == 0x71:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'ACALL 0x%04X'%target,2
    if op == 0x72: return 'ORL C,%s'%bitname(b1),2
    if op == 0x73: return 'JMP @A+DPTR',1
    if op == 0x74: return 'MOV A,#0x%02X'%b1,2
    if op == 0x75: return 'MOV %s,#0x%02X'%(sfr(b1),b2),3
    if op == 0x76: return 'MOV @R0,#0x%02X'%b1,2
    if op == 0x77: return 'MOV @R1,#0x%02X'%b1,2
    if 0x78 <= op <= 0x7F: return 'MOV %s,#0x%02X'%(Rn,b1),2
    if op == 0x80:
        t=(pc+2)+rel8(b1); return 'SJMP 0x%04X'%t,2
    if op == 0x81:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'AJMP 0x%04X'%target,2
    if op == 0x82: return 'ANL C,%s'%bitname(b1),2
    if op == 0x83: return 'MOVC A,@A+PC',1
    if op == 0x84: return 'DIV AB',1
    if op == 0x85: return 'MOV %s,%s'%(sfr(b2),sfr(b1)),3
    if op == 0x86: return 'MOV %s,@R0'%sfr(b1),2
    if op == 0x87: return 'MOV %s,@R1'%sfr(b1),2
    if 0x88 <= op <= 0x8F: return 'MOV %s,%s'%(sfr(b1),Rn),2
    if op == 0x90: return 'MOV DPTR,#0x%04X'%((b1<<8)|b2),3
    if op == 0x91:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'ACALL 0x%04X'%target,2
    if op == 0x92: return 'MOV %s,C'%bitname(b1),2
    if op == 0x93: return 'MOVC A,@A+DPTR',1
    if op == 0x94: return 'SUBB A,#0x%02X'%b1,2
    if op == 0x95: return 'SUBB A,%s'%sfr(b1),2
    if op == 0x96: return 'SUBB A,@R0',1
    if op == 0x97: return 'SUBB A,@R1',1
    if 0x98 <= op <= 0x9F: return 'SUBB A,%s'%Rn,1
    if op == 0xA0: return 'ORL C,/%s'%bitname(b1),2
    if op == 0xA1:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'AJMP 0x%04X'%target,2
    if op == 0xA2: return 'MOV C,%s'%bitname(b1),2
    if op == 0xA3: return 'INC DPTR',1
    if op == 0xA4: return 'MUL AB',1
    if op == 0xA5: return 'DB 0xA5',1
    if op == 0xA6: return 'MOV @R0,%s'%sfr(b1),2
    if op == 0xA7: return 'MOV @R1,%s'%sfr(b1),2
    if 0xA8 <= op <= 0xAF: return 'MOV %s,%s'%(Rn,sfr(b1)),2
    if op == 0xB0: return 'ANL C,/%s'%bitname(b1),2
    if op == 0xB1:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'ACALL 0x%04X'%target,2
    if op == 0xB2: return 'CPL %s'%bitname(b1),2
    if op == 0xB3: return 'CPL C',1
    if op == 0xB4:
        t=(pc+3)+rel8(b2); return 'CJNE A,#0x%02X,0x%04X'%(b1,t),3
    if op == 0xB5:
        t=(pc+3)+rel8(b2); return 'CJNE A,%s,0x%04X'%(sfr(b1),t),3
    if op == 0xB6:
        t=(pc+3)+rel8(b2); return 'CJNE @R0,#0x%02X,0x%04X'%(b1,t),3
    if op == 0xB7:
        t=(pc+3)+rel8(b2); return 'CJNE @R1,#0x%02X,0x%04X'%(b1,t),3
    if 0xB8 <= op <= 0xBF:
        t=(pc+3)+rel8(b2); return 'CJNE %s,#0x%02X,0x%04X'%(Rn,b1,t),3
    if op == 0xC0: return 'PUSH %s'%sfr(b1),2
    if op == 0xC1:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'AJMP 0x%04X'%target,2
    if op == 0xC2: return 'CLR %s'%bitname(b1),2
    if op == 0xC3: return 'CLR C',1
    if op == 0xC4: return 'SWAP A',1
    if op == 0xC5: return 'XCH A,%s'%sfr(b1),2
    if op == 0xC6: return 'XCH A,@R0',1
    if op == 0xC7: return 'XCH A,@R1',1
    if 0xC8 <= op <= 0xCF: return 'XCH A,%s'%Rn,1
    if op == 0xD0: return 'POP %s'%sfr(b1),2
    if op == 0xD1:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'ACALL 0x%04X'%target,2
    if op == 0xD2: return 'SETB %s'%bitname(b1),2
    if op == 0xD3: return 'SETB C',1
    if op == 0xD4: return 'DA A',1
    if op == 0xD5:
        t=(pc+3)+rel8(b2); return 'DJNZ %s,0x%04X'%(sfr(b1),t),3
    if op == 0xD6: return 'XCHD A,@R0',1
    if op == 0xD7: return 'XCHD A,@R1',1
    if 0xD8 <= op <= 0xDF:
        t=(pc+2)+rel8(b1); return 'DJNZ %s,0x%04X'%(Rn,t),2
    if op == 0xE0: return 'MOVX A,@DPTR',1
    if op == 0xE1:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'AJMP 0x%04X'%target,2
    if op == 0xE2: return 'MOVX A,@R0',1
    if op == 0xE3: return 'MOVX A,@R1',1
    if op == 0xE4: return 'CLR A',1
    if op == 0xE5: return 'MOV A,%s'%sfr(b1),2
    if op == 0xE6: return 'MOV A,@R0',1
    if op == 0xE7: return 'MOV A,@R1',1
    if 0xE8 <= op <= 0xEF: return 'MOV A,%s'%Rn,1
    if op == 0xF0: return 'MOVX @DPTR,A',1
    if op == 0xF1:
        target=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; return 'ACALL 0x%04X'%target,2
    if op == 0xF2: return 'MOVX @R0,A',1
    if op == 0xF3: return 'MOVX @R1,A',1
    if op == 0xF4: return 'CPL A',1
    if op == 0xF5: return 'MOV %s,A'%sfr(b1),2
    if op == 0xF6: return 'MOV @R0,A',1
    if op == 0xF7: return 'MOV @R1,A',1
    if 0xF8 <= op <= 0xFF: return 'MOV %s,A'%Rn,1
    return 'DB 0x%02X'%op,1

def disasm(data, base=0, start=0, stop=None):
    out=[]
    pc=start
    end=len(data) if stop is None else stop
    while pc < end:
        op=data[pc]
        b1=data[pc+1] if pc+1<len(data) else 0
        b2=data[pc+2] if pc+2<len(data) else 0
        text,ln=operands(op,b1,b2,base+pc)
        raw=' '.join('%02X'%data[pc+k] for k in range(min(ln,len(data)-pc)))
        out.append((base+pc,raw,text))
        pc+=ln
    return out
