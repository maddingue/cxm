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


import time
from xen.xm import main
import node, core

class Metrics:

	"""This class is used to retrieve metrics of its node and vms."""

	def __init__(self, node):
		"""Instanciate new metrics associated with the given node."""
		self.node=node
		self.server=node.server

		# Initialize cpu_cache
		self.cpu_cache={'timestamp': time.time()}

		# Initialize io_cache
		self.io_cache={'timestamp': time.time()}

	def init_cache(self):
		"""
		Initialize the cache for rate computation.

		If you don't call this function, the first call of get_vms_cpu_usage() and 
		get_vms_disk_io_rate() will return dict with zero values.
		"""
		# First call to feed cache with current value
		self.get_vms_cpu_usage() 
		self.get_vms_disk_io_rate()

	def __repr__(self):
		return "<Metrics Instance : "+ self.node.hostname +">"

	def get_host_nr_cpus(self):
		"""Return the number of CPU on the host."""
		host_record = self.server.xenapi.host.get_record(self.server.xenapi.session.get_this_host(self.server.getSession()))
		if core.cfg['DEBUG']: print "DEBUG Xen-Api: ", host_record
		return host_record['cpu_configuration']['nr_cpus']

	def get_vms_cpu_usage(self):
		"""
		Return a dict with the computed CPU usage for all runing VMs.

		Values are floats with 16 digit of precision (python standard's binary float)
		If you want a string with less precision, you can use "%.1f" % round(xxx).
		If you want a number with less precision, you can use the Decimal module.
		"""
		cpu=dict()

		# Get domains' infos
		doms=self.node.legacy_server.xend.domains(True)
		if core.cfg['DEBUG']: print "DEBUG Legacy-Api: ", doms

		# Timestamp used to compute CPU percentage
		timestamp=time.time()

		for dom in doms:
			dom_info=main.parse_doms_info(dom)

			try:
				# String version with one digit after dot
				# See http://stackoverflow.com/questions/56820/round-in-python-doesnt-seem-to-be-rounding-properly for reasons.
				#cpu[dom_info['name']]="%.1f" % round(
				#	(dom_info['cpu_time']-self.cpu_cache[dom_info['name']])*100/(timestamp-self.cpu_cache['timestamp']),1
				#)
				cpu[dom_info['name']]=(dom_info['cpu_time']-self.cpu_cache[dom_info['name']])*100/(timestamp-self.cpu_cache['timestamp'])

			except KeyError: # First call: return zero values
				cpu[dom_info['name']]=0
			except ZeroDivisionError:
				cpu[dom_info['name']]=0

			# Update cpu_cache with the new value
			self.cpu_cache[dom_info['name']]=dom_info['cpu_time']

		# Update timestamp
		self.cpu_cache['timestamp']=timestamp

		return cpu

	def get_vms_disk_io(self,dom_recs=None):
		"""Return a dict with disks'IO stats for all runing VMs (including Dom0)."""
		if not dom_recs: dom_recs = self.server.xenapi.VM.get_all_records()

		io=dict()
		for dom_rec in dom_recs.values():
			io_read=[ int(val) for val in \
				self.node.run("cat /sys/bus/xen-backend/devices/vbd-" + dom_rec['domid'] + "-*/statistics/rd_req 2>/dev/null").readlines() ]
			io_write=[ int(val) for val in \
				self.node.run("cat /sys/bus/xen-backend/devices/vbd-" + dom_rec['domid'] + "-*/statistics/wr_req 2>/dev/null").readlines() ]
			io[dom_rec['name_label']]={ 'Read': sum(io_read), 'Write': sum(io_write) }
		return io

	def get_vms_disk_io_rate(self,dom_recs=None):
		"""Return a dict with disks'IO bandwith (ie. IO/s) for all runing VMs."""
		io_rate=dict()

		# Timestamp used to compute per second rate
		timestamp=time.time()

		io=self.get_vms_disk_io(dom_recs)
		for vm in io.keys():
			io_rate[vm]=dict()
			try:
				# Compute io rate
				io_rate[vm]['Read']=int((io[vm]['Read']-self.io_cache[vm]['Read'])/(timestamp-self.io_cache['timestamp']))
				io_rate[vm]['Write']=int((io[vm]['Write']-self.io_cache[vm]['Write'])/(timestamp-self.io_cache['timestamp']))

			except KeyError: # First call
				# Initialize io_cache with the current value
				self.io_cache[vm]={'Read': io[vm]['Read'], 'Write': io[vm]['Write']}

				# Return zero values for the first call
				io_rate[vm]['Read']=0
				io_rate[vm]['Write']=0

			except ZeroDivisionError:
				io_rate[vm]['Read']=0
				io_rate[vm]['Write']=0

			# Update io_cache with the current value
			self.io_cache[vm]['Read']=io[vm]['Read']
			self.io_cache[vm]['Write']=io[vm]['Write']

		# Update timestamp of cached values
		self.io_cache['timestamp']=timestamp

		return io_rate

	def get_vms_net_io(self,dom_recs=None):
		"""Return a dict with network IO stats for all runing VMs."""
		if not dom_recs: dom_recs = self.server.xenapi.VM.get_all_records()

		vif_metrics_recs = self.server.xenapi.VIF_metrics.get_all_records()
		if core.cfg['DEBUG']: print "DEBUG Xen-Api: ", vif_metrics_recs

		vifs_doms_metrics=dict()
		for dom_rec in dom_recs.values():
			vifs_metrics=list()
			for vif in dom_rec['VIFs']:
				vifs_metrics.append({
					'Rx': int(float(vif_metrics_recs[vif]['io_total_read_kbs'])*1024),
					'Tx': int(float(vif_metrics_recs[vif]['io_total_write_kbs'])*1024)
				})
			vifs_doms_metrics[dom_rec['name_label']]= vifs_metrics

		return vifs_doms_metrics

	def get_host_net_io(self):
		"""Return a dict with network IO stats for the host."""
		bridges=self.node.get_bridges()
		vlans=self.node.get_vlans()
		io= { 'bridges': dict(), 'vlans': dict() }

		for line in self.node.run('cat /proc/net/dev').readlines():
			stats=line.replace(':',' ').strip().split()
			if stats[0] in bridges:
				io['bridges'][stats[0]]= {'Rx': stats[1], 'Tx': stats[9]}
			if stats[0] in vlans:
				io['vlans'][stats[0]]= {'Rx': stats[1], 'Tx': stats[9]}
		return io

	def get_host_pvs_io(self):
		"""Return a dict with PVs'IO stats for the host."""
		io=dict()

		devices=[ dev.strip().lstrip("/dev/") for dev in self.node.run("pvs -o pv_name --noheadings").readlines() ]
		for line in self.node.run('cat /proc/diskstats').readlines():
			stats=line.strip().split()
			if stats[2] in devices:
				"""
				Struct of file /proc/diskstats :

						Field 3 -- # of reads issued
						Field 4 -- # of reads merged
						Field 5 -- # of sectors read
						Field 6 -- # of milliseconds spent reading
						Field 7 -- # of writes completed
						Field 8 -- # of writes merged
						Field 9 -- # of sectors written
						Field 10 -- # of milliseconds spent writing
						Field 11 -- # of I/Os currently in progress
						Field 12 -- # of milliseconds spent doing I/Os
						Field 13 -- weighted # of milliseconds spent doing I/Os 
				"""
				io[stats[2]]= { 'Read': int(stats[3]), 'Write': int(stats[7]) }

		return io

	def get_host_vgs_io(self):
		"""Return a dict with VGs'IO stats for the host."""
		io=dict()

		pvs_io=self.get_host_pvs_io()
		vgs_map=self.node.get_vgs_map()

		for vg, pvs in  vgs_map.iteritems():
			io[vg]={'Read': 0, 'Write': 0}
			for pv in pvs:
				io[vg]['Read'] += pvs_io[pv]['Read']
				io[vg]['Write'] += pvs_io[pv]['Write']

		return io

	def get_vms_record(self):
		"""Return a tree with CPU, disks'IO and network IO for all running VMs."""
		dom_recs = self.server.xenapi.VM.get_all_records()
		if core.cfg['DEBUG']: print "DEBUG Xen-Api: ", dom_recs
		
		# Fetch all datas once
		vms_cpu=self.get_vms_cpu_usage()
		vms_net_io=self.get_vms_net_io(dom_recs)
		vms_disk_io=self.get_vms_disk_io(dom_recs)

		vms_record=dict()
		for vm in vms_net_io.keys():
			vms_record[vm]=dict()
			vms_record[vm]['disk']=vms_disk_io[vm]
			vms_record[vm]['cpu']=vms_cpu[vm]
			vms_record[vm]['net']=vms_net_io[vm]

		return vms_record

	def get_used_irq(self):
		"""Return the number of used irq on this node."""
		return int(self.node.run('grep Dynamic /proc/interrupts | wc -l').read())

	def get_free_ram(self):
		"""Return the amount of free ram of this node."""
		return self.get_ram_infos()['free']

	def get_total_ram(self):
		"""Return the amount of ram of this node (including Dom0 and Hypervisor)."""
		return self.get_ram_infos()['total']

	def get_used_ram(self):
		"""Return the amount of used ram (including Dom0 and Hypervisor) of this node."""
		return self.get_ram_infos()['used']

	def get_ram_infos(self):
		"""Return a dict with the free, used, and total ram of this node."""
		# TODO add a cache
		if core.cfg['USESSH']:
			vals=map(int, self.node.run('xm info | grep -E total_memory\|free_memory | cut -d: -f 2').read().strip().split())
			return { 'total':vals[0], 'free':vals[1], 'used':vals[0]-vals[1] }
		else:
			host_record = self.server.xenapi.host.get_record(self.server.xenapi.session.get_this_host(self.server.getSession()))
			host_metrics_record = self.server.xenapi.host_metrics.get_record(host_record["metrics"])
			if core.cfg['DEBUG']: print "DEBUG Xen-Api: ", host_metrics_record

			total=int(host_metrics_record["memory_total"])/1024/1024
			free=int(host_metrics_record["memory_free"])/1024/1024

			return { 'total': total, 'free':free, 'used':total-free }

	def get_available_ram(self, vms=None):
		"""Return the amount of really available ram (for VM usage, excluding Dom0 and Hypervisor) of this node."""
		if not vms: vms = self.node.get_vms() # Get all vm running on this node

		# Compute amount of ram used by VMs
		used_ram = sum(map(lambda x: x.get_ram(), vms))

		# Return really available ram for VM
		return self.get_free_ram() + used_ram

	def get_load(self):
		"""Return the load of this node.

		The load is in percentage and computed from free RAM and free IRQs.
		"""
		MAX_IRQ=1024 # Defined by RedHat patch (bz #442736) since 2.6.18

		# Compute IRQ load
		irq_load=(self.get_used_irq()*100)/MAX_IRQ

		# Compute RAM load
		ram=self.get_ram_infos()
		ram_load=(ram['used']*100)/ram['total']

		# Return the higher
		return (irq_load<ram_load and ram_load or irq_load)

	def get_lvs_size(self, lvs):
		"""Return a dict containnig size (in kilobytes) of each specified LVs."""

		if len(lvs)<=0:
			return dict() # empty return if no LV given 

		size=dict()
		for line in self.node.run("lvs -o vg_name,lv_name,lv_size --noheading --units k --nosuffix " + " ".join(lvs)).readlines():
			infos=line.strip().split()
			lv_name="/dev/" + infos[0] + "/" + infos[1]

			if lv_name in lvs:  # In case of output error, don't feed with scrappy data
				size[lv_name]=float(infos[2])

		return size

# vim: ts=4:sw=4:ai

