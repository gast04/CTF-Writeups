from keras.models import Sequential
from keras.layers import Dense
from keras.callbacks import EarlyStopping

import numpy as np
import pickle, sys

import emu_handler as eh

#create model
model = Sequential()
TRAIN = False

def loadTrainingData():
  # load training data
  with open('training_sequences.pickle', 'rb') as handle:
    training_set = pickle.load(handle)

  train_x = []
  train_y = []
  for s in training_set:
    train_x.append(s[:-2].copy())
    train_y.append(s[-2:].copy())

  return train_x, train_y

def createModel():
  # create Model
  model.add(Dense(200, activation='relu', input_shape=(200,)))
  model.add(Dense(200, activation='relu'))
  model.add(Dense(100, activation='relu'))
  model.add(Dense(2))

def preTrainModel():
  train_x, train_y = loadTrainingData()

  # compile model
  model.compile(optimizer='adam', loss='mean_squared_error')

  # reshape data
  resh_x = np.array(train_x)
  resh_y = np.array(train_y)

  #set early stopping monitor, (not used)
  # early_stopping_monitor = EarlyStopping(patience=3)

  #train model
  model.fit(resh_x, resh_y, epochs=40)
  #, validation_split=0.2)
  #, callbacks=[early_stopping_monitor])

# train model before starting the game
createModel()

if TRAIN:
  preTrainModel()
  model.save("savedmodel")
  sys.exit(0)

# else
model.load_weights("savedmodel")

healths = [-1]*2
def printStats(update, attack):
  if update[0] != -1:
    healths[0] = update[0]
  if update[1] != -1:
    healths[1] = update[1]

  dr_att = "missed"
  if update[3] != -1:
    dr_att = update[3]

  h_att = "missed"
  if update[2] != -1:
    h_att = update[2]

  if attack == 0:
    h_att = "shield"

  # statistics print
  print("Pred: {}, DH: {}, HH: {} | DA: {}, HA: {}".format(attack, 
    healths[0], healths[1], dr_att, h_att))

#
# Generate a new Sequence before every Attack
#
def playGame():
  # predict attack or shield
  while True:

    # move this line outside of the loop, to initialze it once
    dr_seq = eh.getDragonSequence()
    pred = model.predict(np.array(dr_seq[-200:]).reshape(1,200))
    pred0 = int(round(pred[0][0]))
    pred1 = int(round(pred[0][1]))

    # we miss, dr hit
    if pred0 == 0 and pred1 == 1:
      attack = 0 # shield

    # we hit, he hit
    elif pred0 == 1 and pred1 == 1:
      attack = 0 # shield

    # we hit, he miss
    elif pred0 == 1 and pred1 == 0:
      attack = 1

    # we miss, he miss
    elif pred0 == 0 and pred1 == 0:
      attack = 0

    update,past = eh.attackDragon(attack, dr_seq)
    if past == -1:
      print("Dragon killed")
      #eh.getInteractive()
      break
      
    if past == -2:
      print("You died...")
      eh.getInteractive()
      break

    # print player stats
    printStats(update, attack)


print("\nStarting the Game\n")

eh.startGame()

#for i in range(10):
#  eh.lookForDragon(move)
#sys.exit(0)

move = eh.lookForDragon()
eh.startFigth()
playGame()
# killed one Dragon
print("\n")
#eh.getInteractive()

for i in range(20):
  healths = [-1]*2
  move = eh.lookForDragon(move)
  if move == b"x":
    break # no more dragons
  eh.startFigth()
  playGame()

#eh.getInteractive()

# we need to talk to valis now
# he is in the bottom left corner
eh.moveToValis()
eh.talk() # give RED BULL
eh.talk() # to get REDFORD Quest

# now we have to find REDFORD
eh.findRedford()
eh.talk() # get PowerStrip

# move to Valis again and give him all he needs
eh.moveToValis()
while True:
  r = eh.talk() # give valis all he needs

  if b"I'VE DONE EVERYTHING..." in r:
    # process flag
    tmp = r.split(b"HERE IT IS:")[1]
    tmp = tmp.split(b"THERE IS A TAVERN HERE.")[0].strip()
    print("FLAG: {}".format(tmp))
    break

eh.getInteractive()
