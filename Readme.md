# WhereDoThePeersComeFrom

This is a tool to monitor/estimate latency to various people in an Elden Ring game session. It is pretty hacky, I have made it purely for my own use. It also works for Dark Souls 3.

<b><u>Currently it has only been tested against PS5.</b></u>

### Why I made this

I was having consistently bad connections at specific times of day (approximately 18:30-22:30, every day). I assumed that I was suddenly hitting players from a different region, and that was the cause of poor connections and opponents suddenly loving the Miyazaki shuffle. Eventually, I found that the same opponent would have a good connection prior to "The Witching Hour", and an awful one during. Because From Software games use peer to peer multiplayer, we can get the IP address (and therefore very approximate location) of other players in the session. Based on their IP address, sometimes we can ping them. Other times we can use the pings of other players we've seen in similar locations and use that to estimate pings.

I also decided to display an estimate of outgoing packet loss - this isn't a real estimate of packet loss, it's just the number of times an identical packet has been re-sent<sup>1<sup>. In Elden Ring, "normal" packet loss is sub-15%. In Dark Souls 3, it is sub-10%. I didn't find a strong link between the reported packet loss and connection quality until the packet loss is significantly higher than those values (over the course of a multiplayer session). 

## Usage

This assumes the ability to capture network traffic from a PS5. One way to do this is to have a suitable upstream router (for example, an [Edgerouter X](https://store.ui.com/products/edgerouter-x)). You will need a router that you can remotely capture wireshark-compatible traces and send them to stdout.

### Setup

Requires python 3. To install required libraries:

`pip install -r requirements.txt`

### Example

Assuming your router is located at 10.0.0.1 and your PS5 is located at 10.0.0.50:

`ssh 10.0.0.1 '/usr/sbin/tcpdump host 10.0.0.50 -U -w - ' | ./WhereDoThePeersComeFrom.py --address=10.0.0.50`

Alternatively,

`./WhereDoThePeersComeFrom.py --address=10.0.0.50 --router_address=10.0.0.1`

If you wish to see more verbose output, use the --debug flag as below:

`ssh 10.0.0.1 '/usr/sbin/tcpdump host 10.0.0.50 -U -w - ' | ./WhereDoThePeersComeFrom.py --address=10.0.0.50 --debug`

Alternatively,

`./WhereDoThePeersComeFrom.py --address=10.0.0.50 --router_address=10.0.0.1 --debug`

Peers will be printed in descending order by default, based on the time of their last packet. The order is only updated when a peer is added/removed from the list.

For full usage info, run `./WhereDoThePeersComeFrom.py -h`.

### Example output

```
local ip address:       10.0.0.50
peer(s):                1

123.456.789.012: 60ms (guess). 8.95% loss. last 09:58:44.200572. (Western Australia, AU)
```

With --debug on:

```
local ip address:       10.0.0.50
last maintenance time:  09:58:38
current time:           09:58:43
scan delay:             0:00:00.356386
ping cache location:    
ping cache size:        0
peer(s):                1

123.456.789.012: 60ms (guess). 8.95% loss. last 09:58:44.200572. (Western Australia, AU)
```

## How it works

Players in From Software multiplayer sessions communicate directly to one another over UDP. Sessions start with a "handshake" where the host sends a 94-byte packet to the guest<sup>2</sup>, and the guest responds with a 94-byte packet. I have not yet made an attempt to decode the UDP stream.

This script looks at all captured traffic, and when a session start is detected that peer is added to a list. Once the start "handshake" has occurred, we estimate the latency to that peer. This is not necessarily accurate, but can form a best-guess estimate. Once a peer is in your session, we can ping them to get a better estimate for latency. This may not work for all peers, as ICMP may be disabled somewhere along the route between you and your peer.

The script also uses a geoip lookup database to estimate the country and region your peer is in - this can be useful when judging if a "guess" ping is accurate. For example, a player in Australia is unlikely to have a latency of less than 150ms to a player in North America.

If a peer has not been seen for 30 seconds<sup>3</sup> (that is, no UDP packets are sent or received) then that peer is removed from the list.

Finally, outgoing packet loss is estimated by counting the number of times identical UDP packet data is sent. This may not be a good estimate, as I currently do not know what is being sent. In testing, "loss" between 5% and 12% appeared to be fine. Peers that visibly skipped around seemed to have "loss" higher than 15%. As UDP does not guarantee reliable transmission, it is not possible to estimate the incoming packet loss.

## Additional Features

### Ping Cache

This program can also store pings on disk. These pings are stored for a Country, Region and City (as per their GeoIP lookup). This cache can then be used to estimate other peers from similar locations.

For example, if you know that a given host (from Melbourne, Victoria, AU) has a latency of 50ms to you, then other hosts from Melbourne may also have a similar latency. The same is true for other hosts from Victoria or Australia. 

This feature caches all pings, whether they're accurate (ie we have an ICMP response) or a guess (based on packet timings). Accurate pings are cached more often than guesses.

### Minimum Ping

Because guess pings are still cached, sometimes estimates will be too low. You can define a "minimum_ping.json" file, containing countries (in 2-letter country code form) and minimum pings for that country. If you never see pings better than, say, 300ms to Brazil then defining the following will be appropriate (in minimum_ping.json):

```
{
    "BR":300
}
```

## Footnotes

<sup>1</sup> This will include "heartbeats", which Elden Ring seems to send more of than Dark Souls 3.
<sup>2</sup> The reality is a little more complex, but this is bird's eye view.  
<sup>3</sup> We actually run a maintenance job every 30 seconds, and in this we remove peers inactive for more than 30 seconds. Stale peers can therefore be held in the list for up 60 seconds.