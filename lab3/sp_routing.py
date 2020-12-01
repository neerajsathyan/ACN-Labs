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
from ryu.lib.packet import ethernet, ether_types
from ryu.lib.packet import icmp
###################################

from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase

import topo
import dijkstra
from collections import defaultdict



# def mac_to_server_id(mac_addr):



#     return server_id

def default_dict():
	return defaultdict(default_dict)


class SPRouter(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SPRouter, self).__init__(*args, **kwargs)
        self.topo_net = topo.Fattree(4)

        # Used for learning switch functioning
        self.mac_to_port = {}

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
        self.switch_dpids = [switch.dp.id for switch in switch_list]
        # print(self.switch_dpids)

        self.switch_name_to_dpid = {str(link.src.name).split("-")[0][2:] : link.src.dpid for link in link_list} 
        # print(self.switch_name_to_dpid)



        # link dictionary {src_dpid : {dst_dpid : {src_port_to_dst}}}
        self.switch_dpid_links = {link.src.dpid : {link.dst.dpid : {link.src.port_no}} for link in link_list}
        # print("Dpid_links: \n", self.switch_dpid_links)

        self.dpid_to_hw_addr = {link.src.dpid : link.src.hw_addr for link in link_list}
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
        
        dst = pkt_eth.dst
        src = pkt_eth.src

        
        #################################################################
        # src, dst = '000000001', '000000014'
        #################################################################
        # print(src, dst)

        # calculate shortest path between src and dst if unknown
        if not (src, dst) in self.shortest_path_dict.keys():
            
            shortest_path = self.calculate_shortest_path(src, dst)

            # save shortest path for src and dst
            self.shortest_path_dict[(src, dst)] = shortest_path

            # print(f'\n\nDpid shortest path = {self.shortest_path_dict[(src, dst)]}\n')

            hw_addr_shortest_path = [self.dpid_to_hw_addr[int(dpid)] for dpid in self.shortest_path_dict[(src, dst)][1:-1] if int(dpid) in self.dpid_to_hw_addr]
            hw_addr_shortest_path.insert(0, src)
            hw_addr_shortest_path.insert(len(self.shortest_path_dict[(src, dst)]) + 1, dst)

            # print(f'Hw_addr_shortest_path = {hw_addr_shortest_path}\n')

        # current dpid
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})

        # self.logger.info("\tpacket in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:

            # determine next dpid hop for current dpid
            next_dpid = self.shortest_path_dict[(src, dst)][dpid]

            # translate next dpid to a hw_addr
            next_dst = self.dpid_to_hw_addr[int(next_dpid)]

            # set next hw_addr as out_port
            out_port = self.mac_to_port[dpid][next_dst]
            print(out_port)


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


    def calculate_shortest_path(self, src_mac, dst_mac):

        # print(f'\nsrc_mac, dst_mac = {src_mac}, {dst_mac}')
        print('src_mac, dst_mac = ',src_mac, dst_mac)
        src_server, dst_server = int(src_mac.replace('0', '').replace(':', '')), int(dst_mac.replace('0', '').replace(':', ''))
        # print(f'src_server, dst_server = {src_server}, {dst_server}\n')
        

        shortest_path_switches = dijkstra.shortest_path_list(self.dijkstra_table, src_server, dst_server, self.n_servers)
        print(f'Shortest_path = {shortest_path_switches}\n')

        shortest_path_mininet = []

        # for (type, id) in shortest_path_switches:

        #     if type == 'server':
        #         continue
        #         # new_type = 'host_' + str(id)
        #     elif type == 'edge switch':
        #         new_type = 'es_' + str(id)
        #     elif type == 'aggregate switch':
        #         new_type = 'as_' + str(id)
        #     elif type == 'core switch':
        #         new_type = 'cs_' + str(id)

            # shortest_path_mininet.append(new_type)

        # print(f'Mininet_shortest_path = {shortest_path_mininet}\n')
        
        dpid_shortest_path = [self.switch_name_to_dpid[name] for name in shortest_path_mininet if name in self.switch_name_to_dpid]
        dpid_shortest_path.insert(0, src_mac)
        dpid_shortest_path.insert(len(dpid_shortest_path), dst_mac)

        # print(f'Dpid_shortest_path = {dpid_shortest_path}\n')


        # hw_addr_shortest_path = [self.dpid_to_hw_addr[int(dpid)] for dpid in dpid_shortest_path if int(dpid) in self.dpid_to_hw_addr]
        # hw_addr_shortest_path.insert(0, src_mac)
        # hw_addr_shortest_path.insert(len(dpid_shortest_path), dst_mac)

        # print(f'Hw_addr_shortest_path = {hw_addr_shortest_path}\n')

    
        return dpid_shortest_path



print('Running..')
SPRouter()
