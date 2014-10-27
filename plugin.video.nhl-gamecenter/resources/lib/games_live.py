from xml.dom.minidom import parseString
from datetime import datetime
import time
import pickle

from dateutil import tz
from resources.lib.common import *


def getLiveGames(live):

    #Download live.xml
    downloadedXML =''
    for i in range(1, 2):
        cj = cookielib.LWPCookieJar()
        cj.load(os.path.join(ADDON_PATH_PROFILE, 'cookies.lwp'),ignore_discard=True)
        url = "http://gamecenter.nhl.com/nhlgc/servlets/games"
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        if live:
            response = opener.open(url, urllib.urlencode({'format':'xml','app':'true'}))
        else:
            response = opener.open(url, urllib.urlencode({'format':'xml'}))
        downloadedXML = response.read()
        print downloadedXML
        
        #Try to login again if File not accessible
        if "<code>noaccess</code>" in downloadedXML:
            print "No access to XML file"
            login()
            continue
        else:
            print "Download successful"
            break
    else:
        print "Login failed. Check your login credentials."
    
    
    #Parse the xml file
    xml = parseString(downloadedXML)
    games = xml.getElementsByTagName('game')
    
    if not live:
        games = reversed(games)
    
    #Get teamnames
    teams = getTeams()
        
    #Invert teams dictionary
    teams2 = {}
    for team in teams.keys():
        teams2[teams[team][4]] = team
    
    #List of live games
    gameList = []

    for game in games:
        #Setup variables
        gid = game.getElementsByTagName('gid')[0].childNodes[0].nodeValue
        season = game.getElementsByTagName('season')[0].childNodes[0].nodeValue
        Type = game.getElementsByTagName('type')[0].childNodes[0].nodeValue
        Id = game.getElementsByTagName('id')[0].childNodes[0].nodeValue
        awayTeam = game.getElementsByTagName('awayTeam')[0].childNodes[0].nodeValue
        homeTeam = game.getElementsByTagName('homeTeam')[0].childNodes[0].nodeValue
        date = game.getElementsByTagName('date')[0].childNodes[0].nodeValue
        startTime = time.strptime(date,"%Y-%m-%dT%H:%M:%S.000")
        
        #Game title
        title = ''
        
        #Check if stream is available
        try:
            if game.getElementsByTagName('hasProgram')[0].childNodes[0].nodeValue == 'true':
                gameStarted = True
            else:
                gameStarted = False
        except:
            gameStarted = False
        
        #Skip games that don't have a stream in 'Latest Games'
        if not live and not gameStarted:
            continue
        
        #Versus string
        versus = 31400 
        if ALTERNATIVEVS == 'true':
            versus = 31401
        
        if gameStarted and live:
            #Displayed titlestring
            if awayTeam in teams and homeTeam in teams:
                title = "LIVE - " + teams[awayTeam][TEAMNAME] + " " + LOCAL_STRING(versus) + " " + teams[homeTeam][TEAMNAME]
            else:
                title = "LIVE - " + awayTeam + " " + LOCAL_STRING(versus) + " " + homeTeam
        else:
            #Convert the time to the local timezone
            date = datetime.fromtimestamp(time.mktime(startTime))
            date = date.replace(tzinfo=tz.gettz('America/New_York'))
            datelocal = date.astimezone(tz.tzlocal()).strftime(xbmc.getRegion('dateshort')+' '+xbmc.getRegion('time').replace('%H%H','%H').replace(':%S',''))

            #Displayed titlestring
            if awayTeam in teams and homeTeam in teams:
                title = datelocal + ': ' + teams[awayTeam][TEAMNAME] + " " + LOCAL_STRING(versus) + " " + teams[homeTeam][TEAMNAME]
            else:
                title = datelocal + ': ' + awayTeam + " " + LOCAL_STRING(versus) + " " + homeTeam
        
        #Add to the list of live games
        gameList.append([gid, season, Type, Id, gameStarted, title, homeTeam, awayTeam])
    
    
    #Save the gameList
    pickle.dump(gameList, open(os.path.join(ADDON_PATH_PROFILE, 'live'),"wb"))
    
    return gameList
    
    
