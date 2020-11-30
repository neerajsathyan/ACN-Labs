import topo
from collections import defaultdict

def default_dict():
		return defaultdict(default_dict)

def dijkstra_shortest_path(servers, switches, report=False):
	# only use the connected servers and switches in the network
	all_servers = [server for server in servers if len(server.edges) > 0]
	switches = [switch for switch in switches if len(switch.edges) > 0]

	possible_server_pairs = int(len(all_servers)/2)
	# possible_server_pairs = len(all_servers)

	dijksta_table = default_dict()


	for start_id in range(possible_server_pairs):

		servers = all_servers[start_id:]
		# servers = all_servers

		if not servers:
			break

		# create two lists of visited and unvisited servers
		visited = []
		unvisited = [server for server in servers] + [switch for switch in switches]


		# add servers and switches to the dijkstra table
		for vertex in unvisited:
			dijksta_table[start_id][vertex.id][vertex.type]['dist'] = float('inf')
			dijksta_table[start_id][vertex.id][vertex.type]['prev']['type'] = None
			dijksta_table[start_id][vertex.id][vertex.type]['prev']['id'] = None

		# set starting point and set its distance to the starting point to zero
		starting_point = servers[0]
		current_vertex = starting_point
		dijksta_table[start_id][starting_point.id][starting_point.type]['dist'] = 0
		

		# create a table with, for each server, its distance from the starting point and its previous vertex
		while unvisited:

			for edge in current_vertex.edges:

				# left node has same id but is of a different type (switch and server)
				if edge.lnode.id == current_vertex.id:
					if not edge.lnode.type == current_vertex.type:
						neighbor = edge.lnode
				else:
					neighbor = edge.lnode

				# right node has same id but different type (switch and server)
				if edge.rnode.id == current_vertex.id:
					if not edge.rnode.type == current_vertex.type:
						neighbor = edge.rnode
				else:
					neighbor = edge.rnode

				if neighbor in unvisited:

					distance = dijksta_table[start_id][current_vertex.id][current_vertex.type]['dist'] + 1

					if distance < dijksta_table[start_id][neighbor.id][neighbor.type]['dist']:

						dijksta_table[start_id][neighbor.id][neighbor.type]['dist'] = distance
						dijksta_table[start_id][neighbor.id][neighbor.type]['prev'] = {'type' : current_vertex.type, 'id' : current_vertex.id}

			visited.append(current_vertex)
			unvisited.remove(current_vertex)

			# vertex with the lowest distance in the unvisited list becomes next current vertex
			shortest_dist = float('inf')
			new_vertex = None
			if unvisited:
				for vertex in unvisited:

					distance = dijksta_table[start_id][vertex.id][vertex.type]['dist']
					# print(distance)

					if distance <= shortest_dist:
						# print(distance, shortest_dist)
						shortest_dist = distance

						new_vertex = vertex
				
				

				current_vertex = new_vertex

			# stop if there are no more servers in the unvisited list
			if not any([True for vertex in unvisited if vertex.type == 'server']):
				break
		
	# print Dijkstra Table if requested
	if report:
		
		for starting_id in dijksta_table:
			print()
			print('------------------------------------------------------------')
			print('|                      Dijkstra Table                      |')
			print(f'|                  Start point = server {starting_id:2}                 |')
			print('------------------------------------------------------------')
			print('|    Server/Switch   |     Distance    |   Previous Node   |')
			print('------------------------------------------------------------')
			for target_type in ['server', 'switch', 'edge switch']:
				for id in dijksta_table[starting_id]:
					for type in dijksta_table[starting_id][id]:
						if type == target_type:
							dist = dijksta_table[starting_id][id][type]['dist']
							
							prev_type = dijksta_table[starting_id][id][type]['prev']['type']

							if not prev_type == None and prev_type[:9] == 'aggregate':
								prev_type = prev_type[10:]

							# print(f'prev_type = {prev_type}\n')
							if not prev_type == None and prev_type[:4] == 'edge':
								prev_type = prev_type[5:]

							print_type = type
							if type[:4] == 'edge':
								print_type = type[5:]

							prev_id = dijksta_table[starting_id][id][type]['prev']['id']

							previous_str = prev_type + ' ' + str(prev_id).ljust(6) if not prev_type == None else '  ' + str(None).ljust(11)

							print(f"|     {print_type} {id:3}     |   {dist:6}        |     {previous_str} |")

				print('------------------------------------------------------------')

			print()

	return dijksta_table, len(all_servers)



def shortest_path_list(dijkstra_table, start_id, end_id, n_servers):


	if start_id >= n_servers or end_id >= n_servers:
		return None


	reversed_path = True

	if start_id > end_id:
		reversed_path = False
		start_id, end_id = end_id, start_id

	prev_id = dijkstra_table[start_id][end_id]['server']['prev']['id']
	prev_type = dijkstra_table[start_id][end_id]['server']['prev']['type']

	# print(prev_type)
	# print()
	# print(dijkstra_table.keys())
	# print(dijkstra_table[0])
	# print()


	# print(dijkstra_table)
	shortest_path = [('server', end_id)]
	while not (prev_id != start_id and prev_type == 'server'):

		# print(dijkstra_table[start_id][prev_id].values())

		try: 
			new_prev_id = dijkstra_table[start_id][prev_id][prev_type]['prev']['id']
			new_prev_type = dijkstra_table[start_id][prev_id][prev_type]['prev']['type']

			if new_prev_id == None or new_prev_type == None:
				break

			shortest_path.append((prev_type, prev_id))

			prev_id = new_prev_id
			prev_type = new_prev_type

		except:
			break

	shortest_path.append((prev_type, prev_id))

	if reversed_path:
		shortest_path.reverse()
	return shortest_path
