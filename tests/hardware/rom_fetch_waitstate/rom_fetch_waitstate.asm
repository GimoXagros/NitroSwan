; WonderSwan cartridge ROM instruction-stream wait-state timing vector.
;
; This ROM deliberately measures both System Control $A0 states:
;   bit 2 = cartridge ROM width (1 = 16-bit)
;   bit 3 = cartridge ROM wait state (1 = +1 bus cycle)
;
; Results are HBlank scanline counts.  Run several times on real hardware;
; a one-line variation is expected because the timer has scanline resolution.

org 0x0000
cpu 186
bits 16

ROM_SEGMENT         equ 0xF000
MAP_BASE            equ 0x1800
TILE_BASE           equ 0x2000
STACK_TOP           equ 0x1000
RESULT_BASE         equ 0x0600
SYSTEM_CTRL_SAVED   equ 0x05F0

RAM_NOP_ADDR        equ 0x0800
RAM_ALU_ADDR        equ 0x0900
RAM_BRANCH_ADDR     equ 0x0A00

IO_DISPLAY_CTRL     equ 0x00
IO_CURRENT_LINE     equ 0x02
IO_BG_MAP           equ 0x07
IO_LCD_CTRL         equ 0x14
IO_LCD_ICONS        equ 0x15
IO_SYSTEM_CTRL      equ 0xA0
IO_TIMER_CTRL       equ 0xA2
IO_HBLANK_RELOAD    equ 0xA4
IO_HBLANK_COUNTER   equ 0xA8

SYSTEM_ROM_WIDTH_16 equ 0x04
SYSTEM_ROM_WAIT     equ 0x08
TEST_COUNT          equ 15

; Measure the same routine with wait state OFF and ON.  A taken CALL after the
; $A0 write flushes the V30MZ instruction prefetch before the timed routine.
%macro measure_pair 2
    mov al, [es:SYSTEM_CTRL_SAVED]
    and al, ~SYSTEM_ROM_WAIT
    out IO_SYSTEM_CTRL, al
    mov bx, %2
    call measure_one
    mov [es:RESULT_BASE + (%1 * 4)], ax

    mov al, [es:SYSTEM_CTRL_SAVED]
    or al, SYSTEM_ROM_WAIT
    out IO_SYSTEM_CTRL, al
    mov bx, %2
    call measure_one
    mov [es:RESULT_BASE + (%1 * 4) + 2], ax
%endmacro

start:
    cli
    cld

    mov ax, ROM_SEGMENT
    mov ds, ax
    xor ax, ax
    mov es, ax
    mov ss, ax
    mov sp, STACK_TOP

    ; Preserve model/cart/boot-lock bits, force a 16-bit ROM bus and begin
    ; with the ROM wait state disabled.
    in al, IO_SYSTEM_CTRL
    and al, 0xF3
    or al, SYSTEM_ROM_WIDTH_16
    mov [es:SYSTEM_CTRL_SAVED], al
    out IO_SYSTEM_CTRL, al

    call initialize_video
    call install_ram_benchmarks

    measure_pair 0,  benchmark_control
    measure_pair 1,  benchmark_ram_nop
    measure_pair 2,  benchmark_ram_alu
    measure_pair 3,  benchmark_ram_branch
    measure_pair 4,  benchmark_rom_nop
    measure_pair 5,  benchmark_rom_alu
    measure_pair 6,  benchmark_rom_immediate
    measure_pair 7,  benchmark_branch_taken
    measure_pair 8,  benchmark_jump_near
    measure_pair 9,  benchmark_branch_not_taken
    measure_pair 10, benchmark_call_ret
    measure_pair 11, benchmark_rom_byte_sequential
    measure_pair 12, benchmark_rom_word_sequential
    measure_pair 13, benchmark_rom_byte_nonsequential
    measure_pair 14, benchmark_rom_modrm_displacement

    mov al, [es:SYSTEM_CTRL_SAVED]
    out IO_SYSTEM_CTRL, al
    call render_results

.halt:
    hlt
    jmp .halt

; BX = near benchmark address, AX = elapsed HBlank scanlines.
measure_one:
    push bx
    call wait_for_new_frame

    xor ax, ax
    out IO_TIMER_CTRL, al
    mov ax, 0xFFFF
    out IO_HBLANK_RELOAD, ax
    mov al, 0x01
    out IO_TIMER_CTRL, al

    pop bx
    call bx

    in ax, IO_HBLANK_COUNTER
    push ax
    xor al, al
    out IO_TIMER_CTRL, al
    pop ax
    not ax
    ret

wait_for_new_frame:
.leave_line_zero:
    in al, IO_CURRENT_LINE
    test al, al
    jz .leave_line_zero
.wait_line_zero:
    in al, IO_CURRENT_LINE
    test al, al
    jnz .wait_line_zero
    ret

