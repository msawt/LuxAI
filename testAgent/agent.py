import math, sys

if __package__ == "":
    # for kaggle-environments
    from lux.game import Game
    from lux.game_map import Position,Cell, RESOURCE_TYPES
    from lux.constants import Constants
    from lux.game_constants import GAME_CONSTANTS
    from lux import annotate
else:
    # for CLI tool
    from .lux.game import Game
    from .lux.game_map import Position,Cell, RESOURCE_TYPES
    from .lux.constants import Constants
    from .lux.game_constants import GAME_CONSTANTS
    from .lux import annotate

DIRECTIONS = Constants.DIRECTIONS
game_state = None


"""

HOW TO TRAIN THIS AI:
	- Each UNIT that is created is assigned a number, and we keep track of each individual's 'score'
		- For WORKERS: Score is calcualted by the total fuel values transferred from it to a CART or CITY as well as the score of any CITIES created by the worker and the number of roads pillaged
			-(Worker-to-worker transfers are not included to avoid loops)
		- For CARTS: Score is calculated by the total fuel values transferred from it to a CITY
			- Could also include the number of roads created by the CART

	- Each CITY that is created is assigned a number, and we keep track of the UNITS and the RESEARCH that a city creates
		- The total value of the UNITS and the RESEARCH that the CITY creates will contribute to the score of the tile

	- For both UNITS and CITIES, dying reduces score to 0
		- Could try adjusting this value (ie a UNIT could sacrifice itself for value)

POTENTIAL METHODS:
    - Q-learning
    - Each UNIT and CITY will have an LSTM associated with it

USEFUL VALUES:
    - Max Inventory
        - CART: 2000
        - WORKER: 100

    - Total fuel needed for a UNIT to survive a full night
        - CART: 100
        - WORKER: 40

    - Total fuel needed for a CITY to survive a full night
        - 30 - 5 * number of adjacent friendly CityTiles

    - General Knowledge
        - Even in the top performing AI games, most of the cities that the AI builds end up dying. Maybe don't prioritize saving cities as much as saving the worker?
        - Wood is more efficient for building cities than uranium or coal. However, it's difficult to 

"""
"""

BASIC GARBAGE AI:

"""

def getBestResourceTile(resource_tiles,worker,destinations,researched_coal,researched_uranium): #Gets the resource tile with the highest FUEL/TURN and the highest NUM RESOURCE/TURN based on research level

    bestFTile = None
    bestFValue = -math.inf

    bestRTile = None
    bestRValue = -math.inf

    for resource_tile in resource_tiles:
        dist = resource_tile.pos.distance_to(worker.pos)
        dist += 1 #Get rid of divide by 0 errors, shouldn't change anything else

        if str(resource_tile.pos) not in destinations:
        ###COAL FUEL PER TURN: 50
        ###COAL RESOURCE PER TURN: 5
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL: 
                if researched_coal:
                    #FUEL
                    if (50/dist)>bestFValue:
                        bestFValue = 50/dist
                        bestFTile = resource_tile

                    #RESOURCE
                    if (5/dist)>bestRValue:
                        bestRValue = 5/dist
                        bestRTile = resource_tile
                else:
                    continue

            ###URANIUM FUEL PER TURN: 80
            ###URANIUM RESOURCE PER TURN: 2
            elif resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM:
                if researched_uranium:
                    #FUEL
                    if (80/dist)>bestFValue:
                        bestFValue = 80/dist
                        bestFTile = resource_tile

                    #RESOURCE
                    if (2/dist)>bestRValue:
                        bestRValue = 2/dist
                        bestRTile = resource_tile
                else:
                    continue

            ###WOOD FUEL PER TURN: 20
            ###WOOD RESOURCE PER TURN: 20
            else:
                #FUEL
                if (20/dist)>bestFValue:
                    bestFValue = 20/dist
                    bestFTile = resource_tile

                #RESOURCE
                if (20/dist)>bestRValue:
                    bestRValue = 20/dist
                    bestRTile = resource_tile
    return bestFTile,bestRTile

