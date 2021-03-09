This repository is an extention layer above the automation-infra project:
https://github.com/AnyVisionoftltd/automation-infra

While automation-infra provides ssh connectivity, this extends a layer on top of that - via a docker or kubernetes container deployed on the remote machine. 

The remote container server 2 main purposes:
+ To have an ubuntu machine running which you can run commands on, so even if the remote is a centOS server, we can still run ubuntu commands on it.
+ To tunnel communication to various services running on the remote.

The proxy container facilitates this by:
+ exposing an ssh connection (on port 2222)
+ being an ubuntu machine with useful binaries installed
+ sitting in the remote host network so has resolve to any dnss the host has resolve to. 

In addition, in this repo there are various application plugins, which tunnel their communication through the proxy container, and enable interaction with applications running on the remote host, including:
+ consul
+ memsql
+ postgres
+ mongodb
+ seaweed
+ docker 