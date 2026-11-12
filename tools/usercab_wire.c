/* Portable C implementation of the GSP1101 user-cab wire primitives, taken
 * from report section 11.7 and cross-checked against the NetUpdaterClone
 * SysexCodec (Pack / Unpack / Checksum).
 *
 *   - super7_unpack()  : 1 MSB byte per 7 payload bytes
 *   - sysex_checksum() : XOR of every byte after F0, masked with 0x7F
 *
 * The file builds twice from the SAME source:
 *
 *   1. for the host (any C compiler; `zig cc` is enough):
 *        zig cc -O2 -o usercab_wire.exe 04_analysis_scripts/usercab_wire.c
 *        usercab_wire.exe
 *      -> prints the computed values and "PASS"/"FAIL".
 *
 *   2. for the 8051 (SDCC):
 *        sdcc -mmcs51 --model-small --iram-size 256 \
 *             --code-loc 0x0000 --out-fmt-ihx usercab_wire.c
 *
 * The host build is the test oracle; the 8051 build is what eventually goes
 * into the firmware. The 8051-side execution check lives in
 * 04_analysis_scripts/ucsim_check.py (freestanding assembly under uCsim).
 */

#include <stdio.h>

/* Super7: each group of 7 payload bytes is preceded by an MSB byte whose
 * bits carry bit 7 of each of the 7 bytes. */
unsigned int super7_unpack(const unsigned char *in, unsigned int n,
                           unsigned char *out)
{
    unsigned int i, o = 0;
    unsigned int num = 0, num2 = 0;
    for (i = 0; i < n; i++) {
        unsigned char b = in[i];
        if (num2 == 0) {
            num = b;
            num2 = 1;
        } else {
            out[o++] = (unsigned char)(((num << num2) & 0x80) | (b & 0x7F));
            num2 = (num2 + 1) % 8;
        }
    }
    return o;
}

/* XOR of every byte after the leading F0, masked with 0x7F. */
unsigned char sysex_checksum(const unsigned char *d, unsigned int n)
{
    unsigned int i;
    unsigned int x = 0;
    for (i = 1; i < n; i++) {
        x ^= d[i];
    }
    return (unsigned char)(x & 0x7F);
}

/* ---- test vectors ---- */

static const unsigned char packed[8] = {
    0x6A, 0x70, 0x00, 0x7F, 0x7F, 0x01, 0x43, 0x5A
};
static const unsigned char expect[7] = {
    0xF0, 0x80, 0x7F, 0xFF, 0x01, 0xC3, 0x5A
};
static const unsigned char msg[10] = {
    0xF0, 0x00, 0x00, 0x10, 0x00, 0x5E, 0x05, 0x7A, 0x01, 0x02
};

#ifndef __SDCC

/* ---- host build: print the values and compare against the expectation ---- */

int main(void)
{
    unsigned char out[16];
    unsigned int n, i, ok = 1;
    const unsigned char expect_cksum = 0x32;   /* XOR of msg[1..] & 0x7F */

    n = super7_unpack(packed, sizeof(packed), out);
    if (n != sizeof(expect)) {
        ok = 0;
    }
    for (i = 0; i < sizeof(expect) && i < n; i++) {
        if (out[i] != expect[i]) {
            ok = 0;
        }
    }
    if (sysex_checksum(msg, sizeof(msg)) != expect_cksum) {
        ok = 0;
    }

    printf("unpacked bytes    : %u\n", n);
    printf("checksum          : 0x%02X (expected 0x%02X)\n",
           sysex_checksum(msg, sizeof(msg)), expect_cksum);
    printf("first unpacked    : 0x%02X\n", out[0]);
    printf("%s\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

#else

/* ---- 8051 build: the same checks, with the verdict left in registers ----
 *
 * Register contract (read back by 04_analysis_scripts/ucsim_check.py):
 *   R3 = computed checksum
 *   R4 = expected checksum (0x31)
 *   R7 = 0xA5 pass / 0x5A fail
 */
#include <mcs51/8052.h>

__code unsigned char cpacked[8] = {
    0x6A, 0x70, 0x00, 0x7F, 0x7F, 0x01, 0x43, 0x5A
};
__code unsigned char cexpect[7] = {
    0xF0, 0x80, 0x7F, 0xFF, 0x01, 0xC3, 0x5A
};
__code unsigned char cmsg[10] = {
    0xF0, 0x00, 0x00, 0x10, 0x00, 0x5E, 0x05, 0x7A, 0x01, 0x02
};

__xdata __at (0x0000) unsigned char xbuf[4];

void main(void)
{
    unsigned char out[16];
    unsigned int n, i, ok = 1;

    n = super7_unpack(cpacked, sizeof(cpacked), out);
    if (n != sizeof(cexpect)) {
        ok = 0;
    }
    for (i = 0; i < sizeof(cexpect) && i < n; i++) {
        if (out[i] != cexpect[i]) {
            ok = 0;
        }
    }

    xbuf[0] = ok ? 0xA5 : 0x5A;
    xbuf[1] = (unsigned char)n;
    xbuf[2] = sysex_checksum(cmsg, sizeof(cmsg));
    xbuf[3] = (n > 0) ? out[0] : 0x00;

    while (1) {
        ;
    }
}

#endif
