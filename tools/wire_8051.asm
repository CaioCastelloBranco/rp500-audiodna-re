; Freestanding 8051 test program for the uCsim simulator.
;
; Toolchain (all from the SDCC install):
;   sdas8051 -o wire.rel wire_8051.asm   (asxxxx assembler)
;   sdld -i wire.ihx wire.rel             (SDCC linker)
;   s51 -t 52 -X 12M wire.ihx             (uCsim 8051 simulator)
;
; The program computes the DigiTech SysEx checksum (XOR of every byte after
; the leading F0, masked with 0x7F) over the reference message
;   F0 00 00 10 00 5E 05 7A
; which lives in external RAM at 0x0010.  Results:
;   R3 = computed checksum          (expected 0x31)
;   R7 = 0xA5 if the checksum matches, 0x5A otherwise
;   R4 = 0x31 (expected value, for reference)
;
; The verdict is left in registers on purpose: ucsim's memory dump commands
; address spaces that are not the ones the 8051 core actually uses for MOVX,
; so the final register state is the reliable channel.  The harness in
; 04_analysis_scripts/ucsim_check.py parses the simulator's final state dump.
;
; No C runtime is involved, deliberately: SDCC's crt0 startup does not
; cooperate with ucsim's split RAM model, and Phase 1 will inject
; freestanding code into the firmware anyway.
;
; Every address is an absolute immediate, so the object links with no
; relocations and no forward references.

	.module wire
	.optsdcc -m

	.area CSEG (CODE)

_start::
	;; --- store the reference message into XRAM 0x0010 ---
	mov	dptr, #0x0010
	mov	a, #0xF0
	movx	@dpTR, a
	inc	dptr
	mov	a, #0x00
	movx	@dpTR, a
	inc	dptr
	mov	a, #0x00
	movx	@dpTR, a
	inc	dptr
	mov	a, #0x10
	movx	@dpTR, a
	inc	dptr
	mov	a, #0x00
	movx	@dpTR, a
	inc	dptr
	mov	a, #0x5E
	movx	@dpTR, a
	inc	dptr
	mov	a, #0x05
	movx	@dpTR, a
	inc	dptr
	mov	a, #0x7A
	movx	@dpTR, a

	;; --- checksum: XOR of bytes 0x0011..0x0017, masked with 0x7F ---
	mov	dptr, #0x0011
	mov	r2, #7
	clr	a
	mov	r3, a
lp:
	movx	a, @dpTR
	mov	r4, a
	mov	a, r3
	xrl	a, r4
	mov	r3, a
	inc	dptr
	djnz	r2, lp
	mov	a, r3
	anl	a, #0x7f
	mov	r3, a

	;; --- compare against the expected value ---
	mov	r4, #0x31
	clr	c
	subb	a, r4		; A = A - R4, C set on borrow
	jnz	fail
	jc	fail
	mov	r7, #0xa5
	sjmp	done
fail:
	mov	r7, #0x5a
done:
	;; keep the result in direct RAM as well, for eyeballing
	mov	0x70, r3
	mov	a, r7
	mov	0x71, a

spin:
	sjmp	spin
