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
from ryu.lib import mac
from ryu.lib.packet import packet
from ryu.lib.packet import ipv4
from ryu.lib.packet import ipv6
from ryu.lib.packet import arp

from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet

import topo

ETHERNET = ethernet.ethernet.__name__
ETHERNET_MULTICAST = "ff:ff:ff:ff:ff:ff"
ARP = arp.arp.__name__


class FTRouter(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FTRouter, self).__init__(*args, **kwargs)
        self.topo_net = topo.Fattree(4)

        # Initialize mac address table
        self.mac_to_port = {}

        # Initialize arp table
        self.arp_table = {}
        self.sw = {}

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
        self.logger.info("switch:%s connected", datapath.id)

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

        # Avoid IPV6 packet for now..
        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            return None

        dst = eth.dst
        src = eth.src

        arp_pkt = pkt.get_protocol(arp.arp)

        if arp_pkt:
            self.arp_table[arp_pkt.src_ip] = src
            self.logger.info(" ARP: %s -> %s", arp_pkt.src_ip, arp_pkt.dst_ip)
            if self.arp_handler(msg):
                return None

        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        # if eth.ethertype != ether_types.ETH_TYPE_ARP:
        if src not in self.mac_to_port[dpid]:
            self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            # Get routing path based on dst and src address (2-level routing)
            out_port = self.mac_to_port[dpid][dst]
        else:
            print(self.mac_to_port[dpid])
            out_port = ofproto.OFPP_FLOOD
            print("Flood")

        actions = [parser.OFPActionOutput(out_port)]

        priority = ofproto.OFP_DEFAULT_PRIORITY

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            self.logger.info("install flow_mode:%s -> %s", in_port, out_port)
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
        # ofproto_v1_2.OXM_OF_IN_PORT
        # in_port = msg.match['in_port']

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
                print(self.sw)
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
                    print("ARP_Reply")
                    return True
        return False
