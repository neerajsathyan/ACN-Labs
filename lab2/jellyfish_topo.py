# # Copyright 2020 Lin Wang
#
# # This code is part of the Advanced Computer Networks (2020) course at Vrije
# # Universiteit Amsterdam.
#
# # Licensed under the Apache License, Version 2.0 (the "License"); you may not
# # use this file except in compliance with the License. You may obtain a copy
# # of the License at
#
# #   http://www.apache.org/licenses/LICENSE-2.0
#
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# # WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# # License for the specific language governing permissions and limitations
# # under the License.
#
# import sys
# import random
# import queue
#
#
# # Class for an edge in the graph
# class Edge:
# 	def __init__(self):
# 		self.lnode = None
# 		self.rnode = None
#
# 	def remove(self):
# 		self.lnode.edges.remove(self)
# 		self.rnode.edges.remove(self)
# 		self.lnode = None
# 		self.rnode = None
#
#
# # Class for a node in the graph
# class Node:
# 	def __init__(self, id, type):
# 		self.edges = []
# 		self.id = id
# 		self.type = type
#
# 	# Add an edge connected to another node
# 	def add_edge(self, node):
# 		edge = Edge()
# 		edge.lnode = self
# 		edge.rnode = node
# 		self.edges.append(edge)
# 		node.edges.append(edge)
# 		return edge
#
# 	# Remove an edge from the node
# 	def remove_edge(self, edge):
# 		self.edges.remove(edge)
#
# 	# Decide if another node is a neighbor
# 	def is_neighbor(self, node):
# 		for edge in self.edges:
# 			if edge.lnode == node or edge.rnode == node:
# 				return True
# 		return False
#
#
# class Jellyfish:
#
# 	def __init__(self, num_servers, num_switches, num_ports, network_report=False):
# 		self.servers = []
# 		self.switches = []
#
# 		# optional report of the network configuration
# 		self.network_report = network_report
#
# 		self.generate(num_servers, num_switches, num_ports)
#
# 	def generate(self, num_servers, num_switches, num_ports):
#
# 		# TODO: code for generating the jellyfish topology
#
# 		# initiate num_switches
# 		self.servers = [Node(i, 'server') for i in range(num_servers)]
# 		self.switches = [Node(i, 'switch') for i in range(num_switches)]
#
# 		if num_ports <= 1:
# 			raise ValueError('Please use a higher value than one for num_ports')
#
# 		portsFree = True
#
# 		if num_switches > 1:
# 			while portsFree:
# 				# select two switches random uniformly
# 				rand1 = int(random.uniform(0, num_switches))
# 				rand2 = int(random.uniform(0, num_switches))
#
# 				S1 = self.switches[rand1]
# 				S2 = self.switches[rand2]
#
# 				# redo if the two switches are the same or neighbours
# 				if S1 == S2 or S1.is_neighbor(S2):
# 					continue
#
# 				else:
# 					# add edge if the two ports have free ports
# 					if len(S1.edges) < num_ports and len(S2.edges) < num_ports:
# 						S1.add_edge(S2)
# 				# print(f'Adding edge between nodes: {rand1} - {rand2}')
#
# 				# count the number of switches that have free ports and count their amount of edges
# 				freeSwitches, nEdges = list(
# 					zip(*[[len(switch.edges) < num_ports - 2, len(switch.edges)] for switch in self.switches]))
# 				nFreeSwitches = freeSwitches.count(True)
#
# 				# stop when no more switches can be connected or all switches are already interconnected
# 				if nFreeSwitches <= 1 or nEdges.count(num_switches - 1) == num_switches:
# 					portsFree = False
# 			# print(f'Stopped adding edges')
#
# 			# reconnect edges to switches with two or more free ports
# 			twoPlusFree = True
# 			while twoPlusFree:
#
# 				twoPlusFound = False
#
# 				for i, S in enumerate(self.switches):
# 					# switch has two or more ports free
# 					if len(S.edges) < num_ports - 1:
# 						# print(f'Switch {i} had {num_ports - len(S.edges)} free ports')
#
# 						# randomly disconnect an edge from a switch
# 						x, y = self.randomly_disconnet(num_switches)
#
# 						S.add_edge(x)
# 						S.add_edge(y)
#
# 						# print(f'Switch {i} now has {num_ports - len(S.edges)} free ports')
#
# 						# a switch with two or more free ports was found
# 						twoPlusFound = True
#
# 				if not twoPlusFound:
# 					twoPlusFree = False
#
# 		connectable_switches = []
#
# 		# connect remaining ports of switches to servers
# 		connection_count = []
# 		for i, switch in enumerate(self.switches):
# 			if len(switch.edges) < num_ports:
# 				connectable_switches.append(switch)
#
# 			connection_count.append(len(switch.edges))
#
# 		# keep connecting servers to switches while possible
# 		while connectable_switches:
#
# 			freeServerPorts = True
#
# 			for i, server in enumerate(self.servers):
#
# 				# stop if there are no more connectable switches
# 				if len(connectable_switches) < 1:
# 					freeServerPorts = False
# 					break
#
# 				elif len(server.edges) < num_ports:
# 					# random uniformly select a switch that can be connected to
# 					rand = int(random.uniform(0, len(connectable_switches)))
# 					rand_switch = connectable_switches[rand]
#
# 					# lay the connection between server and random switch
# 					server.add_edge(rand_switch)
#
# 					# remove switch from 'connectable_switches' list
# 					connectable_switches.pop(rand)
# 					freeServerPorts = True
# 				else:
# 					freeServerPorts = False
#
# 			# stop connecting if there are no more server ports available
# 			if not freeServerPorts:
# 				break
#
# 		# optional network report
# 		if self.network_report:
# 			print(f'Network report:')
# 			print(f'Switches ({num_switches}):')
#
# 			for i, switch in enumerate(self.switches):
# 				not_used = num_ports - len(switch.edges)
# 				servers_connected = len(switch.edges) - connection_count[i]
#
# 				print(
# 					f'	- Switch {i:2} has {connection_count[i]} switches, {servers_connected} servers connected and {not_used} unused ports')
#
# 			print(f'Servers ({num_servers}):')
# 			for i, server in enumerate(self.servers):
# 				not_used = num_ports - len(switch.edges)
#
# 				print(f'	- Server {i:2} has {len(server.edges)} switches connected and {not_used} unused ports')
#
# 		return
#
# 	def randomly_disconnet(self, num_switches):
#
# 		while True:
# 			# select two switches random uniformly
# 			rand1 = int(random.uniform(0, num_switches))
# 			rand2 = int(random.uniform(0, num_switches))
#
# 			S1 = self.switches[rand1]
# 			S2 = self.switches[rand2]
#
# 			# redo if the two switches are the same or either switch has no edges
# 			if S1 == S2 or len(S1.edges) == 0 or len(S2.edges) == 0:
# 				continue
#
# 			# remove a random edge
# 			S1_edge = S1.edges[int(random.uniform(0, len(S1.edges)))]
# 			S2_edge = S2.edges[int(random.uniform(0, len(S2.edges)))]
#
# 			S1.remove_edge(S1_edge)
# 			S2.remove_edge(S2_edge)
#
# 			# return the switches from which edges are disconnected
# 			return S1, S2
#
#
# class Fattree:
#
# 	def __init__(self, num_ports, network_report=False):
# 		self.servers = []
# 		self.switches = []
# 		self.generate(num_ports)
# 		# optional report of the network configuration
# 		self.network_report = network_report
# 		# Store ids
# 		self.core_switch_list = []
# 		self.agg_switch_list = []
# 		self.edge_switch_list = []
# 		self.server_list = []
#
# 		self.generate(num_ports)
#
# 	def generate(self, num_ports):
# 		if num_ports <= 1:
# 			raise ValueError('Please use a higher value than one for num_ports')
#
# 		# No of pods..
# 		pods = num_ports
#
# 		# No of servers per switch (leaves of penultimate node)
# 		end = pods / 2
#
# 		# No of Core Switches..
# 		core_switch_count = (num_ports / 2) ** 2
#
# 		# No of Aggregate Switches..
# 		agg_switch_count = (num_ports / 2) * num_ports
#
# 		# No of Edge Switches..
# 		edge_switch_count = agg_switch_count
#
# 		# No of Servers..
# 		server_count = (num_ports ** 3) / 4
#
# 		# Create Servers..
# 		self.servers = [Node(i, 'server') for i in range(server_count)]
# 		# initiate num_switches
# 		# self.servers = [Node(i, 'server') for i in range(num_servers)]
# 		# self.switches = [Node(i, 'switch') for i in range(num_switches)]
#
# 		# Create edge switches..
# 		edge_switch_starting_id = 0
# 		edge_switch_ending_id = edge_switch_starting_id + (edge_switch_count - 1)
# 		self.switches = [Node(i + edge_switch_starting_id, 'edge switch') for i in range(edge_switch_count)]
#
# 		# Create Aggregate switches..
# 		agg_switch_starting_id = edge_switch_ending_id + 1
# 		agg_switch_ending_id = agg_switch_starting_id + (agg_switch_count - 1)
# 		self.switches = [Node(i + agg_switch_starting_id, 'aggregate switch') for i in range(agg_switch_count)]
#
# 		# Create Core switches..
# 		core_switch_starting_id = agg_switch_ending_id + 1
# 		core_switch_ending_id = core_switch_starting_id + (core_switch_count - 1)
# 		self.switches = [Node(i + core_switch_starting_id, 'core switch') for i in range(core_switch_count)]
#
# 		# Create Edges Between Servers and Edge Switches..
# 		server_id = 0
# 		for i in range(edge_switch_starting_id, edge_switch_ending_id + 1):
# 			for j in range(num_ports / 2):
# 				self.servers[server_id].add_edge(self.switches[i])
# 				server_id += 1
#
# 		# Create Edges Between Edge Switches and Aggregate Switches..
# 		for i in range(agg_switch_starting_id, agg_switch_ending_id + 1):
# 			for j in range(num_ports / 2):
# 				self.switches[i].add_edge(self.switches[i-(j+edge_switch_count)])
#
# 		# Create Edges Between Aggregate Switches and Core Switches..
# 		for i in range(core_switch_starting_id, core_switch_ending_id + 1):
# 			for j in range(num_ports / 2):
# 				self.switches[i].add_edge(self.switches[i-(j+agg_switch_count)])
#
# 		# optional network report
# 		if self.network_report:
# 			print(f'Network report:')
# 			print(f'Edge Switches ({edge_switch_count}):')
# 			print(f'Aggregate Switches ({agg_switch_count}):')
# 			print(f'Core Switches ({core_switch_count}):')
#
# 			for i, switch in enumerate(self.switches):
# 				not_used = num_ports - len(switch.edges)
# 				servers_connected = 0
# 				for j in switch.edges:
# 					if j.lnode
#
# 				print(
# 					f'	- Switch {i:2} has {connection_count[i]} switches, {servers_connected} servers connected and {not_used} unused ports')
#
# 			print(f'Servers ({num_servers}):')
# 			for i, server in enumerate(self.servers):
# 				not_used = num_ports - len(switch.edges)
#
# 				print(
# 					f'	- Server {i:2} has {len(server.edges)} switches connected and {not_used} unused ports')
#
# 		return
#
#
# # command line usage
# def main(argv):
# 	topotype = argv[0]
#
# 	if topotype == 'jellyfish':
# 		if len(argv[1:]) == 3:
# 			num_servers = int(argv[1])
# 			num_switches = int(argv[2])
# 			num_ports = int(argv[3])
# 		elif len(argv[1:]) == 4:
# 			num_servers = int(argv[1])
# 			num_switches = int(argv[2])
# 			num_ports = int(argv[3])
#
# 			if argv[4] == 'report':
# 				network_report = True
# 			else:
# 				raise ValueError('Usage: $ python3 topo.py jellyfish num_servers num_switches num_ports (report')
#
# 			# build the topo
# 			topology = Jellyfish(num_servers, num_switches, num_ports, network_report=network_report)
# 			# save the topo in a dictionary for later use in mininet
# 			jellyfish_topo = {topotype: (lambda: topology)}
# 		else:
# 			raise ValueError('Usage: $ python3 topo.py jellyfish num_servers num_switches num_ports (report')
#
#
# 	elif topotype == 'fattree':
# 		if len(argv[1:]) == 1:
# 			num_ports = int(argv[1])
# 		elif len(argv[1:]) == 2:
# 			num_ports = int(argv[1])
# 			if argv[4] == 'report':
# 				network_report = True
# 			else:
# 				raise ValueError('Usage: $ python3 topo.py fattree num_ports report')
# 		else:
# 			raise ValueError('Usage: $ python3 topo.py fattree num_ports report')
# 		# build the topo
# 		topology = Fattree(num_ports, network_report=network_report)
# 		# save the topo in a dictionary for later use in mininet
# 		fattree_topo = {topotype: (lambda: topology)}
#
# 	else:
# 		raise ValueError('See the documentation in our report for usage of topo.py')
#
#
# if __name__ == "__main__":
# 	main(sys.argv[1:])
