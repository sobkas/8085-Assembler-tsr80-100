# Notes:
# -> Put restrictions on valid symbol and label entries
# -> Add decimal and binary base functionality
##############################################################################################################
import re
import sys
import table
import instructions

##############################################################################################################
# Experimental Code Classes

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
        # Format: [line] [address] [label] [instruction + argument] [hex code] [comment] [expr]

        lineNum = line[0][0]
        addressStr = '0x{0:0{1}X}'.format(self.address,4)

        if(data != "expr"):
            data = '0x{0:0{1}X}'.format(data,2)

        comment = ''
        pc = line[0][1]
        if(len(self.data) == 0 or pc != self.data[-1][0][0][1]):
            comment = line[2]

        self.data.append([line, addressStr, self.label, instrct, data, comment])
        self.address += 1
        self.label = ""

    def update(self, data, index):

        self.data[index][4] = '0x{0:0{1}X}'.format(data,2)


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
        line = line.upper()
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

def output(code, name):
    # Format: [line] [address] [label] [instruction + argument] [hex code]
    f = open(name,'w') if name else sys.stdout
    print('{:<20}{:<20}{:<20}{:<20}{:<20}'.format("Address","Label","Instruction","Hex Code","Comment"),file=f)
    print("----------------------------------------------------------------------------------------------------------------------------------",file=f)
    for l in code.data:
        print('{:<20}{:<20}{:<20}{:<20}{:<20}'.format(l[1],l[2],l[3],l[4],l[5]),file=f)

    if f is not sys.stdout:
        f.close()

##############################################################################################################
# Directive functions
def org(arg, symbols, code, line):
    val = evaluate(arg, symbols, code)
    if(len(val) == 1):
        num = val[0]
        if(num < 0):
            error("Expression must be positive!",line)
            return
        else:
            code.address = num
            return
    else:
        error("Expression depends on unresolved symbol!",line)
        return

def db(args, symbols, code, line):
    for expr in args:
        val = evaluate(expr, symbols, code)
        if(len(val) == 1):
            num = val[0]
            if(num < 0):
                error("Expression must be positive!",line)
                return
            elif(num > 255):
                error("Expression too large! Must evaluate to an 8-bit number!", line)
                return
            else:
                code.write(num,line,instrct="DB")
        else:
            error("Expression depends on unresolved symbol!",line)
            return

def equ(args, symbols, code, line):
    name = args[0][1]
    if(name in table.reserved):
        error("Cannot use reserved keyword in equ directive!",line)
        return
    elif(name in (symbols.eightBitDefs, symbols.sixteenBitDefs)):
        error("Symbol already defined!",line)
        return
    elif(name in symbols.labelDefs):
        error("Symbol conflicts with previous labelDef!",line)
        return

    val = evaluate(args[1], symbols, code)
    if(len(val) == 1):
        num = val[0]
        if num > 65535:
            error("Expression greater than 0xFFFF!",line)
            return
        elif num > 255:
            symbols.sixteenBitDefs[name] = '{0:0{1}X}'.format(num,4)
            return
        elif num >= 0:
            symbols.eightBitDefs[name] = '{0:0{1}X}'.format(num,2)
            return
        else:
            error("Expression must be positive!",line)
            return
    else:
        error("Expression depends on unresolved symbol!",line)
        return

def ds(arg, symbols, code, line):
    val = evaluate(arg, symbols, code)
    if(len(val) == 1):
        num = val[0]
        if(num < 0):
            error("Expression must be positive!",line)
            return
        else:
            code.address += num
            return
    else:
        error("Expression depends on unresolved symbol!",line)
        return

directives = {
    #Format:
    # [function, min_args, max_args, name]
    # -1 means no bound
    "ORG": [org, 1, 1, "ORG"],
    "DB":  [db, 1, -1, "DB"],
    "EQU": [equ, 2, 2, "EQU"],
    "DS":  [ds, 1, 1, "DS"],
}

##############################################################################################################
# Passes
               
def secondPass(symbols, code):
    # Format: [line] [address] [label] [instruction + argument] [hex code] [comment]
    i = 0
    while i < len(code.data):
        codeLine = code.data[i]
        line = codeLine[0]
        data = codeLine[4]
        symbol = ""
        if(data == "expr"):
            expr, kind  = symbols.expr.pop(0)
            val = evaluate(expr, symbols, code)
            if(len(val) == 1):
                numb = val[0]
                if(numb < 0):
                    error("Expression must be positive!",line)
                elif(kind == "data"):
                    if(numb > 255):
                        error("Expression must evaluate to 8-bit number!",line)
                    else:
                        code.update(numb,line)
                elif(kind == "address"):
                    if(numb > 65535):
                        error("Expression must evaluate to 16-bit number!",line)
                    else:
                        code.update((numb & 0xff),i)
                        code.update((numb >> 8),i+1)
                        i += 1
            else:
                error("Expression relies on unresolved symbol!",line)
                print(expr)
        i += 1

