	.arch armv8-a
	.file	"sumsq.c"
	.text
	.align	2
	.global	square
	.type	square, %function
square:
.LFB0:
	.cfi_startproc
	sub	sp, sp, #16
	.cfi_def_cfa_offset 16
	str	s0, [sp, 12]
	ldr	s0, [sp, 12]
	fmul	s0, s0, s0
	add	sp, sp, 16
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE0:
	.size	square, .-square
	.align	2
	.global	sum_squares
	.type	sum_squares, %function
sum_squares:
.LFB1:
	.cfi_startproc
	stp	x29, x30, [sp, -48]!
	.cfi_def_cfa_offset 48
	.cfi_offset 29, -48
	.cfi_offset 30, -40
	mov	x29, sp
	str	d8, [sp, 16]
	.cfi_offset 72, -32
	str	s0, [sp, 44]
	str	s1, [sp, 40]
	ldr	s0, [sp, 44]
	bl	square
	fmov	s8, s0
	ldr	s0, [sp, 40]
	bl	square
	fadd	s0, s8, s0
	ldr	d8, [sp, 16]
	ldp	x29, x30, [sp], 48
	.cfi_restore 30
	.cfi_restore 29
	.cfi_restore 72
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE1:
	.size	sum_squares, .-sum_squares
	.section	.rodata
	.align	3
.LC0:
	.string	"%f\n"
	.text
	.align	2
	.global	main
	.type	main, %function
main:
.LFB2:
	.cfi_startproc
	stp	x29, x30, [sp, -16]!
	.cfi_def_cfa_offset 16
	.cfi_offset 29, -16
	.cfi_offset 30, -8
	mov	x29, sp
	fmov	s1, 1.0e+1
	fmov	s0, 2.0e+0
	bl	sum_squares
	fcvt	d0, s0
	adrp	x0, .LC0
	add	x0, x0, :lo12:.LC0
	bl	printf
	mov	w0, 0
	ldp	x29, x30, [sp], 16
	.cfi_restore 30
	.cfi_restore 29
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE2:
	.size	main, .-main
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