def getLiveGameLinks(url):
    
    #Load the list of games
    gameList = pickle.load(open(os.path.join(ADDON_PATH_PROFILE, 'live'),"rb"))
    
    #Get the url of the game
    for game in gameList:
        if game[0] in url:
            #Add teamnames to the list
            homeTeam = game[6]
            awayTeam = game[7]
            linkList = [[homeTeam, awayTeam]]
            
            for feed in [2,4]:
                #Get the m3u8 URL
                cj = cookielib.LWPCookieJar()
                cj.load(os.path.join(ADDON_PATH_PROFILE, 'cookies.lwp'),ignore_discard=True)
                publishPointURL = "http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=" + game[1] + game[2].zfill(2) + game[3].zfill(4) + "&gs=live&ft=" + str(feed) + "&nt=1"
                opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
                opener.addheaders = [('User-Agent', USERAGENT)]
                response = opener.open(publishPointURL, urllib.urlencode({'app':'true'}))
                downloadedXML = response.read()

                xml = parseString(downloadedXML)
                m3u8URL = xml.getElementsByTagName('path')[0].childNodes[0].nodeValue
            
                #Quality settings
                if QUALITY == 4 or 'bestquality' in url:
                    if "live" in url:#fix needed to download the key below 
                        m3u8URL = m3u8URL.replace('_ced.', '_5000_ced.')
                elif QUALITY == 3 or '5000K' in url:
                    m3u8URL = m3u8URL.replace('_ced.', '_5000_ced.')
                elif QUALITY == 2 or '3000K' in url:
                    m3u8URL = m3u8URL.replace('_ced.', '_3000_ced.')
                elif QUALITY == 1 or '1600K' in url:
                    m3u8URL = m3u8URL.replace('_ced.', '_1600_ced.')
                else:
                    m3u8URL = m3u8URL.replace('_ced.', '_800_ced.')
            
                #
                if 'condensed' in url:
                    m3u8URL = m3u8URL.replace('_whole_', '_condensed_')
                elif 'highlights' in url:
                    m3u8URL = m3u8URL.replace('_whole_', '_continuous_')
                
                #Header for needed for first decryption key
                header = {'Cookie' : 'nlqptid=' +  m3u8URL.split('?', 1)[1], 'User-Agent' : 'Safari/537.36 Mozilla/5.0 AppleWebKit/537.36 Chrome/31.0.1650.57', 'Accept-Encoding' : 'gzip,deflate', 'Connection' : 'Keep-Alive'}
            
                #Live games need additional cookies
                if "live" in url:
                    #Download the m3u8
                    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
                    opener.addheaders = [('Cookie', 'nlqptid=' +  m3u8URL.split('?', 1)[1])]
                    values = {}
                    login_data = urllib.urlencode(values)
                    response = opener.open(m3u8URL, login_data)
                    m3u8File = response.read()
                
                    #Download the keys
                    url2=''
                    for line in m3u8File.split("\n"):
                        searchTerm = "#EXT-X-KEY:METHOD=AES-128,URI="
                        if searchTerm in line:
                            url2=line.strip().replace(searchTerm,'')[1:-1]
                    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
                    values = {}
                    login_data = urllib.urlencode(values)
                    response = opener.open(url2, login_data)

                    #Remove unneeded cookies
                    remove = []
                    for cookie in cj:
                        if cookie.name != "nlqptid" and "as-live" not in cookie.name:
                            remove.append(cookie)
                    for cookie in remove:
                        cj.clear(cookie.domain, cookie.path, cookie.name)
            
                    #Create header needed for playback
                    cookies = ''
                    for cookie in cj:
                        cookies = cookies + cookie.name + "=" + cookie.value + "; "
            
                    header = {'Cookie' : cookies, 'User-Agent' : 'Safari/537.36 Mozilla/5.0 AppleWebKit/537.36 Chrome/31.0.1650.57', 'Accept-Encoding' : 'gzip,deflate', 'Connection' : 'Keep-Alive'}
            
                #Home/Awaay url
                if feed == 2:
                    linkList.append([LOCAL_STRING(31320), m3u8URL + "|" + urllib.urlencode(header)])
                else:
                    linkList.append([LOCAL_STRING(31330), m3u8URL + "|" + urllib.urlencode(header)])
            
            #Away url (Reliabile?)
            #linkList.append([LOCAL_STRING(31330),  m3u8URL.replace('_h_', '_a_') + "|" + urllib.urlencode(header)])
            
            #French streams (experimental)
            """"
            if game[4] != '' and (homeTeam == 'MON' or homeTeam == 'OTT'):
                home_url = home_url.replace('/nhl/', '/nhlfr/')
                home_url = home_url.replace('nlds138', 'nlds60')
                linkList.append([LOCAL_STRING(31320) + ' (' + LOCAL_STRING(31340) + ')', home_url + "|User-Agent=" + USERAGENT])
            if game[5] != '' and (awayTeam == 'MON' or awayTeam == 'OTT'):
                away_url = away_url.replace('/nhl/', '/nhlfr/')
                away_url = away_url.replace('nlds138', 'nlds60')
                linkList.append([LOCAL_STRING(31330) + ' (' + LOCAL_STRING(31340) + ')', away_url + "|User-Agent=" + USERAGENT])
            """
            
            #No streams available
            """"
            if game[4] == '' and game[5] == '':
                if game[0][:5] == 'FINAL':
                    linkList.append([LOCAL_STRING(31370),''])
                else:
                    linkList.append([LOCAL_STRING(31380),''])
            """
            break
    
    return linkList