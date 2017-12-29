import numpy as np
import pandas as pd
import requests
import time

#api key and base constants
API_BASE = "https://na1.api.riotgames.com/lol/"
API_BASE_CHAMPIONGG = "http://api.champion.gg/v2/champions/"
API_KEY = "api_key=RGAPI-8fedf7f8-7c95-43ca-a638-1090b1d32126"
API_KEY_CHAMPIONGG = "api_key=977d33e558311e9fcd259e4314d4115c"

SELF_ID = 37871085 #my account id for idioticfuse, this will be the seed

#request url constants
MATCHES_REQUEST_ACCOUNT = API_BASE + "match/v3/matchlists/by-account/"
MATCHES_REQUEST_MATCHID = API_BASE + "match/v3/matches/"
CHAMPIONS_REQUEST = API_BASE + "static-data/v3/champions?locale=en_US&dataById=false"
MASTERY_REQUEST = API_BASE + "champion-mastery/v3/champion-masteries/by-summoner/"
SUMMONER_REQUEST = API_BASE + "summoner/v3/summoners/by-account/"
LEAGUE_REQUEST = API_BASE + "league/v3/positions/by-summoner/"
CHAMPION_REQUEST_GG = "?champData=averageGames,overallPerformanceScore,matchups&limit=200&elo="

#data file save paths
MATCH_ID_FILE_PATH = "data/match_id.csv"
USER_ID_FILE_PATH = "data/user_id.csv"
CONTINUE_FILE_PATH = "data/get_id_continue.csv"
CHAMPION_FILE_PATH = "data/champions.csv"

MAX_MATCH_IDS = 10000
RANKED_QUEUE = 420 #lol its lit


ROLE_ORDER = {"TOP":0, "JUNGLE":1, "MIDDLE":2, "DUO_CARRY":3, "DUO_SUPPORT":4}
ROLE_LIST = ["TOP", "JUNGLE", "MIDDLE", "DUO_CARRY", "DUO_SUPPORT"]
TIER_ORDER = {"BRONZE":0, "SILVER":1, "GOLD":2, "PLATINUM":3, "DIAMOND":4, "MASTER":5}
TIER_LIST = ["BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER"]
RANK_ORDER = {"V":0, "IV":1, "III":2, "II":3, "I":4}
WIN_LOSS_ORDER = {"Win":1, "Fail":0}

'''
This function collects summoner and match ids by branching out from the original id.
We find all unique summoner ids in the 20 previous matches with the original id, then we find
the unique summoner ids in the new summoner id's matches, and so on...
We search until we hit thresh_size amount of unique match ids, then we store it to
our preset file name as a CSV. It is important that we pause 1.25s after every request so
we don't violate the request limits
'''
def get_ids(origin_id, thresh_size, cont=False): #note: this only collects RANKED data
    if cont == True: #if we are continuing from last time
        df_id, df_matches = pd.read_csv(USER_ID_FILE_PATH), pd.read_csv(MATCH_ID_FILE_PATH),
        df_continue = pd.read_csv(CONTINUE_FILE_PATH)
        id_set = set(df_id.values[:,1])
        match_set = set(df_matches.values[:,1])
        next_id = df_continue.values[:,1].tolist()
    else: #we start from scratch
        id_set = set([origin_id]) #set of unique summoner ids
        match_set = set() #set of unique match ids
        next_id = [origin_id] #random 'queue' of summoner ids to visit
    passes = 0 #for debugging purposes

    while len(match_set) < thresh_size:
        if (len(next_id) == 0):
            print("Ran out of summoner ids")
            break
        passes += 1
        print("pass ", passes, ": matches: ", len(match_set), ", ids: ", len(id_set))
        randindex = np.random.randint(0, len(next_id)) #we sample randomly from our 'queue'
        tmp_id = next_id.pop(randindex)
        req = requests.get(MATCHES_REQUEST_ACCOUNT+str(tmp_id)+"?queue=420&"+API_KEY)
        time.sleep(1.25)
        if req.status_code != 200:
            print("error requesting matches by account data")
            continue
        matchlist = req.json()['matches']
        for i in matchlist[0:5]: #only take the 5 most recent games so we don't end up going too far back in time
            if i['queue'] == RANKED_QUEUE and i['season'] == 9 and i['gameId'] not in match_set:
                req = requests.get(MATCHES_REQUEST_MATCHID+str(i['gameId'])+"?"+API_KEY)
                time.sleep(1.25)
                if req.status_code != 200: continue
                match_set.add(i['gameId'])
                match = req.json()['participantIdentities']
                for j in match:
                    if j['player']['accountId'] not in id_set:
                        id_set.add(j['player']['accountId'])
                        next_id.append(j['player']['accountId'])
    #we now have our summoner and match id sets, let's store them as a csv
    df_id, df_matches = pd.DataFrame([i for i in id_set]), pd.DataFrame([i for i in match_set])
    df_continue = pd.DataFrame(next_id)
    df_continue.to_csv(CONTINUE_FILE_PATH)
    df_id.to_csv(USER_ID_FILE_PATH)
    df_matches.to_csv(MATCH_ID_FILE_PATH)


