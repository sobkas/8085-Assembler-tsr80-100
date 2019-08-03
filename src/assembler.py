# Notes:
# -> Add the location counter access handle "$"
# -> Add basic expression handeling
# -> Put restrictions on valid symbol and label entries
# -> Add decimal and binary base functionality
##############################################################################################################
import re
import sys
import table
import instructions

errors = ""

##############################################################################################################
# Experimental Code Classes

class Symbol:

    def __init__(self):
        self.labelDefs = {}
        self.eightBitDefs = {}
        self.sixteenBitDefs = {}

class Code:

    def __init__(self):
        self.data = []
        self.address = 0
        self.label = ""

    def write(self, data, line, instrct = "", mode = "number"):
        # Format: [line] [address] [label] [instruction + argument] [hex code] [comment]

        lineNum = line[0][0]
        addressStr = '0x{0:0{1}X}'.format(self.address,4)
        a = 0

        if(mode == "number"):
            a = '0x{0:0{1}X}'.format(data,2)
        elif(mode == "symbol"):
            a = data

        comment = ''
        pc = line[0][1]
        if(len(self.data) == 0 or pc != self.data[-1][0][0][1]):
            comment = line[2]

        self.data.append([line, addressStr, self.label, instrct, a, comment])
        self.address += 1
        self.label = ""

    def update(self, data, index):

        self.data[index][4] = "0x" + data


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
    global errors
    errors += "Error at line " + str(line[0][0]) + ": " + message + "\n"

##############################################################################################################
# Directive functions

def org(line, tags_with_comma, tags, args_with_comma, args, symbols, code):

    if(tags[0] == "[xx]" or tags[0] == "[xxxx]"):
        code.address = int(args[0], base = 16)

    else:
        error("Directive has bad argument!",line)
        return

def ds(line, tags_with_comma, tags, args_with_comma, args, symbols, code):

    if(tags[0] == "[xx]" or tags[0] == "[xxxx]"):
        code.address += int(args[0], base = 16)

    elif(tags[0] == "symbol"):

        if(args[0] in symbols.eightBitDefs):
            code.address += int(symbols.eightBitDefs[args[0]], base = 16)

        elif(args[0] in symbols.sixteenBitDefs):
            code.address += int(symbols.sixteenBitDefs[args[0]], base = 16)

        else:
            error("Symbol not defined before use!",line)
    else:
        error("Directive has bad argument!",line)


def db(line, tags_with_comma, tags, args_with_comma, args, symbols, code):

    i = 0
    while(i < len(args_with_comma)):
        if(not i%2):
            if(tags_with_comma[i] == "[xx]"):
                code.write(int(args_with_comma[i],base = 16),line,instrct="DB")
            elif(tags_with_comma[i] == "symbol"):
                code.write("D_"+args_with_comma[i],line, instrct = "DB", mode="symbol")
            elif(tags_with_comma[i] == "comma"):
                error("Directive has bad comma!",line)
                return
            else:
                error("Directive has bad argument!",line)
                return
        else:
            if(tags_with_comma[i] != "comma"):
                error("Directive missing comma!",line)
                return
        i += 1

def equ(line, tags_with_comma, tags, args_with_comma, args, symbols, code):
    if(tags_with_comma[0] == "symbol"):
        if(args_with_comma[0] in table.mnemonics or args_with_comma[0] in table.reserved):
            error("Cannot use reserved keyword in equ directive!",line)
            return
        elif(args_with_comma[0] in symbols.eightBitDefs or
           args_with_comma[0] in symbols.sixteenBitDefs):
            error("Symbol already defined!",line)
            return
        elif(args_with_comma[0] in symbols.labelDefs):
            error("Symbol conflicts with previous labelDef!",line)
            return

        if(tags_with_comma[1] == "[xx]"):
            symbols.eightBitDefs[args_with_comma[0]] = '{0:0{1}X}'.format(int(args_with_comma[1], base=16),2)
        
        elif(tags_with_comma[1] == "[xxxx]"):
            symbols.sixteenBitDefs[args_with_comma[0]] = '{0:0{1}X}'.format(int(args_with_comma[1], base=16),4)

        else:
            error("Directive has bad argument!", line)
    else:
        error("Directive has bad argument!", line)

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
# Parsing functions

