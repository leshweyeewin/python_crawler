from bs4 import BeautifulSoup
from queue import Queue
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
num_of_links_left = multiprocessing.Value('i', 0)
target = 0
amazon_URL = "https://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%3Daps&field-keywords="
ebay_URL = "http://www.ebay.com/sch/i.html?_from=R40&_trksid=m570.l1313&_nkw=%s&_sacat=0"
aliexpress_URL = "https://www.aliexpress.com/wholesale?catId=0&initiative_id=SB_20161031115352&SearchText="
lazada_URL = "http://www.lazada.sg/catalog/?q="

def crawl(pagesToVisit, productPages, target, ebay_URL, amazon_URL):
    global pagesVisited, exitFlag, num_of_crawled_links, num_of_links_left
    while not exitFlag:
        if (target > 0 and num_of_crawled_links.value > target):
            exitFlag = 1
            break
        else:
            url = pagesToVisit.get()
            pagesVisited.add(url)
            lock.acquire()
            print ("#products:" + str(num_of_crawled_links.value) + ", #target:" + str(target) + ", #links:" + str(num_of_links_left.value))
            print("Visiting: "+url)
            lock.release()
                            
            #time.sleep(3) # sleep 1s to avoid crawler being mistaken as DDOS attacker

            html_text, soup, protocol, domain = parse_url(url)                       
            if ("page" not in url and "_pgn=" not in url and url != amazon_URL and url != ebay_URL and url != aliexpress_URL and url != lazada_URL): #product page   
                #print("Product Page")
                data = parse(url, html_text)
                if data != "error":
                    data = url + "," + data 
                    productPages.put(data)
                    num_of_crawled_links.value += 1
                   #file.write(str(n_products)+". "+url+"|urldelimit|"+html_text)
                
                        
            else: #result page
                #print("Result Page")
                #file.write(url+"|urldelimit|"+html_text)
                links = getLinks(url, soup, protocol, domain)        
                for link in links:
                    if (link != None): 
                        if (domain in link or "page=" in link or "hash=" in link or "_pgn=" in link):   
                            if (link not in pagesVisited):
                                # Add the pages that we visited to the end of our collection of pages to visit:
                                pagesToVisit.put(link)
                                num_of_links_left.value+=1
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
    if ("amazon.com" in url):
        links = getLinks_amazon(url, soup, protocol, domain)
    elif ("ebay.com" in url):
        links = getLinks_ebay(url, soup, protocol, domain)    
    elif ("aliexpress" in url):
        links = getLinks_aliexpress(url, soup, protocol, domain)
    elif ("lazada" in url):
        links = getLinks_lazada(url, soup, protocol, domain)    
    return links

def getLinks_amazon(url, soup, protocol, domain):
    links = []
    print(soup.prettify().encode('utf-8'))
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

    for attr in soup.find_all('a'):
        link = attr.get('href')
        if (link != None): 
            if ("hash=" in link or "_pgn=" in link and link not in links):
                if (link not in pagesVisited):
                    links = links + [link]
    return links

def getLinks_lazada(url, soup, protocol, domain):
    links = []
    #print(soup.prettify())
    for attr in soup.find_all('div', attrs={'class':'product-card new_ outofstock installments_ mastercard'}):
        link = attr.a['href']
        if (link != None): 
            if (link not in pagesVisited):
                #print(link)
                links = links + [link]

    for attr in soup.find_all('link'):
        link = attr.get('href')
        if (link != None): 
            if ("?page=" in link and "?page=1" not in link and link not in links):
                if (link not in pagesVisited):
                    #print(link)
                    links = links + [link]       
    return links

# Main Parse Function
def parse(base_url, html_text):
    csv = "error"
    if ("amazon.com" in base_url):
        csv = parse_amazon(html_text)
    elif ("ebay.com" in base_url):
        csv = parse_ebay(html_text)
    elif ("lazada.sg" in base_url):
        csv = parse_lazada(html_text)
    elif ("aliexpress.com" in base_url):
        csv = parse_aliexpress(html_text)
    return csv 
   
