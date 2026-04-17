from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types

class SDNArpLearningSwitch(app_manager.RyuApp):   #class is the controller
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNArpLearningSwitch, self).__init__(*args, **kwargs)  #setting env
        self.mac_to_port = {}   #a dictionary to map mac address to switch ports
        self.arp_table = {}     #dictionary to store ip to mac mapping for proxy logic

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath   #identifies switch sending message
        ofproto = datapath.ofproto   #access to OpenFlow
        parser = datapath.ofproto_parser

        # Install table-miss flow entry: send all unknown packets to controller
        match = parser.OFPMatch()   # empty match to every incoming packet
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]   # action to tell the switch to send any unknown packet to the controller for instructions
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):  #add a new rule into switch's memory and packages into OF instruction set
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)  #triggered whenever switch recieves packet it doesn't recognise
    def _packet_in_handler(self, ev):
        msg = ev.msg   # extract message
        datapath = msg.datapath    #datapath object represents switch
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']  #identifies the port packet entered

        pkt = packet.Packet(msg.data)   #decodes binary data
        eth = pkt.get_protocols(ethernet.ethernet)[0]  #extracts the ethernet header to get mac address

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:  
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # 1. ARP Handling Logic
        if eth.ethertype == ether_types.ETH_TYPE_ARP:  #checks if incoming packet is arp message
            arp_pkt = pkt.get_protocols(arp.arp)[0]    # extracts the arp details: ip and mac
            self.arp_table[arp_pkt.src_ip] = src       # learn the IP->MAC mapping
            
            if arp_pkt.opcode == arp.ARP_REQUEST:      #checks for "who has this ip?""
                if arp_pkt.dst_ip in self.arp_table:   #checks if the controller aldready knows the mac to arp request (ip)
                    self.logger.info("Proxy ARP Reply from Controller for IP %s", arp_pkt.dst_ip)
                    self.send_arp_reply(datapath, self.arp_table[arp_pkt.dst_ip], arp_pkt, in_port)
                    return
            
        # 2. Learning Switch Logic (for ICMP/Ping traffic)
        self.logger.info("Packet In: DPID %s | %s -> %s | Port %s", dpid, src, dst, in_port)
        
        # Learn the MAC to Port mapping
        self.mac_to_port[dpid][src] = in_port   #which port a specific host is using to reach switch

        # If destination MAC is known, set out_port, else Flood
        if dst in self.mac_to_port[dpid]:   #checking if its already known which port is destination linked to
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD  #if not know send packet out of every port: flooding

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow rule to the switch to handle future packets of this flow
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # Verify if we have a valid buffer_id
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)  
                return
            else:
                self.add_flow(datapath, 1, match, actions)   #permanently writing the rule into switch's memory for any further packets between 2 hosts bypass the controller

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,   #sending current packet out of switch
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)   #packet-out: move data

    def send_arp_reply(self, datapath, dst_mac, arp_pkt, out_port):   #custom arp response
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_ARP,   #creates outer ethernet envelope
                                           dst=arp_pkt.src_mac,
                                           src=dst_mac))        
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                 src_mac=dst_mac, src_ip=arp_pkt.dst_ip,    #fills arp answer: ie ip and mac
                                 dst_mac=arp_pkt.src_mac, dst_ip=arp_pkt.src_ip))
        pkt.serialize()   #packet object to binary bytes for transmission
        
        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER,
            in_port=datapath.ofproto.OFPP_CONTROLLER,
            actions=actions, data=pkt.data)
        datapath.send_msg(out)   #send arp reply from controller to host
