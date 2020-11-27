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

        # optional report of the network configuration
        self.network_report = network_report

        self.generate(num_servers, num_switches, num_ports)

    def generate(self, num_servers, num_switches, num_ports):

        # TODO: code for generating the jellyfish topology

        # initiate num_switches
        self.servers = [Node(i, 'server') for i in range(num_servers)]
        self.switches = [Node(i, 'switch') for i in range(num_switches)]

        if num_ports <= 1:
            raise ValueError('Please use a higher value than one for num_ports')

        portsFree = True

        if num_switches > 1:
            while portsFree:
                # select two switches random uniformly
                rand1 = int(random.uniform(0, num_switches))
                rand2 = int(random.uniform(0, num_switches))

                S1 = self.switches[rand1]
                S2 = self.switches[rand2]

                # redo if the two switches are the same or neighbours
                if S1 == S2 or S1.is_neighbor(S2):
                    continue

                else:
                    # add edge if the two ports have free ports
                    if len(S1.edges) < num_ports and len(S2.edges) < num_ports:
                        S1.add_edge(S2)
                # print(f'Adding edge between nodes: {rand1} - {rand2}')

                # count the number of switches that have at least two free ports and count their amount of edges
                freeSwitches, nEdges = list(
                    zip(*[[len(switch.edges) < num_ports - 2, len(switch.edges)] for switch in self.switches]))
                nFreeSwitches = freeSwitches.count(True)

                # stop when no more switches can be connected or all switches are already interconnected
                if nFreeSwitches <= 1 or nEdges.count(num_switches - 1) == num_switches:
                    portsFree = False
            # print(f'Stopped adding edges')

            # reconnect edges to switches with two or more free ports
            twoPlusFree = True
            while twoPlusFree:

                twoPlusFound = False

                for i, S in enumerate(self.switches):
                    # switch has two or more ports free
                    if len(S.edges) <= num_ports - 2:
                        # print(f'Switch {i} had {num_ports - len(S.edges)} free ports')

                        # randomly disconnect an edge from a switch
                        x, y = self.randomly_disconnet(num_switches)

                        S.add_edge(x)
                        S.add_edge(y)

                        # print(f'Switch {i} now has {num_ports - len(S.edges)} free ports')

                        # a switch with two or more free ports was found
                        twoPlusFound = True

                # stop reconnecting switches if there are none with two or more free ports
                if not twoPlusFound:
                    twoPlusFree = False

        connectable_switches = []

        # connect remaining ports of switches to servers
        connection_count = []
        for i, switch in enumerate(self.switches):
            if len(switch.edges) < num_ports:
                connectable_switches.append(switch)

            connection_count.append(len(switch.edges))

        # keep connecting servers to switches while possible
        while connectable_switches:

            freeServerPorts = True

            for i, server in enumerate(self.servers):

                # stop if there are no more connectable switches
                if len(connectable_switches) < 1:
                    freeServerPorts = False
                    break

                elif len(server.edges) < num_ports:
                    # random uniformly select a switch that can be connected to
                    rand = int(random.uniform(0, len(connectable_switches)))
                    rand_switch = connectable_switches[rand]

                    # lay the connection between server and random switch
                    server.add_edge(rand_switch)

                    # remove switch from 'connectable_switches' list
                    connectable_switches.pop(rand)
                    freeServerPorts = True
                else:
                    freeServerPorts = False

            # stop connecting if there are no more server ports available
            if not freeServerPorts:
                break

        # optional network report
        if self.network_report:
            print(f'\nNetwork report:')
            print(f'Switches ({num_switches}):')

            for i, switch in enumerate(self.switches):
                not_used = num_ports - len(switch.edges)
                servers_connected = len(switch.edges) - connection_count[i]

                print(
                    f'	- Switch {i:2} has {connection_count[i]:2} switches, {servers_connected} servers connected and {not_used} unused ports')

            print(f'Servers ({num_servers}):')
            for i, server in enumerate(self.servers):
                not_used = num_ports - len(server.edges)

                print(f'	- Server {i:2} has {len(server.edges)} switches connected and {not_used} unused ports')

    def randomly_disconnet(self, num_switches):

        while True:
            # select two switches random uniformly
            rand1 = int(random.uniform(0, num_switches))
            rand2 = int(random.uniform(0, num_switches))

            S1 = self.switches[rand1]
            S2 = self.switches[rand2]

            # redo if the two switches are the same or either switch has no edges
            if S1 == S2 or len(S1.edges) == 0 or len(S2.edges) == 0:
                continue

            # remove a random edge
            S1_edge = S1.edges[int(random.uniform(0, len(S1.edges)))]
            S2_edge = S2.edges[int(random.uniform(0, len(S2.edges)))]

            S1.remove_edge(S1_edge)
            S2.remove_edge(S2_edge)

            # return the switches from which edges are disconnected
            return S1, S2


