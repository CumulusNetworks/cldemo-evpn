#!/usr/bin/env python

#
#    Topology Converter
#       converts a given topology.dot file to a Vagrantfile
#           can use the virtualbox or libvirt Vagrant providers
# Initially written by Eric Pulvino 2015-10-19
#
#  hosted @ https://github.com/cumulusnetworks/topology_converter
#
#
version = "4.6.1_dev"


import os
import re
import sys
import time
import pprint
import jinja2
import argparse
import importlib
import pydotplus
from operator import itemgetter

pp = pprint.PrettyPrinter(depth=6)

class styles:
    # Use these for text colors
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'

parser = argparse.ArgumentParser(description='Topology Converter -- Convert topology.dot files into Vagrantfiles')
parser.add_argument('topology_file',
                   help='provide a topology file as input')
parser.add_argument('-v','--verbose', action='store_true',
                   help='enables verbose logging mode')
parser.add_argument('-p','--provider', choices=["libvirt","virtualbox"],
                   help='specifies the provider to be used in the Vagrantfile, script supports "virtualbox" or "libvirt", default is virtualbox.')
parser.add_argument('-a','--ansible-hostfile', action='store_true',
                   help='When specified, ansible hostfile will be generated from a dummy playbook run.')
parser.add_argument('-c','--create-mgmt-network', action='store_true',
                   help='When specified, a mgmt switch and server will be created. A /24 is assumed for the mgmt network. mgmt_ip=X.X.X.X will be read from each device to create a Static DHCP mapping for the oob-mgmt-server.')
parser.add_argument('-cco','--create-mgmt-configs-only', action='store_true',
                   help='Calling this option does NOT regenerate the Vagrantfile but it DOES regenerate the configuration files that come packaged with the mgmt-server in the "-c" option. This option is typically used after the "-c" has been called to generate a Vagrantfile with an oob-mgmt-server and oob-mgmt-switch to modify the configuraiton files placed on the oob-mgmt-server device. Useful when you do not want to regenerate the vagrantfile but you do want to make changes to the OOB-mgmt-server configuration templates.')
parser.add_argument('-cmd','--create-mgmt-device', action='store_true',
                   help='Calling this option creates the mgmt device and runs the auto_mgmt_network template engine to load configurations on to the mgmt device but it does not create the OOB-MGMT-SWITCH or associated connections. Useful when you are manually specifying the construction of the management network but still want to have the OOB-mgmt-server created automatically.')
parser.add_argument('-t','--template', action='append', nargs=2,
                   help='Specify an additional jinja2 template and a destination for that file to be rendered to.')
parser.add_argument('-s','--start-port', type=int,
                   help='FOR LIBVIRT PROVIDER: this option overrides the default starting-port 8000 with a new value. Use ports over 1024 to avoid permissions issues. If using this option with the virtualbox provider it will be ignored.')
parser.add_argument('-g','--port-gap', type=int,
                   help='FOR LIBVIRT PROVIDER: this option overrides the default port-gap of 1000 with a new value. This number is added to the start-port value to determine the port to be used by the remote-side. Port-gap also defines the max number of links that can exist in the topology. EX. If start-port is 8000 and port-gap is 1000 the first link will use ports 8001 and 9001 for the construction of the UDP tunnel. If using this option with the virtualbox provider it will be ignored.')
parser.add_argument('-dd','--display-datastructures', action='store_true',
                   help='When specified, the datastructures which are passed to the template are displayed to screen. Note: Using this option does not write a Vagrantfile and supercedes other options.')
parser.add_argument('--synced-folder', action='store_true',
                   help='Using this option enables the default Vagrant synced folder which we disable by default. See: https://www.vagrantup.com/docs/synced-folders/basic_usage.html')
parser.add_argument('--version', action='version', version="Topology Converter version is v%s" % version,
                   help='Using this option displays the version of Topology Converter')
args = parser.parse_args()

#Parse Arguments
network_functions=['oob-switch','internet','exit','superspine','spine','leaf','tor']
function_group={}
provider="virtualbox"
generate_ansible_hostfile=False
create_mgmt_device=False
create_mgmt_network=False
create_mgmt_configs_only=False
verbose=False
start_port=8000
port_gap=1000
synced_folder=False
display_datastructures=False
VAGRANTFILE='Vagrantfile'
VAGRANTFILE_template='templates/Vagrantfile.j2'
customer = os.path.basename(os.path.dirname(os.getcwd()))
TEMPLATES=[[VAGRANTFILE_template,VAGRANTFILE]]
arg_string=" ".join(sys.argv)
if args.topology_file: topology_file=args.topology_file
if args.verbose: verbose=args.verbose
if args.provider: provider=args.provider
if args.ansible_hostfile: generate_ansible_hostfile=True
if args.create_mgmt_device:
    create_mgmt_device=True
if args.create_mgmt_network:
    create_mgmt_device=True
    create_mgmt_network=True
if args.create_mgmt_configs_only:
    create_mgmt_configs_only=True

if args.template:
    for templatefile,destination in args.template:
        TEMPLATES.append([templatefile,destination])
