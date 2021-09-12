from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import math
import sys
import random
import numpy as np
from numpy.lib.shape_base import split
import numpy as np
import random
import copy
from collections import namedtuple, deque, defaultdict
import os

from torch._C import device
from torch.random import seed

import torch
import torch.nn.functional as F 
import torch.nn as nn
from torch.autograd import Variable
import torch.optim as optim

from typing import Dict
import sys

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def generate_offset_map(Hmap, row_c, col_c):
    Hmap_copy = Hmap.copy()
    v_shift = row_c - 16
    h_shift = col_c - 16
    h_index = (np.arange(32) + h_shift) % 32
    v_index = (np.arange(32) + v_shift) % 32
    temp = Hmap_copy[:, v_index]
    
    return temp[:, :, h_index]

class ReplayBuffer:                                                             #This class loads the input data into memory (functions like a torch dataloader)
    def __init__(self, buffer_size, batch_size, seed):
        self.memory = deque(maxlen=buffer_size)
        self.batch_size = batch_size
        self.experience = namedtuple("Experience", field_names=["state", "action", "new_state", "reward", "done"])
        self.seed = random.seed(seed)

    def add(self, state, action, new_state, reward, done):
        e = self.experience(state=state, action=action, new_state=new_state, reward=reward, done=done)
        self.memory.append(e)

    def sample(self):
        experiences = random.sample(self.memory, k=self.batch_size)             #Gets a number of experiences from memory and send them to device (GPU)

        states1 = torch.from_numpy(np.stack([e.state for e in experiences if e is not None], axis=0)).float().to(device)
        actions = torch.from_numpy(np.stack([e.action for e in experiences if e is not None], axis=0)).float().to(device)
        states2 = torch.from_numpy(np.stack([e.new_state for e in experiences if e is not None], axis=0)).float().to(device)
        rewards = torch.from_numpy(np.stack([e.reward for e in experiences if e is not None], axis=0)).float().to(device)
        dones = torch.from_numpy(np.stack([e.done for e in experiences if e is not None], axis=0)).float().to(device)

        return (states1, actions, states2, rewards, dones)

    def __len__(self):
        return len(self.memory)

class Obs():                                                                    # Feeds the state of the game at every turn to a format that is readable by the NN
    def __init__(self, observation):
        self.observation = observation

        self.wood_map = np.zeros((32,32)) #x/y
        self.coal_map = np.zeros((32,32)) #x/y
        self.uran_map = np.zeros((32,32)) #x/y

        self.worker_cooldown = np.zeros((2,32,32)) #Team, x/y
        self.worker_capacity = np.zeros((2, 32, 32)) #Team, x/y

        self.cart_cooldown = np.zeros((2, 32, 32)) #Team, x/y
        self.cart_capacity = np.zeros((2, 32, 32)) #Team, x/y

        self.city_tiles_cooldown = np.zeros((2, 32, 32)) #Team, x/y
        self.city_tiles_fuel = np.zeros((2, 32, 32)) #Team, x/y

        self.step = self.observation["observation"]["step"] #Turn number (?)

        pad_size_width = (32 - self.observation[0]["observation"]["width"]) // 2 #Since the NN must have the same input size, boards with a smaller width/height are padded with 0s
        pad_size_length = (32 - self.observation[0]["observation"]["height"]) // 2

        self.worker_pos_dict = {} 
        self.ct_pos_dict = {}

        for player in range(1):
            ups = observation[player]["observation"]["updates"]
            cities = {}
            for row in ups:
                splits = row.split(" ")
                if splits[0] == "r":
                  if splits[1] == "wood":
                    self.wood_map[(
                      int(splits[2]) + pad_size_width,
                      int(splits[3]) + pad_size_length)] = int(float(splits[4]))
                  elif splits[1] == "uranium":
                    self.uran_map[(
                      int(splits[2]) + pad_size_width, 
                      int(splits[3]) + pad_size_length)] = int(float(splits[4]))
                  elif splits[1] == "coal":
                    self.coal_map[(
                        int(splits[2]) + pad_size_width, 
                        int(splits[3]) + pad_size_length)] = int(float(splits[4]))
                elif splits[0] == "c":
                  cities[splits[2]] = int(splits[3])
                elif splits[0] == "u":
                  self.worker_capacity[(
                    int(splits[2]),
                    int(splits[4]) + pad_size_width,
                    int(splits[5]) + pad_size_length
                  )] = int(splits[7]) + int(splits[8]) + int(splits[9])
                  self.worker_cooldown[(
                    int(splits[2]),
                    int(splits[4]) + pad_size_width,
                    int(splits[5]) + pad_size_length
                  )] = int(splits[6])
                  self.worker_pos_dict[(
                    int(splits[4]) + pad_size_width, 
                    int(splits[5]) + pad_size_length)] = splits[3] 
                elif splits[0] == "ct":
                  city_fuel = cities.get( splits[2] )
                  self.city_tiles_cooldown[(
                    int(splits[1]), 
                    int(splits[3]) + pad_size_width, 
                    int(splits[4]) + pad_size_length)] = int(splits[5])
                  self.city_tiles_fuel[(
                    int(splits[1]), 
                    int(splits[3]) + pad_size_width, 
                    int(splits[4]) + pad_size_length)] = int(city_fuel)
                  self.ct_pos_dict[(
                    int(splits[3]) + pad_size_width, 
                    int(splits[4]) + pad_size_length)] = splits[2]
                
        self.wood_map = np.expand_dims(self.wood_map, axis=0)
        self.uran_map= np.expand_dims(self.uran_map, axis=0)
        self.coal_map = np.expand_dims(self.coal_map, axis=0)

        self.state = np.concatenate((
        self.wood_map / 1000, self.uran_map / 1000, self.coal_map / 1000, 
        self.worker_cooldown / 2, self.worker_capacity / 100, 
        self.city_tiles_fuel / 1000, self.city_tiles_cooldown / 10 ), axis=0)

