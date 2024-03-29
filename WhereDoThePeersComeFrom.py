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
    print(" --friendlyname_file         path to json-formatted map from ip to friendlyname")
    print(" --html_file                 path to a html file for outputting. should be in the same folder as main.css.")
    print("                                 will be created if it does not exist. no output if unspecified.")
    print(" --peers_json_file           path to a json file for outputting peer status. will be created if it does not exist.")
    print("                                 no output if unspecified.")
    print(" --no_tui                    don't print the terminal ui")
    print("")

def clear_stdout_stderr():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stderr.write("\x1b[2J\x1b[H")

def sigint_handler(signum, frame):
    exit()
signal.signal(signal.SIGINT, sigint_handler)

try:
    opts, args = getopt.getopt(sys.argv[1:], ["vha:m:o:"], ["help", "no_tui", "config_file=", "debug", "verbose", \
                                                            "address=", "sortmode=", "sortorder=", \
                                                            "cachepath=","router_address=", \
                                                            "ipinfo_token=","html_file=","friendlyname_file=","peers_json_file="])
except getopt.GetoptError as e:
    print(e)
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
    friendlyname_file_path = ""
    html_file = ""
    peers_json_file = "/tmp/WhereDoThePeersComeFrom.html"
    show_tui = True

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
                print("bad sortmode supplied")
                usage()
                exit()
        elif o in ["--sortorder", "-o"]:
            if a.lower().startswith("asc"):
                sort_order = "ascending"
            elif a.lower().startswith("desc"):
                sort_order = "descending"
            else:
                print("bad sortorder supplied")
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
        elif o in ["--html_file"]:
            html_file = a
        elif o in ["--friendlyname_file"]:
            friendlyname_file_path = a
        elif o in ["--peers_json_file"]:
            peers_json_file = a
        elif o in ["--no_tui"]:
            show_tui = False

    if config_file_path != "":
        with open(config_file_path) as config_file:

            config = json.load(config_file)
            if "address" in config.keys():
                local_ip = config["address"]
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
            if "html_file" in config.keys():
                html_file = config["html_file"]
            if "debug" in config.keys():
                DEBUG = True
            if "verbose" in config.keys():
                DEBUG = True
            if "friendlyname_file" in config.keys():
                friendlyname_file_path = config["friendlyname_file"]
            if "peers_json_file" in config.keys():
                peers_json_file = config["peers_json_file"]
            
    if local_ip == None:
        print("no IP supplied")
        usage()
        exit()
        
    peers = Peers(local_ip, sort_mode, sort_order, cache_path)
    print("local IP address: ",local_ip)
    sys.stdout.flush()
    last_maintenance_time = datetime.now()
    last_print_time = last_maintenance_time
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
            sys.stdout.flush()
            exit(1)
        pipecapture_source = ssh_process.stdout
      
    packet: Packet
    for packet in PipeCapture(pipecapture_source):
        should_run_maintenance = False
        current_time = datetime.now()
        if 'ip' in packet and 'udp' in packet:
            p = peers.add_peer_from_packet(packet)
            # run maintenance as soon as we add a peer
            # this will update the friendlynames.json file
            if p is not None: should_run_maintenance = True
            if p is not None and not show_tui:
                print(f"{packet.sniff_time}: peer {p.get_name()} added ({p.estimate_geoip()})")
                sys.stdout.flush()

        
        # run maintenance every 20 seconds, as long as there's peers
        time_since_last_maint = packet.sniff_time - last_maintenance_time
        if (time_since_last_maint).total_seconds() > 20 and len(peers) > 0:
            should_run_maintenance = True
        # run maintenance every 10 minutes if there's no peers
        # in minute {0,10,20,30,40,50}
        if ( time_since_last_maint.total_seconds() > 600) \
            and packet.sniff_time.minute % 10 == 0:
            should_run_maintenance = True
        
        if should_run_maintenance:
            print("running maintenance")
            sys.stdout.flush()
            # remove all peers that haven't been seen in the last 30s
            peers.remove_stale_peers(packet.sniff_time - timedelta(seconds=30))
            peers.ping_peers()
            peers.ping_cache.apply_minimum_pings()
            peers.estimate_guess_peers()
            peers.persist_cache()
            if friendlyname_file_path != "":
                with open(friendlyname_file_path, 'r+') as friendlyname_file:
                    friendlynames: dict[str,str] = {k:v for k,v in json.load(friendlyname_file).items() if v != ""}
                    p: Peer
                    for p in peers._storage:
                        if p.remote_ip in friendlynames.keys():
                            p.friendly_name = friendlynames[p.remote_ip]
                        else:
                            friendlynames[p.remote_ip] = ""
                    friendlyname_file.seek(0)
                    json.dump(friendlynames, friendlyname_file, sort_keys=True, indent=4)
                    friendlyname_file.truncate()
            last_maintenance_time = current_time

            # Cache all our accurate peers every 10 minutes
            # This means that accurate peers will have more entries in the cache
            if packet.sniff_time.minute % 10 == 0:
                peers.cache_accurate_peers()
        if (packet.sniff_time - last_print_time).total_seconds() >= 1:
            
            if html_file != "":
                with open(html_file, 'w') as html:
                    headers = []
                    headers.append(("local ip address", local_ip))
                    headers.append(("last maintenance time", last_maintenance_time.time().strftime('%H:%M:%S')))
                    headers.append(("current time", current_time.time().strftime('%H:%M:%S')))
                    headers.append(("ping cache size", len(peers.ping_cache._storage)))
                    headers.append(("peers", len(peers)))
                    html.write(LibPeerFrom.Helpers.generate_html_view(headers, peers))     
            if peers_json_file != "":
                with open(peers_json_file, 'w') as j:
                    json_output = dict()
                    json_output["peers"] = peers.to_dict()
                    json_output["statistics"] = {
                                                "local_ip_address": local_ip,
                                                "last_maintenance_time": last_maintenance_time.time().strftime('%H:%M:%S'),
                                                "current_time": current_time.time().strftime('%H:%M:%S'),
                                                "ping_cache_size": len(peers.ping_cache._storage),
                                                "peers":len(peers)
                                                }

                    json.dump(json_output, j, indent=4)

            last_print_time = packet.sniff_time
            
        if show_tui:
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
            sys.stdout.flush()
    


if __name__ == "__main__": 
    main()