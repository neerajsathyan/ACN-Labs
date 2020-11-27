# Copyright 2020 Lin Wang

# This code is part of the Advanced Computer Networks (2020) course at Vrije 
# Universiteit Amsterdam.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import random
import queue
from collections import defaultdict
import matplotlib.pyplot as plt
import math


# Class for an edge in the graph
class Edge:
	def __init__(self):
		self.lnode = None
		self.rnode = None
	
	def remove(self):
		self.lnode.edges.remove(self)
		self.rnode.edges.remove(self)
		self.lnode = None
		self.rnode = None

# Class for a node in the graph
class Node:
	def __init__(self, id, type):
		self.edges = []
		self.id = id
		self.type = type

	# Add an edge connected to another node
	def add_edge(self, node):
		edge = Edge()
		edge.lnode = self
		edge.rnode = node
		self.edges.append(edge)
		node.edges.append(edge)
		return edge

	# Remove an edge from the node
	def remove_edge(self, edge):
		self.edges.remove(edge)

	# Decide if another node is a neighbor
	def is_neighbor(self, node):
		for edge in self.edges:
			if edge.lnode == node or edge.rnode == node:
				return True
		return False


class Jellyfish:

	def __init__(self, num_servers, num_switches, num_ports, network_report=False):
		self.servers = []
		self.switches = []
		self.nSwitches = 0

		# optional report of the network configuration
		self.network_report = network_report

		self.generate(num_servers, num_switches, num_ports)

		

	def generate(self, num_servers, num_switches, num_ports):

		# initiate servers and switches
		self.servers = [Node(i, 'server') for i in range(num_servers)]
		self.switches = [Node(i, 'switch') for i in range(num_switches)]

		if num_ports <= 1:
			raise ValueError('Please use a higher value than one for num_ports')

		portsFree = True

		self.nSwitches = len(self.switches)


		openPorts = [num_ports for i in range(num_switches)]

		# Connect each server with a switch..
		for n in range(num_servers):
			self.servers[n].add_edge(self.switches[n])
			openPorts[n] -= 1

		# Manage the potential link, fully populate the set before creating
		links = set()
		switchesLeft = self.nSwitches
		consecFails = 0

		while switchesLeft > 1 and consecFails < 10:
			s1 = random.randrange(self.nSwitches)
			while openPorts[s1] == 0:
				s1 = random.randrange(self.nSwitches)

			s2 = random.randrange(self.nSwitches)
			while openPorts[s2] == 0 or s1 == s2:
				s2 = random.randrange(self.nSwitches)

			if (s1, s2) in links:
				consecFails += 1
			else:
				consecFails = 0
				links.add((s1, s2))
				links.add((s2, s1))

				openPorts[s1] -= 1
				openPorts[s2] -= 1

				if openPorts[s1] == 0:
					switchesLeft -= 1
				if openPorts[s2] == 0:
					switchesLeft -= 1

		if switchesLeft > 0:
			for i in range(self.nSwitches):
				while openPorts[i] > 1:
					while True:
						# incremental expansion..
						rLink = random.choice(links)
						if (i, rLink[0]) in links:
							continue
						if (i, rLink[1]) in links:
							continue

						# Remove links
						links.remove(rLink)
						links.remove(rLink[::-1])

						# Add new links
						links.add((i, rLink[0]))
						links.add((rLink[0], i))
						links.add((i, rLink[1]))
						links.add((rLink[1], i))

						openPorts[i] -= 2

		for link in links:
			# prevent double counting..
			if link[0] < link[1]:
				self.switches[link[0]].add_edge(self.switches[link[1]])


	def randomly_disconnet(self, S, num_switches):

		while True:
			# select two switches random uniformly 
			rand1 = int(random.uniform(0, num_switches))
			rand2 = int(random.uniform(0, num_switches))

			S1 = self.switches[rand1]
			S2 = self.switches[rand2]

			# redo if the two switches are the same or either switch has no edges
			if S1 == S2 or len(S1.edges) == 0 or len(S2.edges) == 0:
				continue
			elif S1 == S or S2 == S:
				continue

			# remove a random edge
			S1_edge = S1.edges[int(random.uniform(0, len(S1.edges)))]
			S2_edge = S2.edges[int(random.uniform(0, len(S2.edges)))]

			S1.remove_edge(S1_edge)
			S2.remove_edge(S2_edge)

			# return the switches from which edges are disconnected
			return S1,S2


