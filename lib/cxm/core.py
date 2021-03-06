#!/usr/bin/python
#-*- coding:Utf-8 -*-

# cxm - Clustered Xen Management API and tools
# Copyleft 2010 - Nicolas AGIUS <nagius@astek.fr>
# $Id:$

###########################################################################
#
# This file is part of cxm.
#
# cxm is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###########################################################################

# Note that some part of code came from xen/xm

# TODO snapshot
# TODO Add a cache to metrics.get_ram_infos() ?
# Formaliser documentation des fonctions


"""
This package provides an oriented object API for managing Xen Cluster.

Main classes are :
  - XenCluster : object used to do cluster wide actions
  - Node : object used to manipulate a cluster's node
  - VM : object used to access VM properties and configuration
  - Metrics : object used to get node's metrics

Some method could raise ClusterError and ClusterNodeError exceptions.

This package require Xen's modules xen/xm for XenAPI access 
and paramiko module for SSH links.

Some globals variables are avalaibles in the configuration file "/etc/xen/cxm.conf" 
to change the behavior of this package :

 - DEBUG (bool) : Print additionnals informations about internals datas.
 - QUIET (bool) : Just print essentials outpouts (usefull for batch parsing).
 - USESSH (bool) : Don't use the XenAPI, send (mostly) all command via SSH.
 - NOREFRESH (bool) : Don't refresh LVM metadatas (DANGEROUS).
 - VMCONF_DIR (string) : Path to find the VM's configurations files.
 - PATH (string) : Default path to find extern binaries (Only usefull for testing).
 - LB_MAX_VM_PER_NODE (int) : Maximum number of VM on each node (used by loadbalancer). 
 - LB_MAX_LAYER (int) : Maximum number of migration allowed for the loadbalancer.
 - LB_MIN_GAIN (int) : % minimun gain of selected solution by the loadbalancer.

"""

import os, sys


VERSION="0.6.1"

# Default configuration
cfg = { 
	'VMCONF_DIR' :"/etc/xen/vm/",
	'PATH': "",
	'NOREFRESH': False,
	'DEBUG': False,
	'QUIET': False,
	'USESSH': False,
	'LB_MAX_VM_PER_NODE': 20,
	'LB_MAX_LAYER': 4,
	'LB_MIN_GAIN': 5,
	}


#@staticmethod
def get_nodes_list():
	"""Return the list of actives nodes' hostname used to instanciate the cluster."""
	for line in os.popen(cfg['PATH'] + "mounted.ocfs2 -f"):
		if "ocfs2" in line:
			nodes=line.replace(","," ").split()
			del nodes[0:2]  # Purge unwanted text
			return nodes

#@staticmethod 
#def get_nodes_list(): # bouchon pour test
#   return ['xen0node03.virt.s1.p.fti.net','xen0node01.virt.s1.p.fti.net','xen0node02.virt.s1.p.fti.net']

def get_api_version():
	"""Return the version number of this API."""
	return VERSION

def load_cfg():
	"""Load the global configuration file into the cfg dict."""
	try:
		execfile("/etc/xen/cxm.conf",dict(),cfg)
	except Exception,e:
		print "Configuration file error: %s" % e
		sys.exit(3)

if __name__ == "__main__":
	pass

# vim: ts=4:sw=4:ai
