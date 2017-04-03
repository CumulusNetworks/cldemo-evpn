# Created by Topology-Converter v4.6.1_dev
#    https://github.com/cumulusnetworks/topology_converter
#    using topology data from: topology_kvm.dot
#
#    NOTE: in order to use this Vagrantfile you will need:
#       -Vagrant(v1.8.1+) installed: http://www.vagrantup.com/downloads
#       -Cumulus Plugin for Vagrant installed: $ vagrant plugin install vagrant-cumulus
#       -the "helper_scripts" directory that comes packaged with topology-converter.py
#        -Libvirt Installed -- guide to come
#       -Vagrant-Libvirt Plugin installed: $ vagrant plugin install vagrant-libvirt
#       -Boxes which have been mutated to support Libvirt -- see guide below:
#            https://community.cumulusnetworks.com/cumulus/topics/converting-cumulus-vx-virtualbox-vagrant-box-gt-libvirt-vagrant-box
#       -Start with \"vagrant up --provider=libvirt --no-parallel\n")

#Set the default provider to libvirt in the case they forget --provider=libvirt or if someone destroys a machine it reverts to virtualbox
ENV['VAGRANT_DEFAULT_PROVIDER'] = 'libvirt'

# Check required plugins
REQUIRED_PLUGINS_LIBVIRT = %w(vagrant-libvirt vagrant-mutate)
exit unless REQUIRED_PLUGINS_LIBVIRT.all? do |plugin|
  Vagrant.has_plugin?(plugin) || (
    puts "The #{plugin} plugin is required. Please install it with:"
    puts "$ vagrant plugin install #{plugin}"
    false
  )
end

# Check required plugins
REQUIRED_PLUGINS = %w(vagrant-cumulus)
exit unless REQUIRED_PLUGINS.all? do |plugin|
  Vagrant.has_plugin?(plugin) || (
    puts "The #{plugin} plugin is required. Please install it with:"
    puts "$ vagrant plugin install #{plugin}"
    false
  )
end


$script = <<-SCRIPT
if grep -q -i 'cumulus' /etc/lsb-release &> /dev/null; then
    echo "### RUNNING CUMULUS EXTRA CONFIG ###"
    source /etc/lsb-release
    if [[ $DISTRIB_RELEASE =~ ^2.* ]]; then
        echo "  INFO: Detected a 2.5.x Based Release"

        echo "  adding fake cl-acltool..."
        echo -e "#!/bin/bash\nexit 0" > /usr/bin/cl-acltool
        chmod 755 /usr/bin/cl-acltool

        echo "  adding fake cl-license..."
        echo -e "#!/bin/bash\nexit 0" > /usr/bin/cl-license
        chmod 755 /usr/bin/cl-license

        echo "  Disabling default remap on Cumulus VX..."
        mv -v /etc/init.d/rename_eth_swp /etc/init.d/rename_eth_swp.backup

        echo "### Rebooting to Apply Remap..."
        reboot

    elif [[ $DISTRIB_RELEASE =~ ^3.* ]]; then
        echo "  INFO: Detected a 3.x Based Release"
        echo "  Disabling default remap on Cumulus VX..."
        mv -v /etc/hw_init.d/S10rename_eth_swp.sh /etc/S10rename_eth_swp.sh.backup
        #echo "### Applying Remap without Reboot..."
        #~/apply_udev.py --apply
        #echo "### Performing IFRELOAD to Apply any Latent Interface Config..."
        #ifreload -a 2>&1
        echo "### Disabling ZTP service..."
        systemctl stop ztp.service
        ztp -d 2>&1
        echo "### Resetting ZTP to work next boot..."
        ztp -R 2>&1
        echo "### Rebooting Switch to Apply Remap..."
        reboot
    fi
    echo "### DONE ###"
else
    echo "### Rebooting to Apply Remap..."
    reboot
fi
SCRIPT

