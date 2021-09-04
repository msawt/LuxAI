import math, sys,random

if __package__ == "":
	# for kaggle-environments
	from lux.game import Game
	from lux.game_map import Position, Cell, RESOURCE_TYPES
	from lux.constants import Constants
	from lux.game_constants import GAME_CONSTANTS
	from lux import annotate
else:
	# for CLI tool
	from .lux.game import Game
	from .lux.game_map import Position, Cell, RESOURCE_TYPES
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

	resource_fuel_value = [[[0]*height]*width][0] #Shows the total fuel value on a given tile
	resource_amount_value = [[[0]*height]*width][0] #Shows the total number of resources per turn on a given tile
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
			cell = game_state.map.get_cell(x,y) #MIGHT BE y,x??????????

			if cell.has_resource():
				if cell.resource.type == Constants.RESOURCE_TYPES.COAL and player.researched_coal():
					###CELL IS COAL
					resource_amount_value[x][y] = 5
					resource_fuel_value[x][y] = 50
				elif cell.resource.type == Constants.RESOURCE_TYPES.URANIUM and player.researched_uranium():
					###CELL IS URANIUM
					resource_amount_value[x][y] = 2
					resource_fuel_value[x][y] = 80
				elif cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
					###CELL IS WOOD
					resource_amount_value[x][y] = 20
					resource_fuel_value[x][y] = 20
			
			"""
			if cell.citytile == None:
				if (x-1) >= 0:
					temp_cell = game_state.map.get_cell(x-1,y)
					if temp_cell.has_resource():
						if temp_cell.resource.type == Constants.RESOURCE_TYPES.COAL and player.researched_coal():
							resource_amount_value[x][y] += 5
							resource_fuel_value[x][y] += 50
						elif temp_cell.resource.type == Constants.RESOURCE_TYPES.URANIUM and player.researched_uranium():
							resource_amount_value[x][y] += 2
							resource_fuel_value[x][y] += 80
						elif temp_cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
							resource_amount_value[x][y] += 20
							resource_fuel_value[x][y] += 20
				if (y+1) < height:
					temp_cell = game_state.map.get_cell(x,y+1)
					if temp_cell.has_resource():
						if temp_cell.resource.type == Constants.RESOURCE_TYPES.COAL and player.researched_coal():
							resource_amount_value[x][y] += 5
							resource_fuel_value[x][y] += 50
						elif temp_cell.resource.type == Constants.RESOURCE_TYPES.URANIUM and player.researched_uranium():
							resource_amount_value[x][y] += 2
							resource_fuel_value[x][y] += 80
						elif temp_cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
							resource_amount_value[x][y] += 20
							resource_fuel_value[x][y] += 20

				if (x+1) < width:
					temp_cell = game_state.map.get_cell(x+1,y)
					if temp_cell.has_resource():
						if temp_cell.resource.type == Constants.RESOURCE_TYPES.COAL and player.researched_coal():
							resource_amount_value[x][y] += 5
							resource_fuel_value[x][y] += 50
						elif temp_cell.resource.type == Constants.RESOURCE_TYPES.URANIUM and player.researched_uranium():
							resource_amount_value[x][y] += 2
							resource_fuel_value[x][y] += 80
						elif temp_cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
							resource_amount_value[x][y] += 20
							resource_fuel_value[x][y] += 20
				if (y-1) >= 0:
					temp_cell = game_state.map.get_cell(x,y-1)
					if temp_cell.has_resource():
						if temp_cell.resource.type == Constants.RESOURCE_TYPES.COAL and player.researched_coal():
							resource_amount_value[x][y] += 5
							resource_fuel_value[x][y] += 50
						elif temp_cell.resource.type == Constants.RESOURCE_TYPES.URANIUM and player.researched_uranium():
							resource_amount_value[x][y] += 2
							resource_fuel_value[x][y] += 80
						elif temp_cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
							resource_amount_value[x][y] += 20
							resource_fuel_value[x][y] += 20
			"""

			if cell.citytile != None and cell.citytile.cityid in player.cities:
				#Find city associated with CityTile
				city = player.cities[cell.citytile.cityid]
				#Get number of turns of night that city has left before it dies
				turnsLeft = city.fuel//city.get_light_upkeep()
				city_tiles[x][y] = turnsLeft + turns_until_night

				resource_fuel_value[x][y] = 0
				resource_amount_value[x][y] = 0
			
			

	# we iterate over all our units and do something with them
	for unit in player.units:

		if unit.is_worker() and unit.can_act():
			#Iterate through every tile and find the tile with the highest reward