for templatefile,destination in TEMPLATES:
    if not os.path.isfile(templatefile):
        print styles.FAIL + styles.BOLD + " ### ERROR: provided template file-- \"" + templatefile + "\" does not exist!" + styles.ENDC
        exit(1)
if args.start_port: start_port=args.start_port
if args.port_gap: port_gap=args.port_gap
if args.display_datastructures: display_datastructures=True
if args.synced_folder: synced_folder=True

if verbose:
    print "Arguments:"
    print args

###################################
#### MAC Address Configuration ####
###################################

# The starting MAC for assignment for any devices not in mac_map
#Cumulus Range ( https://support.cumulusnetworks.com/hc/en-us/articles/203837076-Reserved-MAC-Address-Range-for-Use-with-Cumulus-Linux )
start_mac="443839000000"
#This file is generated to store the mapping between macs and mgmt interfaces
dhcp_mac_file="./dhcp_mac_map"

######################################################
#############    Everything Else     #################
######################################################

#Hardcoded Variables
script_storage="./helper_scripts"
epoch_time = str(int(time.time()))
mac_map={}

#Static Variables -- #Do not change!
warning=[]
libvirt_reuse_error="""
       When constructing a VAGRANTFILE for the libvirt provider
       interface reuse is not possible because the UDP tunnels
       which libvirt uses for communication are point-to-point in
       nature. It is not possible to create a point-to-multipoint
       UDP tunnel!

       NOTE: Perhaps adding another switch to your topology would
       allow you to avoid reusing interfaces here.
"""

###### Functions
def mac_fetch(hostname,interface):
    global start_mac
    global mac_map
    global warning
    global verbose
    new_mac = ("%x" % (int(start_mac, 16)+1)).upper()
    while new_mac in mac_map:
        warning.append(styles.WARNING + styles.BOLD + "    WARNING: MF MAC Address Collision -- tried to use " + new_mac + " (on "+interface+") but it was already in use." + styles.ENDC)
        start_mac = new_mac
        new_mac = ("%x" % (int(start_mac, 16)+1)).upper()
    start_mac = new_mac
    if verbose: print "    Fetched new MAC ADDRESS: \"%s\"" % new_mac
    return add_mac_colon(new_mac)

def add_mac_colon(mac_address):
    global verbose
    if verbose: print "MAC ADDRESS IS: \"%s\"" % mac_address
    return str(':'.join(s.encode('hex') for s in mac_address.decode('hex')))

def lint_topo_file(topology_file):
    with open(topology_file,"r") as topo_file:
        line_list=topo_file.readlines()
        count=0
        for line in line_list:
            count +=1
            #Try to encode into ascii
            try:
                line.encode('ascii','ignore')
            except UnicodeDecodeError as e:
                print styles.FAIL + styles.BOLD + " ### ERROR: Line %s:\n %s\n         --> \"%s\" \n     Has hidden unicode characters in it which prevent it from being converted to ASCII cleanly. Try manually typing it instead of copying and pasting." % (count,line,line.decode('utf-8').encode('ascii','replace')) + styles.ENDC
                exit(1)

            if line.count("\"")%2 == 1:
                print styles.FAIL + styles.BOLD + " ### ERROR: Line %s: Has an odd number of quotation characters (\").\n     %s\n"%(count,line) + styles.ENDC
                exit(1)
            if line.count("'")%2 == 1:
                print styles.FAIL + styles.BOLD + " ### ERROR: Line %s: Has an odd number of quotation characters (').\n     %s\n"%(count,line) + styles.ENDC
                exit(1)
            if line.count(":") == 2:
                if " -- " not in line:
                    print styles.FAIL + styles.BOLD + " ### ERROR: Line %s: Does not contain the following sequence \" -- \" to seperate the different ends of the link.\n     %s\n"%(count,line) + styles.ENDC
                    exit(1)