Vagrant.configure("2") do |config|
  wbid = 1491226726

  config.vm.provider :libvirt do |domain|
    # increase nic adapter count to be greater than 8 for all VMs.
    domain.nic_adapter_count = 55
  end




  ##### DEFINE VM for oob-mgmt-server #####
  config.vm.define "oob-mgmt-server" do |device|
    device.vm.hostname = "oob-mgmt-server"
    device.vm.box = "yk0/ubuntu-xenial"

    device.vm.provider :libvirt do |v|
      v.memory = 1024
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth1 --> oob-mgmt-switch:swp1
      device.vm.network "private_network",
            :mac => "443839000059",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8052',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9052',
            :libvirt__iface_name => 'eth1',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Shorten Boot Process - Applies to Ubuntu Only - remove \"Wait for Network\"
    device.vm.provision :shell , inline: "sed -i 's/sleep [0-9]*/sleep 1/' /etc/init/failsafe.conf 2>/dev/null || true"

    #Copy over DHCP files and MGMT Network Files
    device.vm.provision "file", source: "./helper_scripts/dhcpd.conf", destination: "~/dhcpd.conf"
    device.vm.provision "file", source: "./helper_scripts/dhcpd.hosts", destination: "~/dhcpd.hosts"
    device.vm.provision "file", source: "./helper_scripts/hosts", destination: "~/hosts"
    device.vm.provision "file", source: "./helper_scripts/ansible_hostfile", destination: "~/ansible_hostfile"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_oob_server.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:59 --> eth1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:59", NAME="eth1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for oob-mgmt-switch #####
  config.vm.define "oob-mgmt-switch" do |device|
    device.vm.hostname = "oob-mgmt-switch"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> NOTHING:NOTHING
      device.vm.network "private_network",
            :mac => "443839000063",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8058',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9058',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp1 --> oob-mgmt-server:eth1
      device.vm.network "private_network",
            :mac => "44383900005a",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9052',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8052',
            :libvirt__iface_name => 'swp1',
            auto_config: false
      # link for swp2 --> server01:eth0
      device.vm.network "private_network",
            :mac => "443839000046",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9041',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8041',
            :libvirt__iface_name => 'swp2',
            auto_config: false
      # link for swp4 --> server03:eth0
      device.vm.network "private_network",
            :mac => "44383900001d",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9016',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8016',
            :libvirt__iface_name => 'swp4',
            auto_config: false
      # link for swp6 --> leaf01:eth0
      device.vm.network "private_network",
            :mac => "44383900001e",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9017',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8017',
            :libvirt__iface_name => 'swp6',
            auto_config: false
      # link for swp7 --> leaf02:eth0
      device.vm.network "private_network",
            :mac => "443839000040",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9037',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8037',
            :libvirt__iface_name => 'swp7',
            auto_config: false
      # link for swp8 --> leaf03:eth0
      device.vm.network "private_network",
            :mac => "44383900002d",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9025',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8025',
            :libvirt__iface_name => 'swp8',
            auto_config: false
      # link for swp9 --> leaf04:eth0
      device.vm.network "private_network",
            :mac => "443839000038",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9032',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8032',
            :libvirt__iface_name => 'swp9',
            auto_config: false
      # link for swp10 --> spine01:eth0
      device.vm.network "private_network",
            :mac => "443839000032",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9028',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8028',
            :libvirt__iface_name => 'swp10',
            auto_config: false
      # link for swp11 --> spine02:eth0
      device.vm.network "private_network",
            :mac => "443839000012",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9010',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8010',
            :libvirt__iface_name => 'swp11',
            auto_config: false
      # link for swp12 --> exit01:eth0
      device.vm.network "private_network",
            :mac => "44383900000d",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9007',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8007',
            :libvirt__iface_name => 'swp12',
            auto_config: false
      # link for swp13 --> exit02:eth0
      device.vm.network "private_network",
            :mac => "44383900004f",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9046',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8046',
            :libvirt__iface_name => 'swp13',
            auto_config: false
      # link for swp14 --> site02:eth0
      device.vm.network "private_network",
            :mac => "443839000043",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9039',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8039',
            :libvirt__iface_name => 'swp14',
            auto_config: false
      # link for swp15 --> internet:eth0
      device.vm.network "private_network",
            :mac => "443839000039",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9033',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8033',
            :libvirt__iface_name => 'swp15',
            auto_config: false
      # link for swp16 --> isp:eth0
      device.vm.network "private_network",
            :mac => "443839000056",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9050',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8050',
            :libvirt__iface_name => 'swp16',
            auto_config: false
      # link for swp17 --> server05:eth0
      device.vm.network "private_network",
            :mac => "443839000033",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9029',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8029',
            :libvirt__iface_name => 'swp17',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"


    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_oob_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:63 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:63", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:5a --> swp1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:5a", NAME="swp1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:46 --> swp2"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:46", NAME="swp2", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:1d --> swp4"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:1d", NAME="swp4", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:1e --> swp6"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:1e", NAME="swp6", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:40 --> swp7"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:40", NAME="swp7", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:2d --> swp8"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:2d", NAME="swp8", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:38 --> swp9"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:38", NAME="swp9", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:32 --> swp10"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:32", NAME="swp10", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:12 --> swp11"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:12", NAME="swp11", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:0d --> swp12"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:0d", NAME="swp12", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:4f --> swp13"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:4f", NAME="swp13", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:43 --> swp14"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:43", NAME="swp14", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:39 --> swp15"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:39", NAME="swp15", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:56 --> swp16"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:56", NAME="swp16", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:33 --> swp17"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:33", NAME="swp17", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for exit02 #####
  config.vm.define "exit02" do |device|
    device.vm.hostname = "exit02"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp13
      device.vm.network "private_network",
            :mac => "a00000000042",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8046',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9046',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp44 --> internet:swp2
      device.vm.network "private_network",
            :mac => "443839000042",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9038',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8038',
            :libvirt__iface_name => 'swp44',
            auto_config: false
      # link for swp45 --> exit02:swp46
      device.vm.network "private_network",
            :mac => "443839000030",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8027',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9027',
            :libvirt__iface_name => 'swp45',
            auto_config: false
      # link for swp46 --> exit02:swp45
      device.vm.network "private_network",
            :mac => "443839000031",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9027',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8027',
            :libvirt__iface_name => 'swp46',
            auto_config: false
      # link for swp47 --> exit02:swp48
      device.vm.network "private_network",
            :mac => "443839000036",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8031',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9031',
            :libvirt__iface_name => 'swp47',
            auto_config: false
      # link for swp48 --> exit02:swp47
      device.vm.network "private_network",
            :mac => "443839000037",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9031',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8031',
            :libvirt__iface_name => 'swp48',
            auto_config: false
      # link for swp49 --> exit01:swp49
      device.vm.network "private_network",
            :mac => "443839000026",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9021',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8021',
            :libvirt__iface_name => 'swp49',
            auto_config: false
      # link for swp50 --> exit01:swp50
      device.vm.network "private_network",
            :mac => "443839000014",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9011',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8011',
            :libvirt__iface_name => 'swp50',
            auto_config: false
      # link for swp51 --> spine01:swp29
      device.vm.network "private_network",
            :mac => "44383900001f",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8018',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9018',
            :libvirt__iface_name => 'swp51',
            auto_config: false
      # link for swp52 --> spine02:swp29
      device.vm.network "private_network",
            :mac => "443839000057",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8051',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9051',
            :libvirt__iface_name => 'swp52',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/exit02/interfaces", destination: "~/interfaces"
    device.vm.provision "file", source: "./config/exit02/daemons", destination: "~/daemons"
    device.vm.provision "file", source: "./config/exit02/Quagga.conf", destination: "~/Quagga.conf"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:42 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:42", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:42 --> swp44"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:42", NAME="swp44", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:30 --> swp45"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:30", NAME="swp45", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:31 --> swp46"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:31", NAME="swp46", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:36 --> swp47"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:36", NAME="swp47", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:37 --> swp48"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:37", NAME="swp48", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:26 --> swp49"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:26", NAME="swp49", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:14 --> swp50"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:14", NAME="swp50", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:1f --> swp51"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:1f", NAME="swp51", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:57 --> swp52"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:57", NAME="swp52", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for exit01 #####
  config.vm.define "exit01" do |device|
    device.vm.hostname = "exit01"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp12
      device.vm.network "private_network",
            :mac => "a00000000041",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8007',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9007',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp44 --> internet:swp1
      device.vm.network "private_network",
            :mac => "443839000008",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9004',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8004',
            :libvirt__iface_name => 'swp44',
            auto_config: false
      # link for swp45 --> exit01:swp46
      device.vm.network "private_network",
            :mac => "443839000047",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8042',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9042',
            :libvirt__iface_name => 'swp45',
            auto_config: false
      # link for swp46 --> exit01:swp45
      device.vm.network "private_network",
            :mac => "443839000048",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9042',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8042',
            :libvirt__iface_name => 'swp46',
            auto_config: false
      # link for swp47 --> exit01:swp48
      device.vm.network "private_network",
            :mac => "443839000010",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8009',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9009',
            :libvirt__iface_name => 'swp47',
            auto_config: false
      # link for swp48 --> exit01:swp47
      device.vm.network "private_network",
            :mac => "443839000011",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9009',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8009',
            :libvirt__iface_name => 'swp48',
            auto_config: false
      # link for swp49 --> exit02:swp49
      device.vm.network "private_network",
            :mac => "443839000025",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8021',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9021',
            :libvirt__iface_name => 'swp49',
            auto_config: false
      # link for swp50 --> exit02:swp50
      device.vm.network "private_network",
            :mac => "443839000013",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8011',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9011',
            :libvirt__iface_name => 'swp50',
            auto_config: false
      # link for swp51 --> spine01:swp30
      device.vm.network "private_network",
            :mac => "443839000009",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8005',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9005',
            :libvirt__iface_name => 'swp51',
            auto_config: false
      # link for swp52 --> spine02:swp30
      device.vm.network "private_network",
            :mac => "44383900005d",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8054',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9054',
            :libvirt__iface_name => 'swp52',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/exit01/interfaces", destination: "~/interfaces"
    device.vm.provision "file", source: "./config/exit01/daemons", destination: "~/daemons"
    device.vm.provision "file", source: "./config/exit01/Quagga.conf", destination: "~/Quagga.conf"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:41 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:41", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:08 --> swp44"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:08", NAME="swp44", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:47 --> swp45"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:47", NAME="swp45", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:48 --> swp46"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:48", NAME="swp46", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:10 --> swp47"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:10", NAME="swp47", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:11 --> swp48"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:11", NAME="swp48", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:25 --> swp49"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:25", NAME="swp49", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:13 --> swp50"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:13", NAME="swp50", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:09 --> swp51"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:09", NAME="swp51", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:5d --> swp52"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:5d", NAME="swp52", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for isp #####
  config.vm.define "isp" do |device|
    device.vm.hostname = "isp"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp16
      device.vm.network "private_network",
            :mac => "a00000000052",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8050',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9050',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp1 --> site02:swp51
      device.vm.network "private_network",
            :mac => "44383900004e",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9045',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8045',
            :libvirt__iface_name => 'swp1',
            auto_config: false
      # link for swp47 --> internet:swp47
      device.vm.network "private_network",
            :mac => "44383900002b",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8024',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9024',
            :libvirt__iface_name => 'swp47',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/isp/interfaces", destination: "~/interfaces"
    device.vm.provision "file", source: "./config/isp/daemons", destination: "~/daemons"
    device.vm.provision "file", source: "./config/isp/Quagga.conf", destination: "~/Quagga.conf"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:52 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:52", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:4e --> swp1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:4e", NAME="swp1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:2b --> swp47"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:2b", NAME="swp47", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for spine02 #####
  config.vm.define "spine02" do |device|
    device.vm.hostname = "spine02"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp11
      device.vm.network "private_network",
            :mac => "a00000000022",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8010',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9010',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp1 --> leaf01:swp52
      device.vm.network "private_network",
            :mac => "443839000024",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9020',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8020',
            :libvirt__iface_name => 'swp1',
            auto_config: false
      # link for swp2 --> leaf02:swp52
      device.vm.network "private_network",
            :mac => "443839000062",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9056',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8056',
            :libvirt__iface_name => 'swp2',
            auto_config: false
      # link for swp3 --> leaf03:swp52
      device.vm.network "private_network",
            :mac => "44383900001a",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9014',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8014',
            :libvirt__iface_name => 'swp3',
            auto_config: false
      # link for swp4 --> leaf04:swp52
      device.vm.network "private_network",
            :mac => "44383900004a",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9043',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8043',
            :libvirt__iface_name => 'swp4',
            auto_config: false
      # link for swp29 --> exit02:swp52
      device.vm.network "private_network",
            :mac => "443839000058",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9051',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8051',
            :libvirt__iface_name => 'swp29',
            auto_config: false
      # link for swp30 --> exit01:swp52
      device.vm.network "private_network",
            :mac => "44383900005e",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9054',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8054',
            :libvirt__iface_name => 'swp30',
            auto_config: false
      # link for swp31 --> spine01:swp31
      device.vm.network "private_network",
            :mac => "44383900004c",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9044',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8044',
            :libvirt__iface_name => 'swp31',
            auto_config: false
      # link for swp32 --> spine01:swp32
      device.vm.network "private_network",
            :mac => "44383900003d",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9035',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8035',
            :libvirt__iface_name => 'swp32',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/spine02/interfaces", destination: "~/interfaces"
    device.vm.provision "file", source: "./config/spine02/daemons", destination: "~/daemons"
    device.vm.provision "file", source: "./config/spine02/Quagga.conf", destination: "~/Quagga.conf"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:22 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:22", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:24 --> swp1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:24", NAME="swp1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:62 --> swp2"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:62", NAME="swp2", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:1a --> swp3"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:1a", NAME="swp3", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:4a --> swp4"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:4a", NAME="swp4", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:58 --> swp29"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:58", NAME="swp29", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:5e --> swp30"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:5e", NAME="swp30", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:4c --> swp31"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:4c", NAME="swp31", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:3d --> swp32"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:3d", NAME="swp32", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for spine01 #####
  config.vm.define "spine01" do |device|
    device.vm.hostname = "spine01"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp10
      device.vm.network "private_network",
            :mac => "a00000000021",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8028',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9028',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp1 --> leaf01:swp51
      device.vm.network "private_network",
            :mac => "443839000055",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9049',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8049',
            :libvirt__iface_name => 'swp1',
            auto_config: false
      # link for swp2 --> leaf02:swp51
      device.vm.network "private_network",
            :mac => "443839000028",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9022',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8022',
            :libvirt__iface_name => 'swp2',
            auto_config: false
      # link for swp3 --> leaf03:swp51
      device.vm.network "private_network",
            :mac => "443839000051",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9047',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8047',
            :libvirt__iface_name => 'swp3',
            auto_config: false
      # link for swp4 --> leaf04:swp51
      device.vm.network "private_network",
            :mac => "44383900003f",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9036',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8036',
            :libvirt__iface_name => 'swp4',
            auto_config: false
      # link for swp29 --> exit02:swp51
      device.vm.network "private_network",
            :mac => "443839000020",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9018',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8018',
            :libvirt__iface_name => 'swp29',
            auto_config: false
      # link for swp30 --> exit01:swp51
      device.vm.network "private_network",
            :mac => "44383900000a",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9005',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8005',
            :libvirt__iface_name => 'swp30',
            auto_config: false
      # link for swp31 --> spine02:swp31
      device.vm.network "private_network",
            :mac => "44383900004b",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8044',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9044',
            :libvirt__iface_name => 'swp31',
            auto_config: false
      # link for swp32 --> spine02:swp32
      device.vm.network "private_network",
            :mac => "44383900003c",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8035',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9035',
            :libvirt__iface_name => 'swp32',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/spine01/interfaces", destination: "~/interfaces"
    device.vm.provision "file", source: "./config/spine01/daemons", destination: "~/daemons"
    device.vm.provision "file", source: "./config/spine01/Quagga.conf", destination: "~/Quagga.conf"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:21 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:21", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:55 --> swp1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:55", NAME="swp1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:28 --> swp2"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:28", NAME="swp2", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:51 --> swp3"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:51", NAME="swp3", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:3f --> swp4"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:3f", NAME="swp4", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:20 --> swp29"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:20", NAME="swp29", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:0a --> swp30"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:0a", NAME="swp30", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:4b --> swp31"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:4b", NAME="swp31", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:3c --> swp32"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:3c", NAME="swp32", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for leaf04 #####
  config.vm.define "leaf04" do |device|
    device.vm.hostname = "leaf04"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp9
      device.vm.network "private_network",
            :mac => "a00000000014",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8032',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9032',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp1 --> server03:eth2
      device.vm.network "private_network",
            :mac => "443839000060",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9055',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8055',
            :libvirt__iface_name => 'swp1',
            auto_config: false
      # link for swp45 --> leaf04:swp46
      device.vm.network "private_network",
            :mac => "443839000017",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8013',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9013',
            :libvirt__iface_name => 'swp45',
            auto_config: false
      # link for swp46 --> leaf04:swp45
      device.vm.network "private_network",
            :mac => "443839000018",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9013',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8013',
            :libvirt__iface_name => 'swp46',
            auto_config: false
      # link for swp47 --> leaf04:swp48
      device.vm.network "private_network",
            :mac => "443839000034",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8030',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9030',
            :libvirt__iface_name => 'swp47',
            auto_config: false
      # link for swp48 --> leaf04:swp47
      device.vm.network "private_network",
            :mac => "443839000035",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9030',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8030',
            :libvirt__iface_name => 'swp48',
            auto_config: false
      # link for swp49 --> leaf03:swp49
      device.vm.network "private_network",
            :mac => "44383900002f",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9026',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8026',
            :libvirt__iface_name => 'swp49',
            auto_config: false
      # link for swp50 --> leaf03:swp50
      device.vm.network "private_network",
            :mac => "443839000006",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9003',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8003',
            :libvirt__iface_name => 'swp50',
            auto_config: false
      # link for swp51 --> spine01:swp4
      device.vm.network "private_network",
            :mac => "44383900003e",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8036',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9036',
            :libvirt__iface_name => 'swp51',
            auto_config: false
      # link for swp52 --> spine02:swp4
      device.vm.network "private_network",
            :mac => "443839000049",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8043',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9043',
            :libvirt__iface_name => 'swp52',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/leaf04/interfaces", destination: "~/interfaces"
    device.vm.provision "file", source: "./config/leaf04/daemons", destination: "~/daemons"
    device.vm.provision "file", source: "./config/leaf04/Quagga.conf", destination: "~/Quagga.conf"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:14 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:14", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:60 --> swp1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:60", NAME="swp1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:17 --> swp45"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:17", NAME="swp45", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:18 --> swp46"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:18", NAME="swp46", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:34 --> swp47"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:34", NAME="swp47", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:35 --> swp48"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:35", NAME="swp48", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:2f --> swp49"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:2f", NAME="swp49", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:06 --> swp50"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:06", NAME="swp50", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:3e --> swp51"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:3e", NAME="swp51", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:49 --> swp52"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:49", NAME="swp52", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for leaf02 #####
  config.vm.define "leaf02" do |device|
    device.vm.hostname = "leaf02"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp7
      device.vm.network "private_network",
            :mac => "a00000000012",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8037',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9037',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp1 --> server01:eth2
      device.vm.network "private_network",
            :mac => "443839000016",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9012',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8012',
            :libvirt__iface_name => 'swp1',
            auto_config: false
      # link for swp45 --> leaf02:swp46
      device.vm.network "private_network",
            :mac => "44383900000b",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8006',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9006',
            :libvirt__iface_name => 'swp45',
            auto_config: false
      # link for swp46 --> leaf02:swp45
      device.vm.network "private_network",
            :mac => "44383900000c",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9006',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8006',
            :libvirt__iface_name => 'swp46',
            auto_config: false
      # link for swp47 --> leaf02:swp48
      device.vm.network "private_network",
            :mac => "44383900005b",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8053',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9053',
            :libvirt__iface_name => 'swp47',
            auto_config: false
      # link for swp48 --> leaf02:swp47
      device.vm.network "private_network",
            :mac => "44383900005c",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9053',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8053',
            :libvirt__iface_name => 'swp48',
            auto_config: false
      # link for swp49 --> leaf01:swp49
      device.vm.network "private_network",
            :mac => "44383900000f",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9008',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8008',
            :libvirt__iface_name => 'swp49',
            auto_config: false
      # link for swp50 --> leaf01:swp50
      device.vm.network "private_network",
            :mac => "443839000002",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9001',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8001',
            :libvirt__iface_name => 'swp50',
            auto_config: false
      # link for swp51 --> spine01:swp2
      device.vm.network "private_network",
            :mac => "443839000027",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8022',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9022',
            :libvirt__iface_name => 'swp51',
            auto_config: false
      # link for swp52 --> spine02:swp2
      device.vm.network "private_network",
            :mac => "443839000061",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8056',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9056',
            :libvirt__iface_name => 'swp52',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/leaf02/interfaces", destination: "~/interfaces"
    device.vm.provision "file", source: "./config/leaf02/daemons", destination: "~/daemons"
    device.vm.provision "file", source: "./config/leaf02/Quagga.conf", destination: "~/Quagga.conf"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:12 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:12", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:16 --> swp1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:16", NAME="swp1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:0b --> swp45"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:0b", NAME="swp45", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:0c --> swp46"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:0c", NAME="swp46", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:5b --> swp47"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:5b", NAME="swp47", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:5c --> swp48"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:5c", NAME="swp48", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:0f --> swp49"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:0f", NAME="swp49", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:02 --> swp50"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:02", NAME="swp50", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:27 --> swp51"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:27", NAME="swp51", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:61 --> swp52"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:61", NAME="swp52", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for leaf03 #####
  config.vm.define "leaf03" do |device|
    device.vm.hostname = "leaf03"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp8
      device.vm.network "private_network",
            :mac => "a00000000013",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8025',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9025',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp1 --> server03:eth1
      device.vm.network "private_network",
            :mac => "443839000022",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9019',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8019',
            :libvirt__iface_name => 'swp1',
            auto_config: false
      # link for swp45 --> leaf03:swp46
      device.vm.network "private_network",
            :mac => "443839000029",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8023',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9023',
            :libvirt__iface_name => 'swp45',
            auto_config: false
      # link for swp46 --> leaf03:swp45
      device.vm.network "private_network",
            :mac => "44383900002a",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9023',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8023',
            :libvirt__iface_name => 'swp46',
            auto_config: false
      # link for swp47 --> leaf03:swp48
      device.vm.network "private_network",
            :mac => "443839000052",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8048',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9048',
            :libvirt__iface_name => 'swp47',
            auto_config: false
      # link for swp48 --> leaf03:swp47
      device.vm.network "private_network",
            :mac => "443839000053",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9048',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8048',
            :libvirt__iface_name => 'swp48',
            auto_config: false
      # link for swp49 --> leaf04:swp49
      device.vm.network "private_network",
            :mac => "44383900002e",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8026',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9026',
            :libvirt__iface_name => 'swp49',
            auto_config: false
      # link for swp50 --> leaf04:swp50
      device.vm.network "private_network",
            :mac => "443839000005",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8003',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9003',
            :libvirt__iface_name => 'swp50',
            auto_config: false
      # link for swp51 --> spine01:swp3
      device.vm.network "private_network",
            :mac => "443839000050",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8047',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9047',
            :libvirt__iface_name => 'swp51',
            auto_config: false
      # link for swp52 --> spine02:swp3
      device.vm.network "private_network",
            :mac => "443839000019",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8014',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9014',
            :libvirt__iface_name => 'swp52',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/leaf03/interfaces", destination: "~/interfaces"
    device.vm.provision "file", source: "./config/leaf03/daemons", destination: "~/daemons"
    device.vm.provision "file", source: "./config/leaf03/Quagga.conf", destination: "~/Quagga.conf"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:13 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:13", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:22 --> swp1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:22", NAME="swp1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:29 --> swp45"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:29", NAME="swp45", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:2a --> swp46"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:2a", NAME="swp46", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:52 --> swp47"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:52", NAME="swp47", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:53 --> swp48"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:53", NAME="swp48", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:2e --> swp49"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:2e", NAME="swp49", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:05 --> swp50"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:05", NAME="swp50", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:50 --> swp51"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:50", NAME="swp51", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:19 --> swp52"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:19", NAME="swp52", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for leaf01 #####
  config.vm.define "leaf01" do |device|
    device.vm.hostname = "leaf01"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp6
      device.vm.network "private_network",
            :mac => "a00000000011",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8017',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9017',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp1 --> server01:eth1
      device.vm.network "private_network",
            :mac => "443839000004",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9002',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8002',
            :libvirt__iface_name => 'swp1',
            auto_config: false
      # link for swp45 --> leaf01:swp46
      device.vm.network "private_network",
            :mac => "44383900001b",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8015',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9015',
            :libvirt__iface_name => 'swp45',
            auto_config: false
      # link for swp46 --> leaf01:swp45
      device.vm.network "private_network",
            :mac => "44383900001c",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9015',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8015',
            :libvirt__iface_name => 'swp46',
            auto_config: false
      # link for swp47 --> leaf01:swp48
      device.vm.network "private_network",
            :mac => "443839000044",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8040',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9040',
            :libvirt__iface_name => 'swp47',
            auto_config: false
      # link for swp48 --> leaf01:swp47
      device.vm.network "private_network",
            :mac => "443839000045",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9040',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8040',
            :libvirt__iface_name => 'swp48',
            auto_config: false
      # link for swp49 --> leaf02:swp49
      device.vm.network "private_network",
            :mac => "44383900000e",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8008',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9008',
            :libvirt__iface_name => 'swp49',
            auto_config: false
      # link for swp50 --> leaf02:swp50
      device.vm.network "private_network",
            :mac => "443839000001",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8001',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9001',
            :libvirt__iface_name => 'swp50',
            auto_config: false
      # link for swp51 --> spine01:swp1
      device.vm.network "private_network",
            :mac => "443839000054",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8049',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9049',
            :libvirt__iface_name => 'swp51',
            auto_config: false
      # link for swp52 --> spine02:swp1
      device.vm.network "private_network",
            :mac => "443839000023",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8020',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9020',
            :libvirt__iface_name => 'swp52',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/leaf01/interfaces", destination: "~/interfaces"
    device.vm.provision "file", source: "./config/leaf01/daemons", destination: "~/daemons"
    device.vm.provision "file", source: "./config/leaf01/Quagga.conf", destination: "~/Quagga.conf"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:11 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:11", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:04 --> swp1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:04", NAME="swp1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:1b --> swp45"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:1b", NAME="swp45", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:1c --> swp46"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:1c", NAME="swp46", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:44 --> swp47"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:44", NAME="swp47", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:45 --> swp48"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:45", NAME="swp48", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:0e --> swp49"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:0e", NAME="swp49", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:01 --> swp50"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:01", NAME="swp50", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:54 --> swp51"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:54", NAME="swp51", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:23 --> swp52"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:23", NAME="swp52", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for site02 #####
  config.vm.define "site02" do |device|
    device.vm.hostname = "site02"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp14
      device.vm.network "private_network",
            :mac => "a00000000051",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8039',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9039',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp1 --> server05:eth1
      device.vm.network "private_network",
            :mac => "44383900003b",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9034',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8034',
            :libvirt__iface_name => 'swp1',
            auto_config: false
      # link for swp51 --> isp:swp1
      device.vm.network "private_network",
            :mac => "44383900004d",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8045',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9045',
            :libvirt__iface_name => 'swp51',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/site02/interfaces", destination: "~/interfaces"
    device.vm.provision "file", source: "./config/site02/daemons", destination: "~/daemons"
    device.vm.provision "file", source: "./config/site02/Quagga.conf", destination: "~/Quagga.conf"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:51 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:51", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:3b --> swp1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:3b", NAME="swp1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:4d --> swp51"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:4d", NAME="swp51", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for server01 #####
  config.vm.define "server01" do |device|
    device.vm.hostname = "server01"
    device.vm.box = "CumulusCommunity/cumulus-vx"

    device.vm.provider :libvirt do |v|
      v.nic_model_type = 'e1000'
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp2
      device.vm.network "private_network",
            :mac => "a00000000031",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8041',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9041',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for eth1 --> leaf01:swp1
      device.vm.network "private_network",
            :mac => "443839000003",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8002',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9002',
            :libvirt__iface_name => 'eth1',
            auto_config: false
      # link for eth2 --> leaf02:swp1
      device.vm.network "private_network",
            :mac => "443839000015",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8012',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9012',
            :libvirt__iface_name => 'eth2',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/server01/interfaces", destination: "~/interfaces"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_server.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:31 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:31", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:03 --> eth1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:03", NAME="eth1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:15 --> eth2"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:15", NAME="eth2", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for server03 #####
  config.vm.define "server03" do |device|
    device.vm.hostname = "server03"
    device.vm.box = "CumulusCommunity/cumulus-vx"

    device.vm.provider :libvirt do |v|
      v.nic_model_type = 'e1000'
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp4
      device.vm.network "private_network",
            :mac => "a00000000033",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8016',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9016',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for eth1 --> leaf03:swp1
      device.vm.network "private_network",
            :mac => "443839000021",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8019',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9019',
            :libvirt__iface_name => 'eth1',
            auto_config: false
      # link for eth2 --> leaf04:swp1
      device.vm.network "private_network",
            :mac => "44383900005f",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8055',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9055',
            :libvirt__iface_name => 'eth2',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/server03/interfaces", destination: "~/interfaces"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_server.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:33 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:33", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:21 --> eth1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:21", NAME="eth1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:5f --> eth2"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:5f", NAME="eth2", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for server05 #####
  config.vm.define "server05" do |device|
    device.vm.hostname = "server05"
    device.vm.box = "CumulusCommunity/cumulus-vx"

    device.vm.provider :libvirt do |v|
      v.nic_model_type = 'e1000'
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp17
      device.vm.network "private_network",
            :mac => "a00000000054",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8029',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9029',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for eth1 --> site02:swp1
      device.vm.network "private_network",
            :mac => "44383900003a",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8034',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9034',
            :libvirt__iface_name => 'eth1',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/server05/interfaces", destination: "~/interfaces"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_server.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:54 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:54", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:3a --> eth1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:3a", NAME="eth1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = vagrant"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="vagrant", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end

  ##### DEFINE VM for internet #####
  config.vm.define "internet" do |device|
    device.vm.hostname = "internet"
    device.vm.box = "CumulusCommunity/cumulus-vx"
    device.vm.box_version = "3.2.1"

    device.vm.provider :libvirt do |v|
      v.memory = 512
    end
    #   see note here: https://github.com/pradels/vagrant-libvirt#synced-folders
    device.vm.synced_folder ".", "/vagrant", disabled: true



    # NETWORK INTERFACES
      # link for eth0 --> oob-mgmt-switch:swp15
      device.vm.network "private_network",
            :mac => "a00000000053",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8033',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9033',
            :libvirt__iface_name => 'eth0',
            auto_config: false
      # link for swp1 --> exit01:swp44
      device.vm.network "private_network",
            :mac => "443839000007",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8004',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9004',
            :libvirt__iface_name => 'swp1',
            auto_config: false
      # link for swp2 --> exit02:swp44
      device.vm.network "private_network",
            :mac => "443839000041",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '8038',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '9038',
            :libvirt__iface_name => 'swp2',
            auto_config: false
      # link for swp47 --> isp:swp47
      device.vm.network "private_network",
            :mac => "44383900002c",
            :libvirt__tunnel_type => 'udp',
            :libvirt__tunnel_local_ip => '127.0.0.1',
            :libvirt__tunnel_local_port => '9024',
            :libvirt__tunnel_ip => '127.0.0.1',
            :libvirt__tunnel_port => '8024',
            :libvirt__iface_name => 'swp47',
            auto_config: false



    # Fixes "stdin: is not a tty" and "mesg: ttyname failed : Inappropriate ioctl for device"  messages --> https://github.com/mitchellh/vagrant/issues/1673
    device.vm.provision :shell , inline: "(grep -q 'mesg n' /root/.profile 2>/dev/null && sed -i '/mesg n/d' /root/.profile  2>/dev/null && echo 'Ignore the previous error, fixing this now...') || true;"

    # Copy over configuration files
    device.vm.provision "file", source: "./config/internet/interfaces", destination: "~/interfaces"

    # Run the Config specified in the Node Attributes
    device.vm.provision :shell , privileged: false, :inline => 'echo "$(whoami)" > /tmp/normal_user'
    device.vm.provision :shell , path: "./helper_scripts/config_switch.sh"


    # Install Rules for the interface re-map
    device.vm.provision :shell , :inline => <<-delete_udev_directory
