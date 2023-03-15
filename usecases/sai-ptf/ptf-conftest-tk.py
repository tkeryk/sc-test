import os
import sys
import pytest
import ptf.dataplane
from ptf import config
import random
import time
import signal
import logging
from saichallenger.common.sai_testbed import SaiTestbedMeta


# Map from strings to debugging levels
DEBUG_LEVELS = {
    "debug"              : logging.DEBUG,
    "verbose"            : logging.DEBUG,
    "info"               : logging.INFO,
    "warning"            : logging.WARNING,
    "warn"               : logging.WARNING,
    "error"              : logging.ERROR,
    "critical"           : logging.CRITICAL,
}

# The default configuration dictionary for PTF
config_default = {
    # Miscellaneous options
    "list"               : False,
    "list_test_names"    : False,
    "allow_user"         : False,
    
    # Test selection options
    "test_spec"          : "",
    "test_file"          : None,
    "test_dir"           : None,
    "test_order"         : "default",
    "test_order_seed"    : 0xABA,
    "num_shards"         : 1,
    "shard_id"           : 0,
    
    # Switch connection options
    "platform"           : "eth",
    "platform_args"      : None,
    "platform_dir"       : None,
    "interfaces"         : [],
    "port_info"          : {},
    "device_sockets"     : [],  # when using nanomsg
    
    # Logging options
    "log_file"           : "ptf.log",
    "log_dir"            : None,
    "debug"              : "verbose",
    "profile"            : False,
    "profile_file"       : "profile.out",
    "xunit"              : False,
    "xunit_dir"          : "xunit",
    
    # Test behavior options
    "relax"              : False,
    "test_params"        : None,
    "failfast"           : False,
    "fail_skipped"       : False,
    "default_timeout"    : 2.0,
    "default_negative_timeout": 0.1,
    "minsize"            : 0,
    "random_seed"        : None,
    "disable_ipv6"       : False,
    "disable_vxlan"      : False,
    "disable_erspan"     : False,
    "disable_geneve"     : False,
    "disable_mpls"       : False,
    "disable_nvgre"      : False,
    "disable_igmp"       : False,
    "disable_rocev2"     : False,
    "qlen"               : 100,
    "test_case_timeout"  : None,
    
    # Socket options
    "socket_recv_size": 4096,
    
    # Packet manipulation provider module
    "packet_manipulation_module": "ptf.packet_scapy",
    
    # Other configuration
    "port_map": None,
}

@pytest.fixture(scope="session", autouse=True)
def set_ptf_params(request):
    if request.config.option.testbed:
        tb_params = SaiTestbedMeta("/sai-challenger", request.config.option.testbed)
        ports = to_ptf_int_list(tb_params.config['dataplane'][0]['port_groups'])
    else:
        ports = ""
    
    # provide required PTF runner params to avoid exiting with an error

    # load PTF runner module to let it collect test params into ptf.config
    import imp
    print("PTF params: ", config)
    
    import ptf

    ptf.config.update(config_default)
    logging_setup(config)
    logging.info("++++++++ " + time.asctime() + " ++++++++")

    # import after logging is configured so that scapy error logs (from importing
    # packet.py) are silenced and our own warnings are logged properly.
    import ptf.testutils

    # Try parsing test params and log them
    # We do this before importing the test modules in case test parameters are being
    # accessed at test import time.

    # Initiallize port information
    ptf.testutils.PORT_INFO = config["port_info"]

    if config["platform_dir"] is None:
        from ptf import platforms

    config["platform_dir"] = os.path.dirname(os.path.abspath(platforms.__file__))

    # Allow platforms to import each other
    sys.path.append(config["platform_dir"])

    # Load the platform module
    platform_name = config["platform"]
    logging.info("Importing platform: " + platform_name)

    platform_mod = None
    try:
        platform_mod = imp.load_module(
            platform_name, *imp.find_module(platform_name, [config["platform_dir"]])
        )
    except:
        logging.warn("Failed to import " + platform_name + " platform module")
        raise

    try:
        platform_mod.platform_config_update(config)
    except:
        logging.warn("Could not run platform host configuration")
        raise

    if config["port_map"] is None:
        logging.critical("Interface port map was not defined by the platform. Exiting.")
        sys.exit(1)

    logging.debug("Configuration: " + str(config))
    logging.info("port map: " + str(config["port_map"]))

    ptf.ptfutils.default_timeout = config["default_timeout"]
    ptf.ptfutils.default_negative_timeout = config["default_negative_timeout"]
    ptf.testutils.MINSIZE = config["minsize"]

    if os.getuid() != 0 and not config["allow_user"]:
        logging.critical("Super-user privileges required. Please re-run with sudo or as root.")
        sys.exit(1)

    seed = config["random_seed"] if config["random_seed"] else random.randrange(100000000)
    logging.info("Random seed: %d" % seed)
    random.seed(seed)

    # Remove python's signal handler which raises KeyboardError. Exiting from an
    # exception waits for all threads to terminate which might not happen.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Set up the dataplane
    ptf.dataplane_instance = ptf.dataplane.DataPlane(config)
    if config["log_dir"] == None:
        filename = os.path.splitext(config["log_file"])[0] + ".pcap"
        ptf.dataplane_instance.start_pcap(filename)

    for port_id, ifname in config["port_map"].items():
        device, port = port_id
        ptf.dataplane_instance.port_add(ifname, device, port)

    yield

    ptf.dataplane_instance.stop_pcap()
    ptf.dataplane_instance.kill()
    ptf.dataplane_instance = None


def pytest_addoption(parser):
    parser.addoption("--testbed", action="store", default=None, help="Testbed name")
    
def to_ptf_int_list(port_map):
    ports = [f"{m['alias']}@{m['name']}" for m in port_map]
    return " ".join([f"--interface {port}" for port in ports]).split(" ")

def logging_setup(config):
    """
    Set up logging based on config
    """

    logging.getLogger().setLevel(DEBUG_LEVELS[config["debug"]])

    if config["log_dir"] != None:
        if os.path.exists(config["log_dir"]):
            import shutil

            shutil.rmtree(config["log_dir"])
        os.makedirs(config["log_dir"])
    else:
        if os.path.exists(config["log_file"]):
            os.remove(config["log_file"])

    ptf.open_logfile("main")
