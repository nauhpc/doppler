#!/usr/bin/env python


"""
Desc: Main source file for the jobstats site

Authors:
    - Chance Nelson <chance-nelson@nau.edu>
    - Ian Otto <iso-ian@nau.edu>
"""


import sys
import time
from configparser import ConfigParser
from datetime import date, timedelta
from difflib import SequenceMatcher

import pygal
from flask import Flask, render_template, request, url_for, redirect

import jobstats

app = Flask(__name__)


# Get the efficiency score normalization options
config = ConfigParser()
config.read('config.ini')
 

# Get the DB args
username     = config['DB']['username']
password     = config['DB']['password']
host         = config['DB']['host']


# Init the DB connection
db = jobstats.Jobstats(host, username, password)


# Get job normalization args
config.read('config.ini')
normalize_scores_options = config['SCORES']['normalize']
normalize_by_score       = False
ideal_score              = 0

for arg in normalize_scores_options.split(' '):
    if 'score' in arg:
        normalize_by_score = True
        ideal_score        = float(config['SCORES']['ideal score'])


def normalize(score, job_count=0, since=7):
    """
    Desc: Normalize a job score based on target total scores and job counts

    Args:
        score (double): score to normalize
        job_count (int) (optional): Job count of user
        since (int) (optional) (DEPRECATED): Timeframe of score

    Returns (double):
        Normalized score based on target total score to meet in config file
    """
    # Attempt to normalize the score
    numerator   = score
    denominator = 1

    if normalize_by_score:
        denominator = ideal_score
    
    return (numerator / denominator) * 100


def getTimeframe(days):
    """
    Desc: Get a timeframe in day count from character

    Args:
        days (char): Timeframe identifier character in [W, M, Q]

    Returns (int):
        Length of timeframe in days
    """
    if days == 'M':
        days = 31
    
    elif days == 'Q':
        days = 100

    else:
        days = 7

    return days


@app.route('/accountsbargraph.svg')
def renderAccountsBarGraph():
    """
    Desc: Endpoint for the account lising bar graph on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    return renderGraph(pygal.Bar, 'account')


@app.route('/usersbargraph.svg')
def renderUsersBarGraph():
    """
    Desc: Endpoint for the user listing bar graph on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    return renderGraph(pygal.Bar, 'user')


@app.route('/userslinegraph.svg')
def renderUsersLineGraph():
    """
    Desc: Endpoint for the user listing line graph on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    return renderGraph(pygal.Line, 'user')


@app.route('/accountslinegraph.svg')
def renderAccountsLineGraph():
    """
    Desc: Endpoint for account listing line graph on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    renderGraph(pygal.Line, 'account')