if [ -d "/etc/udev/rules.d/70-persistent-net.rules" ]; then
    rm -rfv /etc/udev/rules.d/70-persistent-net.rules &> /dev/null
fi
delete_udev_directory

device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: a0:00:00:00:00:53 --> eth0"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="a0:00:00:00:00:53", NAME="eth0", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:07 --> swp1"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:07", NAME="swp1", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:41 --> swp2"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:41", NAME="swp2", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule
     device.vm.provision :shell , :inline => <<-udev_rule
echo "  INFO: Adding UDEV Rule: 44:38:39:00:00:2c --> swp47"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{address}=="44:38:39:00:00:2c", NAME="swp47", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
udev_rule

      device.vm.provision :shell , :inline => <<-vagrant_interface_rule
echo "  INFO: Adding UDEV Rule: Vagrant interface = swp48"
echo 'ACTION=="add", SUBSYSTEM=="net", ATTR{ifindex}=="2", NAME="swp48", SUBSYSTEMS=="pci"' >> /etc/udev/rules.d/70-persistent-net.rules
echo "#### UDEV Rules (/etc/udev/rules.d/70-persistent-net.rules) ####"
cat /etc/udev/rules.d/70-persistent-net.rules
vagrant_interface_rule

# Run Any Platform Specific Code and Apply the interface Re-map
    #   (may or may not perform a reboot depending on platform)
    device.vm.provision :shell , :inline => $script

end



end
