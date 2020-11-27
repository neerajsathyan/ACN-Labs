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

import math
import queue
import random
import sys
from collections import defaultdict
import copy


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
                        rLink = random.sample(links, 1)[0]
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
            return S1, S2


def default_dict():
    return defaultdict(default_dict)


def dijkstra(servers, switches, source, sink):
    # only use the connected servers and switches in the network
    all_servers = [server for server in servers if len(server.edges) > 0]
    all_switches = [switch for switch in switches if len(switch.edges) > 0]
    if len(source.edges) == 0:
        return None
    dijksta_table = default_dict()

    # create two lists of visited and unvisited servers
    visited = []
    unvisited = [server for server in all_servers] + [switch for switch in all_switches]

    # add servers and switches to the dijkstra table
    for vertex in unvisited:
        dijksta_table[vertex.id][vertex.type]['dist'] = float('inf')
        dijksta_table[vertex.id][vertex.type]['prev']['type'] = None
        dijksta_table[vertex.id][vertex.type]['prev']['id'] = None

    # set starting point and set its distance to the starting point to zero
    starting_point = source
    current_vertex = starting_point
    dijksta_table[starting_point.id][starting_point.type]['dist'] = 0

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

                distance = dijksta_table[current_vertex.id][current_vertex.type]['dist'] + 1

                if distance < dijksta_table[neighbor.id][neighbor.type]['dist']:
                    dijksta_table[neighbor.id][neighbor.type]['dist'] = distance
                    dijksta_table[neighbor.id][neighbor.type]['prev'] = {'type': current_vertex.type,
                                                                         'id': current_vertex.id}

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

    # Add path nodes to return variable..
    ret = [sink]
    curr_node = sink
    while True:
        if dijksta_table[curr_node.id][curr_node.type] is not None:
            next_node_id = dijksta_table[curr_node.id][curr_node.type]['prev']['id']
            next_node_type = dijksta_table[curr_node.id][curr_node.type]['prev']['type']
            next_node = findNode(next_node_id, next_node_type, all_servers, all_switches)
            if next_node is not None:
                ret.append(next_node)
                if source.id == next_node.id and source.type == next_node.type:
                    return ret[::-1]
                curr_node = next_node
            else:
                return None

    return None


def findNode(id, type, servers, switches):
    nodes = servers + switches
    for node in nodes:
        if node.id == id and node.type == type:
            return node
    return None


def remove_edge(node1, node2):
    for edge in node1.edges:
        if (edge.lnode.type == node2.type and edge.lnode.id == node2.id) or (
                edge.rnode.type == node2.type and edge.rnode.id == node2.id):
            node1.remove_edge(edge)
            node2.remove_edge(edge)
            return 1
    return -1


def YenKSP(servers, switches, source, sink, K, ecmp=False):
    A = []
    # TODO:
    A.append(dijkstra(servers, switches, source, sink))

    # Initialize the set to store potential kth shortest path.
    B = []

    if not A[0]:
        return A

    for k in range(1, K):
        # The spur node ranges from the first node to the next to
        # last node in the previous k-shortest path.
        for i in range(len(A[k - 1]) - 1):
            # Spur node is retrieved from the previous k-shortest path, k-1.
            spurNode = A[k - 1][i]
            # spurNodePlusOne = A[k-1]["path"][i+1]

            # The sequence of nodes from the source to the spur node
            # of the previous k-shortest path.
            rootPath = A[k - 1][:i]

            edges_removed = []

            for path in A:
                if len(path) - 1 > i and rootPath == path[:i]:
                    cost = remove_edge(path[i], path[i + 1])
                    if cost == -1:
                        continue
                    edges_removed.append((path[i], path[i + 1], cost))
            print("hello!")
            spurPath = dijkstra(servers, switches, spurNode, sink)
            print("sadsa")
            if spurPath is not None and len(spurPath) > 0:
                totalPath = rootPath + spurPath
                B.append((len(totalPath), totalPath))

            # Add back the edges that were removed from the graph..
            remover = []
            for removed_edge in edges_removed:
                node_start, node_end, cst = removed_edge
                if (node_start.id, node_start.type, node_end.id, node_end.type) in remover or (
                node_end.id, node_end.type, node_start.id, node_start.type) in remover:
                    continue
                node_start.add_edge(node_end)
                remover.append((node_start.id, node_start.type, node_end.id, node_end.type))

        # Sort the potential k-shortest paths by cost..
        # B is already sorted..
        # Add the lowest cost path becomes the k-shortest path.
        B.sort(key=lambda tup: tup[0])
        for tup in B:
            cost_, path_ = tup
            if ecmp:
                if cost_ == len(A[0]) and path_ not in A:
                    # TODO: needs implementation..
                    # We found a new path to add..
                    A.append(path_)
                    break
            else:
                if path_ not in A:
                    # TODO: needs implementation..
                    # We found a new path to add..
                    A.append(path_)
                    break

    return A


def main(argv):
    num_servers = argv[0]  # 3#686
    num_switches = argv[1]  # 6#858  # 245
    num_ports = argv[2]  # 4#14

    # run jellyfish topo
    jellyfish_topo = Jellyfish(num_servers, num_switches, num_ports)
    # jellyfish topo's servers and switches
    servers = jellyfish_topo.servers
    switches = jellyfish_topo.switches

    source = servers[0]
    sink = servers[2]

    # Do for random n server-server pairs and then get the graph..
    tr = YenKSP(servers, switches, source, sink, 8, ecmp=False)
    tr2 = YenKSP(servers, switches, source, sink, 8, ecmp=True)
    tr3 = YenKSP(servers, switches, source, sink, 64, ecmp=True)


if __name__ == "__main__":
    main(sys.argv[1:])