def renderGraph(graph_function, data_set):
    """
    Desc: Render pygal SVG graphs for various data sets and timelines

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
        graph_function (func): Pygal function for generating the graph (box and
                               line currently officially supported)
        data_set (string): string representation of what data set to pull from
                           (supports 'cluster', 'user', and 'account')
    """
    days       = getTimeframe(request.args.get('days'))
    days_delta = 1
    
    # Only display one data point per week for timeframes above a month
    if days > 31:
        days_delta = 7

    # Render the line graph
    graph = graph_function(range=[0, 100])
 
    if days == 7:
        graph.title = data_set + ' Efficiency for the Week'
    elif days == 31:
        graph.title = data_set + ' Efficiency for the Month'
    elif days == 100:
        graph.title = data_set + ' Efficiency for the Quarter'
    else:
        graph.title = data_set + ' Efficiency'

    x_labels    = [date.today() - timedelta(i) for i in range(days, 0, days_delta * -1)]
    data_points = {}

    if data_set.lower() == 'account':
        # Get the top ten accounts
        for i in db.getTopAccounts(since=date.today()-timedelta(days) , normalize=normalize)[:10]:
            data_points[i[0]] = []

    elif data_set.lower() == 'user':
        # Get the top ten users
        for i in db.getTopUsers(since=date.today()-timedelta(days) , normalize=normalize)[:10]:
            data_points[i[0]] = []

    elif data_set.lower() == 'cluster':
        data_points = db.getClusterStats(date.today() - timedelta(days))
       
        cores  = []
        memory = []
        tLimit = []
        total  = []

        dates = data_points.keys()
        for i in x_labels:
            stat = {'cores': None, 'memory': None, 'tlimit': None, 'total': None}
            if i in dates:
                stat = data_points[i]
                for j in stat:
                    if stat[j] == 0.0:
                        stat[j] = None

            cores.append(stat['cores'])
            memory.append(stat['memory'])
            tLimit.append(stat['tlimit'])
            total.append(stat['total'])
       
            if total[-1]:
                total[-1] = normalize(total[-1])

        graph.add('cores', cores)
        graph.add('memory', memory)
        graph.add('time limit', tLimit)
        graph.add('total efficiency', total)

        return graph.render()


    # Get the daily stats for the top ten users/accounts
    for i in range(days, 0, days_delta * -1):
        d = date.today() - timedelta(i)
        
        statsOnDate = db.getFullAccountList(d, users=(data_set.lower() == 'user'))
       
        for i in statsOnDate:
            try:
                stats = statsOnDate[i]
                data_points[i].append(normalize(stats['total']))

            except KeyError:
                continue

            except:
                data_points[i].append(0.0) 

    # Add each account in alphabetical order
    for i in sorted(data_points.keys()):
        print(i)
        print(x_labels)
        if i in x_labels:
            print(i, [j for j in data_points[i] if j != 0])
            graph.add(i, [j for j in data_points[i] if j != 0])

    return graph.render()




