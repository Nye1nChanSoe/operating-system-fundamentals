        INP
        STA X

        INP
        STA Y

        LDA ZERO
        STA RESULT_X

        LDA X
        STA COUNT_X

LOOP_X  LDA COUNT_X
        BRZ DONE_X

        LDA RESULT_X
        ADD X
        STA RESULT_X

        LDA COUNT_X
        SUB ONE
        STA COUNT_X

        BRA LOOP_X

DONE_X  LDA ZERO
        STA RESULT_Y

        LDA Y
        STA COUNT_Y

LOOP_Y  LDA COUNT_Y
        BRZ DONE_Y

        LDA RESULT_Y
        ADD Y
        STA RESULT_Y

        LDA COUNT_Y
        SUB ONE
        STA COUNT_Y

        BRA LOOP_Y

DONE_Y  LDA RESULT_X
        ADD RESULT_Y
        OUT

        HLT


X         DAT 0
Y         DAT 0
RESULT_X  DAT 0
RESULT_Y  DAT 0
COUNT_X   DAT 0
COUNT_Y   DAT 0
ZERO      DAT 0
ONE       DAT 1