def parse_mnemonic(line, index, code):
    # This function constructs an instruction and checks
    # to see if it is valid

    pc = line[0][1]
    
    mnemonic = line[1][index]
    instruction = mnemonic + " "
    argument = 0
    
    numOfMArgs = table.numOfMArgs(mnemonic)
    numOfArgs = table.numOfArgs(mnemonic)
    
    # Check the number of arguments to the instruction
    # Create an argument list from the line string
    args_with_comma = list(map(str.strip, line[1][index + 1:]))
    args = [x for x in args_with_comma if x != ","]
    if(len(args) != numOfArgs):
        error("Bad number of arguments to instruction!", line)
        return

    i, q, = 0, 0
    while(q < numOfMArgs):
        instruction += args_with_comma[i]
        if(args_with_comma[i] != ","):
            q += 1
        i += 1
    instruction = instruction.strip()

    # Construct the argStr which is a string of the arguments to the instruction
    argStr = ""
    if(i == 0):
        argStr += " "
    argStr += "".join(line[1][index+i+1:])
    
    # Check to see if the constructed instruction is valid
    if(instruction not in instructions.instructions):
        error("Bad instruction: " + str(instruction),line)
        return

    # Write the instruction to memory
    instructArgStr = instruction+argStr
    code.write(instructions.instructions[instruction],line,instrct=instructArgStr)
    
    # Check to see if the argument to the instruction is valid
    argType = table.mnemonics[mnemonic][2]
    
    if(argType != "none"):
        argument = args[numOfArgs-1]

##        "data"
##        not data, not address, yes symbol--- good
##        not data, not address, not symbol--- bad
##        not data, yes address--------------- bad
##        yes data---------------------------- good
##
##        "address"
##        not address, not data, yes symbol--- good
##        not address, not data, not symbol--- bad
##        not address, yes data--------------- good
##        yes address------------------------- good
##
##
##        "data" and "address"
##        not data, not address, yes symbol--- good, good
##        not data, not address, not symbol--- bad,  bad
##        not data, yes address--------------- bad,  null
##        yes data, not address--------------- null, good
##        yes data---------------------------- good, ~~~~
##        yes address------------------------- ~~~~, good
        
        if(argType == "data"):
            if(not re.match(r'^(0[Xx])?[0-9A-Fa-f]{2}$',argument)):         # If it does not match the data format (not great)
                if(not re.match(r'^(0[Xx])?[0-9A-Fa-f]{2}$',argument)):     # If it does not match the address format (better)                  
                    if(re.match(r'^[A-Za-z_]+[A-Za-z0-9_]*$',argument)):    # If it matches the symbol format (great)
                        code.write("D_" + argument, line, mode = "symbol")
                    else:                                                   # If it does not match the symbol format
                        error("Bad argument: " + argument, line)              
                else:                                                       # If it matches the address format (bad)
                    error("Bad argument: " + argument, line)
            else:                                                           # If it matches the data format (great)
                code.write(int(argument, base = 16), line)

        elif(argType == "address"):
            if(not re.match(r'^(0[Xx])?[0-9A-Fa-f]{4}$',argument)):         # If it does not match the address format (not great)
                if(not re.match(r'^(0[Xx])?[0-9A-Fa-f]{2}$',argument)):     # If it does not match the data format (better)
                    if(re.match(r'^[A-Za-z_]+[A-Za-z0-9_]*$',argument)):    # If it matches the symbol format (great)
                        code.write("L_"+argument, line, mode = "symbol")
                        code.write("H_"+argument, line, mode = "symbol")
                    else:                                                   # If it does not match the symbol format (bad)
                        error("Bad argument: " + argument, line)
                else:                                                       # If it does match the data format, asssume the upper
                    code.write(int(argument, base = 16), line)              # part of the address is 00
                    code.write(00, line)
            else:                                                           # If it matches the address format (great)
                code.write(int(argument[2:], base = 16), line)
                code.write(int(argument[:2], base = 16), line)
    

##############################################################################################################
# Passes
               
def firstPass(lines,symbols,code):
    # Figures what type of statement we have based the first few words in a line of lines
    # Then it calls a particular parser to parese the rest of the command against a
    # particular grammer

    # Recall the format for a line: [[Line_number, Program_Counter] [body] [comment]]
    print(lines)
    for line in lines:
        index = 0
        if(line[1]):
            length = len(line[1])
            lengthLessLbl = length
            if(re.match(r'^.+:$',line[1][0])):
                # First word in the line is: "labelDef:"
                # Since it is, parse the labelDef and move the
                # index so that we can look at the rest of
                # the line, if there is any

                parse_labelDef(line,symbols)
                index += 1
                lengthLessLbl -= 1
            if(length > index):
                # We have a message which includes more than a labelDef, if any.
                # We use index to skip over the labelDef, if any.

                if(line[1][index] in table.mnemonics):
                    parse_mnemonic(line, index, code)

                elif(line[1][index] in table.directives and line[1][index] != "EQU"):
                    parse_directive(line, index, directives[line[1][index]], symbols, code)

                elif(lengthLessLbl >= 2 and line[1][index + 1] == "EQU"):
                    parse_directive(line, index, directives[line[1][index + 1]], symbols, code)

                else:
                    error("Bad initial identifier!", line)
                    return
        if(errors):
            return

