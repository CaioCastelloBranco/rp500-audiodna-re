; S3b source-base block.  Assembled at 0 and relocated to 0xE800.
; On entry (from the stock 0xBE9E) A = counter low, R6 = counter high.
;
; Both source bytes must be read before DPL is written: writing DPL changes
; DPTR, so an INC DPTR after that would no longer point at the high byte.

	.module s3b_source
	.optsdcc -m

	.area CSEG (CODE)

source:
	push	0x07
	push	0x05
	mov	r7, a
	mov	dptr, #0xF8E0
	movx	a, @dptr
	add	a, r7
	mov	r5, a
	inc	dptr
	movx	a, @dptr
	addc	a, r6
	mov	0x83, a
	mov	a, r5
	mov	0x82, a
	pop	0x05
	pop	0x07
	ljmp	0xBEA7
