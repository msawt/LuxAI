import math, sys

if __package__ == "":
    # for kaggle-environments
    from lux.game import Game
    from lux.game_map import Cell, RESOURCE_TYPES
    from lux.constants import Constants
    from lux.game_constants import GAME_CONSTANTS
    from lux import annotate
else:
    # for CLI tool
    from .lux.game import Game
    from .lux.game_map import Cell, RESOURCE_TYPES
    from .lux.constants import Constants
    from .lux.game_constants import GAME_CONSTANTS
    from .lux import annotate

DIRECTIONS = Constants.DIRECTIONS
game_state = None


def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []

    ### AI Code goes down here! ### 
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    resource_tiles = [[[0]*height]*width][0] #Size: width, height; Value: (Type, Amount)
    resource_fuel_value = [[[0]*height]*width][0] #Shows the total fuel value per turn harvested by a worker standing here
    resource_amount_value = [[[0]*height]*width][0] #Shows the total number of resources per turn harvested by a worker standing here

    unit_destinations = [[[(False, False)]*height]*width][0] #Size: width, height; Value: Boolean (1-turn, Path)
    city_tiles = [[[(0, 0)]*height]*width][0] #Size: width, height; Value: (Fuel, Consumption)

    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.resource != None:
            	resource_tiles[x][y] = (cell.resource.type,cell.resource.amount)
            if cell.city_tile != None:



            

    # we iterate over all our units and do something with them
    for unit in player.units:

        if unit.is_worker() and unit.can_act():

        else:



    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    
    return actions