def secondPass(symbols, code):
    # Format: [line] [address] [label] [instruction + argument] [hex code] [comment]
    for i, codeLine in enumerate(code.data):
        line = codeLine[0]
        data = codeLine[4][0]
        symbol = ""
        if(data == "D" or data == "L" or data == "H"):
            symbol = codeLine[4][2:]
            if(symbol not in symbols.labelDefs and symbol not in symbols.eightBitDefs and symbol not in symbols.sixteenBitDefs):
                error("Label \"" + symbol + "\" not defined!",line)
                return
        else:
            continue
            
        if(data == "D"):
            if(symbol in symbols.labelDefs):
                error("You cannot use an address label where an 8-bit value is expected!",line)
                return
                
            elif(symbol in symbols.eightBitDefs):
                code.update(symbols.eightBitDefs[symbol],i)
                   
            elif(symbol in symbols.sixteenBitDefs):
                error("You cannot use a 16-bit label constant where an 8-bit value is expected!",line)
                return
                
        elif(data == "L"):
            if(symbol in symbols.labelDefs):
                code.update(symbols.labelDefs[symbol][2:],i)

            elif(symbol in symbols.eightBitDefs):
                error("You cannot use a 8-bit label constant where a 16-bit value is expected!",line)
                return

            elif(symbol in symbols.sixteenBitDefs): 
                code.update(symbols.sixteenBitDefs[symbol][2:],i)

        elif(data == "H"):
            if(symbol in symbols.labelDefs):
                code.update(symbols.labelDefs[symbol][:2],i)

            elif(symbol in symbols.sixteenBitDefs):
                code.update(symbols.sixteenBitDefs[symbol][:2],i)

##############################################################################################################
# Output

def output(code, name):
    # Format: [line] [address] [label] [instruction + argument] [hex code]
    f = open(name,'w') if name else sys.stdout
    print('{:<20}{:<20}{:<20}{:<20}{:<20}'.format("Address","Label","Instruction","Hex Code","Comment"),file=f)
    print("----------------------------------------------------------------------------------------------------------------------------------",file=f)
    for l in code.data:
        print('{:<20}{:<20}{:<20}{:<20}{:<20}'.format(l[1],l[2],l[3],l[4],l[5]),file=f)

    print("\n" + errors,file=f)
    if f is not sys.stdout:
        f.close()
##############################################################################################################
# Experimental

#for lineNumber, line in enumerate(file, start = 1):
def lexer(lines):
    tokens = []
    i = 0
    for line in lines:
        pc = line[0][1]
        if(len(line[1]) != 0):
            tokens.append([])
            for word in line[1]:
                word = word.strip()
                if word in table.mnm_0:
                    tokens[i].append(["<mnm_0>", word, pc])
                elif(re.match(r'^(0[Xx])?[0-9A-Fa-f]{2}$', word)):
                    tokens[i].append(["<08nm>", word, pc])
                elif word in table.mnm_0_e:
                    tokens[i].append(["<mnm_0_e>", word, pc])
                elif word in table.mnm_1:
                    tokens[i].append(["<mnm_1>", word, pc])
                elif word in table.mnm_1_e:
                    tokens[i].append(["<mnm_1_e>", word, pc])
                elif word in table.mnm_2:
                    tokens[i].append(["<mnm_2>", word, pc])
                elif word in table.reg:
                    tokens[i].append(["<reg>", word, pc])
                elif word == ",":
                    tokens[i].append(["<comma>", word, pc])
                elif word == "+":
                    tokens[i].append(["<plus>", word, pc])
                elif word == "-":
                    tokens[i].append(["<minus>", word, pc])
                elif word in table.drct_1:
                    tokens[i].append(["<drct_1>", word, pc])
                elif word in table.drct_p:
                    tokens[i].append(["<drct_p>", word, pc])
                elif word in table.drct_w:
                    tokens[i].append(["<drct_w>", word, pc])
                elif re.match(r'^.+:$',word):
                    tokens[i].append(["<lbl_def>", word, pc])
                elif(re.match(r'^(0[Xx])?[0-9A-Fa-f]{4}$', word)):
                    tokens[i].append(["<16nm>", word, pc])
                elif(re.match(r'^[A-Za-z_]+[A-Za-z0-9_]*$', word)):
                    tokens[i].append(["<symbol>", word, pc])
                else:
                    tokens[i].append(["<idk_man>", word, pc])
                    print("UNKNOWN TOKEN!")
                    print(word)
            i += 1
    return tokens

