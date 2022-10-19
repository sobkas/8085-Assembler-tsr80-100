# 8085-Assembler

A simple Python based 8085 assembler.

## Usage
```
usage: assembler.py [-h] [-L] [-A] [-B] [-I] [-H] [-C] [-s] [-b] [-t] [-o OUT] source

A simple 8085 assembler.

positional arguments:
  source             source file

options:
  -h, --help         show this help message and exit
  -L, --lineNum      include the line number in output
  -A, --address      include the address in output
  -B, --label        include the labels in output
  -I, --instruction  include the instructions and arguments in output
  -H, --hex          include the hex code in output
  -C, --comment      include the comments in output
  -s, --standard     equivalent to -A -B -I -H -C
  -b, --bin          outputs only binary data
  -t, --trs100       creates basic loader for TRS-80 Model 100
  -o OUT, --out OUT  output file name (stdout, if not specified)
  ```
## Source File Syntax
The assembler is case sensitive.

### Comments
Comments begin with semicolons.
```asm
mvi A, 0x5C ; This is a comment
```

### Constants
8 and 16-bit constants are given in hex. 8-bit constants must have two digits, and 16-bit constants must have 4-digits.
```asm
mvi A, 0x0C
mvi A, 0C   ; The "0x" is optional
mvi A, 'a'  ; letters can be used as input, usage is ascii
mvi A, 7    ; Illegal. 8-bit constants must have two digits

lxi H, 0x03B7
lxi H, 03B7    ; The "0x" is optional
lxi H, 3B7     ; Illegal. 16-bit constants must have four digits
```
If an 8-bit constant is given where a 16-bit constant is expected, the 8-bit constant will be converted to a 16-bit constant, with the upper 8-bits all zero.
```asm
jnz 0x3FC7  ; Jump-not-zero to 0x3FC7
jmp FF      ; JMP takes a 16-bit argument, but given 8-bits. Will JMP to 0x00FF
```

### Label Definitions
Label definitions may be any string ending with a colon, where the string does not match the pattern of an 8 or 16-bit constant.

```asm
  ; Example
  ;*******************************************************************************
        mvi A, 0x5C
  Foo:  dcr A         ; Label definition
        jnz Foo       ; Jump-not-zero to Foo
  ;*******************************************************************************
        mvi A, 0x5C
  FD:   dcr A         ; Illegal. Label definition cannot match hex constant format
        jnz FD
```
### Directives
#### org <16-bit-address>
Sets the origin to the given address. Only forward movement of the origin is permitted.
```asm
; Example
;*******************************************************************************
        mvi A, 55
        out 42
        jmp Start
 Start: org 0x44
        mvi A, 32
        out 42
;*******************************************************************************
; Assembles to the following:

Address             Label               Instruction         Hex Code            
--------------------------------------------------------------------------------
0x0000                                  mvi A, 55           0x3E                
0x0001                                                      0x55                
0x0002                                  out 42              0xD3                
0x0003                                                      0x42                
0x0004                                  jmp START           0xC3                
0x0005                                                      0x44                
0x0006                                                      0x00                
0x0044              START:              mvi A, 32           0x3E                
0x0045                                                      0x32                
0x0046                                  out 42              0xD3                
0x0047                                                      0x42  
```
```asm
; Example
;*******************************************************************************
      org 0x44
      mvi A, C7
      out 44
      org 0x00      ; Illegal. Cannot move origin backwards
      jmp 0x0044
```

#### DB <8-bit-data>, ...
Writes one or more data bytes sequentially into memory.
```asm
; Example
;***********************************************************
      mvi A, 33
      db     0x44, 0xFE, 0x9C
      hlt
;***********************************************************
; Assembles to the following:

Address             Instruction         Hex Code            
------------------------------------------------------------
0x0000              mvi A, 33           0x3E                
0x0001                                  0x33                
0x0002              db                  0x44                
0x0003              db                  0xFE                
0x0004              db                  0x9C                
0x0005              hlt                 0x76  
```

#### DM "<8char><8char>...
Writes one or more char bytes sequentially into memory. At the end 0x00 can be added with \0.
Some of the ASCIIZ control charactgers are supported.
```asm
; Example
;***********************************************************
      mvi A, 33
      dm "Hello\0"
      hlt
;***********************************************************
; Assembles to the following:

Address             Instruction         Hex Code            
------------------------------------------------------------
0x0000              mvi A, 33           0x3E                
0x0001                                  0x33                
0x0002              dm                  0x48                
0x0003              dm                  0x65                
0x0004              dm                  0x6C                
0x0005              dm                  0x6C                
0x0006              dm                  0x6F                
0x0007              dm                  0x00                
0x0008              hlt                 0x76                
```

#### \<symbol> EQU <8 or 16-bit number>
Equates a symbol with a number.
```asm
; Example
;***********************************************************
      foo equ 0xC5F3
      mvi A,  33
      lxi H,  foo
;***********************************************************
; Assembles to the following:

Address             Instruction         Hex Code            
------------------------------------------------------------
0x0000              mvi A, 33           0x3E                
0x0001                                  0x33                
0x0002              lxi H, FOO          0x21                
0x0003                                  0xF3                
0x0004                                  0xC5      
```
#### DS <8 or 16-bit number>
Defines and reserves the next n-bytes for storage.
```asm
; Example
;*******************************************************************************
            jmp END 
Storage:    ds  0x05
            lda Storage
END:        out 42
;*******************************************************************************
; Assembles to the following:

Address             Label               Instruction         Hex Code            
--------------------------------------------------------------------------------
0x0000                                  jmp END             0xC3                
0x0001                                                      0x0B                
0x0002                                                      0x00                
0x0008              STORAGE:            lda STORAGE         0x3A                
0x0009                                                      0x03                
0x000A                                                      0x00                
0x000B              END:                out 42              0xD3                
0x000C                                                      0x42              
```

## Expressions
Anytime an instruction or directive requires a numerical argument, an expression can be used. Supported operations inside expressions include addition and subtraction. The location counter $ is also made available. Expressions may contain symbols, but must resolve within two passes of the assembler, and if used for directive arguments, must resolve in a single pass. All expressions must evaluate to a positive number.
```asm
; Example with expression resolution in one pass.
;***********************************************************
      foo    equ   10
      mvi A, foo - 04
;***********************************************************
; Assembles to the following:

Address             Instruction         Hex Code            
------------------------------------------------------------
0x0000              mvi A, FOO - 04     0x3E                
0x0001                                  0x0C     

```
```asm
; Example with expression resolution in two passes.
;***********************************************************
      mvi A, foo + 04
      foo    equ   30
;***********************************************************
; Assembles to the following:

Address             Instruction         Hex Code            
------------------------------------------------------------
0x0000              mvi A, FOO + 04     0x3E                
0x0001                                  0x34
```
```asm
; Example with expression resolution in two passes, and $
;***********************************************************
      mvi A,  55
      jmp $ + foo
      foo equ 05
      db  $,  $ + 01, $ + foo
      ds  02
      hlt
;***********************************************************
; Assembles to the following:

Address             Instruction         Hex Code            
------------------------------------------------------------
0x0000              mvi A, 55           0x3E                
0x0001                                  0x55                
0x0002              jmp $ + FOO         0xC3                
0x0003                                  0x07                
0x0004                                  0x00                
0x0005              db                  0x05                
0x0006              db                  0x07                
0x0007              db                  0x0C                
0x000A              hlt                 0x76    
```
