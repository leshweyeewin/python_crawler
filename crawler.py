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
                links = links + [link]

    # get all links of result pages
    for attr in soup.find_all('span', attrs={'class':'pagnLink'}):
        link = attr.a.get('href')
        if (link != None): 
            if (link.startswith('/') and "page=" in link and "page=1" not in link ):
                link = protocol + "://" + domain + link
                links = links + [link]
    return links

def getLinks_ebay(url, soup, protocol, domain):
    links = []

    for attr in soup.find_all('a'):
        link = attr.get('href')
        if (link != None): 
            if ("hash=" in link or "_pgn=" in link):
                links = links + [link]
    return links

def parse(base_url, html_text):
    csv = "error"
    if ("amazon.com" in base_url):
        csv = parse_amazon(html_text)
    elif ("ebay.com" in base_url):
        csv = parse_ebay(html_text)
    return base_url + "," + csv 
   
#Input: HTML Text
#Output: "url,name,image,price,mean" (if successful)
#        "error" (if fail)         
def parse_amazon(html_text):
    soup = BeautifulSoup(html_text) # need to change
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
        return name + "," +img + "," + firstVal + "," + firstVal

    # range of prices
    else:
        firstVal = removedDash[0].strip()
        secondVal = removedDash[1].strip()
        firstVal = (firstVal.split('$'))[1]
        secondVal = (secondVal.split('$'))[1]
        mean = (float(firstVal)+float(secondVal))/2.0
        # return format = name, range, mean
        # return example: name, image, 40.00 - 60.00, 50.00
        return name +"," + img + "," + firstVal + "-" + secondVal + "," + mean

#Input: HTML Text
#Output: "url,name,image,price,mean" (if successful)
#        "error" (if fail)  

#find title
def parse_lazada(html_text):
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
        print "error: no price found"
    price = str(seivedSpan[0].contents[0])
        
    return name +"," + image + "," + price + "," + price



#Input: HTML Text
#Output: "url,name,price" (if successful)
#        "error" (if fail) 
def parse_ebay(html_text):
    soup = BeautifulSoup(html_text)
    span = soup.find_all('span', attrs={'id':'prcIsum'})[0]
    name = soup.find_all('h1', attrs={'id':'itemTitle'})[0]
    img = soup.findAll('img', {'id':'icImg'})[0]
    if (len(name.contents) < 2 or len(span.contents) < 1):
        return "error"
    return name.contents[1] + "," + img.get('src') + "," + span.contents[0] + "-" + span.contents[0] + "," + span.contents[0]

#Input: HTML Text
#Output: "url,name,price" (if successful)
#        "error" (if fail) 
def parse_aliexpress(html_text):
    soup = BeautifulSoup(open("Untitled Document 3"))
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
        print "error"
    return name.contents[0] + "," + img.get('src') + "," + lowPrice.contents[0] + "-" + highPrice.contents[0] + "," + mean


# Main Program
# To run:
# python3 crawler.py <filename> <search term>

if __name__ == "__main__":
    if (len(sys.argv) < 1):
        print("Search Term Argument is Missing")
        sys.exit()
    else:
        search_term = sys.argv[1]
        if (len(sys.argv) > 1):
            for i in range(2,len(sys.argv)):
                search_term += "+" + sys.argv[i]

    pagesVisited = set()

    amazon_URL = amazon_format + search_term
    pagesToVisit = [amazon_URL]

    ebay_URL = ebay_format % search_term
    pagesToVisit += [ebay_URL]
    
    search_term.replace("+", "_") 
    file_name = "./" + search_term + '.csv'
    file = open(file_name, 'w+')
    writer = csv.writer(file, delimiter = ",")
    #writer.writerow(["Link", "Title", "Image", "Price range", "Avg price"])

    while pagesToVisit != []:
        # Start from the beginning of collection of pages to visit:
        url = pagesToVisit[0]
        pagesToVisit = pagesToVisit[1:]

        #time.sleep(3) # sleep 1s to avoid crawler being mistaken as DDOS attacker

        if (url not in pagesVisited): #Parse
            html_text, soup, protocol, domain = parse_url(url)
            pagesVisited.add(url)
            # print("Visiting: " + url)
            if ("page" not in url and "_pgn=" not in url and url != amazon_URL and url != ebay_URL): #product page
                data = parse(url.encode('utf-8'), html_text.encode('utf-8'))
                writer.writerow(data.split(','))
                print(html_text)

            else: #Scrape
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