def parse_topology(topology_file):
    global provider
    global verbose
    global warning
    lint_topo_file(topology_file)
    try:
        topology = pydotplus.graphviz.graph_from_dot_file(topology_file)
    except Exception as e:
        print styles.FAIL + styles.BOLD + " ### ERROR: Cannot parse the provided topology.dot file (%s)\n     There is probably a syntax error of some kind, common causes include failing to close quotation marks and hidden characters from copy/pasting device names into the topology file." % (topology_file) + styles.ENDC
        exit(1)

    inventory = {}
    try:
        nodes=topology.get_node_list()
    except Exception as e:
        print e
        print styles.FAIL + styles.BOLD + " ### ERROR: There is a syntax error in your topology file (%s). Read the error output above for any clues as to the source." %(topology_file) + styles.ENDC
        exit(1)
    try:
        edges=topology.get_edge_list()
    except Exception as e:
        print e
        print styles.FAIL + styles.BOLD + " ### ERROR: There is a syntax error in your topology file (%s). Read the error output above for any clues as to the source." %(topology_file) + styles.ENDC
        exit(1)

    #Add Nodes to inventory
    for node in nodes:
        node_name=node.get_name().replace('"','')
        if node_name.startswith(".") or node_name.startswith("-"):
            print styles.FAIL + styles.BOLD + " ### ERROR: Node name cannot start with a hyphen or period. '%s' is not valid!\n"%(node_name) + styles.ENDC
            exit(1)
        reg=re.compile('^[A-Za-z0-9\.-]+$')
        if not reg.match(node_name):
            print styles.FAIL + styles.BOLD + " ### ERROR: Node name for the VM should only contain letters, numbers, hyphens or dots. It cannot start with a hyphen or dot.  '%s' is not valid!\n"%(node_name) + styles.ENDC
            exit(1)

        #Try to encode into ascii
        try:
            node_name.encode('ascii','ignore')
        except UnicodeDecodeError as e:
            print styles.FAIL + styles.BOLD + " ### ERROR: Node name \"%s\" --> \"%s\" has hidden unicode characters in it which prevent it from being converted to Ascii cleanly. Try manually typing it instead of copying and pasting." % (node_name,node_name.decode('utf-8').encode('ascii','replace')) + styles.ENDC
            exit(1)

        if node_name not in inventory:
            inventory[node_name] = {}
            inventory[node_name]['interfaces'] = {}
        node_attr_list=node.get_attributes()

        #Define Functional Defaults
        if 'function' in node_attr_list:
            value=node.get('function')
            if value.startswith('"') or value.startswith("'"): value=value[1:].lower()
            if value.endswith('"') or value.endswith("'"): value=value[:-1].lower()

            if value=='fake':
                inventory[node_name]['os']="None"
                inventory[node_name]['memory']="1"
            if value=='oob-server':
                inventory[node_name]['os']="yk0/ubuntu-xenial"
                inventory[node_name]['memory']="512"
            if value=='oob-switch':
                inventory[node_name]['os']="CumulusCommunity/cumulus-vx"
                inventory[node_name]['memory']="512"
                inventory[node_name]['config'] = "./helper_scripts/oob_switch_config.sh"
            elif value in network_functions:
                inventory[node_name]['os']="CumulusCommunity/cumulus-vx"
                inventory[node_name]['memory']="512"
                inventory[node_name]['config'] = "./helper_scripts/extra_switch_config.sh"
            elif value=='host':
                inventory[node_name]['os']="yk0/ubuntu-xenial"
                inventory[node_name]['memory']="512"
                inventory[node_name]['config'] = "./helper_scripts/extra_server_config.sh"

        if provider == 'libvirt' and 'pxehost' in node_attr_list:
            if node.get('pxehost').replace('"','') == "True": inventory[node_name]['os']="N/A (PXEBOOT)"

        #Add attributes to node inventory
        for attribute in node_attr_list:
            if verbose: print attribute + " = " + node.get(attribute)
            value=node.get(attribute)
            if value.startswith('"') or value.startswith("'"): value=value[1:]
            if value.endswith('"') or value.endswith("'"): value=value[:-1]
            inventory[node_name][attribute] = value

        if provider == 'libvirt':
            if 'os' in inventory[node_name]:
                if inventory[node_name]['os'] =='boxcutter/ubuntu1604' or inventory[node_name]['os'] =='bento/ubuntu-16.04' or inventory[node_name]['os'] =='ubuntu/xenial64':
                    print styles.FAIL + styles.BOLD + " ### ERROR: device " + node_name + " -- Incompatible OS for libvirt provider."
                    print "              Do not attempt to use a mutated image for Ubuntu16.04 on Libvirt"
                    print "              use an ubuntu1604 image which is natively built for libvirt"
                    print "              like yk0/ubuntu-xenial."
                    print "              See https://github.com/CumulusNetworks/topology_converter/tree/master/documentation#vagrant-box-selection"
                    print "              See https://github.com/vagrant-libvirt/vagrant-libvirt/issues/607"
                    print "              See https://github.com/vagrant-libvirt/vagrant-libvirt/issues/609" + styles.ENDC
                    exit(1)

        #Make sure mandatory attributes are present.
        mandatory_attributes=['os',]
        for attribute in mandatory_attributes:
            if attribute not in inventory[node_name]:
                print styles.FAIL + styles.BOLD + " ### ERROR: MANDATORY DEVICE ATTRIBUTE \""+attribute+"\" not specified for "+ node_name + styles.ENDC
                exit(1)

        #Extra Massaging for specific attributes.
        #   light sanity checking.
        if 'function' not in inventory[node_name]: inventory[node_name]['function'] = "Unknown"
        if 'memory' in inventory[node_name]:
            if int(inventory[node_name]['memory']) <= 0:
                print styles.FAIL + styles.BOLD + " ### ERROR -- Memory must be greater than 0mb on " + node_name + styles.ENDC
                exit(1)
        if provider == "libvirt":
            if 'tunnel_ip' not in inventory[node_name]: inventory[node_name]['tunnel_ip']='127.0.0.1'


    #Add All the Edges to Inventory
    net_number = 1
    for edge in edges:
        #if provider=="virtualbox":
        network_string="net"+str(net_number)

        #elifprovider=="libvirt":
        PortA=str(start_port+net_number)
        PortB=str(start_port+port_gap+net_number)


        #Set Devices/interfaces/MAC Addresses
        left_device=edge.get_source().split(":")[0].replace('"','')
        left_interface=edge.get_source().split(":")[1].replace('"','')
        right_device=edge.get_destination().split(":")[0].replace('"','')
        right_interface=edge.get_destination().split(":")[1].replace('"','')

        for value in [left_device,left_interface,right_device,right_interface]:
            #Try to encode into ascii
            try:
                value.encode('ascii','ignore')
            except UnicodeDecodeError as e:
                print styles.FAIL + styles.BOLD + " ### ERROR: in line --> \"%s\":\"%s\" -- \"%s\":\"%s\"\n        Link component: \"%s\" has hidden unicode characters in it which prevent it from being converted to Ascii cleanly. Try manually typing it instead of copying and pasting." % (left_device,left_interface,right_device,right_interface,value.decode('utf-8').encode('ascii','replace')) + styles.ENDC
                exit(1)


        left_mac_address=""
        if edge.get('left_mac') != None :
            temp_left_mac=edge.get('left_mac').replace('"','').replace(':','')
            left_mac_address=add_mac_colon(temp_left_mac)
        else: left_mac_address=mac_fetch(left_device,left_interface)
        right_mac_address=""
        if edge.get('right_mac') != None :
            temp_right_mac=edge.get('right_mac').replace('"','').replace(':','')
            right_mac_address=add_mac_colon(temp_right_mac)
        else: right_mac_address=mac_fetch(right_device,right_interface)

        #Check to make sure each device in the edge already exists in inventory
        if left_device not in inventory:
            print styles.FAIL + styles.BOLD + " ### ERROR: device " + left_device + " is referred to in list of edges/links but not defined as a node." + styles.ENDC
            exit(1)
        if right_device not in inventory:
            print styles.FAIL + styles.BOLD + " ### ERROR: device " + right_device + " is referred to in list of edges/links but not defined as a node." + styles.ENDC
            exit(1)

        #Adds link to inventory datastructure
        add_link(inventory,
                 left_device,
                 right_device,
                 left_interface,
                 right_interface,
                 left_mac_address,
                 right_mac_address,
                 net_number,)

        #Handle Link-based Passthrough Attributes
        edge_attributes={}
        for attribute in edge.get_attributes():
            if attribute=="left_mac" or attribute=="right_mac": continue
            if attribute in edge_attributes:
                warning.append(styles.WARNING + styles.BOLD + "    WARNING: Attribute \""+attribute+"\" specified twice. Using second value." + styles.ENDC)
            value=edge.get(attribute)
            if value.startswith('"') or value.startswith("'"): value=value[1:]
            if value.endswith('"') or value.endswith("'"): value=value[:-1]
            if attribute.startswith('left_'):
                inventory[left_device]['interfaces'][left_interface][attribute[5:]]=value
            elif attribute.startswith('right_'):
                inventory[right_device]['interfaces'][right_interface][attribute[6:]]=value
            else:
                inventory[left_device]['interfaces'][left_interface][attribute]=value
                inventory[right_device]['interfaces'][right_interface][attribute]=value
                #edge_attributes[attribute]=value
        net_number += 1

    #Remove PXEbootinterface attribute from hosts which are not set to PXEboot=True
    for device in inventory:
        count=0
        for link in inventory[device]['interfaces']:
            if 'pxebootinterface' in inventory[device]['interfaces'][link]:
                count += 1 #increment count to make sure more than one interface doesn't try to set nicbootprio
                if 'pxehost' not in inventory[device]: del inventory[device]['interfaces'][link]['pxebootinterface']
                elif 'pxehost' in inventory[device]:
                    if inventory[device]['pxehost'] != "True": del inventory[device]['interfaces'][link]['pxebootinterface']
    #Make sure no host has PXEbootinterface set more than once
    # Have to make two passes here because doing it in one pass could have
    # side effects.
    for device in inventory:
        count=0
        for link in inventory[device]['interfaces']:
            if 'pxebootinterface' in inventory[device]['interfaces'][link]:
                count += 1 #increment count to make sure more than one interface doesn't try to set nicbootprio
        if count > 1:
            print styles.FAIL + styles.BOLD + " ### ERROR -- Device " + device + " sets pxebootinterface more than once." + styles.ENDC
            exit(1)

    #######################
    #Add Mgmt Network Links
    #######################
    if create_mgmt_device:
        mgmt_server=None
        mgmt_switch=None
        for device in inventory:
            if inventory[device]["function"] == "oob-switch": mgmt_switch=device
            elif inventory[device]["function"] == "oob-server": mgmt_server=device

        if verbose:
            print " detected mgmt_server: %s" % mgmt_server
            print "          mgmt_switch: %s" % mgmt_switch
        #Hardcode mgmt server parameters
        if mgmt_server == None:
            if "oob-mgmt-server" in inventory:
                print styles.FAIL + styles.BOLD + ' ### ERROR: oob-mgmt-server must be set to function = "oob-server"' + styles.ENDC
                exit(1)
            inventory["oob-mgmt-server"] = {}
            inventory["oob-mgmt-server"]["function"] = "oob-server"
            inventory["oob-mgmt-server"]["mgmt_ip"] = "192.168.200.254"
            inventory["oob-mgmt-server"]["interfaces"] = {}
            mgmt_server="oob-mgmt-server"
            if provider == "libvirt":
                if 'tunnel_ip' not in inventory["oob-mgmt-server"]: inventory["oob-mgmt-server"]['tunnel_ip']='127.0.0.1'

        else:
            if "mgmt_ip" not in inventory[mgmt_server]:
                inventory[mgmt_server]["mgmt_ip"] = "192.168.200.254"

        inventory[mgmt_server]["os"] = "yk0/ubuntu-xenial"
        if provider=="libvirt":
            inventory[mgmt_server]["os"] = "yk0/ubuntu-xenial"
        if "memory" not in inventory[mgmt_server]:
            inventory[mgmt_server]["memory"] = "512"
        inventory[mgmt_server]["config"] = "./helper_scripts/auto_mgmt_network/OOB_Server_Config_auto_mgmt.sh"

        #Hardcode mgmt switch parameters

        if mgmt_switch == None and create_mgmt_network:
            if "oob-mgmt-switch" in inventory:
                print styles.FAIL + styles.BOLD + ' ### ERROR: oob-mgmt-switch must be set to function = "oob-switch"' + styles.ENDC
                exit(1)
            inventory["oob-mgmt-switch"] = {}
            inventory["oob-mgmt-switch"]["function"] = "oob-switch"
            inventory["oob-mgmt-switch"]["interfaces"] = {}
            if provider == "libvirt":
                if 'tunnel_ip' not in inventory["oob-mgmt-switch"]: inventory["oob-mgmt-switch"]['tunnel_ip']='127.0.0.1'

            mgmt_switch="oob-mgmt-switch"

        if create_mgmt_network:
            inventory[mgmt_switch]["os"] = "CumulusCommunity/cumulus-vx"
            inventory[mgmt_switch]["memory"] = "512"
            inventory[mgmt_switch]["config"] = "./helper_scripts/oob_switch_config.sh"

            #Add Link between oob-mgmt-switch oob-mgmt-server
            net_number+=1
            left_mac=mac_fetch(mgmt_switch,"swp1")
            right_mac=mac_fetch(mgmt_server,"mgmt_net")
            print "  adding mgmt links:"
            if provider=="virtualbox":
               print "    %s:%s (mac: %s) --> %s:%s (mac: %s)     network_string:%s" % (mgmt_switch,"swp1",left_mac,mgmt_server,"mgmt_net",right_mac,network_string)
            elif provider=="libvirt":
                print "    %s:%s udp_port %s (mac: %s) --> %s:%s udp_port %s (mac: %s)" % (mgmt_switch,"swp1",left_mac,PortA,mgmt_server,"mgmt_net",PortB,right_mac)
            add_link(inventory,
                     mgmt_switch,
                     mgmt_server,
                     "swp1",
                     "mgmt_net",
                     left_mac,
                     right_mac,
                     net_number)
            mgmt_switch_swp=1

            #Add Eth0 MGMT Link for every device that is is not oob-switch or oob-server
            for device in inventory:
                if inventory[device]["function"]=="oob-server" or inventory[device]["function"]=="oob-switch": continue
                elif inventory[device]["function"] in network_functions:
                    inventory[device]["config"] = "./helper_scripts/extra_switch_config.sh"
                mgmt_switch_swp+=1
                net_number+=1
                if int(PortA) > int(start_port+port_gap) and provider=="libvirt":
                    print styles.FAIL + styles.BOLD + " ### ERROR: Configured Port_Gap: ("+str(port_gap)+") exceeds the number of links in the topology. Read the help options to fix.\n\n" + styles.ENDC
                    parser.print_help()
                    exit(1)
                mgmt_switch_swp_val="swp"+str(mgmt_switch_swp)
                left_mac=mac_fetch(mgmt_switch,mgmt_switch_swp_val)
                right_mac=mac_fetch(device,"eth0")

                half1_exists=False
                half2_exists=False
                #Check to see if components of the link already exist
                if "eth0" in inventory[device]['interfaces']:
                    if inventory[device]['interfaces']['eth0']['remote_interface'] != mgmt_switch_swp_val:
                        print styles.FAIL + styles.BOLD + " ### ERROR: %s:eth0 interface already exists but not connected to %s:%s" %(device,mgmt_switch,mgmt_switch_swp_val) + styles.ENDC
                        exit(1)
                    if inventory[device]['interfaces']['eth0']['remote_device'] != mgmt_switch:
                        print styles.FAIL + styles.BOLD + " ### ERROR: %s:eth0 interface already exists but not connected to %s:%s" %(device,mgmt_switch,mgmt_switch_swp_val) + styles.ENDC
                        exit(1)
                    if verbose: print "        mgmt link on %s already exists and is good." % (mgmt_switch)
                    half1_exists=True

                if mgmt_switch_swp_val in inventory[mgmt_switch]['interfaces']:
                    if inventory[mgmt_switch]['interfaces'][mgmt_switch_swp_val]['remote_interface'] != "eth0":
                        print styles.FAIL + styles.BOLD + " ### ERROR: %s:%s-- link already exists but not connected to %s:eth0" %(mgmt_switch,mgmt_switch_swp_val,device) + styles.ENDC
                        exit(1)
                    if inventory[mgmt_switch]['interfaces'][mgmt_switch_swp_val]['remote_device'] != device:
                        print styles.FAIL + styles.BOLD + " ### ERROR: %s:%s-- link already exists but not connected to %s:eth0" %(mgmt_switch,mgmt_switch_swp_val,device) + styles.ENDC
                        exit(1)
                    if verbose: print "        mgmt link on %s already exists and is good." % (mgmt_switch)
                    half2_exists=True

                if not half1_exists and not half2_exists:
                    #Display add message
                    if provider=="virtualbox":
                        print "    %s:%s (mac: %s) --> %s:%s (mac: %s)     network_string:net%s" % (mgmt_switch,mgmt_switch_swp_val,left_mac,device,"eth0",right_mac,net_number)
                    elif provider=="libvirt":
                        print "    %s:%s udp_port %s (mac: %s) --> %s:%s udp_port %s (mac: %s)" % (mgmt_switch,mgmt_switch_swp_val,PortA,left_mac,device,"eth0",PortB,right_mac)

                    add_link(inventory,
                             mgmt_switch,
                             device,
                             mgmt_switch_swp_val,
                             "eth0",
                             left_mac,
                             right_mac,
                             net_number,)
    else:
        #Add Dummy Eth0 Link
        for device in inventory:
            if inventory[device]["function"] not in network_functions: continue
            #Check to see if components of the link already exist
            if "eth0" not in inventory[device]['interfaces']:
                net_number+=1

                add_link(inventory,
                         device,
                         "NOTHING",
                         "eth0",
                         "NOTHING",
                         mac_fetch(device,"eth0"),
                         "NOTHING",
                         net_number,)

    #Add Extra Port Ranges (if needed)
    for device in inventory:
        if "ports" in inventory[device] and inventory[device]["function"] in network_functions:
            if provider!="libvirt":
                warning.append(styles.WARNING + styles.BOLD + "    WARNING: 'ports' setting on node %s will be ignored when not using the libvirt hypervisor."%(device) + styles.ENDC)
            port_range = int(inventory[device]["ports"])
            existing_port_list=[]
            ports_to_create=[]
            only_nums = re.compile(r'[^\d]+')
            for port in inventory[device]['interfaces']:
                existing_port_list.append(int(only_nums.sub('', port)))
            print existing_port_list
            for i in range(0,port_range+1):
                if i not in existing_port_list: ports_to_create.append(i)
            if verbose:
                print "  INFO: On %s will create the following ports:" %(device)
                print ports_to_create
            #exit(1)
            for i in ports_to_create:
                net_number+=1
                add_link(inventory,
                         device,
                         "NOTHING",
                         "swp%s"%(i),
                         "NOTHING",
                         mac_fetch(device,"swp%s"%(i)),
                         "NOTHING",
                         net_number,)

    if verbose:
        print "\n\n ### Inventory Datastructure: ###"
        pp.pprint(inventory)

    return inventory

