import sys,pickle
from pwn import *

choice = b"CHOICE:"

dragon = b"(F)IGHT" # otherwise we miss the RED BULL
redford = b"(F)IGHT REDFORD"
valis = b"(T)ALK TO VALIS"
drunk_dragon = b"DRUNK DRAGON"
#dragon = b"DRAGON"
#(F)IGHT THE RED BULL

shield = b"BOUNCES OFF YOUR SHIELD"
south = b"GO (S)OUTH"
north = b"GO (N)ORTH"
east  = b"GO (E)AST"
west  = b"GO (W)EST"

attack_miss = b"ATTACKS YOU, BUT MISSES."
attack_hit = b"HITS YOU."
my_hit = b"YOU HIT"

enemy_health = b"ENEMY HEALTH:"
curr_health = b"CURRENT HEALTH:"

kill_dragon = b"YOU KILL"
got_killed = b"YOU DIE"

M_NORTH = b"n"
M_EAST  = b"e"
M_WEST  = b"w"
M_SOUTH = b"s"

p = None # Game Connection

def dragonCheck(r):
  tmp = r.split(b"THERE IS A")
  dr_type = tmp[1].split(b"HERE.")[0]
  print(dr_type)

  # drunk dragon is not figthing
  if drunk_dragon in r:
    p.sendline(b"f")
    p.readuntil(choice)
    return 1 # continue
  else:
    return 0 # break

def startGame():
  global p
  p = process(["./../emu", "../game.bin", "../flag.txt"])
  p.readuntil(choice)

def getInteractive():
  p.interactive()

forwards_movement = True

def lookForDragon(move=M_NORTH):
  global forwards_movement

  empty_rounds = 0

  cnt = 0
  while True:
    p.sendline(move) # one step
    r = p.readuntil(choice)
    print("move {}".format(cnt))
    cnt += 1

    # stop when we hit a dragon
    if dragon in r and not redford in r:
      if dragonCheck(r) == 1:
        empty_rounds = 0
        continue
      else:
        break

    # check if we reached top
    if north not in r and move == M_NORTH:
      print("NORTH not available")
      if east not in r:
        p.sendline(M_WEST)
        forwards_movement = False
        empty_rounds += 1
        print("Change movement LEFT")
      elif west not in r:
        p.sendline(M_EAST)
        forwards_movement = True
        empty_rounds += 1
        print("Change movement RIGHT")
      else:
        if forwards_movement:
          print("step EAST")
          p.sendline(M_EAST)
        else:
          print("step WEST")
          p.sendline(M_WEST)

      r = p.readuntil(choice)
      move = M_SOUTH
      print("DIRECTION: south")
      print("move {}".format(cnt))
      cnt += 1

    # check if we reached bottom
    if south not in r and move == M_SOUTH:
      print("SOUTH not available")
      if east not in r:
        p.sendline(M_WEST)
        forwards_movement = False
        empty_rounds += 1
        print("Change movement LEFT")
      elif west not in r:
        p.sendline(M_EAST)
        forwards_movement = True
        empty_rounds += 1
        print("Change movement RIGHT")
      else:
        if forwards_movement:
          print("step EAST")
          p.sendline(M_EAST)
        else:
          print("step WEST")
          p.sendline(M_WEST)

      r = p.readuntil(choice)

      move = M_NORTH
      print("DIRECTION: north")
      print("move {}".format(cnt))
      cnt += 1

    if dragon in r and not redford in r:
      if dragonCheck(r) == 1:
        empty_rounds = 0
        continue
      else:
        break

    if empty_rounds >= 4:
      return b"x"

  return move 

def startFigth():
  # figth the dragon
  p.sendline(b"f")
  p.readuntil(choice)

def getDragonSequence():
  # get the sequence of the dragon first
  # we work with sequences of length 200
  learn_length = 200
  dragon_seq = []

  for i in range(learn_length):
    p.sendline(b"s") # always use shield at this stage
    r = p.readuntil(choice)

    # 1 if dragon hits us
    dragon_seq.append(1) if shield in r else dragon_seq.append(0)

  return dragon_seq

# attack dragon based on prediction
def attackDragon(attack, seq):

  retval = [-1]*4

  if attack: # attack
    p.sendline(b"a")
    try:
      r = p.readuntil(choice)
    except:
      # we got killed, if it dies here
      return None, -2

    if attack_hit in r:
      seq.append(1)
    else: 
      seq.append(0)

    if kill_dragon in r:
      return None, -1

    if got_killed in r:
      return None, -2

    if my_hit in r:
      tmp = r.split(enemy_health)
      health = tmp[1][:5].strip().decode("UTF8")
      retval[0] = health
      retval[2] = "hit"

    if attack_hit in r:
      tmp = r.split(curr_health)
      health = tmp[1][:5].strip().decode("UTF8")
      retval[1] = health
      retval[3] = "hit"

  else:  # shield
    p.sendline(b"s")
    r = p.readuntil(choice)
    if shield in r:
      seq.append(1)
      retval[3] = "hit"
    else:
      seq.append(0)

  return retval, 0

def moveToValis():
  # go to total south first
  move = M_SOUTH

  while True:
      p.sendline(move)
      r = p.readuntil(choice)

      # stop when we hit valis
      if valis in r:
          break

      # check if we reached bottom
      if south not in r and move == M_SOUTH:
        move = M_WEST

def talk():
  p.sendline(b"t")
  return p.readuntil(choice)

def findRedford():
  global forwards_movement

  # we start at Valis' point
  forwards_movement = True
  move = M_NORTH

  cnt = 0
  while True:
    p.sendline(move) # one step
    r = p.readuntil(choice)
    print("move {}".format(cnt))
    cnt += 1

    if redford in r:
      break

    # check if we reached top
    if north not in r and move == M_NORTH:
      print("NORTH not available")
      if east not in r:
        p.sendline(M_WEST)
        forwards_movement = False
        print("Change movement LEFT")
      elif west not in r:
        p.sendline(M_EAST)
        forwards_movement = True
        print("Change movement RIGHT")
      else:
        if forwards_movement:
          print("step EAST")
          p.sendline(M_EAST)
        else:
          print("step WEST")
          p.sendline(M_WEST)

      r = p.readuntil(choice)
      move = M_SOUTH
      print("DIRECTION: south")
      print("move {}".format(cnt))
      cnt += 1

    # check if we reached bottom
    if south not in r and move == M_SOUTH:
      print("SOUTH not available")
      if east not in r:
        p.sendline(M_WEST)
        forwards_movement = False
        print("Change movement LEFT")
      elif west not in r:
        p.sendline(M_EAST)
        forwards_movement = True
        print("Change movement RIGHT")
      else:
        if forwards_movement:
          print("step EAST")
          p.sendline(M_EAST)
        else:
          print("step WEST")
          p.sendline(M_WEST)

      r = p.readuntil(choice)
 
      move = M_NORTH
      print("DIRECTION: north")
      print("move {}".format(cnt))
      cnt += 1

    if redford in r:
        break
