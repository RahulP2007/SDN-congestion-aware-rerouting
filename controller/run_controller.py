import sys
from os_ken.lib import hub
hub.patch(thread=False)

from os_ken import cfg, log
from os_ken.base.app_manager import AppManager
from os_ken.controller import controller

CONF = cfg.CONF
CONF.register_cli_opts([
    cfg.MultiStrOpt('app', positional=True, default=[],
                    help='application module name to run'),
])

def main():
    CONF(args=sys.argv[1:], project='os_ken', default_config_files=[])
    log.init_log()
    apps = list(CONF.app) or ['os_ken.controller.ofp_handler']
    mgr = AppManager.get_instance()
    mgr.load_apps(apps)
    contexts = mgr.create_contexts()
    services = []
    services.extend(mgr.instantiate_apps(**contexts))
    ctlr = controller.OpenFlowController()
    services.append(hub.spawn(ctlr))
    try:
        hub.joinall(services)
    except KeyboardInterrupt:
        pass
    finally:
        mgr.close()

if __name__ == '__main__':
    main()
