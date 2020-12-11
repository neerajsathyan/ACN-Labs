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
import binascii

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
import re

import topo

ETHERNET = ethernet.ethernet.__name__
ETHERNET_MULTICAST = "ff:ff:ff:ff:ff:ff"
ARP = arp.arp.__name__


def location_to_dpid(core=None, pod=None, switch=None):
    if core is not None:
        return '0000000010%02x0000' % core
    else:
        return '000000002000%02x%02x' % (pod, switch)


def pod_name_to_location(name):
    match = re.match('p(\d+)_s(\d+)', name)
    pod, switch = match.group(1, 2)
    return int(pod), int(switch)


def is_core(dpid):
    return ((dpid & 0xFF000000) >> 24) == 0x10


def dpid_to_name(dpid):
    if is_core(dpid):
        core_num = (dpid & 0xFF0000) >> 16
        return 'c_s%d' % core_num
    else:
        pod = (dpid & 0xFF00) >> 8
        switch = (dpid & 0xFF)
        return 'p%d_s%d' % (pod, switch)


def host_to_ip(name):
    match = re.match('p(\d+)_s(\d+)_h(\d+)', name)
    pod, switch, host = match.group(1, 2, 3)
    return '10.%s.%s.%s' % (pod, switch, host)


def ip_to_mac(ip):
    match = re.match('10.(\d+).(\d+).(\d+)', ip)
    pod, switch, host = match.group(1, 2, 3)
    return location_to_mac(int(pod), int(switch), int(host))


def location_to_mac(pod, switch, host):
    return '00:00:00:%02x:%02x:%02x' % (pod, switch, host)


