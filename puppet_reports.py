#!/usr/bin/env python

import collectd
import yaml
import os

NAME = 'puppet_reports'


def compute_log_metrics(data):
  return {'log_info': len(filter(lambda x: safe_get(x, ['level'], '') == 'info', data)),
          'log_notice': len(filter(lambda x: safe_get(x, ['level'], '') == 'notice', data)),
          'log_warning': len(filter(lambda x: safe_get(x, ['level'], '') == 'warning', data)),
          'log_error': len(filter(lambda x: safe_get(x, ['level'], '') == 'error', data))}

def tridict(prefix, data):
  dicts = map(lambda x: {(prefix + '_' + x[0]): x[2]}, data)
  return reduce(lambda x,y: dict(x, **y), dicts, {})

def safe_get(data, path, default):
  res = data
  for el in path:
    if res.has_key(el):
      res = res[el]
    else:
      return default
  return res
  
def compute_metrics(data):
  h = {}
  h.update(compute_log_metrics(safe_get(data, ['logs'], [])))
  h.update(tridict('changes', safe_get(data, ['metrics', 'changes', 'values'], {})))
  h.update(tridict('events', safe_get(data, ['metrics', 'events', 'values'], {})))
  h.update(tridict('resources', safe_get(data, ['metrics', 'resources', 'values'], {})))
  h.update(tridict('time', safe_get(data, ['metrics', 'time', 'values'], {})))
  return h

def identity(loader, suffix, node):
  return node

def map_value(node):
  if isinstance(node,yaml.nodes.MappingNode):
    dicts = map(lambda x: dict({map_value(x[0]): map_value(x[1])}), node.value)
    h = reduce(lambda e1,e2: dict(e1, **e2), dicts, {})
    return h
  elif isinstance(node,yaml.nodes.SequenceNode):
    return map(map_value, node.value)
  elif isinstance(node,yaml.nodes.ScalarNode):
    return node.value
  elif isinstance(node,list):
    return map(map_value, node)
  elif isinstance(node,tuple):
    return map(map_value, node)
  else:
    return node

class PuppetReports:
  
  def __init__(self):
      self.report_file = '/var/lib/puppet/state/last_run_report.yaml'
      self.last_report_file_mtime = 0
      self.verbose = False
      
  def read_callback(self):
    yaml.add_multi_constructor("!", identity)
    self.logger('verb', "parsing: %s" % self.report_file)
    
    time = os.path.getmtime(self.report_file)
    if time != self.last_report_file_mtime:
      with open(self.report_file, "r") as stream:
        self.last_report_file_mtime = time
        data = yaml.load(stream)
        data = map_value(data)
        results = compute_metrics(data)
        self.logger('verb', "ready to send")
        for k in results:
          self.logger('verb', ("pushing value for %s => %s = %s" % (self.report_file, k, results[k])))
          val = collectd.Values(plugin=NAME, type='gauge')
          val.plugin_instance = 'last_run'
          val.type_instance = k
          #metric time is the mtime of the file which should match when puppet ran last
          val.time = time
          try:
            val.values = [ float(results[k]) ]
          except:
            self.logger('warn', ("value %s => %s for %s cannot be parsed to float" % (k, results[k], self.report_file)))
            val.values = [ 0.0 ]
          val.dispatch()
      
  
  def configure_callback(self, conf):
    yaml.add_multi_constructor("!", identity)
    self.logger('verb', "configuring")
  
    for node in conf.children:
      if node.key == 'LastReportFile':
        self.report_file = node.values[0]
      elif node.key == 'Verbose':
        self.verbose = node.values[0]
      else:
        self.logger('verb', "unknown config key in puppet module: %s" % node.key)
      
  # logging function
  def logger(self, t, msg):
    if t == 'err':
        collectd.error('%s: %s' % (NAME, msg))
    elif t == 'warn':
        collectd.warning('%s: %s' % (NAME, msg))
    elif t == 'verb':
        if self.verbose:
            collectd.info('%s: %s' % (NAME, msg))
    else:
        collectd.notice('%s: %s' % (NAME, msg))

reports = PuppetReports()
collectd.register_config(reports.configure_callback)
collectd.register_read(reports.read_callback)

