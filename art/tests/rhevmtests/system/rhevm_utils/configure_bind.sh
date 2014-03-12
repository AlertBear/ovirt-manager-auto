MACHINE_NAME=vdc
DOMAIN_NAME=rhevm.utilities.com
LOCAL_DNS_SERVER=10.34.63.229

NAMED_CONF=/etc/named.conf
NAMED_ROOT_DIR=/var/named
RHEVM_ZONE_FILE_NAME=rhevm.zone
RHEVM_ZONE_FILE=$NAMED_ROOT_DIR/$RHEVM_ZONE_FILE_NAME


[ -z `rpm -qa bind` ] && echo 'missing bind package' && exit 1


# FIXME: hardcoded eth0
echo "prepend domain-name-servers 127.0.0.1;" >> /etc/dhcp/dhclient-eth0.conf

cat << __EOF__ > $NAMED_CONF
options {
    listen-on port 53 { 127.0.0.1; };
    listen-on-v6 port 53 { ::1; };
    directory   "$NAMED_ROOT_DIR";
    dump-file   "$NAMED_ROOT_DIR/data/cache_dump.db";
    allow-query     { localhost; };
    recursion yes;
    forwarders { $LOCAL_DNS_SERVER; };

};

logging {
        channel default_debug {
                file "data/named.run";
                severity dynamic;
        };
};

zone "." IN {
    type hint;
    file "named.ca";
};

include "/etc/named.rfc1912.zones";

zone "$DOMAIN_NAME" IN {
    type master;
    file "rhevm.zone";
};

zone "in-addr.arpa" IN {
    type master;
    file "$RHEVM_ZONE_FILE_NAME";
};
__EOF__

# FIXME: problem with regex below ('inet 10'), it is bind to private network
IP=`ip a | grep -o 'inet 10[^/]*' | head -n1 | cut -d' ' -f2`
PTR=`echo $IP | sed 's|\([0-9]*\)[.]\([0-9]*\)[.]\([0-9]*\)[.]\([0-9]*\)|\4.\3.\2.\1|'`

cat << __EOF__ > $RHEVM_ZONE_FILE
\$TTL 1D
@   IN SOA  @ $DOMAIN_NAME. (
                    0   ; serial
                    1D  ; refresh
                    1H  ; retry
                    1W  ; expire
                    3H )    ; minimum
    NS  @
    A   127.0.0.1
    AAAA    ::1
$MACHINE_NAME   A   $IP
$PTR.in-addr.arpa.  PTR $MACHINE_NAME.$DOMAIN_NAME.
__EOF__

sed -i "s/HOSTNAME.*/HOSTNAME=$MACHINE_NAME.$DOMAIN_NAME/" /etc/sysconfig/network

chown root:named $RHEVM_ZONE_FILE
restorecon -RvvF $RHEVM_ZONE_FILE

chkconfig named on
service named restart