class Fattree:

	def __init__(self, num_ports, network_report=False):
		self.servers = []
		self.switches = []
		# optional report of the network configuration
		# Store ids
		self.core_switch_list = []
		self.agg_switch_list = []
		self.edge_switch_list = []
		self.server_list = []
		self.network_report = network_report
		self.generate(num_ports)

	def generate(self, num_ports):
		if num_ports <= 1:
			raise ValueError('Please use a higher value than one for num_ports')

		# No of pods..
		pods = int(num_ports)

		# No of servers per switch (leaves of penultimate node)
		end = int(pods / 2)

		# No of Core Switches..
		core_switch_count = int((num_ports / 2) ** 2)

		# No of Aggregate Switches..
		agg_switch_count = int((num_ports / 2) * num_ports)

		# No of Edge Switches..
		edge_switch_count = int(agg_switch_count)

		# No of Servers..
		server_count = int((num_ports ** 3) / 4)

		# Create Servers..
		for i in range(server_count):
			self.servers.append(Node(i, 'server'))

		# Create edge switches..
		edge_switch_starting_id = 0
		edge_switch_ending_id = edge_switch_starting_id + (edge_switch_count - 1)
		for i in range(edge_switch_count):
			self.switches.append(Node(i + edge_switch_starting_id, 'edge switch'))

		# Create Aggregate switches..
		agg_switch_starting_id = edge_switch_ending_id + 1
		agg_switch_ending_id = agg_switch_starting_id + (agg_switch_count - 1)
		for i in range(agg_switch_count):
			self.switches.append(Node(i + agg_switch_starting_id, 'aggregate switch'))

		# Create Core switches..
		core_switch_starting_id = agg_switch_ending_id + 1
		core_switch_ending_id = core_switch_starting_id + (core_switch_count - 1)
		for i in range(core_switch_count):
			self.switches.append(Node(i + core_switch_starting_id, 'core switch'))

		# Create Edges Between Servers and Edge Switches..
		server_id = 0
		for i in range(edge_switch_starting_id, edge_switch_ending_id + 1):
			for j in range(int(num_ports / 2)):
				self.servers[server_id].add_edge(self.switches[i])
				server_id += 1

		# Create Edges Between Edge Switches and Aggregate Switches..
		for i in range(agg_switch_starting_id, agg_switch_ending_id + 1):
			for j in range(int(num_ports / 2)):
				self.switches[i].add_edge(self.switches[int((end * math.floor(i / end) + j) - edge_switch_count)])

		# Create Edges Between Aggregate Switches and Core Switches..

		for i in range(agg_switch_starting_id, agg_switch_ending_id + 1, end):
			for j in range(int(num_ports / 2)):
				for k in range(int(num_ports / 2)):
					g = int(edge_switch_ending_id + 1 + (j * end + k))
					self.switches[int(i + j)].add_edge(self.switches[int(agg_switch_ending_id + 1 + (j * end + k))])

		# optional network report
		if self.network_report:
			print(f'Network report:')
			print(f'Edge Switches ({edge_switch_count}):')
			print(f'Aggregate Switches ({agg_switch_count}):')
			print(f'Core Switches ({core_switch_count}):')

			print("\n Server Details: ")
			for server in self.servers:
				print("\n Server: %d has %d connected switches and %d unused port.", server.id, len(server.edges),
					  num_ports - len(server.edges))
			print("\n Switch Details: ")
			for switch in self.switches:
				print("\n Switch: %d has %d connections and %d unused port.", switch.id, len(switch.edges),
					  num_ports - len(switch.edges))

		return