initialize_video:
    push ax
    push cx
    push si
    push di

    xor ax, ax
    mov di, MAP_BASE
    mov cx, 0x0400
    rep stosw

    mov si, font_data
    mov di, TILE_BASE
    mov cx, font_data_end - font_data
    rep movsb

    mov al, MAP_BASE >> 11
    out IO_BG_MAP, al
    mov al, 0x01
    out IO_LCD_CTRL, al
    xor al, al
    out IO_LCD_ICONS, al

    ; Eight monochrome shades and palette 0: color 0 light, color 1 dark.
    mov al, 00100000b
    out 0x1C, al
    mov al, 01100100b
    out 0x1D, al
    mov al, 10101000b
    out 0x1E, al
    mov al, 11111100b
    out 0x1F, al
    mov al, 00001111b
    out 0x20, al
    xor al, al
    out 0x21, al

    mov al, 0x01
    out IO_DISPLAY_CTRL, al

    pop di
    pop si
    pop cx
    pop ax
    ret

install_ram_benchmarks:
    mov si, ram_nop_blob
    mov di, RAM_NOP_ADDR
    mov cx, ram_nop_blob_end - ram_nop_blob
    rep movsb

    mov si, ram_alu_blob
    mov di, RAM_ALU_ADDR
    mov cx, ram_alu_blob_end - ram_alu_blob
    rep movsb

    mov si, ram_branch_blob
    mov di, RAM_BRANCH_ADDR
    mov cx, ram_branch_blob_end - ram_branch_blob
    rep movsb
    ret

; ---------------------------------------------------------------------------
; Benchmarks
; ---------------------------------------------------------------------------

align 2, db 0x90
benchmark_control:
    xor cx, cx
.loop:
    loop .loop
    ret

benchmark_ram_nop:
    call 0x0000:RAM_NOP_ADDR
    ret

benchmark_ram_alu:
    call 0x0000:RAM_ALU_ADDR
    ret

benchmark_ram_branch:
    call 0x0000:RAM_BRANCH_ADDR
    ret

align 2, db 0x90
benchmark_rom_nop:
    mov cx, 4096
.loop:
    times 32 nop
    loop .loop
    ret

align 2, db 0x90
benchmark_rom_alu:
    xor ax, ax
    mov bx, 1
    mov cx, 4096
.loop:
    times 16 add ax, bx
    loop .loop
    ret

align 2, db 0x90
benchmark_rom_immediate:
    xor ax, ax
    mov cx, 4096
.loop:
    times 8 add ax, 0x1234
    loop .loop
    ret

align 2, db 0x90
benchmark_branch_taken:
    xor ax, ax
    mov cx, 8192
.loop:
    test ax, ax
    jz .taken1
.taken1:
    jz .taken2
.taken2:
    jz .taken3
.taken3:
    jz .taken4
.taken4:
    loop .loop
    ret

align 2, db 0x90
benchmark_jump_near:
    mov cx, 8192
.loop:
    jmp near .jump1
.jump1:
    jmp near .jump2
.jump2:
    jmp near .jump3
.jump3:
    jmp near .jump4
.jump4:
    loop .loop
    ret

align 2, db 0x90
benchmark_branch_not_taken:
    xor ax, ax
    mov cx, 8192
.loop:
    test ax, ax
    jnz .never1
.never1:
    jnz .never2
.never2:
    jnz .never3
.never3:
    jnz .never4
.never4:
    loop .loop
    ret

align 2, db 0x90
benchmark_call_ret:
    mov cx, 8192
.loop:
    call .subroutine
    call .subroutine
    call .subroutine
    call .subroutine
    loop .loop
    ret
.subroutine:
    ret

align 2, db 0x90
benchmark_rom_byte_sequential:
    mov dx, 256
.outer:
    mov si, rom_data
    mov cx, 256
.inner:
    lodsb
    loop .inner
    dec dx
    jnz .outer
    ret

align 2, db 0x90
benchmark_rom_word_sequential:
    mov dx, 256
.outer:
    mov si, rom_data
    mov cx, 128
.inner:
    lodsw
    loop .inner
    dec dx
    jnz .outer
    ret

align 2, db 0x90
benchmark_rom_byte_nonsequential:
    mov dx, 256
    xor si, si
.outer:
    mov cx, 256
.inner:
    add si, 73
    and si, 0x00FF
    mov al, [rom_data + si]
    loop .inner
    dec dx
    jnz .outer
    ret

align 2, db 0x90
benchmark_rom_modrm_displacement:
    xor bx, bx
    mov si, rom_data
    mov cx, 16384
.loop:
    add bx, [si + 6]
    add bx, 0x1234
    loop .loop
    ret

