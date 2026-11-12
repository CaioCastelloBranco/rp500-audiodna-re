; S3b cabinet-conditional IR gate.  Assembled at 0 and relocated to 0xE095.
; All internal branches are relative; all absolute jumps are explicit.
;
; Decision order matters: at counter == 0 the length cell is still zero, so
; the first-byte path must set it before any length comparison.

	.module s3b_gate_scan_neg
	.optsdcc -m

	.area CSEG (CODE)

gate:
	;; read the 16-bit byte counter at 0xFF24/0xFF25
	mov	dptr, #0xFF24
	movx	a, @dptr
	mov	r6, a
	inc	dptr
	movx	a, @dptr
	mov	r7, a

	mov	a, r6
	orl	a, r7
	jz	first_byte

	;; not the first byte: counter == length ?
	mov	dptr, #0xF8E2
	movx	a, @dptr
	xrl	a, r7
	jnz	stock_path
	inc	dptr
	movx	a, @dptr
	xrl	a, r6
	jnz	stock_path

	;; length reached: optional 0xF5 terminator, then the stock epilogue
	mov	dptr, #0xF8E4
	movx	a, @dptr
	jz	epilogue
	mov	dptr, #0xD070
	mov	a, #0xF5
	movx	@dptr, a
epilogue:
	ljmp	0xBEB0

first_byte:
	sjmp	test_write
do_scan:
	;; scan 100 3-byte cells at 0xF6AA for 00 02 49
	push	0x05
	mov	dptr, #0xF6AA
	mov	r5, #100
scan:
	movx	a, @dptr
	cjne	a, #0x00, scan_next3
	inc	dptr
	movx	a, @dptr
	cjne	a, #0x02, scan_skip2
	inc	dptr
	movx	a, @dptr
	cjne	a, #0x49, scan_skip1

	;; found: IR table 0xE200, length 512, flag 1
	pop	0x05
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
	sjmp	stock_path

scan_skip1:			; DPTR at cell+2
	inc	dptr
	djnz	r5, scan
	sjmp	not_found
scan_skip2:			; DPTR at cell+1
	inc	dptr
	inc	dptr
	djnz	r5, scan
	sjmp	not_found
scan_next3:			; DPTR at cell+0
	inc	dptr
	inc	dptr
	inc	dptr
	djnz	r5, scan

not_found:
	pop	0x05
	;; stock descriptor 0x2E3B, length 24, flag 0
	mov	dptr, #0xF8E0
	mov	a, #0x3B
	movx	@dptr, a
	inc	dptr
	mov	a, #0x2E
	movx	@dptr, a
	mov	dptr, #0xF8E2
	mov	a, #0x18
	movx	@dptr, a
	inc	dptr
	mov	a, #0x00
	movx	@dptr, a
	mov	dptr, #0xF8E4
	mov	a, #0x00
	movx	@dptr, a

stock_path:
	mov	dptr, #0xFF24
	ljmp	0xBE9A

test_write:
	;; SIMULATOR-ONLY test write: cab value at 0xF6AA
	mov	dptr, #0xF6AA
	mov	a, #0x00
	movx	@dptr, a
	inc	dptr
	mov	a, #0x02
	movx	@dptr, a
	inc	dptr
	mov	a, #0x48
	movx	@dptr, a
	sjmp	do_scan