def getBestCityTile(city_tiles,worker,width,height,resource_tiles): #Gets the nearest tile with the higest number of adjacent cityTiles as well as the closest tile adjacent to a city
    
    #priorities: adjacency, then distance

    best_city = None
    best_dist = math.inf
    best_numAdjacent = -math.inf

    closeset_city = None
    closest_dist = math.inf

    for x in range(width):
        for y in range(height):

            posi = Position(x,y)
            numAdjacent = 0
            dist = worker.pos.distance_to(posi)

            cellAtLoc = game_state.map.get_cell_by_pos(posi)

            if cellAtLoc.citytile == None and cellAtLoc.resource == None:

                for city in city_tiles:
                    if posi.is_adjacent(city.pos) and posi.equals(city.pos)==False:
                        numAdjacent+=1

                if numAdjacent > best_numAdjacent: #If there's a tile with more adjacents, use that one
                    best_numAdjacent = numAdjacent
                    best_dist = dist
                    best_city = posi


                elif numAdjacent==best_numAdjacent: #If there's a tie, pick the closeset one
                    if dist < best_dist:
                        best_dist = dist
                        best_city = posi

                if dist < closest_dist: #Find the closest tile adjacent to your city
                    closest_city = posi
                    closest_dist = dist

    return best_city,closest_city

def getNearestCity(city_tiles,worker): #Gets the pos of the cityTile nearest to the worker
    bestDist = math.inf
    bestCity = None
    for city in city_tiles:
        dist = worker.pos.distance_to(city.pos)
        if dist < bestDist:
            bestDist = dist
            bestCity = city
    return bestCity         

def getNearestCityInNeed(cities_in_need,worker,player): #Gets the pos of the cityTile nearest to the worker that needs more fuel
    bestDist = math.inf
    bestCity = None

    listOfCities = []
    for city in player.cities.values():
        if city.cityid in cities_in_need:
            listOfCities.append(city)

    for cityIN in listOfCities:
        for cityTile in cityIN.citytiles:
            dist = worker.pos.distance_to(cityTile.pos)
            if dist < bestDist:
                bestDist = dist
                bestCity = cityTile
    return bestCity
            

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

    resource_tiles: list[Cell] = []
    for y in range(width):
        for x in range(height   ):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)

########################################################################################## GET DATA ABOUT STATE OF GAME


    ##################### DATA ABOUT TURN/NIGHT
    turn_in_phase = (game_state.turn % 40)+1 #turn on a cycle from 1-40
    if turn_in_phase > 29:
        #It is night
        turns_until_night=0
    else:
        turns_until_night=30-turn_in_phase

    ##################### DATA ABOUT UNITS
    numWorkers = 0
    for unit in player.units:
        if unit.is_worker() or unit.is_cart():
            numWorkers+=1

    cityTiles =  []

    for city in player.cities.values():
        cityTiles += city.citytiles
    numCityTiles = len(cityTiles)

    ##################### RECORD ALL DESTINATIONS OF WORKERS
    destinations = {} #pos: 


