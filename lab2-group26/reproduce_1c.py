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

import topo
import dijkstra
from collections import defaultdict
import matplotlib.pyplot as plt
import sys
import numpy as np


def pathlength_distribution(dijkstra_table):
    length_distr = defaultdict(lambda:0)
    server_pairs = 0

    for start_id in dijkstra_table:
        for id in dijkstra_table[start_id]:
            for type in dijkstra_table[start_id][id]:
                if type == 'server':
                    distance = dijkstra_table[start_id][id][type]['dist']

                    # do not count the root server used in the Dijkstra algorithm
                    if not distance == 0:
                        length_distr[distance] += 1
                        server_pairs += 1

    return length_distr, server_pairs


def plot_figure_9c(distribution_dict, num_servers, num_switches, num_ports, iterarions, topotype=None):
    
    if len(distribution_dict) == 1:
        plt.bar(distribution_dict[0].keys(), distribution_dict[0].values(), width=0.3, label=topotype)

    else:
        bars1 = [key - .15 for key in distribution_dict[0].keys()]
        bars2 = [key + .15 for key in distribution_dict[1].keys()]

        plt.bar(bars1, distribution_dict[0].values(), width=0.3, label='Jellyfish')
        plt.bar(bars2, distribution_dict[1].values(), width=0.3, label='Fattree')

    plt.ylim(0,1)
    plt.xlim(1,7)

    plt.yticks(np.arange(0,11)/10)
    plt.xticks([2,3,4,5,6])

    plt.tick_params(axis=u'both', which=u'both',length=0)

    plt.title(f'Figure 1c \n(servers = {num_servers}, switches = {num_switches}, ports = {num_ports}, iterations = {iterarions})', fontsize=10)
    
    plt.ylabel('Fraction of Server Pairs')
    plt.xlabel('Path length')

    plt.legend()

    plt.show()

    return



