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

    unit_destinations = [[[[False, False]]*height]*width][0] #Size: width, height; Value: Boolean (1-turn, Path)
    city_tiles = [[[0]*height]*width][0] #Size: width, height; Value: Night Turns Until Death


    ##################### DATA ABOUT TURN/NIGHT
    turn_in_phase = (game_state.turn % 40)+1 #turn on a cycle from 1-40
    if turn_in_phase > 29:
        #It is night
        turns_until_night=0
    else:
        turns_until_night=30-turn_in_phase

    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.resource != None:
            	resource_tiles[x][y] = (cell.resource.type,cell.resource.amount)
            if cell.city_tile != None:
            	#Find city associated with CityTile
            	city = player.cities[cell.city_tile.cityid]
            	#Get number of turns of night that city has left before it dies
            	turnsLeft = city.fuel//city.get_light_upkeep()
            	city_tiles[x][y] = turnsLeft  

    ##################### DATA ABOUT UNITS/CITIES
    numWorkers = 0
    for unit in player.units:
        if unit.is_worker() or unit.is_cart():
            numWorkers+=1

    cityTiles =  []

    for city in player.cities.values():
        cityTiles += city.citytiles
    numCityTiles = len(cityTiles)

    # we iterate over all our units and do something with them
    for unit in player.units:

        if unit.is_worker() and unit.can_act():
        	#Iterate through every tile and find the tile with the highest reward

################################################## FIND ACTION

        	max_reward = -1*math.inf
        	max_coord = None
        	minDist = None

        	for y in range(height):
        		for x in range(width):
        			#Calculate reward
        			reward = 0 #Placeholder
        			dist = unit.pos.distance_to(Position(x,y))
        			if reward > max_reward:
        				max_reward = reward
        				max_coord = (x,y)
        				minDist = dist

        			elif reward == max_reward and dist < minDist: #If the rewards are the same, prioritize the one that is closer to the unit
        				max_reward = reward
        				max_coord = (x,y)
        				minDist = dist


################################################## TAKE ACTION
        	if max_coord != None:
        		if unit.pos.distance_to(Position(max_coord[0],max_coord[1])) == 0: #If you're at the right cell...
        			#Get location of all citytiles
        			adjacentCities = [c for c in cityTiles if unit.pos.is_adjacent(c.pos)]
        			cell = game_state.map.get_cell(x, y)
        			if (city_tiles[max_coord[0]][max_coord[1]] >= 10 or len(adjacentCities)==0) and unit.can_build() and cell.city_tile==None:
        				actions.append(unit.build_city())
        			elif len(adjacentCities) > 0:
        				if unit.cargo.uranium > 0:
        				    actions.append(unit.transfer(adjacentCities[0].cityid,Constants.RESOURCE_TYPES.URANIUM,unit.cargo.uranium))
        				elif unit.cargo.coal > 0:
        				    actions.append(unit.transfer(adjacentCities[0].cityid,Constants.RESOURCE_TYPES.COAL,unit.cargo.coal))
        				else:
        				    actions.append(unit.transfer(adjacentCities[0].cityid,Constants.RESOURCE_TYPES.WOOD,unit.cargo.wood))
        			else:
        				actions.append(unit.move(unit.pos.direction_to(Position(max_coord[0],max_coord[1]))))


        		else:
        			actions.append(unit.move(unit.pos.direction_to(Position(max_coord[0],max_coord[1]))))
        		

        else:



    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    
    return actions
