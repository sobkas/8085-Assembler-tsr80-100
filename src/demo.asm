;*********************************************************************************          
; Robot Pet Obstacle Avoidance Program                                           *
;                                                                                *
; Ezra Thomas                                                                    *
;*********************************************************************************

            mvi A, 00       ; Setup timer B
            out 44

            mvi A, 42       ; Setup timer B
            out 45

            mvi A, CE       ; Start timer B and set up port BB and BC to OUTPUT
            out 40

            mvi A, 02       ; Enable front sonar
            out 43

            lxi SP, 40FF    ; Set stack pointer

            jmp PRE

            org 44
PRE:        mvi A, 0C       ; Set Servo Port to OUTPUT
            out 00

            mvi A, 20       ; Center Shaft
            out 03

CENTER:     in 41           ; Wait until shaft is centered
            ani 08
            jz CENTER

START:      mvi A, 21       ; Move shaft forward and drive
            out 03

            mvi A, 02       ; Enable front sonar
            out 43

PING_POLL:  call SUB_PING   ; Poll for obstical
            cpi 4F
            jnc PING_POLL

            mvi A, 20       ; Stop
            out 03

            mvi A, 01       ; Enable left sonar
            out 43
            call SUB_PING   ; Read left distance
            mov L,A         ; Store left distance in L

            mvi A, 03       ; Enable right sonar
            out 43
            call SUB_PING   ; Read right distance

            cmp L           ; Compare right distance to left distance
            jc LEFT         ; Turn left if there is more room to the left
            jz FLIP         ; Turn left or right if distances are equal

            mvi A, 3C           ; Turn shaft right
            out 03
            jmp TURN

LEFT:       mvi A, 00           ; Turn shaft left
            out 03
            jmp TURN

FLIP:       lda TurnDir
            xri 3C
            sta TurnDir
            out 03

TURN:       in 41               ; Wait for shaft to finish turning
            ani 08
            jz TURN

            in 03               ; Turn on drive motor to turn
            inr A
            out 03

            call SUB_TURN_DELAY ; Wait for turn to finish 
            jmp START           ; Loop back to START

SUB_PING:   ; Ping subroutine
            call SUB_DELAY  ; Rest delay
            lxi B, 800A     ; Setup timeout timer
            call SUB_TMR

POLL:       in 41           ; Poll for echo or timout
            ani 05
            cpi 05
            jz POLL

            cpi 01          ; If timout reached jump to set max distance
            jz CLEAR

            in 44           ; If echo, calculate distance
            mov B,A
            mvi A, FF
            sub B
            jmp WRITE

CLEAR:      mvi A, FF       ; Set distance to max if no object detected

WRITE:      out 42          ; Write distance to LED readout
            ret             ; Return, note that distance is in A

SUB_TMR:    mov A,B         ; Timer subroutine
            out 05
            mov A,C
            out 04
            mvi A, CC
            out 00
            ret             ; Return

SUB_DELAY:  lxi B,0C37      ; Delay subroutine for PING refresh (50ms)
DELAYLoop:  dcx B
            mov A,B
            ora C
            jnz DELAYLoop
            ret             ; Return

SUB_TURN_DELAY: 
            mvi B, 08       ; Delay subroutine for turning (2s)
LOOP1:      mvi C, D6
LOOP2:      mvi D, 7C
LOOP3:      dcr D
            jnz LOOP3
            dcr C
            jnz LOOP2
            dcr B
            jnz LOOP1
            ret             ; Return

            org F4          
TurnDir:    db 3C
