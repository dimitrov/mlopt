#!/usr/bin/env python2
#
# Mirror list optimizer (mlopt)
#
# Mlopt is designed to organize your mirrorlist. It fetches JSON data 
# from archlinux.org and uses that to sort your new mirror list. The *exact* 
# line you have in your mirror list will be used for writting the new list. 
#
# This program is free software: you can redistribute it and/or modify
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

import os
import time
import json
import urllib2
import argparse

from urlparse import urlparse


class MirrorListOptimizer():
    def __init__(self):
        self.mirror_list = "/etc/pacman.d/mirrorlist"
        self.mirror_list_servers = {}
        
        self.servers_total = 0

        self.complete_servers = {}
        self.incomplete_servers = {}
        self.json_data = None
        self.args = None
    
    def parse_args(self):
        parser = argparse.ArgumentParser(description=
                                         'Mirror list optimizer (mlopt)')
        
        parser.add_argument('--w', dest="write_dest", 
                            help="write servers to file")
        
        parser.add_argument('--a', dest="append", action="store_true",
                            help="append to file")
        
        parser.add_argument('--r', dest="read_from", 
                            help="read servers from path")
        
        parser.add_argument('--i', dest="show_incomplete", action="store_true",
                            help='show incomplete servers')
        
        parser.add_argument('--sort', dest="sort_method", action="store",
                            help="sort mirrorlist by score, last_sync, delay")

        parser.add_argument('--reverse', dest="sort_reverse", 
                            action="store_true", 
                            help="reverse the sorted mirrorlist")
        
        parser.add_argument('--l', dest="limit", action="store", type=int,
                            help="number of servers to show/write")

        parser.add_argument('--v', dest="verbose", action="store_true",
                            help="show more output")
        
        
        self.args = parser.parse_args()
        self.sort_method = self.args.sort_method
                
        if self.args.read_from:
            self.mirror_list = self.args.read_from

        if self.args.limit == 0:
            print "Nothing to do, limit is 0"
            exit()

        self.parse_mirror_list()
        self.get_json_data()
        self.sort_stats()
        
        if self.args.sort_method:
            self.sort_mirror_list()
        
    def print_message(self, message):
        if self.args.verbose:
            print message

    def parse_mirror_list(self):
        """Parses the mirrorlist and returns a list of servers"""        
        self.print_message("Parsing mirrorlist")        
        
        if os.path.exists(self.mirror_list):
            with open(self.mirror_list, "r") as ml:
                for line in ml:
                    line = line.strip()
                    if line.startswith("#") or line == "":
                        continue 
                    else:
                        url = urlparse(line.split()[2])
                        self.mirror_list_servers["%s://%s" % (url[0], 
                                                 url[1])] = line.split()[2]
        else:
             print "path %s does not exist" % (self.mirror_list)
             exit(1)

        self.servers_total = len(self.mirror_list_servers)
        
        if self.servers_total > 0:
            self.print_message('%s %s configured' % (self.servers_total,
                "servers" if self.servers_total > 1 else "server"))
        else:
            print "No servers configured"
            exit()
        
    def get_json_data(self):
        "Fetches JSON data from archlinux.org"
        self.print_message("Fetching mirror statistsics")

        try:
            self.json_data = json.loads(urllib2.urlopen(
                "http://www.archlinux.org/mirrors/status/json/").read())
        except Exception, e:
            print "Could not retrieve statistics, reason: %s" % (e)
            exit(1)
            
    def sort_stats(self):
        """Sorts the gathered statistics"""
        keys = []

        for key in self.mirror_list_servers.keys():
            parts = urlparse(key)
            keys.append("%s://%s" % (parts[0], parts[1]))
                    
        for segment in self.json_data["urls"]:           
            parts = urlparse(segment["url"])
            url = "%s://%s" % (parts[0], parts[1])
            
            if url in keys: 
                if segment["completion_pct"] == 1.0: 
                    self.complete_servers[url] = [segment, 
                                                  self.mirror_list_servers[url]]
                
                else:
                    self.incomplete_servers[url] = [segment, 
                                                    self.mirror_list_servers[
                                                    url]]
            
        self.print_message("%s out of %s servers are up-to-date" % 
                (len(self.complete_servers), self.servers_total))
               
    def sort_mirror_list(self):
        """Rearranges the server lists""" 
        import cStringIO

        temp = {}
        s_dict = self.complete_servers

        if self.args.show_incomplete:
            s_dict = self.incomplete_servers
                
        for server in s_dict:
            temp[s_dict[server][0][self.sort_method]] = server
        
        c_keys = temp.keys()

        if self.sort_method == "last_sync":
            c_keys.sort(reverse=True if not self.args.sort_reverse else False)
        else:
            c_keys.sort(reverse=self.args.sort_reverse)
                
        if self.args.write_dest:
            file_obj = cStringIO.StringIO()
                    
        for i, k in enumerate(c_keys):
            if self.args.limit:
                if i >= self.args.limit:
                    break

            if self.args.write_dest:
                file_obj.write("Server = %s\n" % (s_dict[temp[k]][1]))
                               
            else:
                x = s_dict[temp[k]][0]
                
                if self.sort_method == "score" and x[self.sort_method] != None:
                    print "%s: %.2f  %s" % (self.sort_method, 
                                            x[self.sort_method], 
                                            x["url"])
                else:
                    print "%s: %s %s" % (self.sort_method, x[self.sort_method], 
                                         x["url"])

        if self.args.write_dest:
            self.write_mirror_list(file_obj)
                                          
    def write_mirror_list(self, file_obj):
        """Writes the new mirrorlist to file or stdout"""        
        if self.args.write_dest == "-":
            for line in file_obj.getvalue().splitlines():
                print line
        else:                
            message, mode = "Appending", "a" 
            
            if not self.args.append:
                message, mode = "Writing", "w"

            self.print_message("%s to %s" % (message, self.args.write_dest))

            with open(self.args.write_dest, mode) as ml:
                ml.write(file_obj.getvalue())
                
        file_obj.close()
        self.print_message("Done")
            
                
if __name__ == "__main__":
    optimizer = MirrorListOptimizer()
    optimizer.parse_args()
