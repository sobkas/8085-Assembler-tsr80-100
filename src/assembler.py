#!/usr/bin/env python
# Notes:
# -> Add decimal and binary base functionality
##############################################################################################################
import re
import sys
import argparse
import table
import instructions
import binascii
import os

##############################################################################################################
# Support Classes

class Symbol:

    def __init__(self):
        self.labelDefs = {}
        self.eightBitDefs = {}
        self.sixteenBitDefs = {}
        self.expr = []

class Code:

    def __init__(self):
        self.data = []
        self.address = 0
        self.label = ""

    def write(self, data, line, instrct = ""):
        # Format: [line] [lineNumStr] [address] [label] [instruction + argument] [hex code] [comment]

        if(self.address > 65535):
            error("Cannot write past 0xFFFF. Out of memory!",line)
            sys.exit(2)

        addressStr = '0x{0:0{1}X}'.format(self.address,4)

        if(data != "expr"):
            data = '0x{0:0{1}X}'.format(data,2)

        comment = ''
        lineNumStr = ''
        pc = line[0][1]
        if(len(self.data) == 0 or pc != self.data[-1][0][0][1]):
            comment = line[2]
            lineNumStr = str(line[0][0])

        self.data.append([line, lineNumStr, addressStr, self.label, instrct, data, comment])
        self.address += 1
        self.label = ""

    def update(self, data, index):
        self.data[index][5] = '0x{0:0{1}X}'.format(data,2)

##############################################################################################################
# File reading functions

def read(name):
    # This function reads in lines from the asm file
    # It processes them and puts them into the form:
    # [[Line_number, Program_Counter] [body] [comment]]
    # Line_number corrisponds to the line on the 
    # source code. the Program_Counter is incremented
    # every time there is a non-empty line. Note that
    # two consecutive PC locations do NOT nessisarily
    # corrispond to two consecutive address locations

    # [[Line_number, Program_Counter] [body] 'comment']
    
    file = open(name, 'r')
    lines = []
    lineNumber = 0
    pc = 0
    
    for lineNumber, line in enumerate(file, start = 1):
        line = line.strip()
        if(line):
            block = []
            rest = []
            comment = ''
            commentIndex = line.find(";")
            if(commentIndex != -1):
                comment = line[commentIndex:]
                rest = line[:commentIndex].strip()
            else:
                rest = line

            block.append([lineNumber, pc])
            if(rest):
                split_rest = re.split(r'([-+,\s]\s*)', rest)
                split_rest = [word for word in split_rest if not re.match(r'^\s*$',word)]
                split_rest = list(filter(None, split_rest))
                block.append(split_rest)
            else:
                block.append([])
            block.append(comment)
            lines.append(block)
            pc += 1

    file.close()
    return lines

##############################################################################################################
# Utility functions

def error(message, line):
    print("Error at line " + str(line[0][0]) + ": " + message)

def output(code, name, args):
    # Format: [line] [lineNumStr] [address] [label] [instruction + argument] [hex code] [comment]
    if args.bin:
        f = open(name,'wb') if name else sys.stdout
    else:
        f = open(name,'w') if name else sys.stdout

    width = 0
    bin = bytes()
    if args.bin:
        width = 1
    
    if args.lineNum:
        print('{:<15}'.format("Line number"),file=f,end='')
        width += 15
    if args.address:
        print('{:<10}'.format("Address"),file=f,end='')
        width += 10
    if args.hex:
        print('{:<10}'.format("Hex Code"),file=f,end='')
        width += 10
    if args.label:
        print('{:<30}'.format("Label"),file=f,end='')
        width += 30
    if args.instruction:
        print('{:<30}'.format("Instruction"),file=f,end='')
        width += 30
    if args.comment:
        print('{:<20}'.format("Comment"),file=f,end='')
        width += 20

    if not args.bin:
        print("",file=f)
    
    for i in range(0,width):
        if not args.bin:
            print("-",file=f,end='')

    if not args.bin:
        print("",file=f)

    if width:
        for l in code.data:
            if args.lineNum:
                print('{:<15}'.format(l[1]),file=f,end='')
            if args.address:
                print('{:<10}'.format(l[2]),file=f,end='')
            if args.hex:
                print('{:<10}'.format(l[5]),file=f,end='')
            if args.label:
                print('{:<30}'.format(l[3]),file=f,end='')
            if args.instruction:
                print('{:<30}'.format(l[4]),file=f,end='')
            if args.bin:
               bin += binascii.unhexlify(l[5].split('x')[1])
            if args.comment:
                print('{:<20}'.format(l[6]),file=f,end='')
            if not args.bin:
                print("",file=f)

        if args.bin:
            f.write(bin)

    if f is not sys.stdout:
        f.close()

