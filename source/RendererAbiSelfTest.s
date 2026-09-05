#ifdef RENDERER_ABI_SELF_TEST

	.global rendererAbiSentinelSelfTest
	.syntax unified
	.arm
	.section .text
	.align 2

;@ Return bit 0 for a misaligned C entry, bit 1 for SP corruption, and
;@ bits 4-11 for corrupted callee-saved registers r4-r11.
rendererAbiSentinelSelfTest:
	.type rendererAbiSentinelSelfTest STT_FUNC
	stmfd sp!,{r4-r11,lr}
	sub sp,sp,#4
	str sp,[sp]
	adr r0,rendererAbiSentinels
	ldmia r0,{r4-r11}
	bl rendererAbiSentinelCallback
	and r2,r0,#7
	ldr r0,[sp]
	cmp sp,r0
	orrne r2,r2,#2
	adr r0,rendererAbiSentinels
	ldr r1,[r0],#4
	cmp r4,r1
	orrne r2,r2,#1<<4
	ldr r1,[r0],#4
	cmp r5,r1
	orrne r2,r2,#1<<5
	ldr r1,[r0],#4
	cmp r6,r1
	orrne r2,r2,#1<<6
	ldr r1,[r0],#4
	cmp r7,r1
	orrne r2,r2,#1<<7
	ldr r1,[r0],#4
	cmp r8,r1
	orrne r2,r2,#1<<8
	ldr r1,[r0],#4
	cmp r9,r1
	orrne r2,r2,#1<<9
	ldr r1,[r0],#4
	cmp r10,r1
	orrne r2,r2,#1<<10
	ldr r1,[r0]
	cmp r11,r1
	orrne r2,r2,#1<<11
	mov r0,r2
	add sp,sp,#4
	ldmfd sp!,{r4-r11,pc}

	.align 2
rendererAbiSentinels:
	.long 0x44114411,0x55225522,0x66336633,0x77447744
	.long 0x88558855,0x99669966,0xAA77AA77,0xBB88BB88

#endif
