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
#
# =Todo= 
# Sort servers by score, speed 
# Query server last_sync, num_checks, check_frequency, cutoff, completion_pct
#
# Read from file, then write to another
# 

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
        
        self.s_total_len = 0
        self.s_complete_len = 0
        self.s_incomplete_len = 0


        self.complete_servers = {}
        self.incomplete_servers = {}
        self.json_stats = None
        self.args = None
    
    def parse_args(self):
        p = argparse.ArgumentParser(description='Mirror list optimizer (mlopt)')
        
        p.add_argument('--w', dest="write_dest", help="write servers to file")
        
        p.add_argument('--a', dest="append", action="store_true",
                       help="append to file")
        
        p.add_argument('--r', dest="read_from", help="read servers from path")
        
        p.add_argument('--i', dest="show_incomplete", action="store_true",
                       help='show incomplete servers')
        
        p.add_argument('--sort', dest="sort_method", action="store",
                       help="sort mirrorlist by score, last_sync, delay")

        
        p.add_argument('--v', dest="verbose", action="store_true",
                       help="show more output")
        
        
        self.args = p.parse_args()
            
        # Make things easier
        self.method = self.args.sort_method
                
        # Change the default mirrorlist path if specified
        if self.args.read_from:
            self.ml_path = self.args.read_from

        # Start it
        self.parse_ml()
        self.get_stats()
        self.sort_stats()
        
        if self.args.sort_method:
            self.sort_ml()
        

    def msg(self, msg):
        if self.args.verbose:
            print msg


    def exists(self, path, exit_if_false=True):
        
        if os.path.exists(path):
            return 1
        else:
            if exit_if_false:
                print "path %s does not exist" % (path)
                exit(1)
            
            return 0

    def parse_ml(self):
        """Parses the mirrorlist and returns a 
        list with the servers"""
        
        self.msg("Parsing mirrorlist")        
        
        
        if self.exists(self.ml_path):
            with open(self.ml_path, "r") as ml:
                self.ml_raw = ml.read().splitlines()
                
        for line in self.ml_raw:
            if line.startswith("#") or line == "":
                continue 

            else:
                url = urlparse(line.split()[2])
                self.ml_servers["%s://%s" % (url[0], url[1])] = line.split()[2]


        self.s_total_len = len(self.ml_servers)
        
        # Tell the user the total
        if self.s_total_len == 0:
            print "No servers configured"
            exit()
    
        elif self.s_total_len == 1:
            self.msg("1 server configured")
        
        else:
            self.msg("%s servers configured" % (self.s_total_len))
        



    def get_stats(self):
        """Gets the remote server statistics"""

        self.msg("Fetching mirror statistsics")

        try:
            self.json_stats = json.loads(urllib2.urlopen("http://www.archlinux.org/mirrors/status/json/").read())

        except Exception, e:
            print "Could not retrieve statistics, reason: %s" % (e)
            exit(1)


            

    def sort_stats(self):
        """Sorts the gathered statistics"""     

        keys = []

        # Reconstruct the urls from the mirrorlist
        # so we can compare them later
        for key in self.ml_servers.keys():
            a = urlparse(key)
            keys.append("%s://%s" % (a[0], a[1]))
            
        
        for segment in self.json_stats["urls"]:
            
            p_url = urlparse(segment["url"])

            url = "%s://%s" % (p_url[0], p_url[1])
            

            if url in keys:
                # Check to see if its complete 
                if segment["completion_pct"] == 1.0: 

                    # If so, store the info 
                    self.complete_servers[url] = [segment, self.ml_servers[url]]
                
                else:
                    self.incomplete_servers[url] = [segment, self.ml_servers[url]]

                    
        self.msg("%s out of %s servers are up-to-date" % (len(self.complete_servers), self.s_total_len))
        
        
    def sort_ml(self):
        """Rearranges the server lists"""

        # Pulls info from dictionaries, sorts them, then puts 
        # them into a file_obj (cStringIO)
        
        import cStringIO

        temp = {}
        final_ml = []
        reverse = []
        
        if self.args.show_incomplete:
            s_dict = self.incomplete_servers

        else:
            s_dict = self.complete_servers
        
        for server in s_dict:
            # Grabs the method from the complete servers and assigns 
            # server to it, for easy indexing later 
            temp[s_dict[server][0][self.method]] = server


        # Sort the keys, the keys are the *method*
        # Sorted() returns list in place
        # so I make a copy
        c_keys = temp.keys()
        c_keys = sorted(c_keys)
            
        # Grab the full server from the server dictionary
        # and build a list with it
        for k in c_keys:
            final_ml.insert(0, s_dict[temp[k]][1])
                
        # Reverse it if needed    
        if self.method in reverse:
            
            print final_ml.reverse()
        
        # Create the file_obj only if needed. 
        if self.args.write_dest:
            file_obj = cStringIO.StringIO()
        
        # Now iterate and print the sorted list
        for k in c_keys:
            
            if self.args.write_dest:
                file_obj.write("Server = %s\n" % (s_dict[temp[k]][1]))
                               
            else:
                x = s_dict[temp[k]][0]
                

                if self.method == "score" and x[self.method] != None:
                    print "%s: %.2f  %s" % (self.method, 
                                                    x[self.method],
                                                    x["url"])
                else:
                    print "%s: %s %s" % (self.method,
                                                  x[self.method],
                                                  x["url"])
                                  
        if self.args.write_dest:
            self.write_ml(file_obj)
                                   
        
    def write_ml(self, file_obj):
        """Writes the new mirrorlist to file or stdout"""        

        # If the user wants to write to stdout
        if self.args.write_dest == "-":
            for line in file_obj.getvalue().splitlines():
                print line
        
        # Otherwise write to file
        else:                
            if self.args.append:
                o_msg  = "Appending"
                o_mode = "a"

            else:
                o_msg = "Writting"
                o_mode = "w"

            self.msg("%s to %s" % (o_msg, self.args.write_dest))

            with open(self.args.write_dest, o_mode) as ml:
                ml.write(file_obj.getvalue())
                
        file_obj.close()

        self.msg("Done")
            
    
            
if __name__ == "__main__":
    ml = Update_ML()
    ml.parse_args()
    


