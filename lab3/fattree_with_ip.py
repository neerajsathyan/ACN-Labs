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
from mininet.node import Node, OVSKernelSwitch, RemoteController, CPULimitedHost
from mininet.topo import Topo
from mininet.util import waitListening, custom
import math
#import topo
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

        Core = []
        Aggregation = []
        Edge = []
        hostServers = []
        self.k = ft_topo

        # No of pods..
        pods = int(ft_topo)

        # No of servers per switch (leaves of penultimate node)
        end = int(pods / 2)

        # No of Core Switches..
        core_switch_count = int((ft_topo / 2) ** 2)

        # No of Aggregate Switches..
        agg_switch_count = int((ft_topo / 2) * ft_topo)

        # No of Edge Switches..
        edge_switch_count = int(agg_switch_count)

        # No of Servers..
        server_count = int((ft_topo ** 3) / 4)

        # There are (k/2)^2 core switches having k ports.
        for i in range(1, (end ** 2)+1):
            # Add an item in the list | Creating a switch with name CrSw# | having DPID | K | j coordinate | i
            # coordinate | Openflow Protocol specified as 1.3
            Core.append(self.addSwitch('CrSw%s' % (i - 1), dpid="00:00:00:00:00:0" + str(end ** 2) + ":0" + str(
                (i - 1) // end + 1) + ":0" + str((i - 1) % end + 1)))

            # Printing the generated data of core switch
            print('CrSw%s' % (i - 1) + " DPID: 00:00:00:00:00:0" + str(end ** 2) + ":0" + str(
                (i - 1) // end + 1) + ":0" + str((i - 1) % end + 1))

        # Running loop for Number of pods, loop runs 4 times.

        for i in range(1, self.k + 1):
            # generating 2 switches one aggregation and one edge per loop, loop runs 2 times.
            for j in range(1, end+1):
                # Creating Aggregation Switches
                # Add an item in the list | Creating a switch with name ArSw# | having DPID |K No of pod | i-1 switch |Openflow Protocol specified as 1.3
                Aggregation.append(self.addSwitch('AgSw' + str(i - 1) + '_' + str(j - 1),
                                                  dpid="00:00:00:00:00:0" + str(i - 1) + ":0" + str(
                                                      (j - 1) % end + 2) + ":01"))

                # Printing the generated data of Aggregation switch
                print('AgSw' + str(i - 1) + '_' + str(j - 1) + " DPID: 00:00:00:00:00:0" + str(i - 1) + ":0" + str(
                    (j - 1) % end + 2) + ":01")

                # Creating Edge Switch
                # Add an item in the list | Creating a switch with name EgSw# | having DPID | K No of pod | i-1 switch | |Openflow Protocol specified as 1.3
                Edge.append(self.addSwitch('EdSw' + str(i - 1) + '_' + str(j - 1),
                                           dpid="00:00:00:00:00:0" + str(i - 1) + ":0" + str((j - 1) % end) + ":01"))

                # Printing the generated data of Edge switch
                print('EdSw' + str(i - 1) + '_' + str(j - 1) + " DPID: 00:00:00:00:00:0" + str(i - 1) + ":0" + str(
                    (j - 1) % end) + ":01")

        # Adding links between core and aggregation switches,There are (k/2)^2 core switches so,
        for i in range(1, (end ** 2)+1):
            # Getting core switch one by one
            CoreSwitch = Core[i - 1]
            # There are 0 to k-1 Aggregation switches connections per core switch
            for j in range(0, (self.k - 1)+1):
                # Getting Aggregation switch one by one (k/2*j)+[(i-1)//(k/2)]
                AggreSwitch = Aggregation[int(self.k/2*j+(i-1)//(self.k/2))]

                # Adding link bw core and aggre | Core port | Aggre port |mbps| loss %|
                self.addLink(CoreSwitch, AggreSwitch, port1=(j + 1), port2=((i - 1) % end + 1), bw=15, delay='5ms')

        # Adding links between aggregation and edge switches,There are (k/2*k)-1 aggregation switches so,
        for i in range(0, (end * self.k - 1)+1):
            # Getting Aggregation switch one by one
            AggreSwitch = Aggregation[i]

            # There are (k/2)-1 Edge switches connecctions per aggregation switch
            for j in range(0, (end - 1)+1):
                # Getting edge switch one by one [[i//(k/2)]*(k/2)]+j
                EdgeSwitch = Edge[i // end * end + j]

                # k/2 ports of edge switch are connected to aggregation switches

                # The (k/2 + i - 1)th port of edge switch which should be connected to the jth port of aggregation switch.

                # Adding link bw aggre and edge | Aggre port | Edge port |mbps| loss %|

                self.addLink(AggreSwitch, EdgeSwitch, port1=(end + j + 1), port2=(end + i % end + 1), bw=15,
                             delay='5ms')

        # Adding link bw HoneyPot and edge |Aggre port|Edge port|mbps| loss %|

        # self.addLink(AggreSwitch[7],EdgeSwitch,port1=(), port2=(5),bw=1,loss=0)

        # Adding links between edge switches and hosts,There are (k/2*k)-1 Edge switches so,
        for i in range(0, (end * self.k - 1)+1):
            # Getting Edge switch one by one
            EdgeSwitch = Edge[i]

            # There are (k/2)-1 Edge switches connections per host switch

            for j in range(0, (end - 1)+1):
                # Creating a host |name switch no_host no|ip10 | .pod | switch | ID is the host positon from [2,
                # (k/2)+1] |
                Host = self.addHost('h' + str(i) + '_' + str(j),
                                    ip='10.' + str(i // end) + '.' + str(i % end) + '.' + str(2 + j))

                # The ith host in a subnet should be connected to the ith port of edge switch which manages the subnet.

                # Adding link bw core and host|Edge port |Host port|mbps| loss %|
                self.addLink(EdgeSwitch, Host, port1=(j + 1), port2=1, bw=15, delay='5ms')


def make_mininet_instance(graph_topo):
    net_topo = FattreeNet(graph_topo)
    net = Mininet(topo=net_topo, controller=None, autoSetMacs=True, autoStaticArp=True, host=CPULimitedHost, link=TCLink)
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


#ft_topo = topo.Fattree(4)
run(4)