def dijkstra_shortest_path(servers, switches, report=False):
    # only use the connected servers and switches in the network
    servers = [server for server in servers if len(server.edges) > 0]
    switches = [switch for switch in switches if len(switch.edges) > 0]

    # create two lists of visited and unvisited servers
    visited = []
    unvisited = [server for server in servers] + [switch for switch in switches]

    # create a table with, for each server, its disance from the starting point and its previous vertex

    # dijksta_table = {}
    dijksta_table = default_dict()
    # dijksta_table[int {str, {'dist': float, 'prev': None}}

    # add servers and switches to the dijkstra table
    for vertex in unvisited:
        dijksta_table[vertex.id][vertex.type]['dist'] = float('inf')
        dijksta_table[vertex.id][vertex.type]['prev']['type'] = None
        dijksta_table[vertex.id][vertex.type]['prev']['id'] = None

    # set starting point and set its distance to the starting point to zero
    starting_point = unvisited[0]

    dijksta_table[starting_point.id][starting_point.type]['dist'] = 0

    current_vertex = starting_point

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

                distance = dijksta_table[current_vertex.id][current_vertex.type]['dist'] + 1

                if distance < dijksta_table[neighbor.id][neighbor.type]['dist']:
                    dijksta_table[neighbor.id][neighbor.type]['dist'] = distance
                    dijksta_table[neighbor.id][neighbor.type]['prev'] = {'type': current_vertex.type,
                                                                         'id': current_vertex.id}

        # vertex in unvisited with lowest distance to starting points becomes next vertex

        # print('finished')

        visited.append(current_vertex)
        unvisited.remove(current_vertex)

        # vertex with the lowest distance in the unvisited list becomes next current vertex

        shortest_dist = float('inf')
        new_vertex = None
        if unvisited:
            for vertex in unvisited:

                distance = dijksta_table[vertex.id][vertex.type]['dist']
                # print(distance)

                if distance <= shortest_dist:
                    # print(distance, shortest_dist)
                    shortest_dist = distance

                    new_vertex = vertex

            current_vertex = new_vertex

        # stop if there are no more servers in the unvisited list
        if not any([True for vertex in unvisited if vertex.type == 'server']):
            break

    # use more readable output table of dijkstra's algorithm with only servers
    # dijksta_table_output = {(server.id, server.type): {'dist': float('inf'), 'prev': None} for server in servers}
    # print(dijksta_table_output)
    # {server.id: {'dist': float('inf'), 'prev': None} for server in servers}
    if report:
        print()
        print('----------------------------------------------------------')
        print('|                    Dijkstra Table                      |')
        print('----------------------------------------------------------')
        print('|   Server/Switch  |     Distance    |   Previous Node   |')
        print('----------------------------------------------------------')

        for target_type in ['server', 'switch']:
            for id in dijksta_table:
                for type in dijksta_table[id]:
                    if type == target_type:
                        dist = dijksta_table[id][type]['dist']

                        prev_type = dijksta_table[id][type]['prev']['type']
                        prev_id = dijksta_table[id][type]['prev']['id']

                        previous_str = prev_type + ' ' + str(prev_id).ljust(6) if not prev_type == None else '  ' + str(
                            None).ljust(11)

                        print(f"|     {type} {id}     |   {dist:6}        |     {previous_str} |")

            print('----------------------------------------------------------')

        print()

    return dijksta_table


def default_dict():
    return defaultdict(default_dict)


def pathlength_distribution(dijkstra_table):
    length_distr = defaultdict(lambda: 0)
    server_pairs = 0

    for id in dijkstra_table:
        for type in dijkstra_table[id]:
            distance = dijkstra_table[id][type]['dist']

            length_distr[distance] += 1
            server_pairs += 1

    return length_distr, server_pairs


def plot_figure_9c(distribution_dict):
    plt.ylim(0, 1)

    plt.bar(distribution_dict.keys(), distribution_dict.values())
    plt.show()

    return


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
        # initiate num_switches
        # self.servers = [Node(i, 'server') for i in range(num_servers)]
        # self.switches = [Node(i, 'switch') for i in range(num_switches)]

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
                    self.switches[int(i + j)].add_edge(self.switches[int(agg_switch_ending_id + 1 + (j * end + k))])

        # agg_switch_iter = agg_switch_starting_id
        # #Iterate in steps of k/2 switches per step..
        # for i in range(core_switch_starting_id, core_switch_ending_id + 1, int(num_ports/2)):
        # 	#Split into k/2 groups
        # 	for j in range(int(num_ports/2)):
        # 		#iterate over those k/2 core switch..
        # 		for k  in range(int(num_ports/2)):
        # 			self.switches[i+j].add_edges(self.switches[])
        # 		self.switches[i].add_edges(self.switches[])
        #
        # 		self.switches[i].add_edge(self.switches[i-(j+agg_switch_count)])

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