def add_link(inventory,left_device,right_device,left_interface,right_interface,left_mac_address,right_mac_address,net_number):
    network_string="net"+str(net_number)
    PortA=str(start_port+net_number)
    PortB=str(start_port+port_gap+net_number)
    if int(PortA) > int(start_port+port_gap) and provider=="libvirt":
        print styles.FAIL + styles.BOLD + " ### ERROR: Configured Port_Gap: ("+str(port_gap)+") exceeds the number of links in the topology. Read the help options to fix.\n\n" + styles.ENDC
        parser.print_help()
        exit(1)

    global mac_map
    #Add a Link to the Inventory for both switches

    #Add left host switchport to inventory
    if left_interface not in inventory[left_device]['interfaces']:
        inventory[left_device]['interfaces'][left_interface] = {}
        inventory[left_device]['interfaces'][left_interface]['mac']=left_mac_address
        if left_mac_address in mac_map:
            print styles.FAIL + styles.BOLD + " ### ERROR -- MAC Address Collision - tried to use "+left_mac_address+" on "+left_device+":"+left_interface+"\n                 but it is already in use. Check your Topology File!" + styles.ENDC
            exit(1)
        mac_map[left_mac_address]=left_device+","+left_interface
        if provider=="virtualbox":
            inventory[left_device]['interfaces'][left_interface]['network'] = network_string
        elif provider=="libvirt":
            inventory[left_device]['interfaces'][left_interface]['local_port'] = PortA
            inventory[left_device]['interfaces'][left_interface]['remote_port'] = PortB
    else:
        print styles.FAIL + styles.BOLD + " ### ERROR -- Interface " + left_interface + " Already used on device: " + left_device + styles.ENDC
        exit(1)

    #Add right host switchport to inventory
    if right_device == "NOTHING":
        pass
    elif right_interface not in inventory[right_device]['interfaces']:
        inventory[right_device]['interfaces'][right_interface] = {}
        inventory[right_device]['interfaces'][right_interface]['mac']=right_mac_address
        if right_mac_address in mac_map:
            print styles.FAIL + styles.BOLD + " ### ERROR -- MAC Address Collision - tried to use "+right_mac_address+" on "+right_device+":"+right_interface+"\n                 but it is already in use. Check your Topology File!" + styles.ENDC
            exit(1)
        mac_map[right_mac_address]=right_device+","+right_interface
        if provider=="virtualbox":
            inventory[right_device]['interfaces'][right_interface]['network'] = network_string
        elif provider=="libvirt":
            inventory[right_device]['interfaces'][right_interface]['local_port'] = PortB
            inventory[right_device]['interfaces'][right_interface]['remote_port'] = PortA
    else:
        print styles.FAIL + styles.BOLD + " ### ERROR -- Interface " + right_interface + " Already used on device: " + right_device + styles.ENDC
        exit(1)
    inventory[left_device]['interfaces'][left_interface]['remote_interface'] = right_interface
    inventory[left_device]['interfaces'][left_interface]['remote_device'] = right_device

    if right_device != "NOTHING":
        inventory[right_device]['interfaces'][right_interface]['remote_interface'] = left_interface
        inventory[right_device]['interfaces'][right_interface]['remote_device'] = left_device

    if provider == 'libvirt':
        if right_device != "NOTHING":
            inventory[left_device]['interfaces'][left_interface]['local_ip'] = inventory[left_device]['tunnel_ip']
            inventory[left_device]['interfaces'][left_interface]['remote_ip'] = inventory[right_device]['tunnel_ip']
            inventory[right_device]['interfaces'][right_interface]['local_ip'] = inventory[right_device]['tunnel_ip']
            inventory[right_device]['interfaces'][right_interface]['remote_ip'] = inventory[left_device]['tunnel_ip']
        elif right_device == "NOTHING":
            inventory[left_device]['interfaces'][left_interface]['local_ip'] = "127.0.0.1"
            inventory[left_device]['interfaces'][left_interface]['remote_ip'] = "127.0.0.1"