def action_to_tensor(action_list, worker_pos_dict, ct_pos_dict): #Takes the list of actions for all units and returns a 
  action_dict = {}
  for action in action_list:
    splits = action.split(" ")
    #print(splits)
    if splits[0] == "m":
      action_dict[splits[1]] = splits[2]
    elif splits[0] == "bcity":
      action_dict[splits[1]] = splits[0]
    elif splits[0] == "bw":
      action_dict[(splits[1], splits[2])] = splits[0]
    elif splits[0] == "r":
      action_dict[(splits[1], splits[2])] = splits[0]

  actions = {
    "n": 0,
    "s": 1,
    "w": 2,
    "e": 3,
    "stay":4,
    "bcity": 5,
    "bw":6,
    "r":7,
    "n":8
  }
  #print(action_dict)

  entity_action_tensor = np.zeros((9, 32, 32)) #Action Type, x/y
  if len(worker_pos_dict) > 0:
    for pos, id in worker_pos_dict.items():
      if id not in action_dict:
        entity_action_tensor[5, int(pos[0]), int(pos[1])] = 1
      else:
#         print(action_dict[id])
#         print(actions[action_dict[id]])
        entity_action_tensor[actions[action_dict[id]], pos[0], pos[1]] = 1
    
  if len(ct_pos_dict) > 0:
    for pos, id in ct_pos_dict.items():
      if id not in action_dict:
        entity_action_tensor[6, int(pos[0]), int(pos[1])] = 1
      else:
        entity_action_tensor[actions[action_dict[(int(pos[0]), int(pos[1]))]], int(pos[0]), int(pos[1])] = 1
  #print(entity_action_tensor.shape)
  return entity_action_tensor

def log_to_action(entity_action_prob, is_worker = True): #Takes a set of probabilities (NN output) and turns it into an action readable by the game
    entity_action_dim = {
        0: "n",
        1: "s",
        2: "w",
        3: "e",
        4: "stay",
        5: "bcity",
        6: "bw",
        7: "r",
        8: "None"
    }

    if is_worker:
        ordered_actions = [(entity_action_dim[i], entity_action_prob[i]) for i in range(6)]
    else:
        ordered_actions = [(entity_action_dim[i], entity_action_prob[i]) for i in range(6, 9)]

        ordered_actions = sorted(ordered_actions, key=lambda x: x[1], reverse=True)

    return ordered_actions

def single_conv5(in_channels, out_channels):                                    #This is a single layer of the NN. 
  return nn.Sequential(
    nn.Conv2d(in_channels, out_channels, 5),
    nn.BatchNorm2d(out_channels, eps = 1e-5, momentum=0.1), #Used to make the network more stable in training
    nn.Tanh() #Activation function
  )
def single_conv3(in_channels, out_channels):
  return nn.Sequential(
    nn.Conv2d(in_channels, out_channels, 3),
    nn.BatchNorm2d(out_channels, eps = 1e-5, momentum=0.1),
    nn.Tanh()
  )
def single_conv2(in_channels, out_channels):
  return nn.Sequential(
    nn.Conv2d(in_channels, out_channels, 2),
    nn.BatchNorm2d(out_channels, eps = 1e-5, momentum=0.1),
    nn.Tanh()
  )

