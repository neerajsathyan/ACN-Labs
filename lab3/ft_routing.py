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

# !/usr/bin/env python3

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

from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet

import topo


class FTRouter(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FTRouter, self).__init__(*args, **kwargs)
        self.topo_net = topo.Fattree(4)

        # Initialize mac address table
        self.mac_to_port = {}

    # Topology discovery
    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):
        # Switches and links in the network
        switches = get_switch(self, None)
        links = get_link(self, None)
        for s in links:

            print(" \t\t s: " + str(s))
            print(" \t\t s.src.name: " + str(s.src.name))
            print(" \t\t s.src.name.split(-): " + str(s.src.name).split("-")[0][2:])
            print(" \t\t s.src.port_no: " + str(s.src.port_no))
            print(" \t\t s.src.hw_addr: " + str(s.src.hw_addr))

            print(" \t\t s.dst.name: " + str(s.dst.name))
            print(" \t\t s.dst.name.split(-): " + str(s.dst.name).split("-")[0][2:])
            print(" \t\t s.dst.port_no: " + str(s.dst.port_no))
            print(" \t\t s.dst.hw_addr: " + str(s.dst.hw_addr))
            print()

        #################################################################
        # OBTAIN THE USEFUL INFORMATION FROM GET_SWITCH AND GET_LINK

        # get list of dpid's of all switches
        self.switch_dpids = [switch.dp.id for switch in switches]

        # link dictionary {src_dpid : {dst_dpid : {src_port_to_dst}}}
        self.switch_dpid_links = {link.src.dpid: {link.dst.dpid: {'port': link.src.port_no}} for link in links}

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
    def add_flow(self, datapath, priority, match, actions):
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
        in_port = msg.match['in_port']

        # TODO: handle new packets at the controller
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # Avoid LLDP:
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        self.mac_to_port.setdefault(dpid, {})

        # learn a mac address to avoid FLOOD next time.
        if eth.ethertype != ether_types.ETH_TYPE_ARP:
            self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            # Get routing path based on dst and src address (2-level routing)
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        priority = ofproto.OFP_DEFAULT_PRIORITY

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        # Construct packet_out message and send it
        out = parser.OFPPacketOut(datapath=datapath,
                                  in_port=in_port,
                                  actions=actions,
                                  buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                                  data=data)
        datapath.send_msg(out)
        # ofproto_v1_2.OXM_OF_IN_PORT
        # in_port = msg.match['in_port']
