># collectd-puppet-reports

collectd module to gather metrics from the puppet last_run_report.yaml file.
The script checks the modified time on the file each time it runs and reports 
the metrics if the modified time changes.  Metrics are reported using the modified
time of the file so the data points represent the last run of puppet.

## Prerequisite

* A collectd installation with python support
* The python pyyaml library installed
* Puppet agents with reporting enabled

## Configuration

```

LoadPlugin python

<Plugin python>
  <Module puppet_reports>
    LastReportFile "/var/lib/puppet/state/last_run_report.yaml"
    Verbose False
  </Module>
</Plugin>
```
	
