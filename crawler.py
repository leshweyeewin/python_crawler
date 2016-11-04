from bs4 import BeautifulSoup
from queue import Queue
from parser import Parser
import requests
import sys
import csv
import time
import threading
import multiprocessing

# Global variables
exitFlag = 0
num_thread = 10
pagesVisited = set()
links = multiprocessing.Queue()
productLinks = multiprocessing.Queue()
lock = multiprocessing.Lock()
#pagesToVisit = Queue()
#lock = threading.Lock()
num_of_crawled_links = multiprocessing.Value('i', 0)
target = 0
amazon_URL = "https://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%3Daps&field-keywords="
ebay_URL = "http://www.ebay.com/sch/i.html?_from=R40&_trksid=m570.l1313&_nkw=%s&_sacat=0"
aliexpress_URL = "https://www.aliexpress.com/wholesale?catId=0&initiative_id=SB_20161031115352&SearchText=%s"
lazada_URL = "http://www.lazada.sg/catalog/?q=%s"
rakuten_URL = "http://global.rakuten.com/en/search/?k=%s"
carousell_URL = "https://carousell.com/search/products/?query=%s"
zalora_URL = "https://www.zalora.sg/catalog/?q=%s"


def crawl(pagesToVisit, productPages):
    global pagesVisited, exitFlag, num_of_crawled_links
    while not exitFlag:
        if (target > 0 and num_of_crawled_links.value > target):
            exitFlag = 1
            break
        else:
            url = pagesToVisit.get()
            pagesVisited.add(url)
            #lock.acquire()
            #print ("#products:" + str(num_of_crawled_links.value) + ", #target:" + str(target))
            #lock.release()
                            
            #time.sleep(3) # sleep 1s to avoid crawler being mistaken as DDOS attacker

            html_text, soup, protocol, domain = parse_url(url)                       
            if ("page" not in url and "_pgn=" not in url and "?p=" not in url and url != amazon_URL and url != ebay_URL and url != aliexpress_URL and url != lazada_URL and url != zalora_URL and url != rakuten_URL and url != carousell_URL): #product page   
                print("Parsing: "+url)
                data = Parser.parse(url, html_text)
                if data != "error":
                    data = url + "," + data 
                    productPages.put(data)
                    print(data)
                    num_of_crawled_links.value += 1
                     
            else: #result page
                print("Crawling: "+url)
                links = getLinks(url, soup, protocol, domain)        
                for link in links:
                    if (link != None): 
                        if (domain in link or "page=" in link or "hash=" in link or "_pgn=" in link):   
                            if (link not in pagesVisited):
                                # Add the pages that we visited to the end of our collection of pages to visit:
                                pagesToVisit.put(link)
    print("Process existing")
    
def parse_url(url):
    r  = requests.get(url)
    data = r.text
    soup = BeautifulSoup(data, "html.parser")

    protocol = (url.split(':'))[0]    
    url = url.replace(protocol+"://", "")
    domain = (url.split('/'))[0]

    return data, soup, protocol, domain

def getLinks(url, soup, protocol, domain):
    links = []
    if ("amazon" in url):
        links = getLinks_amazon(url, soup, protocol, domain)
    elif ("ebay" in url):
        links = getLinks_ebay(url, soup, protocol, domain)    
    elif ("aliexpress" in url):
        links = getLinks_aliexpress(url, soup, protocol, domain)
    elif ("lazada" in url):
        links = getLinks_lazada(url, soup, protocol, domain)   
    elif ("zalora" in url):
        links = getLinks_zalora(url, soup, protocol, domain)    
    elif ("rakuten" in url):
        links = getLinks_rakuten(url, soup, protocol, domain)
    elif ("carousell" in url):
        links = getLinks_carousell(url, soup, protocol, domain)  
    return links

def getLinks_amazon(url, soup, protocol, domain):
    links = []
    #print(soup.prettify().encode('utf-8'))
    # get all links of product pages
    for attr in soup.find_all('a', attrs={'class':'a-link-normal a-text-normal'}):    
        link = attr.get('href')
        if (link != None): 
            if (link.startswith('http') and "gp/offer-listing/" not in link and link not in pagesVisited and link not in links):
                links = links + [link]

    # get all links of result pages
    for attr in soup.find_all('span', attrs={'class':'pagnLink'}):
        link = attr.a.get('href')
        if (link != None): 
            if (link.startswith('/') and "page=" in link and "page=1" not in link and link not in links):
                link = protocol + "://" + domain + link
                if (link not in pagesVisited):
                    links = links + [link]
    return links

