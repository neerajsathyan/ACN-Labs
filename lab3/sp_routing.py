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
from ryu.lib.packet import arp


###################################
from ryu.lib.packet import ethernet
from ryu.lib.packet import icmp
###################################

from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase

import topo
import dijkstra


class SPRouter(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SPRouter, self).__init__(*args, **kwargs)
        self.topo_net = topo.Fattree(4)

        #################################################################
        # hardcoded hw_addr and ip_addr, as proposed by some other 
        # architecture (not sure about this!) 
        self.hw_addr = '0a:e4:1c:d1:3e:44'
        self.ip_addr = '192.0.2.9'
        #################################################################

        # USed for learning switch functioning
        self.mac_to_port = {}
        
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

        # for s in link_list:

            # print (" \t\t s: " + str(s))
            # print(" \t\t s.src.name: " + str(s.src.name))
            # print(" \t\t s.src.name.split(-): " + str(s.src.name).split("-")[0][2:])
            # print(" \t\t s.src.port_no: " + str(s.src.port_no))
            # print(" \t\t s.src.hw_addr: " + str(s.src.hw_addr))

            # print(" \t\t s.dst.name: " + str(s.dst.name))
            # print(" \t\t s.dst.name.split(-): " + str(s.dst.name).split("-")[0][2:])
            # print(" \t\t s.dst.port_no: " + str(s.dst.port_no))
            # print(" \t\t s.dst.hw_addr: " + str(s.dst.hw_addr))
            # print()


        #################################################################
        # OBTAIN THE USEFUL INFORMATION FROM GET_SWITCH AND GET_LINK

        # get list of dpid's of all switches
        self.switch_dpids = [switch.dp.id for switch in switch_list]

        # link dictionary {src_dpid : {dst_dpid : {src_port_to_dst}}}
        self.switch_dpid_links = {link.src.dpid : {link.dst.dpid : {'port': link.src.port_no}} for link in link_list}

        print("Switches:\n", self.switch_dpids)
        print("Links: \n", self.switch_dpid_links)
        print()

        #################################################################


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

        # Calculate the path from server 'start' to server 'end'
        start_id, end_id = 1, 14
        shortest_path = dijkstra.shortest_path_list(self.dijkstra_table, start_id, end_id, self.n_servers)
        print(f'Shortest_path = {shortest_path}\n')


        # record in_port
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        pkt_eth = pkt.get_protocol(ethernet.ethernet)

        if not pkt_eth:
            return

        #################################################################
        # HANDLE ARP REQUESTS, ICMP AND IPV4 

        pkt_arp = pkt.get_protocol(arp.arp)
        pkt_icmp = pkt.get_protocol(icmp.icmp)
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)


        if pkt_arp:
            # print("datapath id: "+str(dpid))
            # print("port: "+str(in_port))
            # print("pkt_eth.dst: " + str(pkt_eth.dst))
            # print("pkt_eth.src: " + str(pkt_eth.src))
            # print("pkt_arp: " + str(pkt_arp))
            # print("pkt_arp:src_ip: " + str(pkt_arp.src_ip))
            # print("pkt_arp:dst_ip: " + str(pkt_arp.dst_ip))
            # print("pkt_arp:src_mac: " + str(pkt_arp.src_mac))
            # print("pkt_arp:dst_mac: " + str(pkt_arp.dst_mac))
            # print()

            self._handle_arp(datapath, in_port, pkt_eth, pkt_arp)
            return

        elif pkt_icmp:
            self._handle_icmp(datapath, in_port, pkt_eth, pkt_ipv4, pkt_icmp)
            return

        #################################################################


        #################################################################
        # COPIED FROM LEARNING_SWITCH.PY (LAB1)
        
        dst = pkt_eth.dst
        src = pkt_eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # self.logger.info("\tpacket in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD


        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            # verify if we have a valid buffer_id, if yes avoid to send both flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)

        data = None
        
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

        #################################################################



    #################################################################
    # ADDED FUNCTIONS TO HANDLE ARP REQUESTS AND ICMP

    def _handle_arp(self, datapath, port, pkt_ethernet, pkt_arp):

        if not pkt_arp.opcode == arp.ARP_REQUEST:
            return

        pkt = packet.Packet()

        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                        dst=pkt_ethernet.src,
                                        src=self.hw_addr))

        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                src_mac=self.hw_addr,
                                src_ip=self.ip_addr,
                                dst_mac=pkt_arp.src_mac,
                                dst_ip=pkt_arp.src_ip))

        self._send_packet(datapath, port, pkt)

    

    def _handle_icmp(self, datapath, port, pkt_ethernet, pkt_ipv4, pkt_icmp):

        if not pkt_icmp.type == icmp.ICMP_ECHO_REQUEST:
            return

        pkt = packet.Packet()

        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                           dst=pkt_ethernet.src,
                                           src=self.hw_addr))

        pkt.add_protocol(ipv4.ipv4(dst=pkt_ipv4.src,
                                   src=self.ip_addr,
                                   proto=pkt_ipv4.proto))

        pkt.add_protocol(icmp.icmp(type_=icmp.ICMP_ECHO_REPLY,
                                   code=icmp.ICMP_ECHO_REPLY_CODE,
                                   csum=0,
                                   data=pkt_icmp.data))

        self._send_packet(datapath, port, pkt)


    def _send_packet(self, datapath, port, pkt):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()

        self.logger.info("packet-out %s" % (pkt,))

        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]

        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)

        datapath.send_msg(out)


    #################################################################



print('Running..')
SPRouter()
