        org 0xF6AF
display equ 0x5A58
read    equ 0x12CB
menu    equ 0x5797 
start:  lxi H, message
        call display
        call read
        cpi '\r'
        jz start
        jmp menu
        
message:        dm "Hello, World!\\0\n\r\0"