def getLinks_ebay(url, soup, protocol, domain):
    links = []
    #print(soup.prettify().encode('utf-8'))
    for attr in soup.find_all('a'):
        link = attr.get('href')
        if (link != None): 
            if ("hash=" in link or "_pgn=" in link and link not in links):
                if (link not in pagesVisited):
                    links = links + [link]
    return links

def getLinks_lazada(url, soup, protocol, domain):
    links = []
    #print(soup.prettify().encode('utf-8'))
    # get all links of result pages
    for attr in soup.find_all('div', attrs={'class':'product-card new_ outofstock installments_ mastercard'}):
        link = attr.a['href']
        if (link != None): 
            if (link not in pagesVisited):
                #print(link)
                links = links + [link]

    # get all links of result pages
    for attr in soup.find_all('link'):
        link = attr.get('href')
        if (link != None): 
            if ("?page=" in link and "?page=1" not in link and link not in links):
                if (link not in pagesVisited):
                    #print(link)
                    links = links + [link]       
    return links

def getLinks_rakuten(url, soup, protocol, domain):
    links = []
    #print(soup.prettify().encode('utf-8'))
    # get all links of product pages
    for attr in soup.find_all('div', attrs={'class':'b-content b-fix-2lines'}): 
        if(attr.a != None):
            link = attr.a['href']
            if (link not in pagesVisited):
                link = protocol + "://" + domain + link
                #print(link)
                links = links + [link]

    # get all links of result pages
    for attr in soup.find_all('a'):
        link = attr.get('href')
        if (link != None): 
            if ("?p=" in link and "?p=1" not in link and link not in links):
                if (link not in pagesVisited):
                    link = protocol + "://" + domain + link
                    #print(link)
                    links = links + [link]       
    return links

def getLinks_carousell(url, soup, protocol, domain):
    links = []
    #print(soup.prettify().encode('utf-8'))
    for attr in soup.find_all('a'):
        link = attr.get('href')
        if (link != None): 
            if (("page=" in link and "page=1" not in link) or "/p/" in link):
                if (link not in pagesVisited and link not in links):
                    link = protocol + "://" + domain + link
                    #print(link)
                    links = links + [link] 
    return links


# Main Program
# To run:
# python3 crawler.py <num_links> <search term>
if __name__ == "__main__":
    if (len(sys.argv) < 2):
        print("Search Term Argument is Missing")
        sys.exit()
    else:
        target = int(sys.argv[1])
        search_term = sys.argv[2]
        if (len(sys.argv) > 2):
            for i in range(3,len(sys.argv)):
                search_term += "+" + sys.argv[i]

    # Set URL
    amazon_URL = amazon_URL + search_term
    ebay_URL = ebay_URL % search_term
    lazada_URL = lazada_URL % search_term
    aliexpress_URL = aliexpress_URL % search_term
    zalora_URL = zalora_URL % search_term
    carousell_URL = carousell_URL % search_term
    rakuten_URL = rakuten_URL % search_term
   
    # Add Links
    links.put(amazon_URL)
    links.put(ebay_URL)
    # links.put(aliexpress_URL)
    links.put(lazada_URL)
    # links.put(zalora_URL)
    # links.put(carousell_URL)
    links.put(rakuten_URL)
    
    search_term = search_term.replace("+", "_") 
    file_name = "./" + search_term + '.csv'
    file = open(file_name, 'w+')
    writer = csv.writer(file, delimiter = ",")
    #writer.writerow(["Link", "Title", "Image", "Price range", "Avg price"])

    start = time.time()
    the_pool = multiprocessing.Pool(target, crawl, (links, productLinks,))

    the_pool.close() # no more tasks
    the_pool.join()  # wrap up current tasks

    print("Writing to file")
    for i in range(num_of_crawled_links.value):
        writer.writerow(productLinks.get().split(','))
    file.close()

    end = time.time()
    print("Elapsed time:"+str(end-start))
