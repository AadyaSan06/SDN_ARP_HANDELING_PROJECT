# SDN ARP HANDELING PROJECT

NAME: AADYA SANTHOSH

SRN: PES1UG24CS005

<br>PROBLEM STATEMENT

This project implements an ARP Proxy using the Ryu Controller and OpenFlow 1.3 to optimize address resolution and reduce broadcast traffic within a Mininet-simulated Software Defined Network.

<br>OBJECTIVES

- Minimizes network flooding: by handeling ARP requests at the controller level, we prevent traditional ARP broadcast from reaching every host, saving bandwidth.
- Intelligent forwarding: implementing a learning switch mechanism that installs reactive match-action flow rules in the switch's hardware.
- Performance optimization: validating that hardware-level forwarding (data plane) significantly outperforms software based controller intervention (control plane).

<br>NETWORK TOPOLOGY & DESIGN
- Topology: A custom Mininet topology consisting of a central OpenFlow-enabled switch connected to 3 hosts.
  
  A single-switch, 3-host topology was chosen to clearly demonstrate ARP resolution and flow rule installation without unnecessary     path complexity.
- Controller: Ryu Controller (Python 3.8 based).
- Logic: The controller functions as a Learning Switch with advanced ARP Proxy capabilities to reduce broadcast traffic and optimize the discovery process.

<br>SETUP & EXECUTION
1. Start the Ryu controller

   ryu-manager your_controller_script.py
   <img width="727" height="531" alt="image" src="https://github.com/user-attachments/assets/fb581bc8-f0b4-4497-a0af-971348aeeb18" />

3. Launch Mininet

   sudo mn --topo single,3 --controller remote,ip=127.0.0.1 --mac
   <img width="720" height="346" alt="image" src="https://github.com/user-attachments/assets/2f041fbf-1b04-488f-adf2-90e1a0fc0448" />

5. Verify connectivity
   In the Mininet CLI, run:
   - pingall: to trigger the discovery and flow rule installation process
     <img width="364" height="114" alt="image" src="https://github.com/user-attachments/assets/f1817bfd-72c4-455b-81cc-9b2e8f03b8bc" />

   - iperf h1 h2: to check the maximum network bandwidth
     <img width="455" height="57" alt="image" src="https://github.com/user-attachments/assets/16c08973-70bc-4edd-9b76-c089f6f184da" />

6. Wireshark capture

   - sudo ovs-ofctl dump-flows s1 -O OpenFlow13
     <img width="716" height="191" alt="image" src="https://github.com/user-attachments/assets/961105d1-797f-4fb0-a446-b86e9d0dc2ad" />


   - wireshark orange_project.pcap &
     <img width="727" height="253" alt="image" src="https://github.com/user-attachments/assets/8ae36e73-a4b7-4e93-ba80-4171d60d05a4" />


<br>IMPLEMENTATION DETAILS

- Packet-In Handling: The controller intercepts unknown packets, learns the source MAC/port mapping, and determines the output port.
- Flow Rule Design: Uses OFPFlowMod to install match-action rules with specific priorities to ensure hardware-level forwarding for subsequent packets.
- ARP Proxy: The controller maintains an IP-to-MAC table to directly reply to ARP requests, preventing unnecessary flooding across the network.

<br>PERFORMANCE OBSERVATION & ANALYSIS

The following metrics were used to validate the functional correctness and efficiency of the SDN project:
- Connectivity (using ping)- Running pingall demonstrates successful end to end reachability. Initial pings show higher latency due to "Controller-Switch" handshake (Packet-In) while subsequent pings show minimal latency once flow rules are installed.
- Throughput (using iperf)- High throughput (43.7 Gbits/sec) confirms that after the initial flow rule installation, the data plane handles traffic at hardware capacity without further controller intervention.
- Flow table validation using the command: sudo ovs-ofctl -O OpenFlow13 dump-flows s1

<br>TEST SCENARIOS
1. Normal forwarding: Successful communication between all hosts via the controller's learning logic.
2. Flow installation: Verification that "Packet-In" events cease once the switch flow table is populated for a specific stream.

<br>CONCLUSION

The project successfully demonstrates an efficient SDN architecture where the Ryu controller effectively reduces network overhead by proxying ARP requests and offloading traffic handling to high-speed, hardware-level flow rules.

  

   


