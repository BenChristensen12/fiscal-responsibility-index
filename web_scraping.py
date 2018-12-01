"""
Ben Christensen
Fiscal Responsibility Index
November 14, 2018

Script Name: webscraping.py
Purpose: *Find the voting record for reps. from the House and U.S. Senators for
          every bill signed into law since 1973
         *Find the CBO cost estimate for every bill
         *Create the Fiscal Responsibility Score for each Rep and Senator
         *Organize into a csv called scores_data.csv
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from collections import defaultdict
from matplotlib import pyplot as plt
import numpy as np
import math
from urllib.request import urlretrieve
import textract
from datetime import date
import time
import pandas as pd

def get_members_of_congress(sessions=[i for i in range(105,116)]):
    """Find the names of all members of congress for given sessions of Congress

    Parameters:
        sessions (list): Which sessions to find members of Congress

    Returns:
        (set): House Representatives for the given sessions
               "Last Name, First Name, Title" (Title is Jr. or Sr.)
        (set): Senators for the given session
               "Last Name, First Name, Title"
    """
    base_url = "https://www.congress.gov/"
    url = base_url+"members"
    soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    #Congress.gov requires a wait time of two seconds while web crawling
    time.sleep(2)
    Senators, Representatives = set(), set()
    for session in sessions:
        year1 = (session - 100)*2+1987
        year2 = year1+1
        #Create string needed to find the session search box
        string = "facetItemcongress"+str(session)+"__"+str(year1)+"_"+str(year2)+"_"
        #Limit the members of Congress to the session we want
        session_url = soup.find(name='a', href=True, attrs={"id":string}).attrs['href']
        session_soup=BeautifulSoup(requests.get(base_url+session_url).text, 'html.parser')
        time.sleep(2)
        #Limit the members of Congress to only the Senate
        session_url = session_soup.find(name='a', href=True, attrs={'id':'facetItemchamberSenate'}).attrs['href']
        session_soup=BeautifulSoup(requests.get(base_url+session_url).text, 'html.parser')
        time.sleep(2)
        #Find the number of pages to cycle through for the member names
        num_pages = int(session_soup.find(name='span', attrs={'class':'results-number'}).contents[2].split()[-1].replace(',','')) // 100 + 1
        for page in range(1, num_pages+1):
            session_soup=BeautifulSoup(requests.get(base_url+session_url+"&page="+str(page)).text, 'html.parser')
            time.sleep(2)
            page += 1
            #Get members with title Senator
            senator_tags = session_soup.find_all(name='a', href=True, string=re.compile(r"^Senator "))
            for tag in senator_tags:
                Senators.add(''.join([word + " " for word in tag.string.split()[1:]]).strip())

        #Limit the members of Congress to the session we want
        session_url = soup.find(name='a', href=True, attrs={"id":string}).attrs['href']
        session_soup=BeautifulSoup(requests.get(base_url+session_url).text, 'html.parser')
        time.sleep(2)
        #Limit the members of Congress to only the House
        session_url = session_soup.find(name='a', href=True, attrs={'id':'facetItemchamberHouse'}).attrs['href']
        session_soup=BeautifulSoup(requests.get(base_url+session_url).text, 'html.parser')
        time.sleep(2)
        #Find the number of pages to cycle through for the member names
        num_pages = int(session_soup.find(name='span', attrs={'class':'results-number'}).contents[2].split()[-1].replace(',','')) // 100 + 1
        for page in range(1, num_pages+1):
            session_soup=BeautifulSoup(requests.get(base_url+session_url+"&page="+str(page)).text, 'html.parser')
            time.sleep(2)
            page += 1
            #Get members with title Senator
            senator_tags = session_soup.find_all(name='a', href=True, string=re.compile(r"^Senator "))
            for tag in senator_tags:
                Representatives.add(''.join([word + " " for word in tag.string.split()[1:]]).strip())
            #Get members with title Representative
            representative_tags = session_soup.find_all(name='a', href=True, string=re.compile(r"^Representative "))
            for tag in representative_tags:
                Representatives.add(''.join([word + " " for word in tag.string.split()[1:]]).strip())


    return Representatives, Senators

def quick_members_of_congress(sessions=[i for i in range(105,116)]):
    """Find the names of all members of congress for given sessions of Congress

    Parameters:
        sessions (list): Which sessions to find members of Congress

    Returns:
        (dict): House Representatives for the given sessions
               "Last Name, First Name, Title" (Title is Jr. or Sr.)
               include State, Party, Birth, Congress Year
        (dict): Senators for the given session
               "Last Name, First Name, Title"
               include State, Party, Birth, Congress Year
    """
    member_search_url = "http://bioguide.congress.gov/biosearch/biosearch.asp"
    browser = webdriver.Chrome()
    Representatives, Senators = dict(), dict()
    try:
        browser.get(member_search_url)
        time.sleep(2)
        #soup = BeautifulSoup(browser.page_source, 'html.parser')
        for session in sessions:
            try:
                input_elements = browser.find_elements_by_tag_name("input")
            except:
                print("Couldn't find any input elements")
            #Search bar for year or Congress session
            input_congress = input_elements[2]
            #Button for searching for members of Congress
            input_search = input_elements[3]
            input_congress.clear()
            input_congress.send_keys(str(session))
            input_search.click()
            time.sleep(2)
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            member_name_tags = soup.find_all(name='a', href=True)
            for tag in member_name_tags[:-1]:
                name = tag.next
                split = name.split(sep=',')
                #Deal with the rare case that the last name starts with lowercase
                if split[0][0].islower():
                    for i in range(1,len(split[0])):
                        if split[0][i].isupper():
                            first = split[0][:i+1]
                            for j in range(len(split[0][i+1:])):
                                first += split[0][i+j+1].lower()
                            break
                    split[0] = first
                    name = ''.join([word + "," for word in split]).strip()[:-1]
                #Every other case starts with upper-case, but this website
                #   puts the entire last name in all-caps, so we want to set
                #   the other letters in the last name to lowercase
                else:
                    split[0] = split[0][0] + split[0][1:].lower()
                    name = ''.join([word + "," for word in split]).strip()[:-1]
                birth = tag.next.next.string[:4]

                if tag.next.next.next.next.next.next == "Representative":
                    position = 'R'
                elif tag.next.next.next.next.next.next == "Senator":
                    position = 'S'
                if tag.next.next.next.next.next.next.next.next == "Democrat":
                    party = 'D'
                elif tag.next.next.next.next.next.next.next.next == "Republican":
                    party = 'R'
                elif tag.next.next.next.next.next.next.next.next == "Independent":
                    party = "I"
                state = tag.next.next.next.next.next.next.next.next.next.next
                #Now add the member of Congress with all this information to the dict
                if position == 'R':
                    if name in Representatives.keys():
                        Representatives[name]["Sessions"].append(session)
                    else:
                        Representatives[name] = {"State":state, "Party":party, "Sessions":[session]}
                        Representatives[name]["Position"] = 'Rep'
                        Representatives[name]["Birth"] = int(birth)

                elif position == 'S':
                    if name in Senators.keys():
                        Senators[name]["Sessions"].append(session)
                    else:
                        Senators[name] = {"State":state, "Party":party, "Sessions":[session]}
                        Senators[name]["Position"] = 'Sen'
                        Senators[name]["Birth"] = int(birth)
            browser.get(member_search_url)
            time.sleep(2)



    finally:
        browser.close()


    return Representatives, Senators

def get_bill_names(sessions=[i for i in range(105,116)]):
    """Find the names of all bills signed into law during the given sessions of
    Congress. Default is all sessions available from Congress.gov. Return bills
    initiated in the House of Representatives and bills initiated in the Senate
    in different lists.

    Parameters:
        sessions (list): Which sessions to find bill names for

    Returns:
        house_bills (list): names of bills initiated in H.R. signed into law
        senate_bills (list): names of bills initiated in Senate signed into law
    """

    base_url = "https://www.congress.gov/public-laws/"
    #Bills initiated in the Senate start with "S." followed by numbers
    #Bills initiated in the House of Rep. start with "H.R." followed by numbers
    senate_bill_finder = re.compile(r"^S\.\d+$")
    house_bill_finder = re.compile(r"^H.R.\d+$")
    #Find the names of all the bill names passed with
    #   Senate bill names and House bills in separate lists
    senate_bills = []
    house_bills = []
    #Cycle through every session of congress publicly available on congress.gov
    for session in sessions[::-1]:
        #Navigate to the page corresponding to that session of Congress
        soup = BeautifulSoup(requests.get(base_url+str(session)).text, "html.parser")
        for tag in soup.find_all(name='a'):
            if tag.string is not None:
                if bool(senate_bill_finder.search(tag.string)):
                    senate_bills.append(tag.string+'-'+str(session)+"th")
                if bool(house_bill_finder.search(tag.string)):
                    house_bills.append(tag.string+'-'+str(session)+"th")
        #Congress.gov requires a wait time of 2 seconds while crawling
        time.sleep(2)


    return house_bills, senate_bills

def get_senator_voting_records(Senators, sessions=[i for i in range(105,116)]):
    """Create a dictionary storing the voting records of senators for all of the
    bills for a given session of congress

    Parameters:
        Senators (dict): dictionary of Senators,
        session (int): Session of congress to find senator voting records for

    This function returns nothing because it modifies the dictionary it receives
    """
    for key in Senators.keys():
        Senators[key]["Yeas"] = list()
        Senators[key]["Nays"] = list()
        Senators[key]["Not Voting"] = list()
    browser = webdriver.Chrome()
    try:
        for session in sessions:
            house_names, senate_names = get_bill_names([session])
            bill_names = house_names + senate_names
            other_bills = bill_names
            #Find the names of all the bills signed into law during this session of
            #   Congress.
            senate_url = "https://www.senate.gov/"
            base_url = "https://www.senate.gov/legislative/LIS/roll_call_lists/vote_menu_"
            #URL for the first year of this session of Congress
            first_year_url = base_url + str(session) + "_1.htm"
            #URL for the second year of this session of Congress
            second_year_url = base_url + str(session) + "_2.htm"
################################################################################
#For the first year of the Session of Congress                                 #
################################################################################
            browser.get(first_year_url)
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            tags_with_links = soup.find_all(name='a', href=True)[80:]
            leftover_bills = []
            for name in other_bills:
                found = False
                #senate.gov has strings as S. 1582 rather than S.1582 so we must
                #   add a space to match the text
                split = name.split(sep='.')
                if len(split) < 3:
                    new_name = split[0] + '. ' + split[1]
                else:
                    new_name = split[0]+'.'+split[1]+'. ' + split[2]
                #Find if the bill is on the page
                for tag in tags_with_links:
                    if new_name.split('-')[0] == tag.string:
                        #Save URL for roll-call votes
                        try:
                            roll_call_tag = tag.previous.previous.previous.previous.previous.previous.previous
                            roll_call_page = roll_call_tag.attrs['href']
                        except:
                            roll_call_tag = tag.previous.previous.previous.previous.previous.previous.previous.previous.previous.previous
                            roll_call_page = roll_call_tag.attrs['href']
                        #Skip if they're not voting on the actual passage
                        #   of the bill.
                        if roll_call_tag.next.next.next != "Passed":
                            continue
                        found = True
                        browser.get(senate_url + roll_call_page)
                        roll_call_soup = BeautifulSoup(browser.page_source, 'html.parser')
                        tags = roll_call_soup.find_all(name='span', attrs={"class":"contenttext"})
                        tag = tags[0].next
                        for i in range(100):
                            split = tag.string.split(sep = " ")
                            Sen_name = split[0]
                            try:
                                party = split[1][1]
                                state = split[1][3:5]
                                for key in Senators.keys():
                                    #Check if last name from roll call matches the
                                    #   last name of any Senators that have served
                                    #   during the listed sessions
                                    if Sen_name == key.split(sep=',')[0]:
                                        #Only one Senator should match each of these
                                        #   characteristics
                                        if Senators[key]["Party"] == party and Senators[key]["State"] == state and session in Senators[key]["Sessions"]:
                                            if tag.next.string == "Yea":
                                                    Senators[key]["Yeas"].append(name)
                                            elif tag.next.string == "Nay":
                                                    Senators[key]["Nays"].append(name)
                                            elif tag.next.string == "Not Voting":
                                                    Senators[key]["Not Voting"].append(name)
                                tag = tag.next.next.next.next.next
                            except:
                                #print("Missing Senator")
                                pass
                        break
                if found == False:
                    leftover_bills.append(name)

################################################################################
#Repeat for the second year of the session                                     #
################################################################################
            browser.get(second_year_url)
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            tags_with_links = soup.find_all(name='a', href=True)[80:]
            other_bills = []
            for name in leftover_bills:
                found = False
                #senate.gov has strings as S. 1582 rather than S.1582 so we must
                #   add a space to match the text
                split = name.split(sep='.')
                if len(split) < 3:
                    new_name = split[0] + '. ' + split[1]
                else:
                    new_name = split[0]+'.'+split[1]+'. ' + split[2]
                #Find if the bill is on the page
                for tag in tags_with_links:
                    if new_name.split('-')[0] == tag.string:
                        #Save URL for roll-call votes
                        try:
                            roll_call_tag = tag.previous.previous.previous.previous.previous.previous.previous
                            roll_call_page = roll_call_tag.attrs['href']
                        except:
                            roll_call_tag = tag.previous.previous.previous.previous.previous.previous.previous.previous.previous.previous
                            roll_call_page = roll_call_tag.attrs['href']
                        #Skip if they're not voting on the actual passage
                        #   of the bill.
                        if roll_call_tag.next.next.next != "Passed":
                            continue
                        browser.get(senate_url + roll_call_page)
                        roll_call_soup = BeautifulSoup(browser.page_source, 'html.parser')
                        #if roll_call_soup.find(name='question').string != "On Passage of the Bill":
                        #    continue
                        found = True
                        tags = roll_call_soup.find_all(name='span', attrs={"class":"contenttext"})
                        tag = tags[0].next
                        for i in range(100):
                            split = tag.string.split(sep = " ")
                            Sen_name = split[0]
                            try:
                                party = split[1][1]
                                state = split[1][3:5]
                                for key in Senators.keys():
                                    #Check if last name from roll call matches the
                                    #   last name of any Senators that have served
                                    #   during the listed sessions
                                    if Sen_name == key.split(sep=',')[0]:
                                        #Only one Senator should match each of these
                                        #   characteristics
                                        if Senators[key]["Party"] == party and Senators[key]["State"] == state and session in Senators[key]["Sessions"]:
                                            if tag.next.string == "Yea":
                                                    Senators[key]["Yeas"].append(name)
                                            elif tag.next.string == "Nay":
                                                    Senators[key]["Nays"].append(name)
                                            elif tag.next.string == "Not Voting":
                                                    Senators[key]["Not Voting"].append(name)
                                tag = tag.next.next.next.next.next
                            except:
                                #A senator is missing from the roll_call page
                                pass
                        break
                if found == False:
                    other_bills.append(name)

    finally:
        browser.close()

def get_representative_voting_records(Representatives, sessions=[i for i in range(105,116)]):
    """Create a dictionary storing the voting records of reps for all of the
    bills for a given session of congress

    Parameters:
        Representatives (dict): dictionary of Representatives,
        session (list): Sessions of congress to find rep voting records for

    This function returns nothing because it modifies the dictionary it receives
    """
    home_url = "http://clerk.house.gov/legislative/legvotes.aspx"
    base_url = "http://clerk.house.gov/evs/"
    for key in Representatives.keys():
        Representatives[key]["Yeas"] = list()
        Representatives[key]["Nays"] = list()
        Representatives[key]["Not Voting"] = list()

    browser = webdriver.Chrome()
    try:
        browser.get(home_url)
        #Options for session of Congress to get roll call votes
        option_elements = browser.find_elements_by_tag_name("option")
        submit_button = browser.find_elements_by_tag_name("input")[-2]
        for session in sessions:
            bill_names = get_bill_names([session])
            bill_names = bill_names[0] + bill_names[1]
            other_bills = bill_names
            #101 Session of Congress only has 1 roll call page
            if session == 101:
                num_sessions = 1
                index = 0
                options = [option_elements[0]]
                years = [1990]
            #115 Session of Congress only has 1 roll call page
            elif session == 115:
                index = -1
                num_sessions = 1
                options = [option_elements[-1]]
                years = [2017]
            #Every other session has two roll call pages
            else:
                num_sessions = 2
                index = 2*(session - 102) + 1
                options = option_elements[index:index+2]
                year1 = 2*(session - 102) + 1991
                years = [year1, year1 + 1]
            for i in range(num_sessions):
                #There are two years for each session the first "option"
                #   corresponds to the first year; similarly for the second option
                year = years[i]
                option = browser.find_elements_by_tag_name("option")[index+i]
                submit_button = browser.find_elements_by_tag_name("input")[-2]
                option.click()
                submit_button.click()
                #This brings us to a page with links to pages each containing
                #   several of the roll call vote records for the given year
                soup = BeautifulSoup(browser.page_source, 'html.parser')
                search_page_urls = [tag.attrs['href'] for tag in soup.find_all(name='a', href=True, string=re.compile(r"^Roll Calls"))]
                for page_url in search_page_urls:
                    browser.get(base_url + str(year) + '/' + page_url)
                    #Each page contains links to pages containing the actual
                    #   roll call vote records
                    page_soup = BeautifulSoup(browser.page_source, 'html.parser')

                    bill_tags = page_soup.find_all(name='a', href=True, string=re.compile(r"^H R \d+$"))
                    bill_tags += page_soup.find_all(name='a', href=True, string=re.compile(r"^S \d+$"))
                    bills_on_page = set([tag.string for tag in bill_tags])
                    #Keep track of the bills that haven't been found so we don't
                    #   keep searching for bills we've already added to the
                    #   records
                    leftover_bills = []
                    for bill_name in other_bills:
                        found = False
                        for bill_on_page in bills_on_page:
                            if bill_name.split(sep='-')[0] == ''.join(i+'.' for i in bill_on_page.split())[:-1]:
                                tag = page_soup.find(name='a', href=True, string=bill_on_page)
                                #Skip if they're not voting on the actual passage
                                #   of the bill.
                                if tag.next.next.next.string != "On Passage":
                                    continue
                                found = True
                                roll_call_url = tag.previous.previous.previous.previous.previous.previous.previous.previous.previous.attrs['href']
                                soup = BeautifulSoup(requests.get(roll_call_url).text, 'html.parser')

                                tags = soup.find_all(name='recorded-vote')
                                for tag in tags:
                                    got_state = False
                                    rep_name = tag.next.string
                                    state = tag.next.attrs['state']
                                    party = tag.next.attrs['party']
                                    #Store state if it's there
                                    if bool(re.compile(r"\(").search(rep_name)):
                                        got_state = True
                                        state = rep_name.split(sep='(')[-1][0:2]
                                        #Remove the state from the rep_name
                                        rep_name = ''.join(rep_name.split(sep='(')[:-1]).strip()
                                    #Following we add the vote to the Rep dict, but
                                    #   first we have to uniquely identify the Rep.
                                    #   We use state, party, and session of Congress
                                    #   if all we have is the last name.
                                    #if ',' in rep_name:
                                    #    Representatives[rep_name][vote_types[i]].append(bill_name)
                                    #    print("Success1")
                                    #else:
                                    for key in Representatives.keys():
                                        if rep_name == key.split(sep=',')[0]:
                                            #Use state information to get the right senator
                                            #   if you have it
                                            if got_state == True:
                                                if state == Representatives[key]["State"] and party == Representatives[key]["Party"] and session in Representatives[key]["Sessions"]:
                                                    if tag.next.next.next.string == "Yea":
                                                        Representatives[key]["Yeas"].append(bill_name)
                                                    elif tag.next.next.next.string == "Nay":
                                                        Representatives[key]["Nays"].append(bill_name)
                                                    elif tag.next.next.next.string == "Not Voting":
                                                        Representatives[key]["Not Voting"].append(bill_name)
                                            #This is if we don't have state information
                                            else:
                                                if party == Representatives[key]["Party"] and session in Representatives[key]["Sessions"]:
                                                    if tag.next.next.next.string == "Yea":
                                                        Representatives[key]["Yeas"].append(bill_name)
                                                    elif tag.next.next.next.string == "Nay":
                                                        Representatives[key]["Nays"].append(bill_name)
                                                    elif tag.next.next.next.string == "Not Voting":
                                                        Representatives[key]["Not Voting"].append(bill_name)
                                """
                                browser.get(roll_call_url)
                                soup = BeautifulSoup(browser.page_source, 'html.parser')
                                #Use this to search for the number of reps who voted
                                #   a certain way
                                find_num = re.compile(r"\d+")
                                #Tags for each type of vote
                                yea_tag = soup.find(name='b', string=re.compile(r"^---- "))
                                nay_tag = soup.find(name='b', string=re.compile(r"^---- NAYS"))
                                nv_tag = soup.find(name='b', string=re.compile(r"^---- NOT VOTING"))
                                #Number of votes for each type of vote
                                num_yeas = int(find_num.findall(yea_tag.string)[0].replace(',',''))
                                try:
                                    num_nays = int(find_num.findall(nay_tag.string)[0].replace(',',''))
                                except:
                                    num_nays = 0
                                try:
                                    num_nvs = int(find_num.findall(nv_tag.string)[0].replace(',',''))
                                except:
                                    num_nvs = 0
                                #Create lists of vote tags and num_votes for each type
                                #   of vote for use in the following for loop
                                vote_tags = [yea_tag, nay_tag, nv_tag]
                                num_votes = [num_yeas, num_nays, num_nvs]
                                vote_types = ["Yeas", "Nays", "Not Voting"]
                                #Update dictionary with each type of votes
                                column_heads = soup.find_all(name='td', attrs={'valign':'top', 'width':'33.3%'})
                                starting_tags = column_heads[0:3]
                                for i in range(3):
                                    if num_votes[i] == 0:
                                        num_columns1=num_votes[i]
                                        i-=1
                                        continue
                                    if i == 1:
                                        if num_votes[i] < 3:
                                            num_columns1=num_votes[i]
                                        elif num_votes[i] < 5:
                                            num_columns1 = 2
                                        else:
                                            num_columns1 = 3
                                        starting_tags = column_heads[3:3+num_columns1]
                                    if i == 2:
                                        if num_votes[i] < 3:
                                            num_columns2=num_votes[i]
                                        else:
                                            num_columns2 = 3

                                        starting_tags = column_heads[3+num_columns1:3+num_columns1+num_columns2]
                                        if len(column_heads)>9 or (len(column_heads) > 9 and num_nays==0):
                                            starting_tags = column_heads[num_columns2*-1:]
                                    #The Nays and Not Voting tables behave a little
                                    #   differently from the Yeas column
                                    #if i == 1:
                                    #    starting_tags[0] = starting_tags[0].next
                                    #    starting_tags[1] = starting_tags[1].next
                                    #if i == 2:
                                    #    starting_tags = [tag.next for tag in starting_tags]
                                    tag = starting_tags[0].next
                                    #print(tag.string == '\n')
                                    while tag.string == '\n':
                                        tag = tag.next
                                        #print(tag.string is None)
                                    for j in range(num_votes[i]):
                                        got_state = False
                                        #The names are split between 3 columns
                                        #print(num_votes[i], j)
                                        if j < math.ceil(num_votes[i] / 3):
                                            if j > 0:
                                                tag = tag.next_sibling.next_sibling
                                        elif j == math.ceil(num_votes[i]/3):
                                            tag = starting_tags[1].next
                                            while tag == '\n':
                                                tag = tag.next
                                        elif j > math.ceil(num_votes[i] /3) and j < 2*math.ceil(num_votes[i]/3):
                                            tag = tag.next_sibling.next_sibling
                                        elif j == 2*math.ceil(num_votes[i]/3):
                                            tag = starting_tags[2].next
                                            while tag == '\n':
                                                tag = tag.next
                                        elif j > 2*math.ceil(num_votes[i]/3):
                                            tag = tag.next_sibling.next_sibling

                                        #Democrats are in italics
                                        if tag.name == 'i':
                                            party = "R"
                                        #Independents are underlined
                                        elif tag.name == 'u':
                                            party = "I"
                                        #Republicans are in roman
                                        elif tag.name is None:
                                            party = "D"
                                        #Manipulating representative name
                                        rep_name = tag.string
                                        #Store state if it's there
                                        if bool(re.compile(r"\(").search(rep_name)):
                                            got_state = True
                                            state = rep_name.split(sep='(')[-1][0:2]
                                            #Remove the state from the rep_name
                                            rep_name = ''.join(rep_name.split(sep='(')[:-1]).strip()
                                        #Following we add the vote to the Rep dict, but
                                        #   first we have to uniquely identify the Rep.
                                        #   We use state, party, and session of Congress
                                        #   if all we have is the last name.
                                        #if ',' in rep_name:
                                        #    Representatives[rep_name][vote_types[i]].append(bill_name)
                                        #    print("Success1")
                                        #else:
                                        for key in Representatives.keys():
                                            if rep_name == key.split(sep=',')[0]:
                                                #Use state information to get the right senator
                                                #   if you have it
                                                if got_state == True:
                                                    if state == Representatives[key]["State"] and party == Representatives[key]["Party"] and session in Representatives[key]["Sessions"]:
                                                        Representatives[key][vote_types[i]].append(bill_name)
                                                        #print("Success 1", bill_name)
                                                        #print(Representatives[key])
                                                #This is if we don't have state information
                                                else:
                                                    if party == Representatives[key]["Party"] and session in Representatives[key]["Sessions"]:
                                                        Representatives[key][vote_types[i]].append(bill_name)
                                                        #print("Success 2")
                                    #print(Representatives)
                                """
                                break

                        if found == False:
                            leftover_bills.append(bill_name)
                    other_bills = leftover_bills

                browser.get(home_url)


    finally:
        browser.close()

def get_cost_estimates(bill_names):
    """Find the net cost estimates for each bill and return a dictionary

    Parameters:
        bill_names (list): list of bill names including the session in which
            the bill was passed

    Returns:
        (dict): each bill name with its net cost estimate
    """
    #start_time = time.time()
    home_url = "https://www.cbo.gov"
    base_url = "https://www.cbo.gov/cost-estimates"
    #important_bills = list()
    bill_costs = dict()
    count = 0
    costs, revenues = [],[]
    try:
        browser = webdriver.Chrome()
        for bill_name in bill_names:
            cost, revenue, dollar = 0, 0, 0
            name, session = bill_name.split(sep='-')
            #go to the cost estimates page and search for the bill name
            browser.get(base_url)
            browser_elements = browser.find_elements_by_tag_name("input")
            search_bill = browser_elements[4]
            search_button = browser_elements[8]
            search_bill.clear()
            search_bill.send_keys(name)
            search_button.click()
            #Limit the search to the session of congress that bill was passed
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            try:
                link = soup.find(name='span', attrs={"class":"facet-item__value"}, string=re.compile(session)).previous.attrs['href']
            except:
                #print(bill_name, "No CBO estimate")
                continue
            browser.get(home_url + link)
            #cbo.gov has strings as S. 1582 rather than S.1582 so we must
            #   add a space to match the text
            split = name.split(sep='.')
            if len(split) < 3:
                new_name = split[0] + '. ' + split[1]
            else:
                new_name = split[0]+'.'+split[1]+'. ' + split[2]
            #Get the link for the bill's cost estimate page and navigate to the page
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            try:
                link = soup.find(name='a', string=re.compile(new_name)).attrs['href']
            except:
                #print(bill_name, "Failed to get bill's cost estimate page")
                continue
            browser.get(home_url + link)
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            year = int(soup.find("time").string.split()[-1])
            #Navigate to the pdf
            try:
                pdf_link = soup.find(name='a', string="View Document").attrs['href']
            except exception as e:
                #print(bill_name, 'failed to get the pdf link')
                continue
            browser.get(home_url + pdf_link)
            #Extract the text from the pdf to start parsing for costs/revenues
            urlretrieve(home_url + pdf_link, "pdfs/temp.pdf")
            try:
                text = textract.process("pdfs/temp.pdf").decode("utf-8")
            except:
                #print(bill_name, "Error exracting text from pdf")
                continue
            #Put the dash back in the 1999-2000 that textract accidentally takes
            #   out.
            text = re.sub(r"(\d{4})(\d{4})", r"\1-\2", text)
            try:
                summary = re.compile(r"SUMMARY.*?[A-Z ]{12,}", re.DOTALL).findall(text)[0]
            except:
                #print(bill_name, 'No "ESTIMATED COST" section')
                continue
            #Split the summary into sentences
            sentences = re.compile(r"\. [A-Z]|\.\n[A-Z]").split(summary)
            #Find if the sentence has the word total in it.
            #   if it does, take the last $ as the total cost
################################################################################
#First for costs                                                               #
################################################################################
            first_year, last_year = None, None
            for i, sentence in enumerate(sentences):
                try:
                    dollar_strings = re.compile(r"\$\d+(?:,\d+)?(?:\.\d+)?\n? ?(?:billion|million)?", re.IGNORECASE).findall(sentence)
                except:
                    #print(bill_name, "couldn't find dollar string")
                    continue
                for dollar_string in dollar_strings:
                    last_dollar, last_last_year, last_first_year = dollar, last_year, first_year
                    first_year, last_year = None, None
                    #print(dollar_string)
                    digits = re.compile(r"\d+(?:,\d+)?(?:\.\d+)?").findall(dollar_string)[0].replace(',','').replace('\n',' ')
                    dollar = float(digits)
                    if bool(re.compile("billion").search(dollar_string)):
                        dollar *= 1000000000
                    elif bool(re.compile("million").search(dollar_string)):
                        dollar *= 1000000
                    #This if statement is complicated because in the paragraph
                    #   referring to a cost or revenue, the cost-keyword or
                    #   revenue-key word can come at the beginning of the sentence
                    #   with multiple listed costs or revenues. But sometimes a
                    #   cost-keyword and revenue-keyword occur in the same
                    #   sentence so the most recent keyword must not be revenue-
                    #   if we're looking for cost and vice-versa
                    #stop undoing now
                    if bool(re.compile(r"(?:cost|provides|(?:additional|increase|resul)[ a-z\-]*\n*[ a-z\-]*(?:spending|outlay)|discretion[ a-z\-]*\n*[ a-z\-]*spending|reduc[ a-z\-]*\n*[ a-z\-]*revenue|appropriat|authori|and premium payments|revenue[ a-z\-]*\n*[ a-z\-]losses).*"+dollar_string[1:], re.IGNORECASE | re.DOTALL).search(sentence)) and not bool(re.compile(r"(?:(?:additional|increase|resul)[ a-z\-]*\n*[ a-z\-]*(?:sav|revenue|collection|assessments)|(?:reduc|decrease)[ a-z\-]*\n*[ a-z\-]*(?:cost|spend|outlay)|(?:cost|spend|outlay)[ a-z\-]*\n*[ a-z\-]*decrease|(?:offsetting|rais)[ a-z\-]*\n*[ a-z\-]*(?:collect|receipts))[^\$]+"+r"\$"+dollar_string[1:], re.IGNORECASE | re.MULTILINE).search(sentence)):
                        #If the dollar_string is nested in parentheses, don't
                        #   count it as a cost
                        if bool(re.compile(r"\([^\)]*"+dollar_string[1:]).search(sentence)):
                            #skip to next dollar_string
                            continue
                        cost += dollar
                        #Sometimes there is an estimate that overlaps another
                        #   estimate e.g. $X from 2000-2003 and $Y from 2000-2010
                        #   so in this following code we remove $X from the total
                        #   cost estimate
                        try:
                            first_year = int(re.compile(dollar_string[1:]+r"[^\$-]+?\d{4}").findall(re.compile(dollar_string[1:]+r"[^\$-]+?\d{4}[^\.]+?\d{4}").findall(sentence)[0])[0][-4:])
                            #print(dollar_string, first_year)
                        except:
                            #No first year
                            pass
                        try:
                            last_year = int(re.compile(dollar_string[1:]+r"[^\$]+(?:\d{4}-)?\d{4}").findall(sentence)[0][-4:])
                            #print(dollar_string, last_year)
                        except:
                            #No last year
                            pass
                        if last_year is not None and last_last_year is not None:
                            if first_year is not None and last_first_year is not None:
                                if first_year <= last_first_year and last_year>=last_last_year:
                                    cost -= last_dollar
                            else:
                                if last_last_year > year and last_year > last_last_year:
                                    cost -= last_dollar
                        #If cost or revenue is yearly, cumulate it according to the
                        #   number of years that have occurred since the year after
                        #   the passing of the bill (or as is specified in the text)
                        if bool(re.compile(dollar_string[1:] + r".*?(?:each[ a-z]{1,25}year|a year|annually)").search(sentence)):
                            if last_year is not None:
                                end_year = last_year
                            else:
                                end_year = date.today().year
                            if first_year is not None:
                                begin_year = first_year
                            else:
                                begin_year = year+1
                            #Add one to include the endpoints
                            cost += (1+end_year - begin_year)*dollar - dollar
                        #If at some point they cite the total expense of a bill
                        #   we want to take that as the cost and not double count
                        #   any of the pieces previously mentioned. That's also
                        #   the reason for the else:continue; break sequence below
                        #if bool(re.compile(r"total.{1,21}?\$"+dollar_string[1:], re.IGNORECASE).search(sentence)):
                        #    cost = dollar
                        #    print(bill_name, "used total option")
                        #    break
                #else:
                #    continue
                #break
################################################################################
#Now for revenues                                                              #
################################################################################
            for i, sentence in enumerate(sentences):
                try:
                    dollar_strings = re.compile(r"\$\d+(?:,\d+)?(?:\.\d+)?(?: billion| million)?", re.IGNORECASE).findall(sentence)
                except:
                    #print(bill_name, "couldn't find dollar string")
                    continue
                for dollar_string in dollar_strings:
                    last_dollar, last_last_year, last_first_year = dollar, last_year, first_year
                    first_year, last_year = None, None
                    digits = re.compile(r"\d+(?:,\d+)?(?:\.\d+)?").findall(dollar_string)[0].replace(',','').replace('\n',' ')
                    dollar = float(digits)
                    if bool(re.compile("billion").search(dollar_string)):
                        dollar *= 1000000000
                    elif bool(re.compile("million").search(dollar_string)):
                        dollar *= 1000000
                    #This if statement is complicated because in the paragraph
                    #   referring to a cost or revenue, the cost-keyword or
                    #   revenue-key word can come at the beginning of the sentence
                    #   with multiple listed costs or revenues. But sometimes a
                    #   cost-keyword and revenue-keyword occur in the same
                    #   sentence so the most recent keyword must not be revenue-
                    #   if we're looking for cost and vice-versa
                    if bool(re.compile(r"(?:(?:additional|increase|resul)[ a-z\-]*\n*[ a-z\-]*(?:revenue|collection|assessments)|sav|(?:reduc|decrease)[ a-z\-]*\n*[ a-z\-]*(?:cost|spend|outlay)|(?:cost|spend|outlay)[ a-z\-]*\n*[ a-z\-]*decrease|(?:offsetting|rais)[ a-z\-]*\n*[ a-z\-]*(?:collection|receipts)).*"+dollar_string[1:], re.IGNORECASE | re.DOTALL).search(sentence)) and not bool(re.compile(r"(?:cost|provides|(?:additional|increase|resul)[ a-z\-]*\n*[ a-z\-]*(?:spending|outlay)|reduc[ a-z\-]*\n*[ a-z\-]*revenue|appropriat|and premium payments)[^\$]+"+r"\$"+dollar_string[1:], re.IGNORECASE | re.MULTILINE).search(sentence)):
                        #If the dollar_string is nested in parentheses, don't
                        #   count it as a cost
                        if bool(re.compile(r"\([^\)]*"+dollar_string[1:]).search(sentence)):
                            #skip to next dollar_string
                            continue
                        revenue += dollar
                        #Sometimes there is an estimate that overlaps another
                        #   estimate e.g. $X from 2000-2003 and $Y from 2000-2010
                        #   so in this following code we remove $X from the total
                        #   cost estimate
                        try:
                            first_year = int(re.compile(dollar_string[1:]+r"[^\$-]+?\d{4}").findall(re.compile(dollar_string[1:]+r"[^\$-]+?\d{4}[^\.]+?\d{4}").findall(sentence)[0])[0][-4:])
                            #print(dollar_string, first_year)
                        except:
                            #No first year
                            pass
                        try:
                            last_year = int(re.compile(dollar_string[1:]+r"[^\$]+(?:\d{4}-)?\d{4}").findall(sentence)[0][-4:])
                            #print(dollar_string, last_year)
                        except:
                            #No last year
                            pass
                        if last_year is not None and last_last_year is not None:
                            if first_year is not None and last_first_year is not None:
                                if first_year <= last_first_year and last_year>=last_last_year:
                                    revenue -= last_dollar
                            else:
                                if last_last_year > year and last_year > last_last_year:
                                    revenue -= last_dollar
                        #If cost or revenue is yearly, cumulate it according to the
                        #   number of years that have occurred since the year after
                        #   the passing of the bill (or as is specified in the text)
                        if bool(re.compile(dollar_string[1:] + r".*?(?:each[ a-z]{1,25}year|a year|annually)").search(sentence)):
                            if last_year is not None:
                                end_year = last_year
                            else:
                                end_year = date.today().year
                            if first_year is not None:
                                begin_year = first_year
                            else:
                                begin_year = year+1
                            #Add one to include the endpoints
                            revenue += (1+end_year - begin_year)*dollar - dollar
                        #If at some point they cite the total expense of a bill
                        #   we want to take that as the cost and not double count
                        #   any of the pieces previously mentioned. That's also
                        #   the reason for the else:continue; break sequence below
                        #if bool(re.compile(r"total.{1,21}?\$"+dollar_string[1:], re.IGNORECASE).search(sentence)):
                        #    revenue = dollar
                        #    break
                #else:
                #    continue
                #break

            if cost!=0 or revenue!=0:
                count += 1
                #print(bill_name, "cost:", cost)
                #print(bill_name, "revenue:", revenue)



            #print(bill_name, re.compile(r"\$\d+(?:,\d+)?(?:\.\d+)?(?: billion| million)?", re.IGNORECASE | re.DOTALL | re.MULTILINE).findall(summary))
            #important_bills.append(bill_name)
            #costs.append(cost)
            #revenues.append(revenue)
            if cost < 0:
                cost = 0
            if revenue < 0:
                revenue = 0
            bill_costs[bill_name]= revenue - cost
    finally:
        browser.close()
    #print("count:", count)
    #running_time = time.time()-start_time
    #print("Time to run:", int(running_time//60), "minutes and", int(running_time%60), "seconds")
    return bill_costs

def assign_scores(Representatives, Senators, scores):
    for Sen in Senators.keys():
        Senators[Sen]["score"] = 0
    for Rep in Representatives.keys():
        Representatives[Rep]["score"] = 0
    for bill in scores.keys():
        for Rep in Representatives.keys():
            if bill in Representatives[Rep]["Yeas"]:
                Representatives[Rep]["score"] += scores[bill]
        for Sen in Senators.keys():
            if bill in Senators[Sen]["Yeas"]:
                Senators[Sen]["score"] += scores[bill]

def create_csv(Representatives, Senators):
    names = list(Representatives.keys()) + list(Senators.keys())
    positions = [Representatives[Rep]["Position"] for Rep in Representatives.keys()] + [Senators[Sen]["Position"] for Sen in Senators.keys()]
    parties = [Representatives[Rep]["Party"] for Rep in Representatives.keys()] + [Senators[Sen]["Party"] for Sen in Senators.keys()]
    states = [Representatives[Rep]["State"] for Rep in Representatives.keys()] + [Senators[Sen]["State"] for Sen in Senators.keys()]
    tenures = [len(Representatives[Rep]["Sessions"]) for Rep in Representatives.keys()] + [len(Senators[Sen]["Sessions"]) for Sen in Senators.keys()]
    scores = [Representatives[Rep]["score"] for Rep in Representatives.keys()] + [Senators[Sen]["score"] for Sen in Senators.keys()]
    births = [Representatives[Rep]["Birth"] for Rep in Representatives.keys()] + [Senators[Sen]["Birth"] for Sen in Senators.keys()]
    df = pd.DataFrame({"Name":pd.Series(names), "Position":pd.Series(positions), "Party":pd.Series(parties), "State":pd.Series(states), "Tenure":pd.Series(tenures), "Score":pd.Series(scores), "YOB":pd.Series(births)})
    df.to_csv("scores_data.csv")

"""
if __name__ == "__main__":
    start_times = time.time()
    Representatives, Senators = quick_members_of_congress()
    bill_names = get_bill_names()
    bill_names = bill_names[0] + bill_names[1]
    get_representative_voting_records(Representatives)
    get_senator_voting_records(Senators)
    scores = get_cost_estimates(bill_names)
    assign_scores(Representatives, Senators, scores)
    create_csv(Representatives, Senators)
    running_time = time.time()-start_time
    print("Time to run:", int(running_time//(60*60)), "hours and", int(running_time%(60*60)//60), "minutes")
"""