'''
given two champion ids and rank as a string, returns two dictionaries:
champion_winrate
champion_playrate
champion_percentRolePlayed
matchup_winrate
overallPerformanceScore
Total API requests: 2(GG)
'''
def generate_champion_data(champion1, champion2, rank, role):
    champ_dict1, champ_dict2 = {}, {}
    #get data for champ1
    req = requests.get(API_BASE_CHAMPIONGG+str(champion1)+CHAMPION_REQUEST_GG+rank+"&"+API_KEY_CHAMPIONGG)
    time.sleep(0.2)
    if req.status_code != 200: return -1
    data = req.json()
    for i in data:
        if i['_id']['role'] == role: #we found which one we want
            champ_dict1['champion_winrate'] = i['winRate']
            champ_dict1['champion_playrate'] = i['playRate']
            champ_dict1['champion_percentRolePlayed'] = i['percentRolePlayed']
            champ_dict1['champion_overallPerformanceScore'] = i['overallPerformanceScore']
            for j in i['matchups'][role]:
                if j['champ2_id'] == champion2:
                    champ_dict1['champion_matchupWinrate'] = j['champ1']['winrate']
                    champ_dict2['champion_matchupWinrate'] = 1-j['champ1']['winrate']
                    break
            break
    #get data for champ2
    req = requests.get(API_BASE_CHAMPIONGG+str(champion2)+CHAMPION_REQUEST_GG+rank+"&"+API_KEY_CHAMPIONGG)
    time.sleep(0.2)
    if req.status_code != 200: return -1
    data = req.json()
    for i in data:
        if i['_id']['role'] == role: #we found which one we want
            champ_dict2['champion_winrate'] = i['winRate']
            champ_dict2['champion_playrate'] = i['playRate']
            champ_dict2['champion_percentRolePlayed'] = i['percentRolePlayed']
            champ_dict2['champion_overallPerformanceScore'] = i['overallPerformanceScore']
            break
    return champ_dict1, champ_dict2

'''
given a player id and champion id, compiles the last 500 games by the player, and returns the following dictionary:
wins_last2(ranked) - feature for tilt
wins_last5(ranked)*
wins_last10(ranked)*
gamesplayed(ranked)*
championPoints*
summonerLevel
rank
* = champion specific
Total API Requests: 18(Riot)
'''
def generate_player_features(player, championId, matchId):
    player_dict = {} #setup dictionary that we will return
    req = requests.get(SUMMONER_REQUEST+str(player)+"?"+API_KEY) #gets summoner id and level
    time.sleep(1.25)
    if req.status_code != 200: return -1
    player_dict['summonerId'] = req.json()['id']
    player_dict['summonerLevel'] = req.json()['summonerLevel']
    
    #gets champion points
    req = requests.get(MASTERY_REQUEST+str(player_dict['summonerId'])+"/by-champion/"+str(championId)+"?"+API_KEY)
    time.sleep(1.25)
    if req.status_code != 200: return -1
    player_dict['championPoints'] = req.json()['championPoints']
    
    req = requests.get(LEAGUE_REQUEST+str(player_dict['summonerId'])+"?"+API_KEY) #gets rank of player
    time.sleep(1.25)
    if req.status_code != 200: return -1
    for i in req.json():
        if i['queueType'] == "RANKED_SOLO_5x5":
            player_dict['rank'] = TIER_ORDER[i['tier']]*500+(4-RANK_ORDER[i['rank']])*100+i['leaguePoints']
            player_dict['tier'] = i['tier']
            break
    
    #now, we go through the last 200 ranked games played, and generate the rest of the features
    player_dict['gamesPlayed'] = 0
    player_dict['wins_last2'] = 0
    player_dict['wins_last5'] = 0
    games_recorded = 0
    tilt_recorded = 0
    flag = False
    for i in [0, 100, 200]:
        if i['gameId'] == matchId: flag = True
        if flag == False: continue
        req = requests.get(MATCHES_REQUEST_ACCOUNT+str(player)+"?queue=420&beginIndex="+str(i)+"&"+API_KEY)
        time.sleep(1.25)
        if req.status_code != 200: return -1
        for j in req.json()['matches']:
            if tilt_recorded < 2:
                tilt_recorded += 1
                req = requests.get(MATCHES_REQUEST_MATCHID+str(j['gameId'])+'?'+API_KEY)
                time.sleep(1.25)
                if req.status_code != 200: return -1
                for k in req.json()['participantIdentities']:
                    if k['player']['accountId'] == player: #found a match
                        if k['participantId'] < 6:
                            player_dict['wins_last2'] += WIN_LOSS_ORDER[req.json()['teams'][0]['win']]
                        else:
                            player_dict['wins_last2'] += WIN_LOSS_ORDER[req.json()['teams'][1]['win']]
                        break
            if j['champion'] != championId: continue #we don't care about games not involving our champion
            if games_recorded < 10: #if part of most recent 10 games, we have to find wins
                games_recorded += 1
                req = requests.get(MATCHES_REQUEST_MATCHID+str(j['gameId'])+'?'+API_KEY)
                time.sleep(1.25)
                if req.status_code != 200: return -1
                for k in req.json()['participantIdentities']:
                    if k['player']['accountId'] == player: #found a match
                        if k['participantId'] < 6:
                            player_dict['wins_last5'] += WIN_LOSS_ORDER[req.json()['teams'][0]['win']]
                        else:
                            player_dict['wins_last5'] += WIN_LOSS_ORDER[req.json()['teams'][1]['win']]
                        break
            player_dict['gamesPlayed'] += 1
    return player_dict