#Input: HTML Text
#Output: "url,name,image,price,mean" (if successful)
#        "error" (if fail)         
def parse_amazon(html_text):
    try:
        soup = BeautifulSoup(html_text, "html.parser") # need to change
        # find name
        seivedMeta = soup.find_all('meta', attrs={'name':'title'})
        text = str(seivedMeta[0])
        text = text.replace(":", "|")
        name = text.split('|')
        name = name[1].strip()

        # find image
        seivedImage = soup.findAll('img', {"data-a-dynamic-image":True} ) 
        img = seivedImage[0]['data-a-dynamic-image']
        end = img.split('"')
        img = end[1]

        # find price
        seivedSpan =soup.find_all('span', attrs={'id':'miniATF_price'})
        if(len(seivedSpan) == 0):
            return "error"

        value=  str(seivedSpan[0].contents[0]).strip()
        # remove dash if value is a range etc, $3.00 - $6.00
        removedDash = value.split('-')

        if(removedDash[0].find('$') == -1):
            return "error"

        # only 1 price, not a range
        elif(len(removedDash) ==1):
            firstVal = removedDash[0]
            firstVal = (firstVal.split('$'))[1] # extract the numbers
            mean = float(firstVal)
            # return format = name, value, mean
            # example: name, image, 43.00, 43.00        
            return name + "," +img + "," + firstVal + " - " +firstVal + "," + firstVal

        # range of prices
        else:
            firstVal = removedDash[0].strip()
            secondVal = removedDash[1].strip()
            firstVal = (firstVal.split('$'))[1]
            secondVal = (secondVal.split('$'))[1]
            mean = (float(firstVal)+float(secondVal))/2.0
            # return format = name, range, mean
            # return example: name, image, 40.00 - 60.00, 50.00
            return name +"," + img + "," + firstVal + "-" + secondVal + "," + str(mean)
    except:
        return "error"

#Input: HTML Text
#Output: "url,name,image,price,mean" (if successful)
#        "error" (if fail)  

#find title
def parse_lazada(html_text):
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        seivedMeta = soup.find_all('title')
        name = str(seivedMeta).split(">")[1]
        name = name.split("|")[0].strip()

    #find image
        seivedMeta = soup.find_all('meta', attrs={'itemprop':'image'})
        lastMeta = None
        for lastMeta in seivedMeta:pass
        if lastMeta:
            image = lastMeta
        image = str(image).split("\"")[1]

        #find price
        seivedSpan = soup.find_all('span', attrs={'id':'special_price_box'})
        if(len(seivedSpan) == 0):
            print ("error: no price found")
        price = str(seivedSpan[0].contents[0])
            
        return name +"," + image + "," + str(price) + " - " + str(price) + "," + str(price)
    except:
        return "error"



#Input: HTML Text
#Output: "url,name,price" (if successful)
#        "error" (if fail) 
def parse_ebay(html_text):
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        span = soup.find_all('span', attrs={'id':'prcIsum'})[0]

        name = soup.find_all('h1', attrs={'id':'itemTitle'})[0]
        img = soup.findAll('img', {'id':'icImg'})[0]
        if (len(name.contents) < 2 or len(span.contents) < 1):
            return "error"
        return name.contents[1] + "," + img.get('src') + "," + str(span.contents[0]) + "-" + str(span.contents[0]) + "," + str(span.contents[0].split("$")[1])
    except:
        return "errror"

#Input: HTML Text
#Output: "url,name,price" (if successful)
#        "error" (if fail) 
def parse_aliexpress(html_text):
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        tempPrice = soup.find_all('span', attrs={'itemprop':'lowPrice'})
        if (len(tempPrice)== 0):
            lowPrice = soup.find_all('span', attrs={'itemprop':'price'})[0]
            highPrice = lowPrice            
        else:
            highPrice = soup.find_all('span', attrs={'itemprop':'highPrice'})[0]
            lowPrice = tempPrice[0]
        name = soup.find_all('h1', attrs={'itemprop':'name'})[0]
        img = soup.findAll('img', {'alt':name.contents[0]})[0]
        mean = (float(lowPrice.contents[0]) + float(highPrice.contents[0])) / 2.0
        if (len(name.contents) < 1 or lowPrice.contents[0] < 0 or highPrice.contents[0] < 0):
            print ("error")
        return name.contents[0] + "," + img.get('src') + "," + str(lowPrice.contents[0]) + "-" + str(highPrice.contents[0]) + "," + str(mean)
    except:
        return "error"


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

    amazon_URL = amazon_URL + search_term
    links.put(amazon_URL)
    num_of_links_left.value += 1

    ebay_URL = ebay_URL % search_term
    links.put(ebay_URL)
    num_of_links_left.value += 1

    search_term = search_term.replace("+", "_") 
    file_name = "./" + search_term + '.csv'
    file = open(file_name, 'w+')
    writer = csv.writer(file, delimiter = ",")
    #writer.writerow(["Link", "Title", "Image", "Price range", "Avg price"])

    start = time.time()
    print("Hello world");
    the_pool = multiprocessing.Pool(target, crawl, (links, productLinks, target, ebay_URL, amazon_URL,))

    the_pool.close() # no more tasks

    the_pool.join()  # wrap up current tasks

    for i in range(num_of_crawled_links.value):
        writer.writerow(productLinks.get().split(','))
    file.close()

    end = time.time()
    print("Elapsed time:"+str(end-start))
