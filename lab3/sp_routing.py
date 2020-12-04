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

#!/usr/bin/env python3

from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ipv4
from ryu.lib.packet import ipv6
from ryu.lib.packet import arp
from ryu.lib import mac
from ryu.lib.packet import ethernet, ether_types
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase

import topo
import dijkstra
from collections import defaultdict

ETHERNET = ethernet.ethernet.__name__
ETHERNET_MULTICAST = "ff:ff:ff:ff:ff:ff"
ARP = arp.arp.__name__

def default_dict():
	return defaultdict(default_dict)


class SPRouter(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SPRouter, self).__init__(*args, **kwargs)
        self.topo_net = topo.Fattree(4)

        # Used for learning switch functioning
        self.mac_to_port = {}

        # arp table
        self.arp_table = {}
        self.sw = {}

        self.shortest_path_dict = default_dict()

        # calculate shortest paths between all server pairs
        self.servers = self.topo_net.servers
        self.switches = self.topo_net.switches

        self.dijkstra_table, self.n_servers = dijkstra.dijkstra_shortest_path(self.servers, self.switches)

    # Topology discovery
    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):

        # Switches and links in the network
        switch_list = get_switch(self, None)
        link_list = get_link(self, None)

        # for each src name, calculate its corresponding dpid
        self.switch_name_to_dpid = {str(link.src.name).split("-")[0][2:] : link.src.dpid for link in link_list}

        # for each (src, dst) switch pair, determine port_no (without overwriting dict!!!!)
        self.switch_dpid_links = {}
        for link in link_list:
            if not link.src.dpid in self.switch_dpid_links:
                self.switch_dpid_links[link.src.dpid] = {link.dst.dpid : link.src.port_no}
            else:
                if not link.dst.dpid in self.switch_dpid_links[link.src.dpid]:
                    self.switch_dpid_links[link.src.dpid][link.dst.dpid] = link.src.port_no
            

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install entry-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)


    # Add a flow entry to the flow-table
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Construct flow_mod message and send it
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # TODO: handle new packets at the controller

        # record in_port
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        pkt_eth = pkt.get_protocol(ethernet.ethernet)

        # ignore lldp packet
        if pkt_eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Avoid IPV6 packet for now..
        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=pkt_eth.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            return None
        
        dst = pkt_eth.dst
        src = pkt_eth.src

        arp_pkt = pkt.get_protocol(arp.arp)

        if arp_pkt:
            self.arp_table[arp_pkt.src_ip] = src
            # self.logger.info(" ARP: %s -> %s", arp_pkt.src_ip, arp_pkt.dst_ip)
            if self.arp_handler(msg):
                return None

        # do not calculate shortest path for arp requests
        else:
            # only calculate shortest path between (src, dst) if it's not yet calculated
            if not self.shortest_path_dict[(src, dst)]:

                # calculate shortest path as a list
                shortest_path = self.calculate_shortest_path(src, dst)

                # shortest path becomes value of current (src, dst) pair
                self.shortest_path_dict[(src, dst)] = shortest_path

        
        self.mac_to_port.setdefault(dpid, {})

        # update mac_to_port
        if not src in self.mac_to_port[dpid]:
            self.mac_to_port[dpid][src] = in_port

        # direct ARP packets to dst (ff:ff:ff... not in shortest path)
        if arp_pkt and dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        
        # else if we know the shortest path for the (src, dst) pair
        elif self.shortest_path_dict[(src, dst)]:

            # index of next hop in the shorest path list
            next_hop_index = self.shortest_path_dict[(src, dst)].index(dpid) + 1

            # next hop is the destination
            if next_hop_index == len(self.shortest_path_dict[(src, dst)]) - 1:
                out_port = self.mac_to_port[dpid][dst]

            # else if next hop is in shortest path
            elif dpid in self.shortest_path_dict[(src, dst)][:-1]:

                next_dpid = self.shortest_path_dict[(src, dst)][next_hop_index]
                out_port = self.switch_dpid_links[dpid][next_dpid]

        # FLOOD if packet is not ARP and shortest path for (src, dst) is unknown
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        priority = ofproto.OFP_DEFAULT_PRIORITY

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            # self.logger.info("install flow_mode:%s -> %s", in_port, out_port)
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        # Construct packet_out message and send it
        out = parser.OFPPacketOut(datapath=datapath,
                                  in_port=in_port,
                                  actions=actions,
                                  buffer_id=msg.buffer_id,
                                  data=data)
        datapath.send_msg(out)


    def calculate_shortest_path(self, src_mac, dst_mac):

        # if they are, calculate shortest path between the two
        src_server = int(self.topo_net.mac_to_id[src_mac])
        dst_server = int(self.topo_net.mac_to_id[dst_mac])

        # calculate shortest path with Dijkstra's algorithm (lab2)
        shortest_path_switches = dijkstra.shortest_path_list(self.dijkstra_table, src_server, dst_server, self.n_servers)

        # express in mininet equivalent shortest path
        shortest_path_mininet = []
        for (type, id) in shortest_path_switches:
            
            if type == 'server':
                continue
            elif type == 'edge switch':
                new_type = 'es_' + str(id)
            elif type == 'aggregate switch':
                new_type = 'as_' + str(id)
            elif type == 'core switch':
                new_type = 'cs_' + str(id)

            shortest_path_mininet.append(new_type)


        # shortest path in dpid's of mininet switches
        dpid_shortest_path = [self.switch_name_to_dpid[name] for name in shortest_path_mininet if name in self.switch_name_to_dpid]

        # append destination server to shortest path
        dpid_shortest_path.insert(len(dpid_shortest_path), dst_server)

        return dpid_shortest_path


    def arp_handler(self, msg):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        arp_pkt = pkt.get_protocol(arp.arp)

        if eth:
            eth_dst = eth.dst
            eth_src = eth.src

        # Break the loop for avoiding ARP broadcast storm
        if eth_dst == mac.BROADCAST_STR:  # and arp_pkt:
            arp_dst_ip = arp_pkt.dst_ip
            arp_src_ip = arp_pkt.src_ip

            if (datapath.id, arp_src_ip, arp_dst_ip) in self.sw:
                # packet come back at different port.
                if self.sw[(datapath.id, arp_src_ip, arp_dst_ip)] != in_port:
                    datapath.send_packet_out(in_port=in_port, actions=[])
                    return True
            else:
                # self.sw.setdefault((datapath.id, eth_src, arp_dst_ip), None)
                self.sw[(datapath.id, arp_src_ip, arp_dst_ip)] = in_port
                # print(self.sw)
                self.mac_to_port.setdefault(datapath.id, {})
                self.mac_to_port[datapath.id][eth_src] = in_port

        # Try to reply arp request
        if arp_pkt:
            if arp_pkt.opcode == arp.ARP_REQUEST:
                hwtype = arp_pkt.hwtype
                proto = arp_pkt.proto
                hlen = arp_pkt.hlen
                plen = arp_pkt.plen
                arp_src_ip = arp_pkt.src_ip
                arp_dst_ip = arp_pkt.dst_ip
                if arp_dst_ip in self.arp_table:
                    actions = [parser.OFPActionOutput(in_port)]
                    ARP_Reply = packet.Packet()

                    ARP_Reply.add_protocol(ethernet.ethernet(
                        ethertype=eth.ethertype,
                        dst=eth_src,
                        src=self.arp_table[arp_dst_ip]))
                    ARP_Reply.add_protocol(arp.arp(
                        opcode=arp.ARP_REPLY,
                        src_mac=self.arp_table[arp_dst_ip],
                        src_ip=arp_dst_ip,
                        dst_mac=eth_src,
                        dst_ip=arp_src_ip))

                    ARP_Reply.serialize()

                    out = parser.OFPPacketOut(
                        datapath=datapath,
                        buffer_id=ofproto.OFP_NO_BUFFER,
                        in_port=ofproto.OFPP_CONTROLLER,
                        actions=actions, data=ARP_Reply.data)
                    datapath.send_msg(out)
                    # print("ARP_Reply")
                    return True
        return False



print('Running..')
SPRouter()