def clean_datastructure(devices):
    #Sort the devices by function
    devices.sort(key=getKeyDevices)
    for device in devices:
        device['interfaces']=sorted_interfaces(device['interfaces'])

    if display_datastructures: return devices
    for device in devices:
        print styles.GREEN + styles.BOLD + ">> DEVICE: " + device['hostname'] + styles.ENDC
        print "     code: " + device['os']
        if 'memory' in device:
            print "     memory: " + device['memory']
        for attribute in device:
            if attribute == 'memory' or attribute == 'os' or attribute == 'interfaces': continue
            print "     "+str(attribute)+": "+ str(device[attribute])
        for interface_entry in device['interfaces']:
            print "       LINK: " + interface_entry["local_interface"]
            for attribute in interface_entry:
                if attribute != "local_interface":
                    print "               " + attribute +": " + interface_entry[attribute]

    #Remove Fake Devices
    indexes_to_remove=[]
    for i in range(0,len(devices)):
        if 'function' in devices[i]:
            if devices[i]['function'] == 'fake':
                indexes_to_remove.append(i)
    for index in sorted(indexes_to_remove, reverse=True):
        del devices[index]
    return devices

def remove_generated_files():
    if display_datastructures: return
    if verbose: print "Removing existing DHCP FILE..."
    if os.path.isfile(dhcp_mac_file):  os.remove(dhcp_mac_file)