######################################################
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
# <drct> ::= <drct_1> ( <08nm> | <16nm> )
#          | <drct_p> <08nm> { ","  <08nm> }
#          | <symbol> <drct_w> <expr>
#
# <numb> := <08nm> | <16nm> | <symbol>
######################################################
def parse(token_lines, symbols, code):
    tree = []
    for tokens in token_lines:
        tree.append(parse_line(tokens, symbols, code))

    print("tree:")
    for l in tree:
        print(l)

######################################################
def parse_lbl_def(tokens, symbols, code):
    if not tokens:
        return 0
    if(tokens[0][0] == "<lbl_def>"):
        lbl = tokens[0][1]
        if lbl[:-1] in symbols.labelDefs:
            print("Label already in use!")
        elif lbl[:-1] in table.reserved:
            print("Label cannot be keyword!")
        elif lbl[:-1] in (symbols.eightBitDefs, symbols.sixteenBitDefs):
            print("Label conflicts with previous symbol definition")
        else:
            symbols.labelDefs[lbl[:-1]] = '{0:0{1}X}'.format(code.address,4)
            code.label = lbl
        return tokens.pop(0)
    else:
        return 0

######################################################
def parse_expr(tokens, symbols, code):
    data = ["<expr>"]
    error = ["<error>"]
    if not tokens:
        print("Empty expr")
        return 0
    ##################################################
    if(tokens[0][0] in {"<plus>", "<minus>"}):
        data.append(tokens.pop(0))
    if(not tokens):
        print("Missing number/symbol!")
        return error
    if(tokens[0][0] not in {"<08nm>", "<16nm>", "<symbol>"}):
        if(tokens[0][0] not in {"<plus>", "<minus>"}):
            print("Expression had bad identifier!")
            return error
        print("Expression has extra operator!")
        return error

    data.append(tokens.pop(0))
    while(tokens):
        if(tokens[0][0] not in {"<plus>", "<minus>"}):
            if(tokens[0][0] not in {"<08nm>", "<16nm>", "<symbol>"}):
                print("Expression has bad identifier!")
                return error
            print("Expression missing operator!")
            return error
        data.append(tokens.pop(0))
        if(not tokens):
            print("Expression missing number/symbol!")
            return error
        if(tokens[0][0] not in {"<08nm>", "<16nm>", "<symbol>"}):
            if(tokens[0][0] not in {"<plus>", "<minus>"}):
                print("Expression has bad identifier: ",tokens[0][0])
                return error
            print("Expression has extra operator!")
            return error
        data.append(tokens.pop(0))
    return data
######################################################
def parse_drct(tokens, symbols, code):
    data = ["<drct>"]
    error = ["<error>"]
    if not tokens:
        return 0
    ##################################################
    # [drct_1]
    if(tokens[0][0] == "<drct_1>"):
        data.append(tokens.pop(0))
        if(not tokens):
            print("Directive missing argument!")
            return error
        if(tokens[0][0] not in {"<08nm>", "<16nm>"}):
            print("Directive has bad argument!")
            return error
        data.append(tokens.pop(0))
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
            print("Directive missing argument!")
            return error
        if(tokens[0][0] != "<08nm>"):
            print("Directive has bad argument!")
        data.append(tokens.pop(0))
        while(tokens):
            if(tokens[0][0] != "<comma>"):
                if(tokens[0][0] != "<08nm>"):
                    print("Directive has bad argument!")
                    return error
                print("Missing comma!")
            data.append(tokens.pop(0))
            if(not tokens):
                print("Directive missing last argument or has extra comma!")
                return error
            if(tokens[0][0] != "<08nm>"):
                if(tokens[0][0] != "<comma>"):
                    print("Directive has bad argument!")
                    return error
                print("Directive missing arguments!")
                return error
            data.append(tokens.pop(0))
        return data
    ##################################################
    # [drct_w]
    elif(tokens[0][0] == "<symbol>"):
        data.append(tokens.pop(0))
        if(not tokens or tokens[0][0] != "<drct_w>"):
            print("Bad Identifier!")
            return error
        data.append(tokens.pop(0))
        if(not tokens):
            print("Directive missing argument!")
            return error
        expr = parse_expr(tokens, symbols, code)
        if(expr == error):
            return error
        data.append(expr)
        return data
    elif(tokens[0][0] == "<drct_w>"):
        print("Directive missing initial argument!")
        return error

    return 0
