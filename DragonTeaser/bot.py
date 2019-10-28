import sys,pickle
from pwn import *

choice = b"CHOICE:"
dragon = b"DRAGON"
shield = b"BOUNCES OFF YOUR SHIELD"

p = process(["./emu", "game.bin", "flag.txt"])
p.readuntil(choice)

safety = 0
while True:
  p.sendline(b"n") # go north
  r = p.readuntil(choice)

  # stop when we hit a dragon
  if dragon in r:
    break

  safety += 1
  # TODO: check if we reached top of field
  if safety > 10:
    print("Reached North without hitting a dragon")
    sys.exit(0)    


p.sendline(b"f") # figth dragon
p.readuntil(choice)

# now let's generate some sequences
seq_num = 10000
seq_len = 202
sequences = []

for n in range(seq_num):
  s = []
  
  for i in range(seq_len):
    p.sendline(b"s") # use shield
    r = p.readuntil(choice)

    if shield in r:
      s.append(1) # dragon hit us 
    else:
      s.append(0) # dragon miss us

  sequences.append(s)

print("Generated {}-Sequences".format(seq_num))

# dump as pickle
with open('sequences.pickle', 'wb') as handle:
    pickle.dump(sequences, handle, protocol=pickle.HIGHEST_PROTOCOL)