_nsre = re.compile('([0-9]+)')
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(_nsre, s)]


def getKeyDevices(device):
    # Used to order the devices for printing into the vagrantfile
    if device['function'] == "oob-server": return 1
    elif device['function'] == "oob-switch": return 2
    elif device['function'] == "exit": return 3
    elif device['function'] == "superspine": return 4
    elif device['function'] == "spine": return 5
    elif device['function'] == "leaf": return 6
    elif device['function'] == "tor": return 7
    elif device['function'] == "host": return 8
    else: return 9

def sorted_interfaces(interface_dictionary):
    sorted_list=[]
    interface_list=[]
    for link in interface_dictionary:
        sorted_list.append(link)
    sorted_list.sort(key=natural_sort_key)
    for link in sorted_list:
        interface_dictionary[link]["local_interface"]= link
        interface_list.append(interface_dictionary[link])
    return interface_list

def generate_dhcp_mac_file(mac_map):
    if verbose: print "GENERATING DHCP MAC FILE..."
    mac_file = open(dhcp_mac_file,"a")
    if '' in mac_map: del mac_map['']
    dhcp_display_list=[]
    for line in mac_map:
        dhcp_display_list.append(mac_map[line]+","+line)
    dhcp_display_list.sort()
    for line in dhcp_display_list:
        mac_file.write(line+"\n")
    mac_file.close()

