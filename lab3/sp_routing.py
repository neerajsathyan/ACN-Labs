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

        print(f'self.topo_net.mac_to_id.keys(): {self.topo_net.mac_to_id.keys()}')
        print(f'self.topo_net.mac_to_id.values(): {self.topo_net.mac_to_id.values()}\n\n\n\n')


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
        self.switch_dpid_links = {link.src.dpid : {link.dst.dpid : link.src.port_no} for link in link_list}
        # print(f'\n\n\n\nswitch_dpid_links: {self.switch_dpid_links} \nlen = {len(self.switch_dpid_links)}\n\n\n\n')
        # for link in link_list:

        #     dst_dpid = link.dst.dpid
        #     src_dpid = link.src.dpid
        #     dst_port_no = link.dst.port_no

        #     self.switch_dpid_links[dst_dpid][src_dpid] = dst_port_no
            
        # print(f'switch_name_to_dpid: {self.switch_dpid_links} \nlen =  {len(self.switch_dpid_links)}\n\n\n\n')
        
            # self.switch_name_to_dpid[dst_name] = link.dst.dpid
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
        # src_server = int(self.topo_net.mac_to_id[src])
        # dst_server = int(self.topo_net.mac_to_id[dst])

        # destination is next hop
        if dpid in self.mac_to_port and dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]

        else:

            # calculate shortest path between src and dst if unknown
            if not self.shortest_path_dict[(src, dst)]:
                # print(f'src, dst: {src} {dst}')

                # print('yes')


                #####################################
                # ARP REQUEST
                ###########################################

                # see if source and destination are servers
                if src in self.topo_net.mac_to_id.keys() and dst in self.topo_net.mac_to_id.keys():
                    
                    # print('yes2')

                    # print(f'src_mac, src_server: {src}, {self.topo_net.mac_to_id[src]}')
                    # print(f'dst_mac, dst_server: {dst}, {self.topo_net.mac_to_id[dst]}')
                
                    shortest_path = self.calculate_shortest_path(src, dst)

                    # save shortest path for src and dst
                    self.shortest_path_dict[(src, dst)] = shortest_path

                    # print(f'\n\n\n{shortest_path}\n')

                    src_server = int(self.topo_net.mac_to_id[src])
                    dst_server = int(self.topo_net.mac_to_id[dst])

                    print(f'src_server, dst_server: {src_server}, {dst_server}')

                    print(f'\n\nDpid shortest path = {self.shortest_path_dict[(src, dst)]}\n')

                    # hw_addr_shortest_path = [self.dpid_to_hw_addr[int(dpid)] for dpid in self.shortest_path_dict[(src, dst)][1:-1] if int(dpid) in self.dpid_to_hw_addr]
                    # hw_addr_shortest_path.insert(0, src)
                    # hw_addr_shortest_path.insert(len(self.shortest_path_dict[(src, dst)]) + 1, dst)

                    # print(f'Hw_addr_shortest_path = {hw_addr_shortest_path}\n')

                # else: 
                #     return

            

            # current dpid
            dpid = datapath.id
            # print(dpid)

            self.mac_to_port.setdefault(dpid, {})

            # self.logger.info("\tpacket in %s %s %s %s", dpid, src, dst, in_port)

            # learn a mac address to avoid FLOOD next time.
            self.mac_to_port[dpid][src] = in_port

            port_no = None

            next_dst = None
            next_dpid = None

            # determine next dpid hop for current dpid
            print(f'\n\nDpid shortest path = {self.shortest_path_dict[(src, dst)]}')

            if self.shortest_path_dict[(src, dst)]:

                print(f'Shorest path: {self.shortest_path_dict[(src, dst)]}')
                print(f'dpid: {dpid}')
                if dpid in self.shortest_path_dict[(src, dst)]:
                    print(f'Current index: {self.shortest_path_dict[(src, dst)].index(dpid)}')

                    next_hop_index = self.shortest_path_dict[(src, dst)].index(dpid) + 1

                    if next_hop_index == len(self.shortest_path_dict[(src, dst)]) - 1:

                        next_dpid = self.shortest_path_dict[(src, dst)][next_hop_index]

                        for mac, id in self.topo_net.mac_to_id.items():
                            
                            if int(id) == next_dpid:
                                next_dst = mac
                                continue

                        print(f'Current dpid: {int(dpid)}')
                        print(f'Next_dpid: {next_dpid}')

                        print(f'Next_dst: {next_dst}')
                        # self.mac_to_port[dpid][next_dst] = 

                    else:
                        print(f'\n\n\n\nShortest path: {self.shortest_path_dict[(src, dst)]}')
                        print(f'Next hop index: {next_hop_index}')

                        next_dpid = self.shortest_path_dict[(src, dst)][next_hop_index]
                        print(f'next dpid: {next_dpid}')

                        # translate next dpid to a hw_addr
                        next_dst = self.dpid_to_hw_addr[int(next_dpid)]

                        
                        print(f'Current dpid: {int(dpid)}')
                        print(f'Next dpid: {int(next_dpid)}')
                        print(f'Current mac: {self.dpid_to_hw_addr[int(dpid)]}')
                        print(f'Next mac: {self.dpid_to_hw_addr[int(next_dpid)]}\n')

                        print(f'mac_to_port.keys(): {self.mac_to_port.keys()}\n')
                        print(f'mac_to_port[{dpid}].keys(): {self.mac_to_port[dpid].keys()}\n')
                        print(f'mac_to_port[{dpid}].values(): {self.mac_to_port[dpid].values()}\n\n\n\n')

                        try:
                            port_no = self.switch_dpid_links[dpid][next_dpid]
                        except:
                            pass
                        print(f'port_no: {port_no}')


                print(f'self.mac_to_port[dpid]: {self.mac_to_port[dpid].keys()}')
                print(f'next_dst: {next_dst}')
                if next_dst in self.mac_to_port[dpid].keys():

                    if port_no:
                        out_port = port_no
                    else:
                        # set next hw_addr as out_port
                        out_port = self.mac_to_port[dpid][next_dst]
                        print(f'out_port: {out_port}')

                else:
                    print('Flood_1')
                    out_port = ofproto.OFPP_FLOOD
                


            else:
                print('Flood_2')
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

        # if they are, calculate shortest path between the two
        src_server = int(self.topo_net.mac_to_id[src_mac])
        dst_server = int(self.topo_net.mac_to_id[dst_mac])

        # src_server, dst_server = 1, 14
        

        # print(f'\nsrc_mac, dst_mac = {src_mac}, {dst_mac}')
        # print('\n\n\n\nsrc_server, dst_server = ',src_server, dst_server)

    
        # print(src_server, dst_server)

        # src_server, dst_server = int(src_mac.replace('0', '').replace(':', '')), int(dst_mac.replace('0', '').replace(':', ''))
        # print(f'src_server, dst_server = {src_server}, {dst_server}\n')
        
        # print(f'')
        # print(f'\nDijkstra')
        # for start_id in self.dijkstra_table:
        #     for end_id in self.dijkstra_table[start_id]:
        #         for type in self.dijkstra_table[start_id][end_id]:

                    
        #             print(f'{start_id} : {end_id} : {type}')
        #             continue

        #         continue
        #     continue

        # print(f"\nDict for {src_server}, {dst_server} {self.dijkstra_table[src_server][dst_server].keys()}\n\n")

        shortest_path_switches = dijkstra.shortest_path_list(self.dijkstra_table, src_server, dst_server, self.n_servers)
        # print(f'\n\n\n\nShortest_path = {shortest_path_switches}\n')
        # print(path for path in shortest_path_switches)

        shortest_path_mininet = []

        for (type, id) in shortest_path_switches:
            # print(f'type, id = {type}, {id}')

            if type == 'server':
                continue
                # new_type = 'host_' + str(id)
            elif type == 'edge switch':
                new_type = 'es_' + str(id)
            elif type == 'aggregate switch':
                new_type = 'as_' + str(id)
            elif type == 'core switch':
                new_type = 'cs_' + str(id)

            shortest_path_mininet.append(new_type)

        # print(f'Mininet_shortest_path = {shortest_path_mininet}\n')
        
        dpid_shortest_path = [self.switch_name_to_dpid[name] for name in shortest_path_mininet if name in self.switch_name_to_dpid]
        # dpid_shortest_path.insert(0, src_server)
        dpid_shortest_path.insert(len(dpid_shortest_path), dst_server)

        # print(f'Dpid_shortest_path = {dpid_shortest_path}\n')


        hw_addr_shortest_path = [self.dpid_to_hw_addr[int(dpid)] for dpid in dpid_shortest_path if int(dpid) in self.dpid_to_hw_addr]
        hw_addr_shortest_path.insert(0, src_mac)
        hw_addr_shortest_path.insert(len(dpid_shortest_path) + 1, dst_mac)

        # print(f'Hw_addr_shortest_path = {hw_addr_shortest_path}\n\n\n\n\n\n')

    
        return dpid_shortest_path



print('Running..')
SPRouter()