# command line usage
def main(argv):
    arg1 = argv[0]

    if arg1 == 'jellyfish':
        if len(argv[1:]) == 3:
            num_servers = int(argv[1])
            num_switches = int(argv[2])
            num_ports = int(argv[3])
        elif len(argv[1:]) > 3:
            num_servers = int(argv[1])
            num_switches = int(argv[2])
            num_ports = int(argv[3])

            network_report = False
            dijkstra = False
            dijkstra_report = False

            if len(argv[1:]) == 4:
                if argv[4] == '-nr':
                    network_report = True

                elif argv[4] == 'dijkstra':
                    dijkstra = True

                else:
                    raise ValueError(
                        'Usage: $ python topo.py jellyfish num_servers num_switches num_ports (-nr dijkstra -r)')

            elif len(argv[1:]) == 5:
                if argv[4] == 'dijkstra' and argv[5] == '-nr':
                    network_report = True
                    dijkstra = True

                elif argv[4] == 'dijkstra' and argv[5] == '-dr':
                    dijkstra = True
                    dijkstra_report = True

                elif argv[4] == 'dijkstra' and argv[5] == '-fr':
                    network_report = True
                    dijkstra = True
                    dijkstra_report = True

                else:
                    raise ValueError(
                        'Usage: $ python topo.py jellyfish num_servers num_switches num_ports (-nr dijkstra -r)')

            else:
                raise ValueError(
                    'Usage: $ python topo.py jellyfish num_servers num_switches num_ports (-nr dijkstra -r)')

            # build the topo and save the servers and switches
            jellyfish_topo = Jellyfish(num_servers, num_switches, num_ports, network_report=network_report)

            if dijkstra:
                servers = jellyfish_topo.servers
                switches = jellyfish_topo.switches

                dijkstra_table = dijkstra_shortest_path(servers, switches, report=dijkstra_report)

        else:
            raise ValueError('Usage: $ python topo.py jellyfish num_servers num_switches num_ports (report)')

    elif arg1 == 'fattree':
        network_report = False
        if len(argv[1:]) == 1:
            num_ports = int(argv[1])
        elif len(argv[1:]) == 2:
            num_ports = int(argv[1])
            if argv[2] == 'report':
                network_report = True
        else:
            raise ValueError('Usage: $ python3 topo.py fattree num_ports report')
        # build the topo

        fattree_topo = Fattree(num_ports, network_report=network_report)



    elif arg1 == '9c':

        network_report = False
        dijkstra = False
        dijkstra_report = False

        num_servers = 686
        num_switches = 686
        num_ports = 14

        if len(argv[1:]) > 0:

            if argv[1] == '-nr':
                network_report = True
                dijkstra = True

            elif argv[1] == '-dr':
                dijkstra = True
                dijkstra_report = True

            elif argv[1] == '-fr':
                network_report = True
                dijkstra = True
                dijkstra_report = True

            else:
                raise ValueError('See the documentation in our report for usage of topo.py')

        total_pathlen_distr = defaultdict(lambda: 0)
        total_pairs = 0

        total_pathlen_distr_ft = defaultdict(lambda: 0)
        total_pairs_ft = 0

        iterations = 10
        for i in range(iterations):
            print(f'Iteration {i + 1} / {iterations}', end='\r')

            jellyfish_topo = Jellyfish(num_servers, num_switches, num_ports, network_report=network_report)

            servers = jellyfish_topo.servers
            switches = jellyfish_topo.switches

            dijkstra_table = dijkstra_shortest_path(servers, switches, report=dijkstra_report)
            length_distr, num_pairs = pathlength_distribution(dijkstra_table)

            for path_len in length_distr.keys():
                # print(path_len, total_pathlen_distr[path_len])
                total_pathlen_distr[path_len] += length_distr[path_len]

            total_pairs += num_pairs

        fattree_topo = Fattree(num_ports, network_report=network_report)
        fattree_servers = fattree_topo.servers
        fattree_switches = fattree_topo.switches

        dijkstra_table_ft = dijkstra_shortest_path(fattree_servers, fattree_switches, report=dijkstra_report)
        length_distr_ft, num_pairs_ft = pathlength_distribution(dijkstra_table_ft)

        for path_len in length_distr_ft.keys():
            # print(path_len, total_pathlen_distr[path_len])
            total_pathlen_distr_ft[path_len] += length_distr_ft[path_len]

        total_pairs_ft += num_pairs_ft

        for distance in total_pathlen_distr.keys():
            total_pathlen_distr[distance] /= total_pairs

        for distance in total_pathlen_distr_ft.keys():
            total_pathlen_distr_ft[distance] /= total_pairs_ft

        plot_figure_9c(total_pathlen_distr)
        plot_figure_9c(total_pathlen_distr_ft)


    else:
        raise ValueError('See the documentation in our report for usage of topo.py')


if __name__ == "__main__":
    main(sys.argv[1:])