################################################## FIND ACTION

			max_reward = -1*math.inf
			max_coord = None
			minDist = math.inf

			for y in range(height):
				for x in range(width):
					#Calculate reward
					reward = (resource_amount_value[x][y] + resource_fuel_value[x][y])

					if (x+1) < width:
						reward += (resource_amount_value[x+1][y] + resource_fuel_value[x+1][y])
					if (x-1) >= 0:
						reward += (resource_amount_value[x-1][y] + resource_fuel_value[x-1][y])
					if (y+1) < height:
						reward += (resource_amount_value[x][y+1] + resource_fuel_value[x][y+1])
					if (y-1) >= 0:
						reward += (resource_amount_value[x][y-1] + resource_fuel_value[x][y-1])


					reward = reward * (unit.get_cargo_space_left()/100)
					if city_tiles[x][y] > 0:
						reward = reward + (100 - 10*city_tiles[x][y])

					if unit.pos.distance_to(Position(x,y)) > 5:
						reward = reward / unit.pos.distance_to(Position(x,y))

					if game_state.map.get_cell(x,y).has_resource()==False and game_state.map.get_cell(x,y).citytile == None and unit.get_cargo_space_left()==0 and any([city.pos.is_adjacent(Position(x,y)) for city in cityTiles]):
						reward = 70

					if unit_destinations[x][y][1] == True: #If a worker is pathing to a tile, then any other workers should not path there
						reward = -1*math.inf

					dist = unit.pos.distance_to(Position(x,y))
					if reward > max_reward:
						max_reward = reward
						max_coord = (x,y)
						minDist = dist

					elif reward == max_reward and dist < minDist: #If the rewards are the same, prioritize the one that is closer to the unit
						max_reward = reward
						max_coord = (x,y)
						minDist = dist

			# actions.append(annotate.sidetext(str(unit.id) + " Cargo Space Left: " + str(unit.get_cargo_space_left())))
			actions.append(annotate.x(max_coord[0],max_coord[1]))
			# actions.append(annotate.sidetext("Highest Reward: " + str(max_reward)))
			# actions.append(annotate.sidetext("Resource Fuel+Amount: " + str(resource_fuel_value[max_coord[0]][max_coord[1]]+resource_amount_value[max_coord[0]][max_coord[1]])))



			# actions.append(annotate.sidetext("Fuel+Amount (19 3): " +str(resource_fuel_value[19][3]+resource_fuel_value[19][3])))

			actions.append(annotate.sidetext("Resource Fuel at " + str(max_coord[0]+1) + " " + str(max_coord[1]) + ": " + str(resource_fuel_value[max_coord[0]+1][max_coord[1]])))
			actions.append(annotate.sidetext("Resource Fuel at " + str(max_coord[0]-1) + " " + str(max_coord[1]) + ": " + str(resource_fuel_value[max_coord[0]-1][max_coord[1]])))
			actions.append(annotate.sidetext("Resource Fuel at " + str(max_coord[0]) + " " + str(max_coord[1]+1) + ": " + str(resource_fuel_value[max_coord[0]][max_coord[1]+1])))
			actions.append(annotate.sidetext("Resource Fuel at " + str(max_coord[0]) + " " + str(max_coord[1]-1) + ": " + str(resource_fuel_value[max_coord[0]][max_coord[1]-1])))
				
			# for city in cityTiles:
			# 	actions.append(annotate.sidetext(city.cityid + " turns left: " + str(city_tiles[city.pos.x][city.pos.y])))