; Position-independent RAM copies.  RETF returns to the ROM wrapper.
align 2, db 0x90
ram_nop_blob:
    mov cx, 4096
.loop:
    times 32 nop
    loop .loop
    retf
ram_nop_blob_end:

align 2, db 0x90
ram_alu_blob:
    xor ax, ax
    mov bx, 1
    mov cx, 4096
.loop:
    times 16 add ax, bx
    loop .loop
    retf
ram_alu_blob_end:

align 2, db 0x90
ram_branch_blob:
    xor ax, ax
    mov cx, 8192
.loop:
    test ax, ax
    jz .taken1
.taken1:
    jz .taken2
.taken2:
    jz .taken3
.taken3:
    jz .taken4
.taken4:
    loop .loop
    retf
ram_branch_blob_end:

; ---------------------------------------------------------------------------
; Result rendering
; ---------------------------------------------------------------------------

render_results:
    mov dh, 0
    mov dl, 0
    call set_cursor
    mov si, title_text
    call print_string

    mov dh, 1
    mov dl, 0
    call set_cursor
    mov si, header_text
    call print_string

    mov bp, RESULT_BASE
    mov bx, label_table
    mov dh, 2
    mov cx, TEST_COUNT
.line:
    push cx
    push bx

    mov dl, 0
    call set_cursor
    mov si, [bx]
    call print_string

    mov dl, 10
    call set_cursor
    mov ax, [es:bp]
    call print_hex4

    mov dl, 16
    call set_cursor
    mov ax, [es:bp + 2]
    call print_hex4

    mov dl, 23
    call set_cursor
    mov ax, [es:bp + 2]
    sub ax, [es:bp]
    call print_hex4

    add bp, 4
    inc dh
    pop bx
    add bx, 2
    pop cx
    loop .line
    ret

; DH = row, DL = column.  Returns ES:DI tile-map cursor.
set_cursor:
    push ax
    xor ax, ax
    mov al, dh
    shl ax, 6
    add ax, MAP_BASE
    mov di, ax
    xor ax, ax
    mov al, dl
    shl ax, 1
    add di, ax
    pop ax
    ret

print_string:
    lodsb
    test al, al
    jz .done
    xor ah, ah
    stosw
    jmp print_string
.done:
    ret

print_hex4:
    push ax
    push bx
    push cx
    push dx
    mov dx, ax
    mov cx, 4
.digit:
    rol dx, 4
    mov bx, dx
    and bx, 0x000F
    mov al, [hex_digits + bx]
    xor ah, ah
    stosw
    loop .digit
    pop dx
    pop cx
    pop bx
    pop ax
    ret

title_text  db "ROM FETCH WAITSTATE VECTOR", 0
header_text db "TEST      W0    W1     DELTA", 0
hex_digits db "0123456789ABCDEF"

label_table:
    dw label_control, label_ram_nop, label_ram_alu, label_ram_branch
    dw label_rom_nop, label_rom_alu, label_rom_immediate
    dw label_branch_taken, label_jump_near, label_branch_not_taken
    dw label_call_ret, label_byte_seq, label_word_seq, label_byte_nonseq
    dw label_modrm_disp

label_control      db "CONTROL", 0
label_ram_nop      db "RAM NOP", 0
label_ram_alu      db "RAM ALU", 0
label_ram_branch   db "RAM BR", 0
label_rom_nop      db "ROM NOP", 0
label_rom_alu      db "ROM ALU", 0
label_rom_immediate db "ROM IMM", 0
label_branch_taken db "BR TAKE", 0
label_jump_near    db "JMP NEAR", 0
label_branch_not_taken db "BR NOT", 0
label_call_ret     db "CALL RET", 0
label_byte_seq     db "BYTE SEQ", 0
label_word_seq     db "WORD SEQ", 0
label_byte_nonseq  db "BYTE RND", 0
label_modrm_disp   db "MODRM+IM", 0

align 2, db 0x00
rom_data:
%assign value 0
%rep 256
    db value
%assign value value + 1
%endrep

font_data:
    incbin "font.bin"
font_data_end:

; Build a 64 KiB final-bank payload. fix_checksum.py prepends the unused banks
; to produce the declared 1 MiB cartridge image.
times ((64 * 1024) - 16) - ($ - $$) db 0xFF

    db 0xEA                    ; far JMP reset vector
    dw start
    dw ROM_SEGMENT
    db 0x00
    db 0x42                    ; developer ID used by common homebrew tests
    db 0x00                    ; monochrome-compatible
    db 0x77                    ; test cartridge ID
    db 0x00                    ; revision
    db 0x03                    ; 1 MiB ROM
    db 0x00                    ; no save memory
    db 0x04                    ; horizontal orientation, no RTC
    db 0x00
    dw 0x0000                  ; patched by fix_checksum.py