class Actor (nn.Module):
  def __init__(self,Cin,out_size):
    super(Actor, self).__init__()
    self.Cin = Cin
    self.out_size = out_size

    #Layer definitions go here
    self.maxpool = nn.MaxPool2d(2)

    self.layer1 = single_conv3(Cin, 16)
    self.layer2_1 = single_conv5(16, 32)

    self.layer2_2 = single_conv5(32, 32)
    self.layer2_3 = single_conv3(32, 32)

    self.layer3_1 = single_conv3(32, 32)
    self.layer3_2 = single_conv3(32, 64)
    self.layer4 = single_conv5(64, 128)

    self.fc1 = nn.Sequential(
        nn.Linear(128*2*2, 64),
        nn.ReLU(inplace=True)
        )
    self.fc2 = nn.Linear(64, out_size)

  def forward(self,x1):
    #Forward pass goes here

    x1 = self.layer1(x1)
    x1 = self.layer2_1(x1)

    x1 = self.layer2_2(x1)
    x1 = self.layer2_3(x1)

    x1 = self.maxpool(x1)

    x1 = self.layer3_1(x1)
    x1 = self.layer3_2(x1)
    x1 = self.layer4(x1)


    x1 = x1.view(-1, 128*2*2) #Reshapes tensor

    x = self.fc1(x1)
    
    out = self.fc2(x)

    return out
  
class ActorAgent():                                                             #This combines the different models for workers and citytiles into a single class. 
    def __init__(self, cin, out_worker, out_ctiles, worker_path, ctile_path):
        self.cin = cin #Input dimension
        self.out_worker = out_worker
        self.out_ctiles = out_ctiles

        self.worker_model = Actor(Cin=cin, out_size=out_worker).to(device)
        self.ctiles_model = Actor(Cin=cin, out_size=out_ctiles).to(device)

        self.worker_model.load_state_dict(torch.load(worker_path))
        self.ctiles_model.load_state_dict(torch.load(ctile_path))

        self.ctiles_model.eval()
        self.worker_model.eval()

    def act(self, state, is_worker = True):
        state = torch.from_numpy(state).float().to(device)
        if is_worker:
            with torch.no_grad():
                out = self.worker_model(state)
                out = out.cpu().data.numpy()
        else: 
            with torch.no_grad():
                out = self.ctiles_model(state)
                out = out.cpu().data.numpy()
        return out

# path1 = os.path.join(os.getcwd(),"models/worker_model_v29.pt")
# path2 = os.path.join(os.getcwd(),"models/ctiles_model_v29.pt")

path1 = os.path.join(os.getcwd(),"models/worker_model_v29.pt")
path2 =  os.path.join(os.getcwd(),"models/ctiles_model_v29.pt")

#a = ActorAgent(cin = 11, out_worker=6, out_ctiles=3,worker_path=path1,ctile_path=path2)
a = ActorAgent(cin = 11, out_worker=6, out_ctiles=3,worker_path=path1,ctile_path=path2)
game_state = None

def agent(observation, configuration):
    global game_state
    global a

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])

    obs = Obs(observation)
    current_state = obs.state
    player = game_state.players[observation.player]

    direction_dict = {
            0: Constants.DIRECTIONS.NORTH,
            1: Constants.DIRECTIONS.SOUTH,
            2: Constants.DIRECTIONS.WEST,
            3: Constants.DIRECTIONS.EAST,
    }

    actions = []
    unit_actions = {}
    ctiles_ation = {}
    for unit in player.units:
        if unit.can_act():
            if unit.is_worker():
                offset_state = generate_offset_map(current_state, unit.pos.x, unit.pos.y)
                offset_state_expand = np.expand_dims(offset_state, axis=0)
                player_action = np.argmax( a.act(offset_state_expand, is_worker=True) ) #The NN output is a list of [out_worker] probabilities. Take the highest probability action
                unit_actions[(unit.pos.x, unit.pos.y)] = [offset_state, player_action]      #The actions for each unit are coded based on the x and y values (not sure why)
                action = None
                if player_action < 4: #0,1,2,3 = Movement
                    action = unit.move(direction_dict[player_action])
                elif player_action == 5: #5 = Build
                    action = unit.build_city()
                if action is not None:
                    actions.append(action)
    cities = list(player.cities.values())
    if len(cities) > 0:
        for city in cities:
            for city_tile in city.citytiles[::-1]:
                if city_tile.can_act():
                    offset_state = generate_offset_map(current_state, city_tile.pos.x, city_tile.pos.y)
                    offset_state_expand = np.expand_dims(offset_state, axis=0)
                    ctile_action = np.argmax( a.act( offset_state_expand, is_worker=False ))
                    ctiles_ation[(city_tile.pos.x, city_tile.pos.y)] = [offset_state, ctile_action]
                    action = None
                    if ctile_action == 0:
                        action = city_tile.build_worker()
                    elif ctile_action == 1:
                        action = city_tile.research()
                    if action is not None:
                        actions.append(action)

    return actions