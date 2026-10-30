import os
import time

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from os_ken.controller.handler import DEAD_DISPATCHER, set_ev_cls
from os_ken.lib import hub
from os_ken.ofproto import ofproto_v1_3

H1, H2, H3 = '10.0.0.1', '10.0.0.2', '10.0.0.3'
PORT_A, PORT_B = 3, 4            # s1 ports towards s2 (path A) and s3 (path B)
LINK_MBPS = 10.0
THRESH = 0.85 * LINK_MBPS        # congested at or above this rate
ALT_MAX = 0.5 * THRESH           # the other path must be below this
POLL = 1.0                       # seconds between statistics requests
HOT_NEEDED = 2                   # consecutive congested readings required
EVENTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'results', 'events.log')

# default routes: everything starts on path A (s1 - s2 - s4).
# s3 gets rules too, so path B is ready when we need it.
ROUTES = {
    1: {H2: PORT_A, H1: 1, H3: 2},
    2: {H2: 2, H1: 1, H3: 1},
    3: {H2: 2, H1: 1, H3: 1},
    4: {H2: 3, H1: 1, H3: 1},
}


class AdaptiveRouting(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dps = {}
        self.reset_state()
        self.monitor = hub.spawn(self._monitor)

    def reset_state(self):
        self.prev = {}
        self.main_port = PORT_A
        self.hot = 0

    def log_event(self, text):
        line = '%.3f %s' % (time.time(), text)
        self.logger.info(line)
        try:
            with open(EVENTS, 'a') as f:
                f.write(line + '\n')
        except OSError:
            pass

    def add_flow(self, dp, priority, match, actions):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS,
                                             actions)]
        dp.send_msg(parser.OFPFlowMod(datapath=dp, priority=priority,
                                      match=match, instructions=inst))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        dp = ev.msg.datapath
        parser = dp.ofproto_parser
        for ip, port in ROUTES.get(dp.id, {}).items():
            match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=ip)
            self.add_flow(dp, 10, match, [parser.OFPActionOutput(port)])
        if dp.id == 1:
            self.reset_state()
            match = parser.OFPMatch(eth_type=0x0800,
                                    ipv4_src=H1, ipv4_dst=H2)
            self.add_flow(dp, 20, match, [parser.OFPActionOutput(PORT_A)])
            self.log_event('S1_READY main flow on path A')

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.dps[dp.id] = dp
        else:
            self.dps.pop(dp.id, None)

    def _monitor(self):
        while True:
            dp = self.dps.get(1)
            if dp:
                parser = dp.ofproto_parser
                dp.send_msg(parser.OFPPortStatsRequest(
                    dp, 0, dp.ofproto.OFPP_ANY))
            hub.sleep(POLL)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def stats_reply_handler(self, ev):
        dp = ev.msg.datapath
        if dp.id != 1:
            return
        now = time.time()
        rates = {}
        for st in ev.msg.body:
            if st.port_no in (PORT_A, PORT_B):
                old = self.prev.get(st.port_no)
                self.prev[st.port_no] = (now, st.tx_bytes)
                if old and now > old[0]:
                    rates[st.port_no] = ((st.tx_bytes - old[1]) * 8
                                         / (now - old[0]) / 1e6)
        if len(rates) < 2:
            return
        cur = self.main_port
        alt = PORT_B if cur == PORT_A else PORT_A
        self.logger.info("A=%.2f Mbps  B=%.2f Mbps  main flow on %s",
                         rates[PORT_A], rates[PORT_B],
                         'A' if cur == PORT_A else 'B')
        if rates[cur] >= THRESH:
            self.hot += 1
        else:
            self.hot = 0
        if self.hot == HOT_NEEDED:
            self.log_event('CONGESTION_DETECTED path %s at %.2f Mbps' %
                           ('A' if cur == PORT_A else 'B', rates[cur]))
        if (self.hot >= HOT_NEEDED and rates[alt] < ALT_MAX
                and self.mode() != 'static'):
            self.reroute(dp, alt)

    def mode(self):
        try:
            return open(os.path.join(os.path.dirname(EVENTS), 'mode')).read().strip()
        except OSError:
            return 'adaptive'

    def reroute(self, dp, new_port):
        parser = dp.ofproto_parser
        match = parser.OFPMatch(eth_type=0x0800, ipv4_src=H1, ipv4_dst=H2)
        self.add_flow(dp, 20, match, [parser.OFPActionOutput(new_port)])
        self.main_port = new_port
        self.hot = 0
        self.log_event('REROUTED main flow to path %s' %
                       ('A' if new_port == PORT_A else 'B'))
