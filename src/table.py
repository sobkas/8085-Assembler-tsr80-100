bin_op = {
    '+',
    '-',
}

uni_op = {
    '+',
    '-'
}

mnm_0 = {
	'xchg',
	'xthl',
	'sphl',
	'pchl',
	'ret',
	'rc',
	'rnc',
	'rz',
	'rnz',
	'rp',
	'rm',
	'rpe',
	'rpo',
	'rlc',
	'rrc',
	'ral',
	'rar',
	'cma',
	'stc',
	'cmc',
	'daa',
	'ei',
	'di',
	'nop',
	'hlt',
	'rim',
	'sim',
}

mnm_0_e = {
    'adi': "data",
    'aci': "data",
    'sui': "data",
    'sbi': "data",
    'sta': "address",
    'lda': "address",
    'shld': "address",
    'lhld': "address",
    'jmp': "address",
    'jc': "address",
    'jnc': "address",
    'jz': "address",
    'jnz': "address",
    'jp': "address",
    'jm': "address",
    'jpe': "address",
    'jpo': "address",
    'call': "address",
    'cc': "address",
    'cnc': "address",
    'cz': "address",
    'cnz': "address",
    'cp': "address",
    'cm': "address",
    'cpe': "address",
    'cpo': "address",
    'in': "data",
    'out': "data",
    'ani': "data",
    'xri': "data", 
    'ori': "data",
    'cpi': "data",
}

mnm_1 = {
    'stax',
    'ldax',
    'push',
    'pop',
    'rst',
    'inr',
    'dcr',
    'inx',
    'dcx',
    'add',
    'adc',
    'dad', 
    'sub',
    'sbb',
    'ana',
    'xra',
    'ora',
    'cmp',
}

mnm_1_e = {
	'mvi': "data",
    'lxi': "address",
}

mnm_2 = {
	'mov',
}

drct_1 = {
	'org',
	'ds',
        'dm'
}

drct_p = {
	'db',
}

drct_w = {
	'equ'
}

reg = {
    'A',
    'B',
    'C',
    'D',
    'E',
    'H',
    'L',
    'SP',
    'PSW',
    'M',
    '0',
    '1',
    '2',
    '3',
    '4',
    '5',
    '6',
    '7'
}

reserved_mnm_0_e = {key for key in mnm_0_e}
reserved_mnm_1_e = {key for key in mnm_1_e}
reserved =  bin_op | uni_op | mnm_0 | reserved_mnm_0_e | mnm_1 | reserved_mnm_1_e | mnm_2 | drct_1 | drct_p | drct_w | reg 