class FTRouter(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FTRouter, self).__init__(*args, **kwargs)
        self.topo_net = topo.Fattree(4)
        self.k = 4

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
        # for s in links:
        #     print(" \t\t s: " + str(s))
        #     print(" \t\t s.src.name: " + str(s.src.name))
        #     print(" \t\t s.src.name.split(-): " + str(s.src.name).split("-")[0][2:])
        #     print(" \t\t s.src.port_no: " + str(s.src.port_no))
        #     print(" \t\t s.src.hw_addr: " + str(s.src.hw_addr))
        #
        #     print(" \t\t s.dst.name: " + str(s.dst.name))
        #     print(" \t\t s.dst.name.split(-): " + str(s.dst.name).split("-")[0][2:])
        #     print(" \t\t s.dst.port_no: " + str(s.dst.port_no))
        #     print(" \t\t s.dst.hw_addr: " + str(s.dst.hw_addr))
        #     print()

        #################################################################
        # OBTAIN THE USEFUL INFORMATION FROM GET_SWITCH AND GET_LINK

        # get list of dpid's of all switches
        # self.switch_dpids = [switch.dp.id for switch in switches]

        # link dictionary {src_dpid : {dst_dpid : {src_port_to_dst}}}
        # self.switch_dpid_links = {link.src.dpid: {link.dst.dpid: {'port': link.src.port_no}} for link in links}

        # print("Switches:\n", self.switch_dpids)
        # print("Links: \n", self.switch_dpid_links)
        print()

        #################################################################

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        # k = self.topo_net.k
        k = 4
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        dpid = str(hex(datapath.id))[2:].zfill(16)

        # Printing out the DPID of the switch
        print(
            "DPID :" + dpid[0:2] + ":" + dpid[2:4] + ":" + dpid[4:6] + ":" + dpid[6:8] + ":" + dpid[8:10] + ":" + dpid[
                                                                                                                  10:12] + ":" + dpid[
                                                                                                                                 12:14] + ":" + dpid[
                                                                                                                                                14:16])

        # If in DPID K is = 4 then it is a core switch
        if dpid[10:12] == "0" + str(k):
            # DPID_pod value from 0 to 3 for pods
            for dpid_pod in range(0, k):
                # setting IP address (10.dpid_pod.0.0) is the IP address of the core switch
                ip = "10." + str(dpid_pod) + ".0.0"
                # setting subnet mask
                mask = "255.255.0.0"
                match = parser.OFPMatch(eth_type=0x800, ipv4_dst=(ip, mask))
                port = dpid_pod + 1
                actions = [parser.OFPActionOutput(port, 0)]
                print(ip + "/16 output port : " + str(port))
                self.add_flow(datapath, 500, match, actions)


        # If in DPID k is 2 or 3 then it is a aggregation switch
        elif int(dpid[12:14]) >= (k / 2):
            # DPID_pod value from 0 to 3 and the 4th one for the core
            for dpid_pod in range(0, k):
                # if DPID_pod = pod then the destination host is in the same pod or core
                if (dpid_pod == int(dpid[10:12])):
                    # If the destination host is in the same pod, aggregation switch should transfer the packet to edge switch
                    for dpid_edge in range(0, int(k / 2)):
                        # setting IP address (10.pod.edge.0) is the IP address of the edge switch
                        ip = "10." + str(dpid_pod) + "." + str(dpid_edge) + ".0"
                        # setting subnet mask
                        mask = "255.255.255.0"
                        match = parser.OFPMatch(eth_type=0x800, ipv4_dst=(ip, mask))
                        port = dpid_edge + 3
                        actions = [parser.OFPActionOutput(port, 0)]
                        print(ip + "/24 output port : " + str(port))
                        self.add_flow(datapath, 500, match, actions)

                # If the destination host is not in the same pod, aggregation switch should forward the packet to the core switch
                else:
                    # setting IP address (10.pod.0.0) is the IP address of the core switch
                    ip = "10." + str(dpid_pod) + ".0.0"
                    # setting subnet mask
                    mask = "255.255.0.0"
                    match = parser.OFPMatch(eth_type=0x800, ipv4_dst=(ip, mask))
                    port = int(k - 2 - (dpid_pod % (k / 2)))
                    actions = [parser.OFPActionOutput(port, 0)]
                    print(ip + "/16 output port : " + str(port))
                    self.add_flow(datapath, 500, match, actions)



        # If in DPID k is 0 or 1 then it is a edge switch
        else:

            for dpid_pod in range(0, k):
                # if DPID_pod = pod then the destination host is in the same pod
                if (dpid_pod == int(dpid[10:12])):
                    # If the destination host is in the same pod, then check if the destination host is in the same edge or not
                    for dpid_edge in range(0, int(k / 2)):
                        # If dpid_edge == switch then the destination host is in the same edge
                        if (dpid_edge == int(dpid[12:14])):
                            # If the destination host is in the same edge, then the Edge switch should transfer the packet to the host
                            for ip_host in range(0, int(k / 2)):
                                # setting IP address (10.dpid_pod.dpid_edge.ip_host) is the IP address of the host
                                ip = "10." + str(dpid_pod) + "." + str(dpid_edge) + "." + str(ip_host + 2)
                                match = parser.OFPMatch(eth_type=0x800, ipv4_dst=ip)
                                actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
                                print(ip + "/24 output port : Forwarding to Controller Packetin")
                                self.add_flow(datapath, 500, match, actions)

                        # If If dpid_edge not = switch then the destination host is in the same pod but not in the same edge switch
                        else:
                            # If the destination host is not in the same edge switch, then the Edge switch should transfer the packet to the Aggregation switch
                            for ip_host in range(0, int(k / 2)):
                                # setting IP address (10.dpid_pod.dpid_edge.ip_host) is the IP address of the other edge switch host
                                ip = "10." + str(dpid_pod) + "." + str(dpid_edge) + "." + str(ip_host + 2)
                                match = parser.OFPMatch(eth_type=0x800, ipv4_dst=ip)
                                actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
                                print(ip + "/24 output port : Forwarding to Controller Packetin")
                                self.add_flow(datapath, 500, match, actions)

                # If DPID_pod not = pod then the destination host is not in the same pod
                else:
                    ip = "10." + str(dpid_pod) + ".0.0"
                    # setting subnet mask
                    mask = "255.255.0.0"
                    match = parser.OFPMatch(eth_type=0x800, ipv4_dst=(ip, mask))
                    actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
                    print(ip + "/24 output port : Forwarding to Controller Packetin")
                    self.add_flow(datapath, 500, match, actions)

        # Install entry-miss flow entry
        # match = parser.OFPMatch()
        # actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        # self.add_flow(datapath, 0, match, actions)
        # self.logger.info("switch:%s connected", datapath.id)

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
        k = 4
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        buffer_id = ofproto.OFP_NO_BUFFER
        dpid = str(hex(datapath.id))[2:].zfill(16)

        # Printing out the DPID of the switch
        print("DPID is :" + dpid[0:2] + ":" + dpid[2:4] + ":" + dpid[4:6] + ":" + dpid[6:8] + ":" + dpid[
                                                                                                    8:10] + ":" + dpid[
                                                                                                                  10:12] + ":" + dpid[
                                                                                                                                 12:14] + ":" + dpid[
                                                                                                                                                14:16])

        # Extracting the pod No from the DPID
        pod_no = dpid[10:12]

        # Extracting the switch No from the DPID
        switch_no = dpid[12:14]

        print('Current Switch No = ' + str(int(switch_no) + 1) + '; Current Pod No = ' + str((int(pod_no) + 1)))

        # Get packet information
        msg = ev.msg
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        data = msg.data
        in_port = msg.match['in_port']

        # Avoid LLDP:
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Avoid IPV6 packet for now..
        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            return None

        self.mac_to_port.setdefault(dpid, {})

        if eth.ethertype == ether_types.ETH_TYPE_ARP:

            arp_packet = pkt.get_protocol(arp.arp)

            ip_dst = arp_packet.dst_ip

            ip_src = arp_packet.src_ip

            print('\nARP Packet:' '\nSource IP = ' + str(ip_src) + '\nDestination IP = ' + str(
                ip_dst) + '\nData = "' + str(data) + '"')

            if self.arp_handler(msg):
                return None


        elif eth.ethertype == ether_types.ETH_TYPE_IP:

            ip_packet = pkt.get_protocol(ipv4.ipv4)

            ip_src = ip_packet.src

            ip_dst = ip_packet.dst

            print('\nIPv4 Packet:' '\nSource IP = ' + str(ip_src) + '\nDestination IP = ' + str(
                ip_dst) + '\nData = "' + str(data) + '"')

        else:

            return


        x, pod_dst, edge_sw_dst, host_ip_dst = ip_dst.split('.')
        pod_dst = int(pod_dst) + 1
        edge_sw_dst = int(edge_sw_dst) + 1
        host_ip_dst = int(host_ip_dst) - 2
        current_pod = int(pod_no) + 1
        current_sw = int(switch_no) + 1

        print('\nPacket intended destination was:\nPod = ' + str(pod_dst) + '\nDestination Switch = ' + str(
            edge_sw_dst) + '\nDestination Host = ' + str(host_ip_dst))

        print('\nPacket Origin was:\nOrigin Pod = ' + str(current_pod) + '\nOrigin Switch = ' + str(current_sw))

        print('\nInstalling Destination Flows:')

        # DPID_pod value from 0 to 3

        for dpid_pod in range(0, k):

            # if DPID_pod = pod then the destination host is in the same pod
            if dpid_pod == int(dpid[10:12]):
                # If the destination host is in the same pod, then check if the destination host is in the same edge or not
                for dpid_edge in range(0, int(k / 2)):
                    # If dpid_edge == switch then the destination host is in the same edge
                    if dpid_edge == int(dpid[12:14]):
                        # If the destination host is in the same edge, then the Edge switch should transfer the packet to the host
                        for ip_host in range(0, int(k / 2)):
                            # setting IP address (10.dpid_pod.dpid_edge.ip_host) is the IP address of the host
                            ip = "10." + str(dpid_pod) + "." + str(dpid_edge) + "." + str(ip_host + 2)
                            match = parser.OFPMatch(eth_type=0x800, ipv4_dst=ip)
                            port = ip_host + 1
                            actions = [parser.OFPActionOutput(port, 0)]
                            print(ip + "/24 output port : " + str(port))
                            self.add_flow(datapath, 500, match, actions)

                    # If If dpid_edge not = switch then the destination host is in the same pod but not in the same edge switch
                    else:
                        # If the destination host is not in the same edge switch, then the Edge switch should transfer the packet to the Aggregation switch
                        for ip_host in range(0, int(k / 2)):
                            # setting IP address (10.dpid_pod.dpid_edge.ip_host) is the IP address of the other edge switch host
                            ip = "10." + str(dpid_pod) + "." + str(dpid_edge) + "." + str(ip_host + 2)
                            match = parser.OFPMatch(eth_type=0x800, ipv4_dst=ip)
                            port = int(k - (ip_host % (k / 2)))
                            actions = [parser.OFPActionOutput(port, 0)]
                            print(ip + "/24 output port : " + str(port))
                            self.add_flow(datapath, 500, match, actions)


            # If DPID_pod not = pod then the destination host is not in the same pod
            else:

                # setting IP address (10.dpid_pod.0.0) is the IP address of the core switch
                ip = "10." + str(dpid_pod) + ".0.0"
                # setting subnet mask
                mask = "255.255.0.0"
                match = parser.OFPMatch(eth_type=0x800, ipv4_dst=(ip, mask))
                port = int(k - (dpid_pod % (k / 2)))
                actions = [parser.OFPActionOutput(port, 0)]
                print(ip + "/16 output port : " + str(port))
                self.add_flow(datapath, 500, match, actions)

        # Construct packet_out message and send it
        # out = parser.OFPPacketOut(datapath=datapath,
        # in_port=port,
        # actions=actions,
        # buffer_id=ev.msg.buffer_id,
        # data=data)
        # datapath.send_msg(out)

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
