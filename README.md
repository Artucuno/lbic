# Load Balanced Interactions.py Client (LBIC)
![Network Map](/assets/netmap.png)

A Load Balanced and Decentralised Interactions.py Client made for mission-critical tasks or tasks that require load balancing.

**Client is WORKING but is not intended for production use in its current state**

## Why use LBIC?
- Redundancy
- Load Balancing
- Decentralised
- Fault Tolerant
- Scalable

## Features
- Internal SocketIO Messaging Channels
- Load Balance based on Machine Resources
  - CPU, RAM, Storage, Network Up/Down
  - Discord Latency
  - ~~GPU Utilisation, GPU Temperature (Requires nvidia-smi)~~

## Things TODO
- Share paginators across all instances
- Add voice support
- "Sticky" sessions (Sessions that are bound to a specific node)
- Live Patching (+ Sync across all nodes)
- Auto Sharding (+ Auto-Scaling)
- Web Management Dashboard (LBIC Dashboard)
- Node Authentication
- Add Documentation

## Contribution
All contributions are welcome!