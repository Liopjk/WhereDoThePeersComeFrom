#!/usr/bin/python3
import sys
import signal
import getopt
import subprocess

import json
from datetime import datetime, timedelta
import time

import pyshark
from pyshark.packet.packet import Packet
from pyshark.capture.pipe_capture import PipeCapture

import LibPeerFrom.Helpers
from LibPeerFrom.Peer import Peer
from LibPeerFrom.Peers import Peers

def usage():
    print("WhereDoThePeersComeFrom.py: a tool to monitor latency to peers in a from software multiplayer session")
    print("accepts a wireshark capture from stdin or an ssh session and shows peer info. ctrl+c to exit.")
    print("options:")
    print(" -h, --help:                  print this text and exit")
    print(" -a, --address (required):    ip address of the host you are playing elden ring or dark souls 3 on")
    print(" -v, --debug, --verbose:      print additional output")
    print(" -m, --sortmode:              how peers should be sorted when displayed. options are:")
    print("                                 {first_seen, last_seen, ip, ping}")
    print("                                 default is last_seen")
    print(" -o, --sortorder:            sort order of the peers. options: {asc, desc, ascending, descending}")
    print("                                 default is descending")
    print(" --cachepath:                path to the ping cache file")
    print("                                 default is \"\" (no cache). will be created if none exists.")
    print(" --router_address:           address to ssh to. if this is not supplied we assume a wireshark capture")
    print("                                 is supplied to stdin. assumes that default ssh settings will work")
    print(" --ipinfo_token              token for accessing ipinfo.io. if this is not provided you may be rate limited")
    print(" --config_file               path to json-formatted config file")
    print("")

def clear_stdout_stderr():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stderr.write("\x1b[2J\x1b[H")

def sigint_handler(signum, frame):
    exit()
signal.signal(signal.SIGINT, sigint_handler)

try:
    opts, args = getopt.getopt(sys.argv[1:], ["vha:m:o:"], ["help", "config_file=", "debug", "verbose", \
                                                            "address=", "sortmode=", "sortorder=", \
                                                            "cachepath=","router_address=", \
                                                            "ipinfo_token="])
except getopt.GetoptError:
    usage()
    exit()

def main():
    DEBUG = False
    local_ip = None
    sort_mode = "last_seen"
    sort_order = "descending"
    cache_path = ""
    router_address = ""
    config_file_path = ""

    for o, a in opts:
        if o in ["--help", "-h"]:
            usage()
            exit()
        elif o in ["--debug", "--verbose", "-v"]:
            DEBUG = True
        elif o in ["--address", "-a"]:
            local_ip = a
        elif o in ["--sortmode", "-m"]:
            if a.lower() in ["first_seen","last_seen", "ip", "ping"]:
                sort_mode = a.lower()
            else:
                usage()
                exit()
        elif o in ["--sortorder", "-o"]:
            if a.lower().startswith("asc"):
                sort_order = "ascending"
            elif a.lower().startswith("desc"):
                sort_order = "descending"
            else:
                usage()
                exit()
        elif o in ["--cachepath"]:
            cache_path = a
        elif o in ["--router_address"]:
            router_address = a
        elif o in ["--ipinfo_token"]:
            LibPeerFrom.Helpers.IPINFO_TOKEN = a
        elif o in ["--config_file"]:
            config_file_path = a

    if config_file_path != "":
        with open(config_file_path) as config_file:

            config = json.load(config_file)
            if "address" in config.keys():
                local_up = config["address"]
            if "sortmode" in config.keys():
                if config["sortmode"] in ["first_seen","last_seen", "ip", "ping"]:
                    sort_mode = config["sortmode"]
            if "sortorder" in config.keys():
                if config["sortorder"].startswith("asc"):
                    sort_order = "ascending"
                if config["sortorder"].startswith("desc"):
                    sort_order = "descending"

            if "router_address" in config.keys():
                router_address = config["router_address"]
            if "cachepath" in config.keys():
                cache_path = config["cachepath"]
            if "ipinfo_token" in config.keys():
                LibPeerFrom.Helpers.IPINFO_TOKEN = config["ipinfo_token"]
            

    

    if local_ip == None:
        usage()
        exit()
        

    peers = Peers(local_ip, sort_mode, sort_order, cache_path)
    print("local IP address: ",local_ip)
    last_maintenance_time = datetime.now()
    peers.restore_cache()
    
    # Assume we're using stdin
    pipecapture_source = sys.stdin

    if router_address != "":
        ssh_command = f"/usr/sbin/tcpdump host {local_ip} -U -w - "
        ssh_process = subprocess.Popen(["ssh", router_address, ssh_command], stdout=subprocess.PIPE)
        
        time.sleep(2)
        if ssh_process.poll() is not None:    
            print("error: ssh session has closed")
            print(ssh_process.stderr)
            exit(1)

        pipecapture_source = ssh_process.stdout
    
    
    packet: Packet
    for packet in PipeCapture(pipecapture_source):
        current_time = datetime.now()
        if 'ip' in packet and 'udp' in packet:
            peers.add_peer_from_packet(packet)

        if (packet.sniff_time - last_maintenance_time).total_seconds() > 20:
            print("running maintenance")
            # remove all peers that haven't been seen in the last 30s
            peers.remove_stale_peers(packet.sniff_time - timedelta(seconds=30))
            peers.ping_peers()
            peers.ping_cache.apply_minimum_pings()
            peers.estimate_guess_peers()
            peers.persist_cache()
            last_maintenance_time = current_time

            # Cache all our accurate peers every 10 minutes
            # This means that accurate peers will have more entries in the cache
            if packet.sniff_time.minute % 10 == 0:
                peers.cache_accurate_peers()
            
        
        clear_stdout_stderr()
        print(f"local ip address:       {local_ip}")

        if DEBUG:
            if current_time > packet.sniff_time:
                scan_delay = current_time - packet.sniff_time
            else:
                scan_delay = packet.sniff_time - current_time 
            print(f"last maintenance time:  {last_maintenance_time.time().strftime('%H:%M:%S')}")
            #print(f"last packet sniff time: {packet.sniff_time.time().strftime('%H:%M:%S')}")
            print(f"current time:           {current_time.time().strftime('%H:%M:%S')}")
            print(f"scan delay:             {scan_delay}")
            print(f"ping cache location:    {cache_path}")
            print(f"ping cache size:        {len(peers.ping_cache._storage)}")
            #print(f"ping cache hit count:   {peers.ping_cache.hit_count}")
        
        print(f"peer(s):                {len(peers)}")
        print()

        # finally, we print
        print(peers)


if __name__ == "__main__": 
    main()