#!/usr/bin/env python

import codecs
import collections
import csv
import google
import gzip
import json
import operator
import pkg_resources
import random
import re
import requests
import sys
import time
#import urllib2
import xmltodict


# make random REALLY random.
seed = random.SystemRandom().random()
random.seed(seed)

# Trim out LinkedIn and RateMyProfessors sites, etc.
trimstrings = ['\.php\?', 'youtube', 'researchgate', 'dblp.uni-trier.','ratemyprofessors.com', 'linkedin.com', 'wikipedia.org','2018','2017','2016','2015','\.pdf','wikipedia']


def find_fix(name,affiliation):
    string = name + ' ' + affiliation
    results = google.search(string, stop=1)
    actualURL = "http://csrankings.org"
    for url in results:
        actualURL = url
        matched = 0
        for t in trimstrings:
            match = re.search(t, url)
            if (match != None):
                matched = matched + 1
        if (matched == 0):
            break
                        
    # Output the name and this resolved URL.
    match = re.search('www.google.com', actualURL)
    if (match == None):
        return actualURL
    else:
        return "http://csrankings.org"

#print(find_fix("Michael H. Albert","University of Otago"))

# sys.exit()


# Load alias lists (name -> [aliases])
aliases = {}
aliasToName = {}
with open('dblp-aliases.csv', mode='r') as infile:
    reader = csv.DictReader(infile)
    for row in reader:
        if row['name'] in aliases:
            aliases[row['name']].append(row['alias'])
        else:
            aliases[row['name']] = [row['alias']]
        aliasToName[row['alias']] = row['name']

# Read in CSrankings file.
csrankings = {}
with open('csrankings.csv', mode='r') as infile:
    reader = csv.DictReader(infile)
    for row in reader:
        csrankings[row['name']] = { 'affiliation' : row['affiliation'],
                                    'homepage'    : row['homepage'],
                                    'scholarid'   : row['scholarid'] }

# Add any missing aliases.
for name in aliases:
    if name in csrankings:
        # Make sure all aliases are there.
        for a in aliases[name]:
            # Add any missing aliases.
            if not a in csrankings:
                # print("Missing "+a+"\n")
                csrankings[a] = csrankings[name]
    else:
        # There might be a name that isn't there but an alias that IS. If so, add the name.
        for a in aliases[name]:
            if a in csrankings:
                csrankings[name] = csrankings[a]
                break

# Correct any missing scholar pages.
for name in csrankings:
    if csrankings[name]['scholarid'] == 'NOSCHOLARPAGE':
        page = "NOSCHOLARPAGE"
        if name in aliases:
            for a in aliases[name]:
                if csrankings[a]['scholarid'] != 'NOSCHOLARPAGE':
                    page = csrankings[a]['scholarid']
        if name in aliasToName:
            if csrankings[aliasToName[name]] != 'NOSCHOLARPAGE':
                page = csrankings[aliasToName[name]]['scholarid']
                
        if page != "NOSCHOLARPAGE":
            csrankings[name]['scholarid'] = page

# Look up web sites. If we get a 404 or similar, disable the homepage for now.

ks = list(csrankings.keys())
random.shuffle(ks)

count = 0

for name in ks:
    count = count + 1
    if count > 75:
        break
    page = csrankings[name]['homepage']
    if page == "http://csrankings.org":
        # Placeholder page.
        # Try to fix it.
        print("SEARCHING NOW FOR FIX FOR "+name)
        actualURL = find_fix(name, csrankings[name]['affiliation'])
        print("changed to "+actualURL)
        csrankings[name]['homepage'] = actualURL
        continue
    
    try:
        r = requests.head(page,allow_redirects=True)
        print(r.status_code)
        if (r.status_code == 404):
            failure = True
            # prints the int of the status code. Find more at httpstatusrappers.com :)
            print("SEARCHING NOW FOR FIX FOR "+name)
            actualURL = find_fix(name, csrankings[name]['affiliation'])
            print("changed to "+actualURL)
            csrankings[name]['homepage'] = actualURL
            continue
        if (r.status_code == 301):
            failure = False
            print("redirect: changing home page to "+r.url)
            csrankings[name]['homepage'] = r.url
            continue
            # Forward
            
    except requests.ConnectionError:
        failure = False
        print("failed to connect")
    except:
        print("got me")
        failure = False


# Now rewrite csrankings.csv.

csrankings = collections.OrderedDict(sorted(csrankings.items(), key=lambda t: t[0]))
with open('csrankings.csv', mode='w') as outfile:
    sfieldnames = ['name', 'affiliation', 'homepage', 'scholarid']
    swriter = csv.DictWriter(outfile, fieldnames=sfieldnames)
    swriter.writeheader()
    for n in csrankings:
        h = { 'name' : n,
              'affiliation' : csrankings[n]['affiliation'],
              'homepage'    : csrankings[n]['homepage'].rstrip('/'),
              'scholarid'   : csrankings[n]['scholarid'] }
        swriter.writerow(h)
        