# command line usage
def main(argv):

    # no argument executes default case for fig 1.c
    if not argv:
        num_servers = 686
        num_switches = 245
        num_ports = 14

        total_pathlen_distr_Jelly = defaultdict(lambda:0)
        total_pathlen_distr_Fat = defaultdict(lambda:0)
        total_pairs = 0


        # run jellyfish topology for for 10 iterations
        iterations = 10
        for i in range(iterations):
            print(f'Iteration {i+1} / {iterations}', end='\r')
            
            # run jellyfish topo
            jellyfish_topo = topo.Jellyfish(num_servers, num_switches, num_ports)
            
            # jellyfish topo's servers and switches
            servers = jellyfish_topo.servers
            switches = jellyfish_topo.switches

            # run dijkstra's algorithm on both topos
            dijkstra_table = dijkstra.dijkstra_shortest_path(servers, switches)

            # calculate dict['pathlength between servers']['amount of occurences'], num_pairs = total number of server pairs
            length_distr, num_pairs = pathlength_distribution(dijkstra_table)

            for path_len in length_distr.keys():
                total_pathlen_distr_Jelly[path_len] += length_distr[path_len]

            total_pairs += num_pairs


        # average over all iterarions
        for distance in total_pathlen_distr_Jelly.keys():
            total_pathlen_distr_Jelly[distance] /= total_pairs



        # run fattree topology for 1 iteration
        topology = topo.Fattree(num_ports)

        servers = topology.servers
        switches = topology.switches

        dijkstra_table = dijkstra.dijkstra_shortest_path(servers, switches)
        length_distr, num_pairs = pathlength_distribution(dijkstra_table)

        for path_len in length_distr.keys():
            total_pathlen_distr_Fat[path_len] += length_distr[path_len]

        total_pairs += num_pairs


        # average results
        for distance in total_pathlen_distr_Fat.keys():
            total_pathlen_distr_Fat[distance] /= total_pairs
        

        # plot figure 1.c
        plot_figure_9c([total_pathlen_distr_Jelly, total_pathlen_distr_Fat], num_servers, num_switches, num_ports, iterations)

    # else if argumetns are given, execute custom 
    else:
        network_report = False
        dijkstra_report = False

        run_both = False

        # individually test jellyfish or fattree topology
        try: 

            if argv[0] == 'fattree' and bool(type(int(argv[1])) == type(0)):
                num_ports = int(argv[1])
                iterations = 1
                
                # optional report settings
                if len(argv) == 3:

                    if argv[2] == '-dr':
                        dijkstra_report = True

                    elif argv[2] == '-fr':
                        network_report = True
                        dijkstra_report = True


                    elif argv[2] == '-nr':
                        network_report = True

            elif argv[0] == 'jellyfish' and all([bool(type(int(arg)) == type(0)) for arg in argv[1:4]]):

                num_servers = int(argv[1])
                num_switches = int(argv[2])
                num_ports = int(argv[3])

                # set amount of iterations for jellyfish
                if argv[0] == 'jellyfish' and argv[-2] == '-i' and bool(type(int(argv[-1])) == type(0)):
                    iterations = int(argv[-1])

                else:
                    iterations = 1


                # optional report settings
                if len(argv) == 5 or len(argv) == 7:

                    if argv[4] == '-dr':
                        dijkstra_report = True

                    elif argv[4] == '-fr':
                        network_report = True
                        dijkstra_report = True


                    elif argv[4] == '-nr':
                        network_report = True

            elif all([bool(type(int(arg)) == type(0)) for arg in argv[0:3]]):

                num_servers = int(argv[0])
                num_switches = int(argv[1])
                num_ports = int(argv[2])

                iterations = 1
                
                if len(argv) > 3:

                    if argv[3] == '-i' and bool(type(int(argv[4])) == type(0)):

                        iterations = int(argv[4])

            total_pathlen_distr = defaultdict(lambda: 0)
            total_pairs = 0



            for i in range(iterations):
                print(f'Iteration {i + 1} / {iterations}', end='\r')

                # build the topo and save the servers and switches
                if argv[0] == 'jellyfish':
                    jellyfish = topo.Jellyfish(num_servers, num_switches, num_ports, network_report=network_report)
                    servers = jellyfish.servers
                    switches = jellyfish.switches
                elif argv[0] == 'fattree':
                    fattree = topo.Fattree(num_ports, network_report=network_report)
                    servers = fattree.servers
                    switches = fattree.switches
                else:
                    run_both = True

                    jellyfish = topo.Jellyfish(num_servers, num_switches, num_ports, network_report=network_report)
                    servers = jellyfish.servers
                    switches = jellyfish.switches

                dijkstra_table = dijkstra.dijkstra_shortest_path(servers, switches, report=dijkstra_report)
                length_distr, num_pairs = pathlength_distribution(dijkstra_table)

                for path_len in length_distr.keys():
                    # print(path_len, total_pathlen_distr[path_len])
                    total_pathlen_distr[path_len] += length_distr[path_len]

                total_pairs += num_pairs


            # average results
            for distance in total_pathlen_distr.keys():
                total_pathlen_distr[distance] /= total_pairs

            if not run_both:
                num_servers = len(servers)
                num_switches = len(switches)

                topotype = 'fattree' if argv[0] == 'fattree' else 'jellyfish'

                plot_figure_9c([total_pathlen_distr], num_servers, num_switches, num_ports, iterations, topotype=topotype)
            else:
                total_pathlen_distr_Jelly = total_pathlen_distr
                total_pathlen_distr_Fat = defaultdict(lambda:0)
                
                # run fattree topology for 1 iteration
                topology = topo.Fattree(num_ports)

                servers = topology.servers
                switches = topology.switches

                dijkstra_table = dijkstra.dijkstra_shortest_path(servers, switches)
                length_distr, num_pairs = pathlength_distribution(dijkstra_table)

                for path_len in length_distr.keys():
                    total_pathlen_distr_Fat[path_len] += length_distr[path_len]

                total_pairs += num_pairs


                # average results
                for distance in total_pathlen_distr_Fat.keys():
                    total_pathlen_distr_Fat[distance] /= total_pairs
                

                # plot figure 1.c
                plot_figure_9c([total_pathlen_distr_Jelly, total_pathlen_distr_Fat], num_servers, num_switches, num_ports, iterations)

        except:
            raise ValueError('Usage: $ python topo.py (topo_type) num_servers num_switches num_ports (-report) (-iterations N')

if __name__ == "__main__":
	main(sys.argv[1:]) 