/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

// Defining constants
const bit<16> TYPE_IPV4 = 0x800;

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

header ethernet_t {
    // Ethernet Headers..
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

// IPv4 Headers..
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

struct metadata {
    /* empty */
}

// header struct
struct headers {
    ethernet_t ethernet;
    ipv4_t ipv4;
}

/*************************************************************************
*********************** P A R S E R  ***********************************
*************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    /*
     * If type is IPv4, then parse_ipv4
     * else accept state..
     */
    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    /*
     * IPv4 packet transition to accept state..
     */
    state parse_ipv4 {
        packet.extract(hdr.ipv4);
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
    /*
     * egress port->destination MAC to source MAC of next HOP conversion
     * ->New MAC Address from table->TTL Reduction..
     */
    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        standard_metadata.egress_spec = port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;

        // Decrease Time To Live (TTL) of IPv4 packet with one
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
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
    apply {  
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

// Generate a new checksum for the updated headers with HashAlgorithm
control MyComputeChecksum(inout headers  hdr, inout metadata meta) {
    apply {
        update_checksum(
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
    }
}

/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

// Parts not parsed as a header are regarded as data/payload of packet.
control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
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
