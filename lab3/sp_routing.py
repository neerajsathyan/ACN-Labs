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


###################################
from ryu.lib.packet import ethernet, ether_types
from ryu.lib.packet import icmp
###################################

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

        # print(self.dijkstra_table)

    # Topology discovery
    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):


        # Switches and links in the network
        switch_list = get_switch(self, None)
        link_list = get_link(self, None)

        # for switch in switch_list:
            # print(dir(switch))
            # print(dir(switch.dp))

        # print(f'self.topo_net.mac_to_id.keys(): {self.topo_net.mac_to_id.keys()}')
        # print(f'self.topo_net.mac_to_id.values(): {self.topo_net.mac_to_id.values()}\n\n\n\n')


        # for s in link_list:

        #     print (" \t\t s: " + str(s))
        #     print(" \t\t s.src.name: " + str(s.src.name))
        #     print(" \t\t s.src.name.split(-): " + str(s.src.name).split("-")[0][2:])
        #     print(" \t\t s.src.port_no: " + str(s.src.port_no))
        #     print(" \t\t s.src.hw_addr: " + str(s.src.hw_addr))

        #     print(" \t\t s.dst.name: " + str(s.dst.name))
        #     print(" \t\t s.dst.name.split(-): " + str(s.dst.name).split("-")[0][2:])
        #     print(" \t\t s.dst.port_no: " + str(s.dst.port_no))
        #     print(" \t\t s.dst.hw_addr: " + str(s.dst.hw_addr))
        #     print()


        #################################################################
        # OBTAIN THE USEFUL INFORMATION FROM GET_SWITCH AND GET_LINK

        # get list of dpid's of all switches
        # self.switch_dpids = [switch.dp.id for switch in switch_list if len(str(switch.dp.id)) < 5]
        # print(len(self.switch_dpids))
        # print(f'\n\nSwitch dpids: \n{self.switch_dpids}')
        # for 

        #################### MININET NAME TO DPID #########################
        self.switch_name_to_dpid = {str(link.src.name).split("-")[0][2:] : link.src.dpid for link in link_list}
        # print(self.switch_name_to_dpid)
        # print(f'\n\n\n\nswitch_name_to_dpid: {self.switch_name_to_dpid}, {len(self.switch_name_to_dpid)}')
        

        #################### HARDCODED NAME TO DPID #########################
        # switch_names = [str(link.src.name).split("-")[0][2:] for link in link_list]
        # self.switch_name_to_dpid = {switch_name : int(switch_name[3:]) for switch_name in switch_names}

        # print(self.switch_name_to_dpid)
        # for switch_name in switch_names:
            
        #     switch_id = int(switch_name[3:])

        
        # for link in link_list:
        #     dst_name = str(link.dst.name).split("-")[0][2:]

        #     self.switch_name_to_dpid[dst_name] = link.dst.dpid

        # print(f'switch_name_to_dpid: {self.switch_name_to_dpid}, {len(self.switch_name_to_dpid)}')


        # link dictionary {src_dpid : {dst_dpid : {src_port_to_dst}}}
        # self.switch_dpid_links = {link.src.dpid : {link.dst.dpid : link.src.port_no} for link in link_list}
        # print(len(link_list))
        # self.switch_dpid_links = {}
        # self.switch_dpid_links.setdefault({int : {int : {[]} }})
        # print()
        self.switch_dpid_links = {}
        for link in link_list:
            if not link.src.dpid in self.switch_dpid_links:
                self.switch_dpid_links[link.src.dpid] = {link.dst.dpid : link.src.port_no}
            else:
                if not link.dst.dpid in self.switch_dpid_links[link.src.dpid]:
                    self.switch_dpid_links[link.src.dpid][link.dst.dpid] = link.src.port_no
               
        # print(self.switch_dpid_links[32][41])
                # else:
                #     self.switch_dpid_links[link.src.dpid][link.dst.dpid].append(link.src.port_no)

            # else:
                # if not link.dst.dpid in self.switch_dpid_links[link.src.dpid]:
            # self.switch_dpid_links[link.src.dpid].update({link.dst.dpid: link.src.port_no} )
            # print(link.src.dpid, link.dst.dpid, link.src.port_no)
            # self.switch_dpid_links[link.src.dpid][link.dst.dpid].extend(link.src.port_no)
            

        print(f'\n\n\n\nswitch_dpid_links: {self.switch_dpid_links} \nlen = {len(self.switch_dpid_links)}\n\n\n\n')
        # for link in link_list:

        #     dst_dpid = link.dst.dpid
        #     src_dpid = link.src.dpid
        #     dst_port_no = link.dst.port_no

        #     self.switch_dpid_links[dst_dpid][src_dpid] = dst_port_no
            
        # print(f'switch_name_to_dpid: {self.switch_dpid_links} \nlen =  {len(self.switch_dpid_links)}\n\n\n\n')
        
            # self.switch_name_to_dpid[dst_name] = link.dst.dpid
        # print("Dpid_links: \n", self.switch_dpid_links)

        # self.dpid_to_hw_addr = {link.src.dpid : link.src.hw_addr for link in link_list}

        self.dpid_to_hw_addr = {}
        for link in link_list:
            if not link.src.dpid in self.dpid_to_hw_addr:
                self.dpid_to_hw_addr[link.src.dpid] = {link.dst.dpid : link.src.hw_addr}
            else:
                if not link.dst.dpid in self.dpid_to_hw_addr[link.src.dpid]:
                    self.dpid_to_hw_addr[link.src.dpid][link.dst.dpid] = link.src.hw_addr
        # print("Hw_addr_links: \n", self.dpid_to_hw_addr)


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

        #################################################################

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

        
        #################################################################
        # src, dst = '000000001', '000000014'
        #################################################################


        arp_pkt = pkt.get_protocol(arp.arp)

        if arp_pkt:
            # print(dir(arp_pkt))
            self.arp_table[arp_pkt.src_ip] = src

            # self.logger.info(" ARP: %s -> %s", arp_pkt.src_ip, arp_pkt.dst_ip)
            if self.arp_handler(msg):
                return None

            
        
        # no shortest path for arp requests
        else:
            # calculate shortest path between src and dst if it's not yet calculated
            if not self.shortest_path_dict[(src, dst)]:

                # # see if source and destination are servers
                # if src in self.topo_net.mac_to_id.keys() and dst in self.topo_net.mac_to_id.keys():

                # calculate shortest path as a list
                shortest_path = self.calculate_shortest_path(src, dst)
                # shortest path becomes value of current (src, dst) pair
                self.shortest_path_dict[(src, dst)] = shortest_path

        
        self.mac_to_port.setdefault(dpid, {})

        if not src in self.mac_to_port[dpid]:
        
            self.mac_to_port[dpid][src] = in_port

        # print(f'self.mac_to_port {self.mac_to_port}\n\n')


        if arp_pkt and dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
            # print('Flood_1')
            # out_port = ofproto.OFPP_FLOOD

            # out_port = None

        
        # else if we have the shortest path for the (src, dst) pair
        elif self.shortest_path_dict[(src, dst)]:


            print(f'\n\nDpid shortest path = {self.shortest_path_dict[(src, dst)]}')
            print(f'\n\nDpid shortest path[:-1] = {self.shortest_path_dict[(src, dst)][:-1]}')
            print(f'dpid: {dpid}')
            
            # print(f'Current index: {self.shortest_path_dict[(src, dst)].index(dpid)}')

            next_hop_index = self.shortest_path_dict[(src, dst)].index(dpid) + 1

            if next_hop_index == len(self.shortest_path_dict[(src, dst)]) - 1:
                # if dst in self.mac_to_port[dpid]:
                # print(f'self.mac_to_port[dpid]: {self.mac_to_port[dpid]}')
                # if dst in self.mac_to_port[dpid]:

                # print(f'self.mac_to_port[dpid][dst]: {self.mac_to_port[dpid][dst]}')

                out_port = self.mac_to_port[dpid][dst]

                next_dpid = self.shortest_path_dict[(src, dst)][next_hop_index]


                # print(f'Current dpid: {int(dpid)}')
                # print(f'Next_dpid: {next_dpid}')
                # print(f'Next_dst: {dst}')

            elif dpid in self.shortest_path_dict[(src, dst)][:-1]:

                next_dpid = self.shortest_path_dict[(src, dst)][next_hop_index]
                # print(f'next dpid: {next_dpid}')

                # # translate next dpid to a hw_addr
                # next_dst = self.dpid_to_hw_addr[int(next_dpid)]

                
                # print(f'Current dpid: {int(dpid)}')
                # print(f'Next dpid: {int(next_dpid)}')
                # print(f'Current mac: {self.dpid_to_hw_addr[int(dpid)]}')
                # print(f'Next mac: {self.dpid_to_hw_addr[int(next_dpid)]}\n')

                # print(f'mac_to_port.keys(): {self.mac_to_port.keys()}\n')
                # print(f'mac_to_port[{dpid}].keys(): {self.mac_to_port[dpid].keys()}\n')
                # print(f'mac_to_port[{dpid}].values(): {self.mac_to_port[dpid].values()}\n\n\n\n')

                # # if dpid in self.switch_dpid_links and next_dpid in self.switch_dpid_links[dpid]:
                out_port = self.switch_dpid_links[dpid][next_dpid]

                # out_port = self.mac_to_port[dpid][next_dst]

            else:
                # print('Flood_2')
                out_port = ofproto.OFPP_FLOOD
                # return


            # print(f'self.mac_to_port[dpid]: {self.mac_to_port[dpid].keys()}')
            # print(f'next_dst: {next_dst}')
            # if next_dst in self.mac_to_port[dpid].keys():

            #     # set next hw_addr as out_port
            #     out_port = self.mac_to_port[dpid][next_dst]

            # else:
            #     # print('Flood_1')
            #     out_port = ofproto.OFPP_FLOOD
            
        # if not dpid in self.shortest_path_dict[(src, dst)]:

        #     print('flood 1!')
        #     out_port = ofproto.OFPP_FLOOD

        else:
            # print('Flood_3')
            out_port = ofproto.OFPP_FLOOD


        # print(f'port_out: {out_port}')
        # actions = [parser.OFPActionOutput(out_port)]

        # # install a flow to avoid packet_in next time
        # if out_port != ofproto.OFPP_FLOOD:
        #     match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
        #     # verify if we have a valid buffer_id, if yes avoid to send both flow_mod & packet_out
        #     if msg.buffer_id != ofproto.OFP_NO_BUFFER:
        #         self.add_flow(datapath, 1, match, actions, msg.buffer_id)
        #         return
        #     else:
        #         self.add_flow(datapath, 1, match, actions)

        # data = None
        
        # if msg.buffer_id == ofproto.OFP_NO_BUFFER:
        #     data = msg.data

        # out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
        #                           in_port=in_port, actions=actions, data=data)
        # datapath.send_msg(out)



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

        #################################################################


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
            try:
                shortest_path_mininet.append(new_type)
            except:
                print(f'src_server, dst_server: {src_server}, {dst_server}')
                print(f'type, id: {type, id}')
                print(f'shortest_path_switches: {shortest_path_switches}')
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
                    print("ARP_Reply")
                    return True
        return False



print('Running..')
SPRouter()
