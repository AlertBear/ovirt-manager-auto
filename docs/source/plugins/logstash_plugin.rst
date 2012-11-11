
----------------
Log Stash Plugin
----------------

Plugin adds hyperlinks pointed to logs collected from engine and vdsm
by logstash tool: http://logstash.net/

Configuration Options:
----------------------
    [LOGSTASH]
    enabled - to enable the plugin (true/false)
    site - link to logstash web page
    [[vdc]] - sub-section to specify log names-paths pairs from vdc server,
        default: engine = /var/log/jbossas/standalone/engine/engine.log

    [[vds]] - sub-section to specify log names-paths pairs from vds server,
        default: vdsm = /var/log/vdsm/vdsm.log
