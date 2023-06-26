#!/usr/bin/env python3

import dbus
import subprocess # for remounting drive

def remount_ro(mountpoint='/'):
    subprocess.call('/bin/mount -o remount,ro {}'.format(mountpoint), shell=True)
    return

def remount_rw(mountpoint='/'):
    subprocess.call('/bin/mount -o remount,rw {}'.format(mountpoint), shell=True)
    return

class systemd_control(object):
    def __init__(self):
        self.sysbus = dbus.SystemBus()
        self.systemd1 = self.sysbus.get_object('org.freedesktop.systemd1',
                                               '/org/freedesktop/systemd1')
        self.manager = dbus.Interface(self.systemd1, 'org.freedesktop.systemd1.Manager')
        return

    def enable(self, unit_file_list):
        remount_rw('/')
        # has to be a list!
        try:
            job = self.manager.EnableUnitFiles(unit_file_list, False, False)
        except Exception as e:
            print('Failed to enable job: {}'.format(unit_file_list))
            print(e)
            remount_ro('/')
            return False
        remount_ro('/')
        print('OOT_start.py:systemd:enable:  Enabled: {}'.format(unit_file_list))
        return True

    def disable(self, unit_file_list):
        remount_rw('/')
        try:
            job = self.manager.DisableUnitFiles(unit_file_list, False)
        except Exception as e:
            print('Failed to disable job: {}'.format(unit_file_list))
            print(e)
            remount_ro('/')
            return False
        remount_ro('/')
        print('OOT_start.py:systemd:disable:  Disabled: {}'.format(unit_file_list))
        return True

    def start(self, unit_file):
        try:
            job = self.manager.StartUnit(unit_file, 'replace')
        except Exception as e:
            print('Failed to start job: {}'.format(unit_file))
            print(e)
            return False
        print('OOT_start.py:systemd:start:  Started: {}'.format(unit_file))
        return

    def stop(self, unit_file):
        try:
            job = self.manager.StopUnit(unit_file, 'replace')
        except Exception as e:
            print('Failed to stop job: {}'.format(unit_file))
            print(e)
            return False
        print('OOT_start.py:systemd:stop:  Stopped: {}'.format(unit_file))
        return

    def status(self, unit_file):
        unit = self.manager.GetUnit(unit_file)
        proxy = self.sysbus.get_object('org.freedesktop.systemd1', str(unit))
        service = dbus.Interface(proxy, dbus_interface='org.freedesktop.systemd1.Unit')
        state = proxy.Get('org.freedesktop.systemd1.Unit', 'ActiveState', dbus_interface='org.freedesktop.DBus.Properties')
        return str(state) # 'active', 'inactive'
    
    def running(self, unit_file):
        return self.status(unit_file) == 'active'

