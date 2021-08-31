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

    ##################### DATA ABOUT UNITS/CITIES
    numWorkers = 0
    for unit in player.units:
        if unit.is_worker() or unit.is_cart():
            numWorkers+=1

    cityTiles =  []

    for city in player.cities.values():
        cityTiles += city.citytiles
    numCityTiles = len(cityTiles)

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

            	### Put turnsLeft on tiles adjacent to all cities (for calculating tile rewards)
            	if (x-1) >= 0:
            		city_tiles[x-1][y] = turnsLeft
            	elif (x+1) < width:
            		city_tiles[x+1][y] = turnsLeft
            	if (y-1) >= 0:
            		city_tiles[x][y-1] = turnsLeft
            	elif (y+1) < height:
            		city_tiles[x][y+1] = turnsLeft
            	###

                resource_fuel_value[x][y] = 0
                resource_amount_value[x][y] = 0
                continue
            
            if cell.has_resource():
                if (cell.resource.type == Constants.RESOURCE_TYPES.COAL) and player.researched_coal():
                    ###CELL IS COAL
                    resource_amount_value[x][y] = 5
                    resource_fuel_value[x][y] = 50
                elif (cell.resource.type == Constants.RESOURCE_TYPES.URANIUM) and player.researched_uraniam():
                    ###CELL IS URANIUM
                    resource_amount_value[x][y] = 2
                    resource_fuel_value[x][y] = 80
                else:
                    ###CELL IS WOOD
                    resource_amount_value[x][y] = 20
                    resource_fuel_value[x][y] = 20
            if (x-1) >= 0:
                temp_cell = game_state.map.get_cell(x-1,y)
                if temp_cell.has_resource():
                    if (temp_cell.resource.type == Constants.RESOURCE_TYPES.COAL) and player.researched_coal():
                        resource_amount_value[x][y] += 5
                        resource_fuel_value[x][y] += 50
                    elif (temp_cell.resource.type == Constants.RESOURCE_TYPES.URANIUM) and player.researched_uraniam():
                        resource_amount_value[x][y] += 2
                        resource_fuel_value[x][y] += 80
                    else:
                        resource_amount_value[x][y] += 20
                        resource_fuel_value[x][y] += 20
            if (x+1) < width:
                temp_cell = game_state.map.get_cell(x+1,y)
                if temp_cell.has_resource():
                    if (temp_cell.resource.type == Constants.RESOURCE_TYPES.COAL) and player.researched_coal():
                        resource_amount_value[x][y] += 5
                        resource_fuel_value[x][y] += 50
                    elif (temp_cell.resource.type == Constants.RESOURCE_TYPES.URANIUM) and player.researched_uraniam():
                        resource_amount_value[x][y] += 2
                        resource_fuel_value[x][y] += 80
                    else:
                        resource_amount_value[x][y] += 20
                        resource_fuel_value[x][y] += 20
            if (y-1) >= 0:
                temp_cell = game_state.map.get_cell(x,y-1)
                if temp_cell.has_resource():
                    if (temp_cell.resource.type == Constants.RESOURCE_TYPES.COAL) and player.researched_coal():
                        resource_amount_value[x][y] += 5
                        resource_fuel_value[x][y] += 50
                    elif (temp_cell.resource.type == Constants.RESOURCE_TYPES.URANIUM) and player.researched_uraniam():
                        resource_amount_value[x][y] += 2
                        resource_fuel_value[x][y] += 80
                    else:
                        resource_amount_value[x][y] += 20
                        resource_fuel_value[x][y] += 20
            if (y+1) < height:
                temp_cell = game_state.map.get_cell(x,y+1)
                if temp_cell.has_resource():
                    if (temp_cell.resource.type == Constants.RESOURCE_TYPES.COAL) and player.researched_coal():
                        resource_amount_value[x][y] += 5
                        resource_fuel_value[x][y] += 50
                    elif (temp_cell.resource.type == Constants.RESOURCE_TYPES.URANIUM) and player.researched_uraniam():
                        resource_amount_value[x][y] += 2
                        resource_fuel_value[x][y] += 80
                    else:
                        resource_amount_value[x][y] += 20
                        resource_fuel_value[x][y] += 20

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
        			try:
        				reward = (unit.get_cargo_capacity()*(resource_amount_value[x][y] + resource_fuel_value[x][y]) - 10*city_tiles[x][y]) / (unit.pos.distance_to(Position(x,y))+1)
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


        			if (city_tiles[max_coord[0]][max_coord[1]] >= 10 or len(adjacentCities)==0) and unit.can_build() and cell.city_tile==None: #Only build a city if all adjacent cities will survive for at least 10 turns
        				actions.append(unit.build_city())
        			elif len(adjacentCities) > 0:																								#If they can't survive another 10 turns, transfer instead
        				if unit.cargo.uranium > 0:
        				    actions.append(unit.transfer(adjacentCities[0].cityid,Constants.RESOURCE_TYPES.URANIUM,unit.cargo.uranium))
        				elif unit.cargo.coal > 0:
        				    actions.append(unit.transfer(adjacentCities[0].cityid,Constants.RESOURCE_TYPES.COAL,unit.cargo.coal))
        				else:
        				    actions.append(unit.transfer(adjacentCities[0].cityid,Constants.RESOURCE_TYPES.WOOD,unit.cargo.wood))
        			else:																														#If you can't build or transfer, do nothing
        				actions.append(unit.move(unit.pos.direction_to(Position(max_coord[0],max_coord[1]))))


        		else:
        			actions.append(unit.move(unit.pos.direction_to(Position(max_coord[0],max_coord[1]))))
        		

        else:



    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    
    return actions
