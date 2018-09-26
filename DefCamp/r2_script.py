
import r2pipe
r2p = r2pipe.open()

# get base address, because its PIE
baddr = int(r2p.cmd("e bin.baddr"))
print("baseaddr: {}".format(hex(baddr)))

# set breakpoints
r2p.cmd("db {}".format(baddr+0x2E9D)) # break before AntiDebug
r2p.cmd("db {}".format(baddr+0x48D4)) # break before compare
r2p.cmd("db {}".format(baddr+0x4B4F)) # after installed printing

# debug until end of main stack setup
# (otherwise we will get a segfault)
r2p.cmd("dcu {}".format(baddr+0x2C44))

# set RIP after Anti DebugStuff
r2p.cmd("dr rip={}".format(baddr+0x2DA2))

# start debugging
r2p.cmd("dc")

# skipt anti debug (first BP which gets hit)
r2p.cmd("dr rip={}".format(baddr+0x2EA4))

# now its only valid code without any debug stuff...
def decChar(c):
    if c.isalpha():
        if ord(c.lower()) - ord('a') <= 13:
            return chr(ord(c)+12)
        else:
            return chr(ord(c)-14)
    else:
        try:
            return chr(ord(c)-1)
        except:
            return "a" # this character did not work...

# bruteforce the flag
flag = ""
for _ in range(70):
    for i in range(255): # bruteforce byte by byte
        r2p.cmd("dc")
        regs = r2p.cmdj("drj") # get registers
        hexrdi = r2p.cmdj("pxj 32 @ [{}]".format(regs["rdi"]))
        hexrsi = r2p.cmdj("pxj 32 @ [{}]".format(regs["rsi"]))

        byte_hash = "".join(chr(x) for x in hexrdi)
        buff_hash = "".join(chr(x) for x in hexrsi)

        # hash has to be the same
        if byte_hash == buff_hash:
            flag += decChar(chr(i))
            print flag
            break
        else:
            # try next byte
            r2p.cmd("dr rip={}".format(baddr+0x4842))
            r2p.cmd("dr eax={}".format(i))

print "Flag: ", flag