##############################################################################################################
# Experimental

def lexer(lines):
    tokens = []
    code_lines = [x for x in lines if len(x[1])]
    for line in code_lines:
        tl = []
        for word in line[1]:
            word = word.strip()
            if word in table.mnm_0:
                tl.append(["<mnm_0>", word])
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
                error("Uknown token!", line)
        tokens.append(tl)

    return [code_lines, tokens]
######################################################################################
def evaluate(expr, symbols, code):
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
        elif(expr[-1][0] == "<lc>"):
            result += sign*code.address
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
# <expr> ::= [ (<plus> | <minus>) ] <numb> { (<plus> | <minus> <numb> }
#
# <drct> ::= <drct_1> <expr>
#          | <drct_p> <expr> { ","  <expr> }
#          | <symbol> <drct_w> <expr>
#
# <numb> := <08nm> | <16nm> | <symbol> | <lc>
######################################################################################
def parse(lines, symbols, code):

    code_lines, tokenLines = lexer(lines)
    tree = []
    for tokens, line in zip(tokenLines, code_lines):
        tree.append(parse_line(tokens, symbols, code, line))

    secondPass(symbols, code)

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
        if(tokens[0][0] not in {"<08nm>", "<16nm>", "<symbol>", "<lc>"}):
            if(tokens[0][0] not in {"<plus>", "<minus>"}):
                if(len(data) > 1):
                    error("Expression had bad identifier!",line)
                    return er
                else:
                    return 0
            else:
                error("Expression has extra operator!",line)
                return er
        data.append(tokens.pop(0))
    return data
######################################################################################
def parse_drct(tokens, symbols, code, line):
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
        expr = parse_expr(tokens, symbols, code, line)
        if(not expr):
            error("Directive has bad argument!", line)
            return er
        if(expr == er):
            return er
        data.append(expr)
        arg = data[2][1:]
        directives[data[1][1]][0](arg,symbols,code,line)
        return data
    ##################################################
    # [drct_p]
    elif(tokens[0][0] in {"<drct_p>", "<08nm>"}):
        if(tokens[0][0] == "<08nm>"):
            if(tokens[0][1] != "DB"):
                return 0
            tokens[0][0] = "<drct_p>"
        data.append(tokens.pop(0))

        if(not tokens):
            error("Directive missing argument!",line)
            return er
        expr = parse_expr(tokens, symbols, code, line)
        if(not expr):
            error("Directive has bad argument!",line)
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
            expr = parse_expr(tokens, symbols, code, line)
            if(not expr):
                error("Directive has bad argument!",line)
                return er
            elif(expr == error):
                return er
            data.append(expr)

        args = [x[1:] for x in data[2:] if x[0] != "<comma>"]
        directives[data[1][1]][0](args,symbols,code,line)
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
        expr = parse_expr(tokens, symbols, code, line)
        if(not expr):
            error("Directive has bad argument!",line)
            return er
        elif(expr == er):
            return er
        data.append(expr)
        ##############################################
        arg1 = data[1]
        arg2 = data[3][1:]
        directives[data[2][1]][0]([arg1,arg2],symbols,code,line)
        return data
    elif(tokens[0][0] == "<drct_w>"):
        error("Directive missing initial argument!",line)
        return er

    return 0

######################################################
def parse_code(tokens, symbols, code, line):
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

        expr = parse_expr(tokens, symbols, code, line)
        if(not expr):
            error("Instruction has bad argument!")
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

        val = evaluate(expr[1:],symbols,code)
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
        expr = parse_expr(tokens, symbols, code, line)
        if(not expr):
            error("Instruction has bad argument!",line)
            return er
        elif(expr == er):
            return er
        instStr = inst+" "+reg
        data.append(expr)

        expr_str = " ".join([x[1] for x in expr[1:]])
        if(instStr in instructions.instructions):
            code.write(instructions.instructions[instStr],line,instrct=instStr+", "+expr_str)
        else:
            error("Bad instruction: "+instStr,line)
            return er

        val = evaluate(expr[1:],symbols,code)
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
        error("Bad Identifier!",line)
        return er
    ###############################
    # everything's good
    return data

######################################################################################
# Main program

code = Code()
symbols = Symbol()

callArgs = sys.argv
inFile =""
outFile = ""

if(len(sys.argv) == 3):
    inFile = sys.argv[1]
    outFile = sys.argv[2]
else:
    inFile = "program.asm"

parse(read(inFile),symbols,code)
output(code,outFile)