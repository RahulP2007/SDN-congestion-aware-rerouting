#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel


def build():
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink,
                  autoSetMacs=True)
    net.addController('c0', controller=RemoteController,
                      ip='127.0.0.1', port=6653)

    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')

    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    s3 = net.addSwitch('s3', protocols='OpenFlow13')
    s4 = net.addSwitch('s4', protocols='OpenFlow13')

    # hosts (fast links)
    net.addLink(h1, s1, port2=1, bw=100)
    net.addLink(h3, s1, port2=2, bw=100)
    net.addLink(h2, s4, port2=3, bw=100)
    # path A: s1 - s2 - s4  (10 Mbps)
    net.addLink(s1, s2, port1=3, port2=1, bw=10, max_queue_size=50)
    net.addLink(s2, s4, port1=2, port2=1, bw=10, max_queue_size=50)
    # path B: s1 - s3 - s4  (10 Mbps)
    net.addLink(s1, s3, port1=4, port2=1, bw=10, max_queue_size=50)
    net.addLink(s3, s4, port1=2, port2=2, bw=10, max_queue_size=50)
    return net


if __name__ == '__main__':
    setLogLevel('info')
    net = build()
    net.start()
    net.staticArp()
    CLI(net)
    net.stop()