def populate_data_structures(inventory):
    global function_group
    devices = []
    for device in inventory:
        inventory[device]['hostname']=device
        devices.append(inventory[device])
    devices_clean = clean_datastructure(devices)

    #Create Functional Group Map
    for device in devices_clean:
        if device['function'] not in function_group: function_group[device['function']] = []
        function_group[device['function']].append(device['hostname'])

    return devices_clean

def render_jinja_templates(devices):
    global function_group
    if verbose: print "RENDERING JINJA TEMPLATES..."

    #Render the MGMT Network stuff
    if create_mgmt_device:
        #Check that MGMT Template Dir exists
        mgmt_template_dir="./templates/auto_mgmt_network/"
        if not os.path.isdir("./templates/auto_mgmt_network"):
            print styles.FAIL + styles.BOLD + "ERROR: " + mgmt_template_dir + " does not exist. Cannot populate templates!" + styles.ENDC
            exit(1)

        #Scan MGMT Template Dir for .j2 files
        mgmt_templates=[]
        for file in os.listdir(mgmt_template_dir):
            if file.endswith(".j2"): mgmt_templates.append(file)
        if verbose:
            print " detected mgmt_templates:"
            print mgmt_templates

        #Create output location for MGMT template files
        mgmt_destination_dir="./helper_scripts/auto_mgmt_network/"
        if not os.path.isdir(mgmt_destination_dir):
            if verbose: print "Making Directory for MGMT Helper Files: " + mgmt_destination_dir
            try:
                os.mkdir(mgmt_destination_dir)
            except:
                print styles.FAIL + styles.BOLD + "ERROR: Could not create output directory for mgmt template renders!" + styles.ENDC
                exit(1)

        #Render out the templates
        for template in mgmt_templates:
            render_destination=os.path.join(mgmt_destination_dir,template[0:-3])
            template_source=os.path.join(mgmt_template_dir,template)
            if verbose: print "    Rendering: " + template + " --> " + render_destination
            template = jinja2.Template(open(template_source).read())
            with open(render_destination, 'w') as outfile:
                outfile.write(template.render(devices=devices,
                                              synced_folder=synced_folder,
                                              provider=provider,
                                              version=version,
					      customer=customer,
                                              topology_file=topology_file,
                                              arg_string=arg_string,
                                              epoch_time=epoch_time,
                                              script_storage=script_storage,
                                              generate_ansible_hostfile=generate_ansible_hostfile,
                                              create_mgmt_device=create_mgmt_device,
                                              function_group=function_group,
                                              network_functions=network_functions,)
                             )
   #Render the main Vagrantfile
    if display_datastructures: print_datastructures(devices)
    if create_mgmt_device and create_mgmt_configs_only:
        return 0
    for templatefile,destination in TEMPLATES:
        if verbose: print "    Rendering: " + templatefile + " --> " + destination
        template = jinja2.Template(open(templatefile).read())
        with open(destination, 'w') as outfile:
            outfile.write(template.render(devices=devices,
                                          synced_folder=synced_folder,
                                          provider=provider,
                                          version=version,
                                          topology_file=topology_file,
                                          arg_string=arg_string,
                                          epoch_time=epoch_time,
                                          script_storage=script_storage,
                                          generate_ansible_hostfile=generate_ansible_hostfile,
                                          create_mgmt_device=create_mgmt_device,
                                          function_group=function_group,
                                          network_functions=network_functions,)
                         )