################################################## TAKE ACTION
			if max_coord != None:
				unit_destinations[max_coord[0]][max_coord[1]][1] = True #Update the matrix to show that a unit is pathing to a tile
				if unit.pos.distance_to(Position(max_coord[0],max_coord[1])) == 0:																#If you're at the right cell, take the most appropriate action
					cell = game_state.map.get_cell(max_coord[0],max_coord[1])


					if unit.can_build(game_state.map) and cell.citytile==None:
						actions.append(unit.build_city())
					else:																														#If you can't build or transfer, do nothing
						actions.append(unit.move(unit.pos.direction_to(Position(max_coord[0],max_coord[1]))))


				else:																															#If not, move towards the cell with highest reward
					direction = unit.pos.direction_to(Position(max_coord[0],max_coord[1]))

					#NORTH = TOWARDS Y0; SOUTH = TOWARDS Ymax; EAST = TOWARDS Xmax; WEST = TOWARDS X0
					x,y = max_coord[0],max_coord[1]
					blocked = True
					if direction == DIRECTIONS.NORTH:
						if unit_destinations[x][y-1][0]== False: #If there isnt' already a unit pathing to that tile, update the destinations list and move there
							unit_destinations[x][y-1][0] = True
							blocked = False
					if direction == DIRECTIONS.SOUTH:
						if unit_destinations[x][y+1][0]== False: #If there isnt' already a unit pathing to that tile, update the destinations list and move there
							unit_destinations[x][y+1][0] = True
							blocked = False
					if direction == DIRECTIONS.EAST:
						if unit_destinations[x+1][y][0]== False: #If there isnt' already a unit pathing to that tile, update the destinations list and move there
							unit_destinations[x+1][y][0] = True
							blocked = False
					if direction == DIRECTIONS.WEST:
						if unit_destinations[x-1][y][0]== False: #If there isnt' already a unit pathing to that tile, update the destinations list and move there
							unit_destinations[x-1][y][0] = True
							blocked = False

					if not blocked:
						actions.append(unit.move(direction))
					else: #If blocked, just move in a random cardinal direction
						i = random.randint(1,4)
						if i == 1:
							direction = DIRECTIONS.NORTH
						if i == 2:
							direction = DIRECTIONS.EAST
						if i == 3:
							direction = DIRECTIONS.SOUTH
						if i == 4:
							direction = DIRECTIONS.WEST

						actions.append(unit.move(direction))

	workersCreated = 0
	for city in cityTiles:
		if city.can_act():
			#If you can create a worker, create one. Otherwise, research.
			if (numWorkers+workersCreated) < numCityTiles:
				actions.append(city.build_worker())
				workersCreated += 1
			else:
				actions.append(city.research())

	# actions.append(annotate.sidetext("Resources at 17 6: " + str(resource_fuel_value[17][6]+resource_amount_value[17][6])))
	# actions.append(annotate.sidetext("Resources at 6 17: " + str(resource_fuel_value[6][17]+resource_amount_value[6][17])))

	# actions.append(annotate.sidetext("17 6 has_resource: " + str(game_state.map.get_cell(17,6).has_resource())))
	# actions.append(annotate.sidetext("6 17 has_resource: " + str(game_state.map.get_cell(6,17).has_resource())))

	# actions.append(annotate.sidetext("17 6 type: " + str(game_state.map.get_cell(17,6).resource.type)))
	# #actions.append(annotate.sidetext("6 17 type: " + str(game_state.map.get_cell(6,17).resource.type)))

	# actions.append(annotate.sidetext("17 6 amount: " + str(game_state.map.get_cell(17,6).resource.amount)))
	# #actions.append(annotate.sidetext("6 17 amount: " + str(game_state.map.get_cell(6,17).resource.amount)))
	# # you can add debug annotations using the functions in the annotate object
	# # actions.append(annotate.circle(0, 0))
	
	return actions
