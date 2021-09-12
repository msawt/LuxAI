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

from agent import *

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

if __name__ == "__main__":
    
    def read_input():
        """
        Reads input from stdin
        """
        try:
            return input()
        except EOFError as eof:
            raise SystemExit(eof)
    step = 0
    class Observation(Dict[str, any]):
        def __init__(self, player=0) -> None:
            self.player = player
            # self.updates = []
            # self.step = 0
    observation = Observation()
    observation["updates"] = []
    observation["step"] = 0
    player_id = 0
    while True:
        inputs = read_input()
        observation["updates"].append(inputs)
        
        if step == 0:
            player_id = int(observation["updates"][0])
            observation.player = player_id
        if inputs == "D_DONE":
            actions = agent(observation, None)
            observation["updates"] = []
            step += 1
            observation["step"] = step
            print(",".join(actions))
            print("D_FINISH")