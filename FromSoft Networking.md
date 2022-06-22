# How From Software Networking Works

This is an overview of how FromSoft networking works. It's been gathered from about five years of pvp, and a bit of network trace analysis. It mainly pertains to Dark Souls 3 (DS3) and Elden Ring (ER), though I expect that the broad strokes also apply to Dark Souls 2, Dark Souls and Demon's Souls.

## Some Background

Just a few definitions to help us get on our way.

### Sessions

In general, a session is when two computers are talking to each other for a period of time. Sessions have a well-defined beginning and end. In this post, I'll be referring to "multiplayer sessions" as "sessions". A multiplayer session begins when a guest (phantom) enters a host's world. It ends when the phantom is sent home, or when the phantom or host dies. 

### Peer to Peer Multiplayer

Peer to peer multiplayer games have two players communicate directly with each other. In this model, if a red hits the host the red's game will send the host's game a message saying "I hit you". This contrasts with multiplayer games with dedicated or central servers, where if a red hits the host, the red tells the central server "I hit the host". The central server then tells the host's game "the red hit you".

While dedicated servers provide a more consistent experience, this sort of architecture is much more expensive to run. Peer to peer multiplayer can therefore be kept alive for longer periods of time for a lower cost. 

Fromsoftware games use peer to peer multiplayer. 

## Starting a session

### Phantoms - Using an Invasion Item


### Phantoms - Putting a Summon Sign down

Putting a sign down sends a message from your game to the central matchmaking server. This message includes your character name, Steam/PSN/Xbox ID and relevant matchmaking info (password, character level, covenant, weapon upgrade level).  Hosts with a suitable session will then be able to see your sign. 

When a host hits your sign, they will first communicate with the matchmaking server to get your connection info (IP address, port). Once they have done that they will connect to you.



### Hosts

A host starts a session by using a relevant in-game item (Ember in DS3, Furlcalling Finger Remedy in ER). In DS3, this makes them available for invasions. In both, the host can now see summon signs on the ground.

### Hosts - Summoning from a Sign

# TODO: mention "unable to summon"

When summoning from a sign, the host's game contacts the matchmaking server to get the details of the guest's game. If the guest is able to be summoned (i.e. they are not already in a session, their game is still open, they did not move areas to a place that their summon sign disappears) then the host then makes a connection to the guest's game.


### Hosts - Summoning from Invasion

## Peer to Peer

## Platform Blocking