from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3

H1, H2, H3 = '10.0.0.1', '10.0.0.2', '10.0.0.3'

# output port for each destination IP, per switch id.
# Everything is forced over path A (s1 - s2 - s4). s3 gets no rules.
ROUTES = {
    1: {H2: 3, H1: 1, H3: 2},
    2: {H2: 2, H1: 1, H3: 1},
    4: {H2: 3, H1: 1, H3: 1},
}


class StaticRouting(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        dp = ev.msg.datapath
        parser = dp.ofproto_parser
        for ip, port in ROUTES.get(dp.id, {}).items():
            match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=ip)
            actions = [parser.OFPActionOutput(port)]
            self.add_flow(dp, 10, match, actions)
            self.logger.info("s%s: to %s -> port %s", dp.id, ip, port)

    def add_flow(self, dp, priority, match, actions):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS,
                                             actions)]
        dp.send_msg(parser.OFPFlowMod(datapath=dp, priority=priority,
                                      match=match, instructions=inst))
