/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4 = 0x800;
const bit<16> PROTOCOL_UDP = 0x11;

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

/* define packet headers for Ethernet, IPv4, UDP, and RTP */

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

// Multicast group
typedef bit<16> mcg_t;

// Define header format of ethernet 
header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

// Define header format of ipv4 
header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<8>    diffserv;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

// Define header format of udp 
header udp_t {
    bit<16>    src_port;
    bit<16>    dst_port;
    bit<16>    oct_length;
    bit<16>    checksum;
}

// Define header format of rtp
header rtp_t {
    bit<2>    version;
    bit<1>    padding;
    bit<1>    extension;
    bit<4>    csrc_count;
    bit<1>    marker;
    bit<7>    payload_type;
    bit<16>   sequence_number;
    bit<32>   timestamp;
    bit<32>   ssrc;
}


struct metadata {
    /* empty */
}

struct headers {
    ethernet_t  ethernet;
    ipv4_t      ipv4;
    udp_t       udp;
    rtp_t       rtp;
}


/*************************************************************************
*********************** P A R S E R  ***********************************
*************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        /* parse packet headers up to RTP if possible */
        transition parse_ethernet;
    }

    // Parse ethernet
    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    // Parse ipv4
    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select((bit<16>)hdr.ipv4.protocol) {
            PROTOCOL_UDP: parse_udp;
            default: accept;
        }
    }

    // Parse udp
    state parse_udp {
        packet.extract(hdr.udp);
        transition accept;
    }

    // Parse rtp
    state parse_rtp {
        packet.extract(hdr.rtp);
        transition accept;
    }
}

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {   
    apply {  
    }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    // drop metadata
    action drop() {
        mark_to_drop(standard_metadata);
    }
    
    // Forward ipv4 packet
    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        standard_metadata.egress_spec = port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;

        // Decrease Time To Live (TTL) of IPv4 packet with one
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    // Assign multicast group ID
    action mcast_group(macAddr_t dstAddr, egressSpec_t port, mcg_t mcast_grp_id) {
        if(hdr.udp.isValid()) {
            standard_metadata.mcast_grp = mcast_grp_id;
        } else {
            ipv4_forward(dstAddr, port);
        }
    }
    
    // Ipv4_LPM table from tutorial
    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            ipv4_forward;
            drop;
            NoAction;
            mcast_group;
        }
        size = 1024;
        default_action = drop();
    }
    
    apply {
        if (hdr.ipv4.isValid()) {
            ipv4_lpm.apply();
        }
    }

}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    // drop metadata
    action drop() {
        mark_to_drop(standard_metadata);
    }


    //Multicast UDP Packets, changing destination mac AND IP to h3..
    action update_destination(macAddr_t dstAddr_mac, ip4Addr_t dstAddr_ip) {
        hdr.ethernet.dstAddr = dstAddr_mac;
        hdr.ipv4.dstAddr = dstAddr_ip;
        hdr.udp.checksum = 0;
    }

    // Forward ipv4 packet
    action ipv4_forward(macAddr_t dstAddr) {
        // Port is set in set_mcg
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;

        // Decrease Time To Live (TTL) of IPv4 packet with one
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    // Route to new dstAddr
    action set_new_dst(ip4Addr_t dstAddr){
        hdr.ipv4.dstAddr = dstAddr;
    }
    
    // Ipv4_LPM table from tutorial
    table NAT_match_action_table {
        key = {
            standard_metadata.egress_rid : exact;
            standard_metadata.egress_port: exact;
        }
        actions = {
            NoAction;
            update_destination;
        }

        size = 1024;
        default_action = NoAction;
    }
    
    apply {
        // drop packet when it's send to ingress port
        if (hdr.udp.isValid()) {
            NAT_match_action_table.apply();
    	}
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
     apply {
         update_checksum (
    	    hdr.ipv4.isValid(),
                {
                  hdr.ipv4.version,
    	          hdr.ipv4.ihl,
                  hdr.ipv4.diffserv,
                  hdr.ipv4.totalLen,
                  hdr.ipv4.identification,
                  hdr.ipv4.flags,
                  hdr.ipv4.fragOffset,
                  hdr.ipv4.ttl,
                  hdr.ipv4.protocol,
                  hdr.ipv4.srcAddr,
                  hdr.ipv4.dstAddr
                },
                hdr.ipv4.hdrChecksum,
                HashAlgorithm.csum16);

        update_checksum_with_payload (
			hdr.udp.isValid(), 
			{
			    hdr.ipv4.srcAddr,
    			    hdr.ipv4.dstAddr,
    			    8w0,
    			    hdr.ipv4.protocol,
    			    hdr.udp.oct_length,
    			    hdr.udp.src_port,
    			    hdr.udp.dst_port,
    			    hdr.udp.oct_length
			},
                        hdr.udp.checksum,
                        HashAlgorithm.csum16);
     }
}

/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
	packet.emit(hdr.udp);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;