########################################################################################## GETS ALL CITIES WHO WILL NOT LAST UNTIL END OF GAME

    cities_in_need = {} #CityID:TurnsLeft(Including Day Turns)
    for k,city in player.cities.items():

        turnsLeft = 0
        turnsLeft += turns_until_night

        fuel_consumption_per_night_cycle = 10*city.get_light_upkeep()
        turnsLeft += 40*(city.fuel//fuel_consumption_per_night_cycle)
        turnsLeft += city.fuel//city.get_light_upkeep()
        if turnsLeft < (360-game_state.turn):
            cities_in_need[city.cityid] = turnsLeft

##########################################################################################
    # we iterate over all our units and do something with them
    for unit in player.units:

        ################################################ WORKER
        if unit.is_worker() and unit.can_act():

            action = ""

            if unit.get_cargo_space_left() > 0:
                # if the worker has space in cargo, lets find the best resource tile and try to mine it
                bestFTile,bestRTile = getBestResourceTile(resource_tiles,unit,destinations,player.researched_coal(),player.researched_uranium())

                if cities_in_need == {} or all(x >= 20 for x in cities_in_need.values()): #If the city has enough fuel for the next 30 turns, then go get resources to build more cities
                    closest_resource_tile = bestRTile

                elif unit.get_cargo_space_left() < 100:                                   #If not, go get resources to maximize fuel OR deliver current fuel to city
                    nearestCity = getNearestCityInNeed(cities_in_need,unit,player)
                    if cities_in_need[nearestCity.cityid] >= nearestCity.pos.distance_to(unit.pos) and (cities_in_need[nearestCity.cityid] - turns_until_night) < 10: 
                        #If the time it takes to get there is less than the time it takes for the city to die AND the city won't survive the next night cycle, go to the city and deposit
                        action = 'deposit'
                        closest_resource_tile = bestFTile                                 #Just so the code runs, shouldn't be used
                    else:
                        closest_resource_tile = bestFTile
                else:                                                                     #If you don't have any inventory, go mining
                    closest_resource_tile = bestFTile

                if closest_resource_tile is not None:
                    destinations[str(closest_resource_tile.pos)] = True
                    if action == 'deposit':
                        if unit.pos.distance_to(nearestCity.pos) > 1:
                            actions.append(unit.move(unit.pos.direction_to(nearestCity.pos)))
                        else:
                            if unit.cargo.uranium > 0:
                                actions.append(unit.transfer(nearestCity.cityid,Constants.RESOURCE_TYPES.URANIUM,unit.cargo.uranium))
                            elif unit.cargo.coal > 0:
                                actions.append(unit.transfer(nearestCity.cityid,Constants.RESOURCE_TYPES.COAL,unit.cargo.coal))
                            else:
                                actions.append(unit.transfer(nearestCity.cityid,Constants.RESOURCE_TYPES.WOOD,unit.cargo.wood))
                    else:
                        actions.append(unit.move(unit.pos.direction_to(closest_resource_tile.pos)))

            elif unit.get_cargo_space_left==0:
                if len(cityTiles) > 0:
                    best_city,closest_city = getBestCityTile(cityTiles,unit,width,height,resource_tiles)
                    if cities_in_need == {}:                            #If the city is good until the end of the game, build a cityTile as close to you as possible
                        closest_city_tile = closest_city
                        a = "build"
                    elif all(x >= 15 for x in cities_in_need.values()): #If the city is good for at least 15 more turns, build a cityTile in the most valuable spot
                        closest_city_tile = best_city
                        a = "build"
                    else:                                               #If the city will survive less than 15 turns, desposit resources into the nearest cityTile    
                        closest_city_tile = getNearestCity(cityTiles,unit)
                        a = "deposit"

                    if closest_city_tile is not None:
                        if a=='build':
                            actions.append(annotate.circle(closest_city_tile.x, closest_city_tile.y))
                            if unit.pos==closest_city_tile:
                                actions.append(unit.build_city())
                            else:
                                actions.append(unit.move(unit.pos.direction_to(closest_city_tile)))
                        elif a=='deposit':
                            actions.append(annotate.x(closest_city_tile.pos.x, closest_city_tile.pos.y))
                            if unit.pos==closest_city_tile.pos:         #Since you can transfer resource when you're one tile away, you don't need to move directly onto the cityTile. However, moving onto the tile saves units from dying to Nighttime.
                                if unit.cargo.uranium > 0:
                                    actions.append(unit.transfer(closest_city_tile.cityid,Constants.RESOURCE_TYPES.URANIUM,unit.cargo.uranium))
                                elif unit.cargo.coal > 0:
                                    actions.append(unit.transfer(closest_city_tile.cityid,Constants.RESOURCE_TYPES.COAL,unit.cargo.coal))
                                else:
                                    actions.append(unit.transfer(closest_city_tile.cityid,Constants.RESOURCE_TYPES.WOOD,unit.cargo.wood))
                        else:
                            move_dir = unit.pos.direction_to(closest_city_tile)
                            actions.append(unit.move(move_dir)) 
                else:
                    actions.append(unit.build_city())

        ################################################ CITYTILE
    for city in cityTiles:
        if city.can_act():
            #If you can create a worker, create one. Otherwise, research.
            if numWorkers < numCityTiles:
                actions.append(city.build_worker())
            else:
                actions.append(city.research())


    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    
    return actions
