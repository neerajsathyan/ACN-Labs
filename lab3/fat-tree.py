# Copyright 2020 Lin Wang

# This code is part of the Advanced Computer Networks (ACN) course at VU 
# Amsterdam.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# !/usr/bin/env python3

# A dirty workaround to import topo.py from lab2

import os
import subprocess
import time

import mininet
import mininet.clean
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import lg, info
from mininet.link import TCLink
from mininet.node import Node, OVSKernelSwitch, RemoteController
from mininet.topo import Topo
from mininet.util import waitListening, custom
import math
import topo
import re


def location_to_dpid(core=None, pod=None, switch=None):
    if core is not None:
        return '0000000010%02x0000' % core
    else:
        return '000000002000%02x%02x' % (pod, switch)


def ip_to_mac(ip):
    match = re.match('10.(\d+).(\d+).(\d+)', ip)
    pod, switch, host = match.group(1, 2, 3)
    return location_to_mac(int(pod), int(switch), int(host))


def location_to_mac(pod, switch, host):
    return '00:00:00:%02x:%02x:%02x' % (pod, switch, host)


class FattreeNet(Topo):
    """
	Create a fat-tree network in Mininet
	"""

    def __init__(self, ft_topo):

        Topo.__init__(self)

        # TODO: please complete the network generation logic here

        Switches = []
        hostServers = []

        # No of pods..
        pods = int(ft_topo.num_ports)

        # No of servers per switch (leaves of penultimate node)
        end = int(pods / 2)

        # No of Core Switches..
        core_switch_count = int((ft_topo.num_ports / 2) ** 2)

        # No of Aggregate Switches..
        agg_switch_count = int((ft_topo.num_ports / 2) * ft_topo.num_ports)

        # No of Edge Switches..
        edge_switch_count = int(agg_switch_count)

        # No of Servers..
        server_count = int((ft_topo.num_ports ** 3) / 4)

        # create switches..
        for switch in ft_topo.switches:
            if switch.type == 'edge switch':
                print(f'edge switch: {switch.id}')
                Switches.append(self.addSwitch("es_" + str(switch.id), dpid=str(switch.id)))

            elif switch.type == 'aggregate switch':
                print(f'aggregate switch: {switch.id}')
                Switches.append(self.addSwitch("as_" + str(switch.id), dpid=str(switch.id)))

            elif switch.type == 'core switch':
                print(f'core switch: {switch.id}')
                Switches.append(self.addSwitch("cs_" + str(switch.id), dpid=str(switch.id)))

        # print(f'\n\n\nSwitches: \n{Switches}\n\n\n')
        # [print(switch) for switch in Switches]

        pod_num = 0
        i = 0
        j = 2
        for server in ft_topo.servers:
            if j == int(ft_topo.num_ports / 2) + 2:
                j = 2
                i = i + 1
            if i == int(ft_topo.num_ports / 2):
                i = 0
                pod_num = pod_num + 1
            hostServers.append(self.addHost(server.id,
                                            ip='10.%d.%d.%d' % (pod_num, i, j),
                                            mac=location_to_mac(pod_num, i, j)))
            j = j + 1

        # create links..
        server_id = 0
        for i in range(ft_topo.edge_switch_starting_id, ft_topo.edge_switch_ending_id + 1):
            for j in range(int(ft_topo.num_ports / 2)):
                self.addLink(hostServers[server_id], Switches[i], bw=15, delay='5ms')
                server_id += 1

        # Create Edges Between Edge Switches and Aggregate Switches..
        for i in range(ft_topo.agg_switch_starting_id, ft_topo.agg_switch_ending_id + 1):
            for j in range(int(ft_topo.num_ports / 2)):
                self.addLink(Switches[i], Switches[int((end * math.floor(i / end) + j) - edge_switch_count)], bw=15, delay='5ms')

        # Create Edges Between Aggregate Switches and Core Switches..
        for i in range(ft_topo.agg_switch_starting_id, ft_topo.agg_switch_ending_id + 1, end):
            for j in range(int(ft_topo.num_ports / 2)):
                for k in range(int(ft_topo.num_ports / 2)):
                    self.addLink(Switches[i + j], Switches[int(ft_topo.agg_switch_ending_id + 1 + (j * end + k))], bw=15, delay='5ms')


def make_mininet_instance(graph_topo):
    net_topo = FattreeNet(graph_topo)
    net = Mininet(topo=net_topo, controller=None, autoSetMacs=True)
    net.addController('c0', controller=RemoteController, ip="127.0.0.1", port=6653)
    return net


def run(graph_topo):
    # Run the Mininet CLI with a given topology
    lg.setLogLevel('info')
    mininet.clean.cleanup()
    net = make_mininet_instance(graph_topo)

    info('*** Starting network ***\n')
    net.start()
    info('*** Running CLI ***\n')
    CLI(net)
    info('*** Stopping network ***\n')
    net.stop()


ft_topo = topo.Fattree(4)
run(ft_topo)
