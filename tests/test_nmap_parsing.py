from portscout.infrastructure.nmap_adapter import NmapAdapter

SAMPLE_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="192.168.1.10" addrtype="ipv4"/>
    <hostnames><hostname name="router.local"/></hostnames>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="9.6"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="closed"/>
        <service name="https"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""


def test_parse_hosts_extracts_open_ports() -> None:
    hosts = NmapAdapter._parse_hosts(SAMPLE_XML)
    assert len(hosts) == 1
    host = hosts[0]
    assert host.address == "192.168.1.10"
    assert host.hostname == "router.local"
    assert host.state == "up"
    assert len(host.ports) == 2
    assert len(host.open_ports) == 1
    ssh = host.open_ports[0]
    assert ssh.number == 22
    assert ssh.service is not None
    assert ssh.service.describe() == "ssh (OpenSSH 9.6)"


def test_parse_empty_xml_returns_no_hosts() -> None:
    assert NmapAdapter._parse_hosts("") == ()
