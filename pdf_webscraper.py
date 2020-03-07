import requests
from tika import parser
import os
import re
from bs4 import BeautifulSoup

#def 

headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:10.0) Gecko/20100101 Firefox/10.0'}
req = requests.get('https://www.who.int/emergencies/diseases/novel-coronavirus-2019/situation-reports', headers)
raw_html = req.text

clean_html = BeautifulSoup(raw_html, "html5lib")
links_outer_container = clean_html.find(id="PageContent_C006_Col01")
links_inner_container = links_outer_container.find_all('div', class_='sf-content-block')[0]
a_tags =  links_inner_container.find_all('a', href=True)  #only return a tags which have a href field


pdf_tuples = []
for i in range(len(a_tags)):
    a_tag = a_tags[i]
    if a_tag is not None and a_tag.text != "":
        pdf_tuples.append((a_tag.text, 'https://www.who.int' + a_tag['href']))

pdf_tuples.sort()   
print(len(pdf_tuples))


#downloading takes a long time, so only download missing pdfs
list_of_existing_pdfs = os.listdir("./WHO_reports")

for title, url in pdf_tuples:
    if title + '.pdf' not in list_of_existing_pdfs:
        print("Downloading", title + '.pdf')
        req = requests.get(url, headers)
        with open("./WHO_reports/" + title + '.pdf', 'wb') as file:
            file.write(req.content)




#*******************************************************
#******************* PROCESSING PDFS *******************
#*******************************************************


def get_date_from_text(text):
    """ Takes a string of text and returns the first date the text which is in 
        the format day month_text year. Returns a string with the date in the 
        format year/month/day.
    """
    
    date_regex = r'[0-9]{1,2} (January|February|March|April|May|June|July|August|September|October|November|December) ([0-9]{4})'
    months = "January|February|March|April|May|June|July|August|September|October|November|December".split("|")
    date_split = re.search(date_regex, text).group().split()
    date = "{2}/{1}/{0}".format(int(date_split[0]), months.index(date_split[1]), int(date_split[2]))
    return date


def replace_list(string, lst):
    """ Takes a string and a lst of charaters. Returns the string with all 
        elements in the list removed
    """
    
    for c in lst:
        string = string.replace(c, "")
        
    return string

        
#extract data from each pdf, WHO report format has changed over time so we need to use different techniques depending on issue
print("Getting connection to tika server, this can take a few minutes.")

list_of_data_tuples = []
provinces = ['hubei', 'guangdong', 'zhejiang', 'henan', 'hunan', 'anhui', 'jiangxi', 'jiangsu', 'chongqing', 'shandong', 'sichuan', 'beijing', 'heilongjiang', 'shanghai', 'fujian', 'shaanxi', 'hebei', 'guangxi', 'yunnan', 'hainan', 'shanxi', 'liaoning', 'guizhou', 'tianjin', 'gansu', 'jilin', 'inner mongolia', 'ningxia', 'xinjiang', 'hong kong sar', 'qinghai', 'taipei', 'macao sar', 'xizang', 'total']
provinces_extra = provinces + ['taipei and environs', 'macau sar']
replace_dict = {'taipei and environs' : 'taipei', 'macau sar' : 'macao sar'}


for title, url in pdf_tuples:
    issue = int(re.search('[0-9]+', title).group())
    
    raw = parser.from_file('./WHO_reports/' + title + '.pdf')
    content = raw['content']
    
    #get the date first
    date = get_date_from_text(content)  
    data_dict = dict()
    
    if issue >= 28:        
        #To get china we want to find: "Total 142823 2051 1563 106 70635 1772 "
        regex = r = r"(?P<province>[a-zA-Z ]+) (?P<population>[0-9]+(\*)?) ([0-9]+(\*)? ){3}(?P<confirmed_cases>[0-9]+(\*)?) (?P<deaths>[0-9]+(\*)?)"        
        matches = list(re.finditer(regex, content))
        assert(len(matches) == len(provinces))
        
        for match in matches:        #better to have a dict which is by province, than just returning a list of matches
            province = match.groupdict()['province'].strip().lower()
            province = replace_dict.get(province, province)
            data_dict[province] = match.groupdict() 
            
        #print(data_dict.keys())
            
        list_of_data_tuples.append((date, data_dict))
        
        
    elif issue >= 12 and issue < 23:
        #To get province we want to find: "province 142823 "
        regex = r"\n(?P<province>(" + "|".join(provinces_extra) + r")) (\n)?(?P<confirmed_cases>[0-9 ]+(\*)?)"  
        matches = list(re.finditer(regex, content, re.IGNORECASE | re.M))
        
        if len(matches) > len(provinces):    #there are two matches for totals in some files
            matches = matches[:-1]
        
        try:
            assert(len(matches) == len(provinces))
        except AssertionError:
            print(len(matches), len(provinces))
            kek = set([match.groupdict()['province'].strip().lower() for match in matches])
            print(matches)
            print(kek.symmetric_difference(set(provinces)))
            print(content)
        
        for match in matches:        #better to have a dict which is by province, than just returning a list of matches
            province = match.groupdict()['province'].strip().lower()
            province = replace_dict.get(province, province)
            data_dict[province] = match.groupdict()  
            
        #print(data_dict.keys())
            
        list_of_data_tuples.append((date, data_dict))        
        


with open('china_province_confirmed_cases.csv', 'w') as file:
    text_to_write = ""
    is_first = True
    for date, data_dict in list_of_data_tuples:
        if is_first:
            provinces = list(data_dict.keys())
            text_to_write = ",".join(["Date"] + provinces) + "\n"
            is_first = False    
          
        print(date)
        csv_line = [date] + [replace_list(data_dict[province]['confirmed_cases'], ["*", " "]) for province in provinces]   
        text_to_write += ",".join(csv_line) + "\n"
        
        
    file.write(text_to_write)
    



