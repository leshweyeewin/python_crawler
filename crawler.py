from bs4 import BeautifulSoup

import requests
import sys
import csv
import time

amazon_format = "https://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%3Daps&field-keywords="
ebay_format = "http://www.ebay.com/sch/i.html?_from=R40&_trksid=m570.l1313&_nkw=%s&_sacat=0"

def parse_url(url):
    r  = requests.get(url)
    data = r.text
    soup = BeautifulSoup(data)

    protocol = (url.split(':'))[0]
    url = url.replace(protocol+"://", "")
    domain = (url.split('/'))[0]

    return data, soup, protocol, domain

def getLinks_amazon(url, soup, protocol, domain):
    links = []


    # get all links of product pages
    for attr in soup.find_all('a', attrs={'class':'a-link-normal a-text-normal'}):    
        link = attr.get('href')
        if (link != None): 
            if (link.startswith('http') and "gp/offer-listing/" not in link):
                print(link)
                links = links + [link]

    # get all links of result pages
    for attr in soup.find_all('span', attrs={'class':'pagnLink'}):
        link = attr.a.get('href')
        if (link != None): 
            if (link.startswith('/') and "page=" in link and "page=1" not in link ):
                link = protocol + "://" + domain + link
                print(link)
                links = links + [link]
    return links

def getLinks_ebay(url, soup, protocol, domain):
    links = []

    for attr in soup.find_all('a'):
        link = attr.get('href')
        if (link != None): 
            if ("hash=" in link or "_pgn=" in link):
                print(link)
                links = links + [link]
    return links

# Main Program
# To run:
# python3 crawler.py <filename> <search term>

if (len(sys.argv) < 2):
    print("Search Term Argument is Missing")
    sys.exit()
else:
    search_term = sys.argv[2]
    if (len(sys.argv) > 2):
        for i in range(3,len(sys.argv)):
            search_term += "+" + sys.argv[i]

file_name = "./" + sys.argv[1] + '.txt'
file = open(file_name, 'w')

pagesVisited = set()

amazon_URL = amazon_format + search_term
pagesToVisit = [amazon_URL]

ebay_URL = ebay_format % search_term
pagesToVisit += [ebay_URL]

while pagesToVisit != []:
    # Start from the beginning of collection of pages to visit:
    url = pagesToVisit[0]
    pagesToVisit = pagesToVisit[1:]

    #time.sleep(3) # sleep 1s to avoid crawler being mistaken as DDOS attacker

    if (url not in pagesVisited):
        html_text, soup, protocol, domain = parse_url(url)
        pagesVisited.add(url)
        print("Visiting: "+url)
        if ("page" not in url and "_pgn=" not in url and url != amazon_URL and url != ebay_URL): #product page
            file.write(url+"|urldelimit|"+html_text)
            #print(url+"|urldelimit|"+soup.prettify())
        else:
            #print(soup.prettify())
            if ("amazon.com" in url):
                links = getLinks_amazon(url, soup, protocol, domain)
            elif ("ebay.com" in url):
                links = getLinks_ebay(url, soup, protocol, domain)
         
            for link in links:
                if (link != None): 
                   if (domain in link or "page=" in link or "hash=" in link or "_pgn=" in link):
                       # Add the pages that we visited to the end of our collection
                       # of pages to visit:
                       pagesToVisit = pagesToVisit + [link]
file.close()
