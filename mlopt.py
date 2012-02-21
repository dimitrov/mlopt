#!/usr/bin/env python2


#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.



# Sorts servers for the pacman mirrorlist. 

# Todo 
# Sort servers by score, 
# Sort by speed
# Query server last_sync, num_checks, check_frequency, cutoff, protocol, completion_pct


import urllib2
import json
import os
import argparse
from urlparse import urlparse


class Update_ML():
    def __init__(self):
        self.ml_path = "/etc/pacman.d/mirrorlist"
        self.ml_raw = None
        self.ml_sorted = None
        self.ml_servers = {}
        self.ml_servers_len = 0
        self.complete_servers = {}
        self.incomplete_servers = {}
        self.json_stats = None
        self.args = None
    
    def parse_args(self):
        p = argparse.ArgumentParser(description='Mirror list optimizer (mlopt)')
        
        p.add_argument('--w', dest="write_dest", help="write to path")
        
        p.add_argument('--i', dest="show_incomplete", action="store_true",
                       help='show incomplete servers')
        
        p.add_argument('--v', dest="verbose", action="store_true",
                       help="show more output")
        
        
        self.args = p.parse_args()
        
    
    def msg(self, msg):
        if self.args.verbose:
            print msg

    def exists(self, path):
        if os.path.exists(path):
            return 1
        
        return 0

    def parse_ml(self, path):
        """Parses the mirrorlist and returns a 
        list with the servers"""
        
        self.msg("Parsing mirrorlist")        
        
        if self.exists(path):
            with open(path, "r") as ml:
                self.ml_raw = ml.read().splitlines()
                
        for line in self.ml_raw:
            if line.startswith("#") or line == "":
                continue 

            else:
                self.ml_servers[urlparse(line.split()[2])[1]] = line.split()[2]

        self.ml_servers_len = len(self.ml_servers)
        
        self.msg("%s servers configured" % (self.ml_servers_len))

    

        
    def get_stats(self):
        """Gets the remote server statistics"""

        self.msg("Fetching mirror statistsics")

        try:
            self.json_stats = json.loads(urllib2.urlopen("http://www.archlinux.org/mirrors/status/json/").read())

        except Exception, e:
            print "Could not retrieve statistics, reason: %s" % (e)
            exit(1)

            

    def sort_ml(self):
        """Sorts the parsed mirrorlist"""     
    
        self.get_stats()

        for segment in self.json_stats["urls"]:
            
            segment_url = segment["url"]
            server_url = urlparse(segment["url"])[1]
            
            # Compare the servers from the mirrorlist
            # to the server stats
            if server_url in self.ml_servers.keys():
                
                # Check to see if its complete 
                if segment["completion_pct"] == 1.0:
                    
                    # If so, store the info 
                    self.complete_servers[server_url] = [segment, self.ml_servers[server_url]]
                else:
                    self.incomplete_servers[server_url] = [segment, self.ml_servers[server_url]]

        self.msg("%s out of %s servers are up-to-date" % (len(self.complete_servers), self.ml_servers_len))
        
        if self.args.show_incomplete:
            print "%s servers incomplete" % (len(self.incomplete_servers))
            
            for server in self.incomplete_servers:
                s = self.incomplete_servers[server]
                print "percent: %.2f server: %s" % (s["completion_pct"], s["url"])
        


    def write_ml(self, path):
        """Writes the new mirrorlist to file or stdout"""
        
        if path == "-":
            for l in self.complete_servers:
                print "Server = %s" % (self.complete_servers[l][1])

        else:
            with open(path, "w") as to_write:
                
                for l in self.complete_servers:
                    to_write.write("Server = %s\n" % (self.complete_servers[l][1]))
                    
        
    
    def update(self):
        self.parse_ml(self.ml_path)
        self.sort_ml()
        
        if self.args.write_dest:
            
            self.write_ml(self.args.write_dest)
            

    
if __name__ == "__main__":
    ml = Update_ML()
    ml.parse_args()
    ml.update()