def print_datastructures(devices):
    print "\n\n######################################"
    print "   DATASTRUCTURES SENT TO TEMPLATE:"
    print "######################################\n"
    print "provider=" + provider
    print "synced_folder=" + str(synced_folder)
    print "version=" + str(version)
    print "topology_file=" + topology_file
    print "arg_string=" + arg_string
    print "epoch_time=" + str(epoch_time)
    print "script_storage=" + script_storage
    print "generate_ansible_hostfile=" + str(generate_ansible_hostfile)
    print "create_mgmt_device=" + str(create_mgmt_device)
    print "function_group="
    pp.pprint(function_group)
    print "network_functions="
    pp.pprint(network_functions)
    print "devices="
    pp.pprint(devices)
    exit(0)

def generate_ansible_files():
    if not generate_ansible_hostfile: return
    if verbose: print "Generating Ansible Files..."
    with open("./helper_scripts/empty_playbook.yml","w") as playbook:
        playbook.write("""---
- hosts: all
  user: vagrant
  gather_facts: no
  tasks:
    - command: "uname -a"
""")
    with open("./ansible.cfg","w") as ansible_cfg:
        ansible_cfg.write("""[defaults]
inventory = ./.vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory
hostfile= ./.vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory
host_key_checking=False
callback_whitelist = profile_tasks
jinja2_extensions=jinja2.ext.do""")



def main():
    global mac_map
    print styles.HEADER + "\n######################################"
    print styles.HEADER + "          Topology Converter"
    print styles.HEADER + "######################################"
    print styles.BLUE + "           originally written by Eric Pulvino"

    inventory = parse_topology(topology_file)

    devices=populate_data_structures(inventory)

    remove_generated_files()

    render_jinja_templates(devices)

    generate_dhcp_mac_file(mac_map)

    generate_ansible_files()

    if create_mgmt_configs_only:
        print styles.GREEN + styles.BOLD + "\n############\nSUCCESS: MGMT Network Templates have been regenerated!\n############" + styles.ENDC
    else:
        print styles.GREEN + styles.BOLD + "\n############\nSUCCESS: Vagrantfile has been generated!\n############" + styles.ENDC
        print styles.GREEN + styles.BOLD + "\n            %s devices under simulation." %(len(devices)) + styles.ENDC
    for warn_msg in warning:
        print warn_msg
    print "\nDONE!\n"

if __name__ == "__main__":
    main()
exit(0)