######################################################
def parse_code(tokens, symbols, code):
    data = ["<code>"]
    error = ["<error>"]
    if not tokens:
        return 0
    ##################################################
    # [mnm_0]
    if(tokens[0][0] == "<mnm_0>"):
        data.append(tokens.pop(0))
        return data
    ##################################################
    # [mnm_0_e]
    elif(tokens[0][0] in {"<mnm_0_e>", "<08nm>"}):
        if(tokens[0][0] == "<08nm>"):
            if(tokens[0][1] != "CC"):
                return 0
            tokens[0][0] = "<mnm_0_e>"
        data.append(tokens.pop(0))
        if(not tokens):
            print("Instruction missing argument!")
            return error
        expr = parse_expr(tokens, symbols, code)
        if(expr == error):
            return error
        data.append(expr)
        return data
    ##################################################
    # [mnm_1]
    elif(tokens[0][0] == "<mnm_1>"):
        data.append(tokens.pop(0))
        if(not tokens):
            print("Instruction missing register/register-pair")
            return error
        if(tokens[0][0] != "<reg>"):
            print("Instruction has bad register/register-pair")
            return error
        data.append(tokens.pop(0))
        return data
    ##################################################
    # [mnm_1_e]
    elif(tokens[0][0] == "<mnm_1_e>"):
        data.append(tokens.pop(0))
        if(not tokens):
            print("Instruction missing register/register-pair!")
            return error
        if(tokens[0][0] != "<reg>"):
            print("Instruction has bad register/register-pair!")
            return error
        data.append(tokens.pop(0))
        if(not tokens):
            print("Instruction missing comma and argument!")
            return error
        if(tokens[0][0] != "<comma>"):
            if(tokens[0][0] not in {"<08nm>", "<16nm>", "<symbol>"}):
                print("Instruction has bad argument!")
                return error
            print("Instruction missing comma!")
            return error
        data.append(tokens.pop(0))
        if(not tokens):
            print("Instruction missing argument!")
            return error
        expr = parse_expr(tokens, symbols, code)
        if(expr == error):
            return error
        data.append(expr)
        return data
    ##################################################
    # [mnm_2]
    elif(tokens[0][0] == "<mnm_2>"):
        data.append(tokens.pop(0))
        if(not tokens):
            print("Instruction missing register/register-pair!")
            return error
        if(tokens[0][0] != "<reg>"):
            print("Instruction has bad register/register-pair!")
            return error
        data.append(tokens.pop(0))
        if(not tokens):
            print("Instruction missing comma and register/register-pair!")
            return error
        if(tokens[0][0] != "<comma>"):
            if(tokens[0][0] != "<reg>"):
                print("Instruction has bad register/register-pair!")
                return
            print("Instruction missing comma!")
            return error
        data.append(tokens.pop(0))
        if(not tokens):
            print("Instruction missing register/register-pair!")
            return error
        if(tokens[0][0] != "<reg>"):
            print("Instruction has bad register/register-pair!")
            return error
        data.append(tokens.pop(0))
        return data

    return 0
######################################################
def parse_line(tokens, symbols, code):
    data = ["<line>"]
    error = ["<error>"]
    if(len(tokens) == 0):
        return 0
    ################################
    # [lbl_def]
    lbl_def = parse_lbl_def(tokens, symbols, code)
    if(lbl_def):
        if(lbl_def == error):
            return error
        data.append(lbl_def)
    ################################
    # [drct]
    drct = parse_drct(tokens, symbols, code)
    if(drct):
        if(drct == error):
            return error
        data.append(drct)
    ################################
    # [code]
    code = parse_code(tokens, symbols, code)
    if(code):
        if(code == error):
            return error
        data.append(code)
    ###############################
    # check to see that we have at
    # least one of lbl_def, drct,
    # or code
    if(len(data) < 2):
        tokens.pop(0)
        print("Bad Initial Identifier!")
        return error
    ###############################
    # check to see if we have any
    # tokens left
    if(len(tokens)):   
        print("Bad Identifier!")
        return error
    ###############################
    # everything's good
    return data

##############################################################################################################
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
    inFile = "pgm.asm"

parse(lexer(read(inFile)),symbols,code)