def output_basic(code, name, args):
    # Format: [line] [lineNumStr] [address] [label] [instruction + argument] [hex code] [comment]
    f = open(name,'w') if name else sys.stdout
    if name:
        simName = os.path.basename(name).split('.')[0]
    else:
        simName = 'deflt'

    address = code.data[0][2]
    length = len(code.data)
    print("1 CLS:?\"Loading Machine Code File", file=f)
    print(f"2 FORN={int(address,16)}TO{int(address, 16)+length}:READA:POKEN,A:NEXT", file=f)
    print(f"3 ?\"Don't forget to run clear 256,{int(address,16)}", file=f)
    if args.trs100_save:
      print(f"4 SAVEM\"{simName}.CO\",{int(address,16)},{int(address,16)+length},{int(address,16)}", file=f)
    if args.trs100_new:
      print(f"5 NEW", file=f)

    # Break code.data into 40 numbers each, so the line length doesn't get too long
    n=40
    # Taken from https://www.geeksforgeeks.org/break-list-chunks-size-n-python/
    chunks = [code.data[i * n:(i + 1) * n] for i in range((len(code.data) + n - 1) // n )]

    # BASIC line number
    linenum = 6
    for chunk in chunks:
        # Convert each datum from hex to decimal.
        decimal_string_list=[f"{int(datum[5],16)}" for datum in chunk]
        linedata = ','.join(decimal_string_list)
        print(f"{linenum} DATA {linedata}", file=f)
        linenum += 1
    # End with a zero
    print(f"{linenum} DATA 0", file=f)
    print(f"Size: {length} bytes")

    if f is not sys.stdout:
        f.close()

class myord:
    control = 0
    def ord(self, ch):
        if ch == '\\':
            self.control += 1
        elif self.control == 2:
            self.control = 0
            return [0x5C, ord(ch)]
        elif self.control == 1:
            self.control = 0
            return [table.controlchars['\\'+ch]]
        else:
            return [ord(ch)]

##############################################################################################################
# Directive functions
def org(arg, symbols, code, line):
    val = evaluate(arg, symbols, code.address)
    if(len(val) == 1):
        num = val[0]
        if(num < 0):
            error("Expression must be positive!",line)
            return 0
        elif(num < code.address):
            error("Cannot move origin backwards!",line)
            return 0
        elif(num > 65535):
            error("Cannot set origin past 0xFFFF!",line)
            return 0
        else:
            code.address = num
            if(code.label):
                symbols.labelDefs[code.label[:-1]] = '{0:0{1}X}'.format(num,4)
            return 1
    else:
        error("Expression depends on unresolved symbol!",line)
        return 0

def db(args, symbols, code, line):
    for expr in args:
        val = evaluate(expr, symbols, code.address)
        if(len(val) == 1):
            num = val[0]
            if(num < 0):
                error("Expression must be positive!",line)
                return 0
            elif(num > 255):
                error("Expression too large! Must evaluate to an 8-bit number!", line)
                return 0
            else:
                code.write(num,line,instrct="db")
        else:
            error("Expression depends on unresolved symbol!",line)
            return 0
    return 1

def dm(args, symbols, code, line):
    ords = myord()

    for expr in args:
        val = evaluate(expr, symbols, code.address)
        if(val[0] in {'<08str>'}):
            val_string = val[1].replace("\"","")
            for num in map(ords.ord, val_string):
                if num != None:
                    for i in num:
                        if i > 255:
                            error("Expression too large! Must evaluate to an 8-bit number!", line)
                            return 0
                        elif i < 0:
                            error("Expression must be positive!",line)
                            return 0
                        else:
                            code.write(i, line,instrct="dm")
                else:
                    pass
        else:
            error("Expression depends on unresolved symbol!",line)
            return 0
    return 1

def equ(args, symbols, code, line):
    name = args[0][1]
    if(name in table.reserved):
        error("Cannot use reserved keyword in equ directive!",line)
        return 0
    elif(name in (symbols.eightBitDefs, symbols.sixteenBitDefs)):
        error("Symbol already defined!",line)
        return 0
    elif(name in symbols.labelDefs):
        error("Symbol conflicts with previous label definition!",line)
        return 0

    val = evaluate(args[1], symbols, code.address)
    if(len(val) == 1):
        num = val[0]
        if num > 65535:
            error("Expression evaluates to value greater than 0xFFFF!",line)
            return 0
        elif num > 255:
            symbols.sixteenBitDefs[name] = '{0:0{1}X}'.format(num,4)
            return 1
        elif num >= 0:
            symbols.eightBitDefs[name] = '{0:0{1}X}'.format(num,2)
            return 1
        else:
            error("Expression must be positive!",line)
            return 0
    else:
        error("Expression depends on unresolved symbol!",line)
        return 0

def ds(arg, symbols, code, line):
    val = evaluate(arg, symbols, code.address)
    if(len(val) == 1):
        num = val[0]
        if(num < 0):
            error("Expression must be positive!",line)
            return 0
        elif(num + code.address > 65536):
            error("Cannot define that much storage! Only " + str((65536 - code.address)) + 
                  " bytes left. Overflow by " + str(num + code.address - 65536) + ".",line)
            return 0
        else:
            code.address += num
            return 1
    else:
        error("Expression depends on unresolved symbol!",line)
        return 0

directives = {
    #Format:
    # [function, min_args, max_args, name]
    # -1 means no bound
    "org": [org, 1, 1, "org"],
    "db":  [db, 1, -1, "db"],
    "equ": [equ, 2, 2, "equ"],
    "ds":  [ds, 1, 1, "ds"],
    "dm":  [dm, 1, 1, "dm"],
}
     
def secondPass(symbols, code):
    # Format: [line] [lineNumStr] [address] [label] [instruction + argument] [hex code] [comment]
    i = 0
    address = 0
    while i < len(code.data):
        codeLine = code.data[i]
        line = codeLine[0]
        data = codeLine[5]
        if(data == "expr"):
            expr, kind  = symbols.expr.pop(0)
            val = evaluate(expr, symbols, address)
            if(len(val) == 1):
                numb = val[0]
                if(numb < 0):
                    error("Expression must be positive!",line)
                    return 0
                elif(kind == "data"):
                    if(numb > 255):
                        error("Expression must evaluate to 8-bit number!",line)
                        return 0
                    else:
                        code.update(numb,i)
                elif(kind == "address"):
                    if(numb > 65535):
                        error("Expression must evaluate to 16-bit number!",line)
                        return 0
                    else:
                        code.update((numb & 0xff),i)
                        code.update((numb >> 8),i+1)
                        i += 1
            else:
                error("Expression relies on unresolved symbol!",line)
                return 0
        else:
            address = int(codeLine[2], base=16) 
        i += 1

def lexer(lines):
    tokens = []
    buildString = False
    buildedString = ""
    code_lines = [x for x in lines if len(x[1])]
    for line in code_lines:
        tl = []
        for wordstr in line[1]:
            word = wordstr.strip()
            if word in table.mnm_0:
                tl.append(["<mnm_0>", word])
            elif('"' in wordstr and buildString):
                buildString = False
                buildedString +=wordstr
                tl.append(["<08str>", buildedString])
                buildedString = ""
                continue
            elif(buildString):
                buildedString += wordstr
                continue
            elif(re.match(r'^\"', word)):
                buildString = True
                buildedString = wordstr
                continue
            elif(re.match(r'^\'', word)):
                tl.append(["<08ch>", word])
            elif(re.match(r'^(0[Xx])?[0-9A-Fa-f]{2}$', word)):
                tl.append(["<08nm>", word])
            elif word in table.mnm_0_e:
                tl.append(["<mnm_0_e>", word])
            elif word in table.mnm_1:
                tl.append(["<mnm_1>", word])
            elif word in table.mnm_1_e:
                tl.append(["<mnm_1_e>", word])
            elif word in table.mnm_2:
                tl.append(["<mnm_2>", word])
            elif word in table.reg:
                tl.append(["<reg>", word])
            elif word == ",":
                tl.append(["<comma>", word])
            elif word == "+":
                tl.append(["<plus>", word])
            elif word == "-":
                tl.append(["<minus>", word])
            elif word in table.drct_1:
                tl.append(["<drct_1>", word])
            elif word in table.drct_p:
                tl.append(["<drct_p>", word])
            elif word in table.drct_w:
                tl.append(["<drct_w>", word])
            elif re.match(r'^.+:$',word):
                tl.append(["<lbl_def>", word])
            elif(re.match(r'^(0[Xx])?[0-9A-Fa-f]{4}$', word)):
                tl.append(["<16nm>", word])
            elif(re.match(r'^[A-Za-z_]+[A-Za-z0-9_]*$', word)):
                tl.append(["<symbol>", word])
            elif word == "$":
                tl.append(["<lc>", word])
            else:
                tl.append(["<idk_man>", word])
                error("Unknown token: " + word, line)
                return [0 , 0]

        tokens.append(tl)

    return [code_lines, tokens]
######################################################################################
def evaluate(expr, symbols, address):
    sign, pop, result = 1, 2, 0
    while(expr):
        ###################################
        if(len(expr) >= 2):
            pop = 2
            if(expr[-2][0] == "<plus>"):
                sign = 1
            else:
                sign = -1
        else:
            pop = 1
            sign = 1
        ###################################
        if(expr[-1][0] in {"<08nm>", "<16nm>", "<numb>"}):
            result += sign*int(expr[-1][1], base=16)
            expr = expr[:-pop]
        elif(expr[-1][0] in {"<08ch>"}):
            chars = expr[-1][1].replace("'","")
            if len(chars) == 1:
                result += ord(chars)
            if len(chars) == 2:
                result += table.controlchars[chars]
            expr = expr[:-pop]
        elif(expr[-1][0] == "<lc>"):
            result += sign*(address)
            expr = expr[:-pop] 
        else:
            if(expr[-1][1] in symbols.eightBitDefs):
                result += sign*int(symbols.eightBitDefs[expr[-1][1]], base=16)
                expr = expr[:-pop]
            elif(expr[-1][1] in symbols.sixteenBitDefs):
                result += sign*int(symbols.sixteenBitDefs[expr[-1][1]], base=16)
                expr = expr[:-pop]
            elif(expr[-1][1] in symbols.labelDefs):
                result += sign*int(symbols.labelDefs[expr[-1][1]], base=16)
                expr = expr[:-pop]
            else:
                expr += [["<plus>", "+"],["<numb>", hex(result)]]
                return expr
        ###################################
    return [result]

######################################################################################
# Grammar:
#
# <line> ::= <lbl_def> [<drct>] [<code>]
#          | <drct> [<code>]
#          | <code>
#
# <code> ::= <mnm_0>
#          | <mnm_0_e> <expr>
#          | <mnm_1> <reg>
#          | <mnm_1_e> <reg> "," <expr>
#          | <mnm_2> <reg> "," <reg>
#
# <expr> ::= [ (<plus> | <minus>) ] <numb> { (<plus> | <minus>) <numb> }
#
# <drct> ::= <drct_1> <expr>
#          | <drct_p> <expr> { ","  <expr> }
#          | <symbol> <drct_w> <expr>
#
# <numb> ::= <08nm> | <16nm> | <symbol> | <lc>
######################################################################################
def parse(lines, symbols, code):

    code_lines, tokenLines = lexer(lines)
    if(code_lines == 0):
        sys.exit(1)

    tree = []

    for tokens, line in zip(tokenLines, code_lines):
        parsed_line = parse_line(tokens, symbols, code, line)
        if(parsed_line[0] == "<error>"):
            sys.exit(1)
        tree.append(parsed_line)

    status = secondPass(symbols, code)
    if(status == 0):
        sys.exit(1)
######################################################################################
def parse_expr(tokens, symbols, code, line):
    data = ["<expr>"]
    er = ["<error>"]
    if not tokens:
        return 0
    ##################################################
    while(tokens):
        if(tokens[0][0] in {"<plus>", "<minus>"}):
            data.append(tokens.pop(0))
        elif(len(data) > 1):
            return data
        if(len(data) > 1 and (not tokens)):
            error("Expression missing number/symbol!",line)
            return er
        if(tokens[0][0] not in {"<08str>", "<08ch>", "<08nm>", "<16nm>", "<symbol>", "<lc>"}):
            if(tokens[0][0] not in {"<plus>", "<minus>"}):
                if(len(data) > 1):
                    error("Expression has bad identifier!",line)
                    return er
                else:
                    return 0
            else:
                error("Expression has extra operator!",line)
                return er
        tok = tokens.pop(0)
        data.append(tok)
    return data
######################################################################################
def parse_lbl_def(tokens, symbols, code, line):
    er = ["<error>"]
    if not tokens:
        return 0
    if(tokens[0][0] == "<lbl_def>"):
        lbl = tokens[0][1]
        if lbl[:-1] in symbols.labelDefs:
            error("Label already in use!",line)
            return er
        elif lbl[:-1] in table.reserved:
            error("Label cannot be keyword!",line)
            return er
        elif(re.match(r'^(0[Xx])?[0-9A-Fa-f]{2}$', lbl[:-1]) or
             re.match(r'^(0[Xx])?[0-9A-Fa-f]{4}$', lbl[:-1])):
            error("Label cannot be hex number!",line)
            return er
        elif lbl[:-1] in (symbols.eightBitDefs, symbols.sixteenBitDefs):
            error("Label conflicts with previous symbol definition",line)
            return er
        else:
            symbols.labelDefs[lbl[:-1]] = '{0:0{1}X}'.format(code.address,4)
            code.label = lbl
        return tokens.pop(0)
    else:
        return 0

######################################################################################
def parse_drct(tokens, symbols, code, line):
    args = [tokens, symbols, code, line]
    data = ["<drct>"]
    er = ["<error>"]
    if not tokens:
        return 0
    ##################################################
    # [drct_1]
    if(tokens[0][0] == "<drct_1>"):
        data.append(tokens.pop(0))
        if(not tokens):
            error("Directive missing argument!",line)
            return er
        expr = parse_expr(*args)
        if(not expr):
            error("Directive has bad argument A!", line)
            return er
        if(expr == er):
            return er
        data.append(expr)
        arg = data[2][1:]
        status = directives[data[1][1]][0](arg,symbols,code,line)
        if not status:
            return er
        return data
    ##################################################
    # [drct_p]
    elif(tokens[0][0] in {"<drct_p>", "<08nm>"}):
        drct_p = tokens[0][1]
        if(tokens[0][0] == "<08nm>"):
            if(tokens[0][1] != "db"):
                return 0
            tokens[0][0] = "<drct_p>"
        data.append(tokens.pop(0))

        if(not tokens):
            error("Directive missing argument!",line)
            return er
        expr = parse_expr(*args)
        if(not expr):
            error("Directive has bad argument B!",line)
            return er
        elif(expr == er):
            return er
        data.append(expr)

        while(tokens):
            if(tokens[0][0] != "<comma>"):
                error("Missing comma!",line)
                return er
            data.append(tokens.pop(0))
            if(not tokens):
                error("Directive missing last argument or has extra comma!",line)
                return er
            expr = parse_expr(*args)
            if(not expr):
                error("Directive has bad argument C !",line)
                return er
            elif(expr == error):
                return er
            data.append(expr)

        d_args = [x[1:] for x in data[2:] if x[0] != "<comma>"]
        status = directives[drct_p][0](d_args,symbols,code,line)
        if not status:
            return er
        return data
    ##################################################
    # [drct_w]
    elif(tokens[0][0] == "<symbol>"):
        data.append(tokens.pop(0))
        if(not tokens or tokens[0][0] != "<drct_w>"):
            error("Bad Identifier!",line)
            return er
        data.append(tokens.pop(0))
        if(not tokens):
            error("Directive missing argument!",line)
            return er
        expr = parse_expr(*args)
        if(not expr):
            error("Directive has bad argument D !",line)
            return er
        elif(expr == er):
            return er
        data.append(expr)
        ##############################################
        arg1 = data[1]
        arg2 = data[3][1:]
        status = directives[data[2][1]][0]([arg1,arg2],symbols,code,line)
        if not status:
            return er
        return data
    elif(tokens[0][0] == "<drct_w>"):
        error("Directive missing initial argument!",line)
        return er

    return 0

######################################################
def parse_code(tokens, symbols, code, line):
    args = [tokens, symbols, code, line]
    data = ["<code>"]
    er = ["<error>"]
    if not tokens:
        return 0
    ##################################################
    # [mnm_0]
    if(tokens[0][0] == "<mnm_0>"):
        inst = tokens[0][1]
        data.append(tokens.pop(0))
        code.write(instructions.instructions[inst],line,instrct=inst)
        return data
    ##################################################
    # [mnm_0_e]
    elif(tokens[0][0] in {"<mnm_0_e>", "<08nm>"}):
        if(tokens[0][0] == "<08nm>"):
            if(tokens[0][1] != "CC"):
                return 0
            tokens[0][0] = "<mnm_0_e>"
        inst = tokens[0][1]
        data.append(tokens.pop(0))

        if(not tokens):
            error("Instruction missing argument!",line)
            return er

        expr = parse_expr(*args)
        if(not expr):
            error("Instruction has bad argument!",line)
            return er
        if(expr == er):
            return er
        data.append(expr)

        expr_str = " ".join([x[1] for x in expr[1:]])
        if(inst in instructions.instructions):
            code.write(instructions.instructions[inst],line,instrct=inst+" "+expr_str)
        else:
            error("Bad instruction: "+inst,line)
            return er

        val = evaluate(expr[1:],symbols,code.address-1)
        if(len(val) == 1):
            numb = val[0]
            if(numb < 0):
                error("Expression must be positive!",line)
                return er
            elif(table.mnm_0_e[inst] == "data"):
                if(numb > 255):
                    error("Expression must evaluate to 8-bit number!",line)
                    return er
                code.write(numb,line)
            elif(table.mnm_0_e[inst] == "address"):
                if(numb > 65535):
                    error("Expression must evaluate to 16-bit number!",line)
                    return er
                else:
                    code.write((numb & 0xff),line)
                    code.write((numb >> 8),line)
        else:
            symbols.expr.append([val,table.mnm_0_e[inst]])
            code.write("expr",line)
            if(table.mnm_0_e[inst] == "address"):
                code.write("expr",line)
        return data

    ##################################################
    # [mnm_1]
    elif(tokens[0][0] == "<mnm_1>"):
        inst = tokens[0][1]
        data.append(tokens.pop(0))
        if(not tokens):
            error("Instruction missing register/register-pair",line)
            return er
        if(tokens[0][0] != "<reg>"):
            error("Instruction has bad register/register-pair",line)
            return er
        reg = tokens[0][1]
        data.append(tokens.pop(0))
        if(inst+" "+reg in instructions.instructions):
            code.write(instructions.instructions[inst+" "+reg],line,instrct=inst+" "+reg)
        else:
            error("Bad instruction: "+inst+" "+reg,line)
            return er
        return data
    ##################################################
    # [mnm_1_e]
    elif(tokens[0][0] == "<mnm_1_e>"):
        inst = tokens[0][1]
        data.append(tokens.pop(0))
        if(not tokens):
            error("Instruction missing register/register-pair!",line)
            return er
        if(tokens[0][0] != "<reg>"):
            error("Instruction has bad register/register-pair!",line)
            return er
        reg = tokens[0][1]
        data.append(tokens.pop(0))
        if(not tokens):
            error("Instruction missing comma and argument!",line)
            return er
        if(tokens[0][0] != "<comma>"):
            if(tokens[0][0] not in {"<08nm>", "<16nm>", "<symbol>"}):
                error("Instruction has bad argument!",line)
                return er
            error("Instruction missing comma!",line)
            return er
        data.append(tokens.pop(0))
        if(not tokens):
            error("Instruction missing argument!",line)
            return er
        expr = parse_expr(*args)
        if(not expr):
            error("Instruction has bad argument!",line)
            return er
        elif(expr == er):
            return er
        data.append(expr)
        instStr = inst+" "+reg

        expr_str = " ".join([x[1] for x in expr[1:]])
        if(instStr in instructions.instructions):
            code.write(instructions.instructions[instStr],line,instrct=instStr+", "+expr_str)
        else:
            error("Bad instruction: "+instStr,line)
            return er

        val = evaluate(expr[1:],symbols,code.address-1)
        if(len(val) == 1):
            numb = val[0]
            if(numb < 0):
                error("Expression must be positive!",line)
                return er
            elif(table.mnm_1_e[inst] == "data"):
                if(numb > 255):
                    error("Expression must evaluate to 8-bit number!",line)
                    return er
                code.write(numb,line)
            elif(table.mnm_1_e[inst] == "address"):
                if(numb > 65535):
                    error("Expression must evaluate to 16-bit number!",line)
                    return er
                else:
                    code.write((numb & 0xff),line)
                    code.write((numb >> 8),line)
        else:
            symbols.expr.append([val,table.mnm_1_e[inst]])
            code.write("expr",line)
            if(table.mnm_1_e[inst] == "address"):
                code.write("expr",line)

        return data

    ##################################################
    # [mnm_2]
    elif(tokens[0][0] == "<mnm_2>"):
        inst = tokens[0][1]
        data.append(tokens.pop(0))
        if(not tokens):
            error("Instruction missing register/register-pair!",line)
            return er
        if(tokens[0][0] != "<reg>"):
            error("Instruction has bad register/register-pair!",line)
            return er
        reg1 = tokens[0][1]
        data.append(tokens.pop(0))
        if(not tokens):
            error("Instruction missing comma and register/register-pair!",line)
            return er
        if(tokens[0][0] != "<comma>"):
            if(tokens[0][0] != "<reg>"):
                error("Instruction has bad register/register-pair!",line)
                return er
            error("Instruction missing comma!",line)
            return er
        data.append(tokens.pop(0))
        if(not tokens):
            error("Instruction missing register/register-pair!",line)
            return er
        if(tokens[0][0] != "<reg>"):
            error("Instruction has bad register/register-pair!",line)
            return er
        reg2 = tokens[0][1]
        data.append(tokens.pop(0))

        instStr = inst+" "+reg1+","+reg2
        if(instStr in instructions.instructions):
            code.write(instructions.instructions[instStr],line,instrct=instStr)
        else:
            error("Bad instruction: "+instStr,line)
            return er
        return data

    return 0
######################################################################################
def parse_line(tokens, symbols, code, line):
    data = ["<line>"]
    er = ["<error>"]
    if(len(tokens) == 0):
        return 0
    ################################
    # [lbl_def]
    lbl_def = parse_lbl_def(tokens, symbols, code, line)
    if(lbl_def):
        if(lbl_def == er):
            return er
        data.append(lbl_def)
    ################################
    # [drct]
    drct = parse_drct(tokens, symbols, code, line)
    if(drct):
        if(drct == er):
            return er
        data.append(drct)
    ################################
    # [code]
    code = parse_code(tokens, symbols, code, line)
    if(code):
        if(code == er):
            return er
        data.append(code)
    ###############################
    # check to see that we have at
    # least one of lbl_def, drct,
    # or code
    if(len(data) < 2):
        tokens.pop(0)
        error("Bad Initial Identifier!",line)
        return er
    ###############################
    # check to see if we have any
    # tokens left
    if(len(tokens)):   
        error("Bad Final Identifier!",line)
        return er
    ###############################
    # everything's good
    return data

######################################################################################
# Main program

code = Code()
symbols = Symbol()

outFile = ""
discription = 'A simple 8085 assembler.'

p = argparse.ArgumentParser(description = discription)
p.add_argument("source", help="source file")
p.add_argument("-L", "--lineNum", help="include the line number in output", action="store_true")
p.add_argument("-A", "--address", help="include the address in output", action="store_true")
p.add_argument("-B", "--label",   help="include the labels in output", action="store_true")
p.add_argument("-I", "--instruction", help="include the instructions and arguments in output", action="store_true")
p.add_argument("-H", "--hex", help="include the hex code in output", action="store_true")
p.add_argument("-C", "--comment", help="include the comments in output", action="store_true")
p.add_argument("-s", "--standard", help="equivalent to -A -B -I -H -C", action="store_true")
p.add_argument("-b", "--bin", help="outputs only binary data", action="store_true")
p.add_argument("-t", "--trs100", help="creates basic loader for TRS-80 Model 100", action="store_true")
p.add_argument("-n", "--trs100_new", help="runs 'new' after poking Model 100 program into memory", action="store_true")
p.add_argument("-S", "--trs100_save", help="in the Model 100 program, SAVEM the binary file", action="store_true")
p.add_argument("-o", "--out", help="output file name (stdout, if not specified)")
args = p.parse_args();

if(args.standard and (args.address or args.label or args.instruction and args.hex and args.comment)):
    p.error("-s is mutually exclusive with (-A, -B, -I, -H, -C")

if(args.bin and not args.out):
    p.error("-b needs a file to output to")

if(args.source):
    outFile = args.source

if(args.standard):
    args.address, args.label, args.instruction, args.hex, args.comment = True, True, True, True, True

parse(read(args.source),symbols,code)
if args.trs100:
    output_basic(code, (args.out if args.out else ""), args)
else:
    output(code, (args.out if args.out else ""), args)
