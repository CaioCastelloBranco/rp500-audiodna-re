; S3b TEST variant: hard-code the IR source path.  SIMULATOR ONLY.
; The production gate (s3b_gate.asm) scans 0xF6AA for 00 02 49.
; This variant skips the scan so the source/length/terminator path can be
; exercised in uCsim, where the boot stream runs before the real cab write.

	.module s3b_gate_test
	.optsdcc -m

	.area CSEG (CODE)

gate:
	mov	dptr, #0xFF24
	movx	a, @dptr
	mov	r6, a
	inc	dptr
	movx	a, @dptr
	mov	r7, a

	mov	a, r6
	orl	a, r7
	jz	first_byte

	mov	dptr, #0xF8E2
	movx	a, @dptr
	xrl	a, r7
	jnz	stock_path
	inc	dptr
	movx	a, @dptr
	xrl	a, r6
	jnz	stock_path

	mov	dptr, #0xF8E4
	movx	a, @dptr
	jz	epilogue
	mov	dptr, #0xD070
	mov	a, #0xF5
	movx	@dptr, a
epilogue:
	ljmp	0xBEB0

first_byte:
	;; hard-coded IR: source 0xE200, length 512, terminator 1
	mov	dptr, #0xF8E0
	mov	a, #0x00
	movx	@dptr, a
	inc	dptr
	mov	a, #0xE2
	movx	@dptr, a
	mov	dptr, #0xF8E2
	mov	a, #0x00
	movx	@dptr, a
	inc	dptr
	mov	a, #0x02
	movx	@dptr, a
	mov	dptr, #0xF8E4
	mov	a, #0x01
	movx	@dptr, a

stock_path:
	mov	dptr, #0xFF24
	ljmp	0xBE9A