@app.route('/accountsboxplot.svg')
def renderAccountsBoxPlot():
    """
    Desc: Endpoint for account listing line graph on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    days       = getTimeframe(request.args.get('days'))
    days_delta = 1
    
    # Only display one data point per week for timeframes above a month
    if days > 31:
        days_delta = 7

    # Render the line graph
    line_graph = pygal.Box(range=[0, 100])
 
    if days == 7:
        line_graph.title = 'Account Efficiency for the Week'
    elif days == 31:
        line_graph.title = 'Account Efficiency for the Month'
    elif days == 100:
        line_graph.title = 'Account Efficiency for the Quarter'
    else:
        line_graph.title = 'Account Efficiency'

    #line_graph.x_labels = [date.today() - timedelta(i) for i in range(days, 0, days_delta * -1)]
    accounts            = {}

    # Get the top ten accounts
    for i in db.getTopAccounts(since=date.today()-timedelta(days) , normalize=normalize)[:10]:
        accounts[i[0]] = []

    # Get the daily stats for the top ten accounts
    for i in range(days, 0, days_delta * -1):
        d = date.today() - timedelta(i)
        
        accountStatsOnDate = db.getFullAccountList(d)
       
        for i in accounts:
            try:
                stats = accountStatsOnDate[i]
                accounts[i].append(normalize(stats['total']))

            except:
                accounts[i].append(0.0) 

    # Add each account in alphabetical order
    for i in sorted(accounts.keys()):
        print(i, [j for j in accounts[i] if j != 0])
        line_graph.add(i, [j for j in accounts[i] if j != 0])

    return line_graph.render_response()


@app.route('/clusterlinegraph.svg')
def renderClusterLineGraph():
    """
    Desc: Endpoint for cluster line graph on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """   
    days       = getTimeframe(request.args.get('days'))
    days_delta = 1
   
    if days > 31:
        days_delta = 7

    line_graph = pygal.Line(x_label_rotation=30, range=[0, 100])

    if days == 7:
        line_graph.title = 'Cluster Efficiency for the Week'
    elif days == 31:
        line_graph.title = 'Cluster Efficiency for the Month'
    elif days == 100:
        line_graph.title = 'Cluster Efficiency for the Quarter'
    else:
        line_graph.title = 'Cluster Efficiency'

    line_graph.x_labels = [date.today() - timedelta(i) for i in range(days, 0, days_delta * -1)]
    stats               = db.getClusterStats(date.today() - timedelta(days))
   
    cores  = []
    memory = []
    tLimit = []
    total  = []

    dates = stats.keys()
    for i in line_graph.x_labels:
        stat = {'cores': None, 'memory': None, 'tlimit': None, 'total': None}
        if i in dates:
            stat = stats[i]
            for j in stat:
                if stat[j] == 0.0:
                    stat[j] = None

        cores.append(stat['cores'])
        memory.append(stat['memory'])
        tLimit.append(stat['tlimit'])
        total.append(stat['total'])
   
        if total[-1]:
            total[-1] = normalize(total[-1])

    line_graph.add('cores', cores)
    line_graph.add('memory', memory)
    line_graph.add('time limit', tLimit)
    line_graph.add('total efficiency', total)

    return line_graph.render_response()


@app.route('/')
@app.route('/home')
def home():
    """
    Desc: Endpoint for home page

    Args:
        view (string) (optional): What data to display in 
                                  [cluster, accounts, users]
        time (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    view      = request.args.get('view')
    time      = getTimeframe(request.args.get('time'))
    timeframe = request.args.get('time')

    top_accounts = []

    # Default to accounts view
    if not view or view in ['cluster', 'accounts']:
        top_accounts = db.getTopAccounts(since=(date.today()-timedelta(time)),
                                         normalize=normalize)[:100]

    else:
        top_accounts = db.getTopUsers(since=(date.today()-timedelta(time)), 
                                      normalize=normalize)[:100]

    account_ranks = []

    # Gather data on the top 100 accounts
    for i in top_accounts:
        accName = i[0]
      
        data = None

        if not view or view in ['cluster', 'accounts']:
            data = db.getAccountTotalScore(accName, 
                                           since=(date.today() - timedelta(time)))
       
        else:
            data = db.getUserStats(accName, 
                                   since=(date.today() - timedelta(time)))

        cores   = '-'
        memory  = '-'
        t_limit = '-'
        total   = '-'
        job_sum = '-'
        
        if data['cores']:
            cores = data['cores']

        if data['memory']:
            memory = data['memory']

        if data['tlimit']:
            t_limit = data['tlimit']
        
        if data['total']:
            total = data['total']
            total = int(normalize(total, job_count=data['jobsum']))

        if data['jobsum']:
            job_sum = data['jobsum']

        account_ranks.append([len(account_ranks)+1, accName, cores,
                              memory, t_limit, total, job_sum])

    return render_template('home.html', graph=renderGraph, box=pygal.Box, line=pygal.Line, account_ranks=account_ranks, view=view, time=timeframe)


@app.route('/account/<account_name>/linegraph.svg')
def renderAccountLineGraph(account_name):
    """
    Desc: Endpoint for the account-centric line graph

    Args:
        account_name (string): Account to query
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    days = int(request.args.get('days'))
  
    data = db.getAccountStats(account_name, since=(date.today() - timedelta(days)))

    # Render the line graph
    line_graph = pygal.Line(x_label_rotation=20, range=[0, 100])
    line_graph.title = account_name + ' Efficiency over Time'
    line_graph.x_labels = sorted(data.keys())

    cores  = [data[i]['cores']  for i in data]
    memory = [data[i]['memory'] for i in data]
    tLimit = [data[i]['tlimit'] for i in data]
    total  = [data[i]['total']  for i in data]
    
    for index, i in enumerate(total):
        if i:
            total[index] = normalize(i)

    line_graph.add('cores', cores)
    line_graph.add('memory', memory)
    line_graph.add('time limit', tLimit)
    line_graph.add('total', total)

    return line_graph.render_response()


@app.route('/account/<account_name>/userpiegraph.svg')
def renderAccountUsersGraph(account_name):
    """
    Desc: Endpoint for the accont users job distribution pie graph

    Args:
        account_name (string): Account to query
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    days = int(request.args.get('days'))

    data = db.getAccountUserJobCounts(account_name, since=date.today()-timedelta(days))

    # Render the pie graph
    pie_graph = pygal.Pie()
    pie_graph.title = 'Jobs Per User'
    for i in sorted(data.keys()):
        pie_graph.add(i, [{
            "value": data[i],
            "xlink": url_for("viewUser", user_name=i)
        }])
    
    return pie_graph.render_response()


@app.route('/account')
@app.route('/account/<account_name>')
def viewAccount(account_name=None):
    """
    Desc: Endpoint for the account view page

    Args:
        account (string) (optional): Account to query, extracted from URL
                                     args.
        account_name (string) (optional): Account to query
        time (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    # Make sure we have an account name from either the url or the args
    # It will be in the args if we're coming from a search
    if not account_name:
        # Find the most similar account to the searched name
        search = request.args.get('search')

        if not search:
            search = request.args.get('account')

        if not search:
            return redirect(url_for('home'))

        start    = time.time()
        accounts = db.getAccountList()
        start    = time.time()

        similarities = [SequenceMatcher(None, search, i).ratio() for i in accounts]
        account_name = accounts[similarities.index(max(similarities))]

    days      = getTimeframe(request.args.get('time'))
    timeframe = request.args.get('time')
    
    since = date.today() - timedelta(days)
    total = db.getAccountTotalScore(account_name, since=since)

    for i in total:
        if total[i] == 0:
            total[i] = '-'

    users = {}
    user_list = db.getAccountUsers(account_name)

    for user in user_list:
        users[user] = db.getUserStats(user, account_name, since=since)
        
        for element in users[user].keys():
            if users[user][element] == 0:
                users[user][element] = '-'

    # Render the account view template
    return render_template('account.html', account_name=account_name, users=users, total=total, time=timeframe, timeframe=days)


@app.route('/user/<user_name>/linegraph.svg')
def renderUserAccountLineGraph(user_name, account=None):
    """
    Desc: Endpoint for the account line graph, displaying indiviual user
          efficiencies

    Args:
        user_name (string): Username to query
        account_name (string) (optional): Account to query, used to narrow
                                          down search for users with multiple
                                          slurm accounts
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    days    = int(request.args.get('days'))
    account = request.args.get('account')

    data = db.getUserStats(user_name, account, 
                           since=(date.today() - timedelta(days)), 
                           as_list=True)

    # Render the line graph
    line_graph = pygal.Line(x_label_rotation=20, range=[0, 100])
    line_graph.title = user_name + ' ' + account + ' Efficiency over Time'
    line_graph.x_labels = sorted([i[2] for i in data])
    
    cores   = []
    memory  = []
    t_limit = []
    total   = []
    
    for i in data:
        cores.append(i[3])
        memory.append(i[4])
        t_limit.append(i[5])
        total.append(i[6])
   
    for index, i in enumerate(total):
        if i:
            total[index] = normalize(i)

        avg_jobs = db.getAverageJobCount(since=date.today()-timedelta(7))

    line_graph.add('cores', cores)
    line_graph.add('memory', memory)
    line_graph.add('time limit', t_limit)
    line_graph.add('total', total)

    return line_graph.render_response()


@app.route('/user')
@app.route('/user/<user_name>')
def viewUser(user_name=None):
    """
    Desc: Endpoint for the user view page 

    Args:
        user_name (string) (optional): Username to query
        search (string) (optional): Username to query, extracted from URL args
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    # Make sure we have an account name from either the url or the args
    # It will be in the args if we're coming from a search
    if not user_name:
        # Find the most similar account to the searched name
        search = request.args.get('search')

        if not search:
            return redirect(url_for('home'))

        users        = db.getUserList()
        similarities = [SequenceMatcher(None, search, i).ratio() for i in users]
        user_name    = users[similarities.index(max(similarities))]
 
    days      = getTimeframe(request.args.get('time'))
    timeframe = request.args.get('time')

    since = date.today() - timedelta(days)

    accounts = {}

    for account in db.getUserAccounts(user_name):
        accounts[account[0]] = db.getUserStats(user_name, account[0], since=since)

    # Render the account view template
    return render_template('user.html', user_name=user_name, accounts=accounts, time=timeframe, timeframe=days)


if __name__ == '__main__':
    if '--debug' in sys.argv:
        app.run(debug=True, threaded=True, host='0.0.0.0')

    else:
        app.run()