'''
Given a match id, generates two feature sets for that match - one for each team. The features we are interested in are:
wins_last2(ranked). - feature for tilt
wins_last5(ranked)*.
wins_last10(ranked)*.
gamesplayed(ranked)*.
championPoints*.
summonerLevel.
rank.
champion_winrate*<
champion_playrate*<
champion_percentRolePlayed*<
champion_overallPerformanceScore*<
matchup_winrate*<

* = champion specific
. = player specific
< = rank specific
Total API Requests: 181(Riot), 20(GG) - 5 minutes without multiple API Keys
Generates 2 samples
'''
def generate_featureset(match):
    req = requests.get(MATCHES_REQUEST_MATCHID+str(match)+"?"+API_KEY)
    time.sleep(1.25)
    if req.status_code != 200: return -1
    match_data = req.json()
    #generate the two teams' player dictionaries, in order of [top jg mid adc sup]
    team = {0:{}, 1:{}}
    #generates win t/f for each team
    team[0]['win'] = WIN_LOSS_ORDER[match_data['teams'][0]['win']]
    team[1]['win'] = WIN_LOSS_ORDER[match_data['teams'][1]['win']]
    
    participantId_index_dict = {}
    for i in match_data['participants']: #generates player specific dictionary values
        if i['timeline']['lane'] == "BOTTOM": index = ROLE_ORDER[i['timeline']['role']] #generate index based on role
        else: index = ROLE_ORDER[i['timeline']['lane']]
        participantId_index_dict[i['participantId']] = index
        if i['participantId'] < 6: teamId = 0
        else: teamId = 1
        
        team[teamId][ROLE_LIST[index]] = {}
        team[teamId][ROLE_LIST[index]]['spell1Id'] = i['spell1Id']
        team[teamId][ROLE_LIST[index]]['spell2Id'] = i['spell2Id']
        team[teamId][ROLE_LIST[index]]['highestAchievedSeasonTier'] = i['highestAchievedSeasonTier']
        team[teamId][ROLE_LIST[index]]['championId'] = i['championId']
    
    for i in match_data['participantIdentities']: #generates account ids for each player
        if i['participantId'] < 6: teamId = 0
        else: teamId = 1
        team[teamId][ROLE_LIST[participantId_index_dict[i['participantId']]]]['accountId'] = i['player']['accountId']

    #generates more player and champion specific dictionary values with use of helper function
    for i in range(2): #which team?
        for j in ROLE_LIST: #which role?
            team[i][j].update(generate_player_features(team[i][j]['accountId'], team[i][j]['championId'], match))
            if i == 0:
                dict1, dict2 = generate_champion_data(team[i][j]['championId'], team[1-i][j]['championId'],
                                                     team[i][j]['tier'], j)
                team[0][j].update(dict1)
                team[1][j].update(dict2)
    #now we have our full dictionary, let's transform it into features
    return team


get_ids(SELF_ID, MAX_MATCH_IDS, cont=False)
#print(generate_featureset(2681596787))



