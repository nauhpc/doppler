# -*- coding: utf-8 -*-
"""Main source file for the Doppler web front end

Authors:
    - Chance Nelson <chance-nelson@nau.edu>
    - Ian Otto <iso-ian@nau.edu>
"""


import sys
import time
import statistics
import os
from configparser import ConfigParser
from datetime import date, timedelta
from difflib import SequenceMatcher

import pygal
from flask import Flask, render_template, request, url_for, redirect

import jobstats


app = Flask(__name__)


# Get the efficiency score normalization options
config = ConfigParser()
config.read(os.path.dirname(os.path.realpath(__file__)) + '/config.ini')
 

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
ideal_score              = 100


for arg in normalize_scores_options.split(' '):
    if 'score' in arg:
        normalize_by_score = True
        ideal_score        = float(config['SCORES']['ideal score'])

def getCoreHours(my_dict):
    """Get a formatted string for core hours

    Args:
        my_dict (dict): a dictionary with jobstats data
    Returns:
        string
    """    
    result = '-'
    if(my_dict['cputime']):
        my_dict['cputime'] = my_dict['cputime'] / 3600.0
        result = '{:.1f}'.format(my_dict['cputime'])
    return result

def normalize(data, all_scores=False, by_date=False):
    """Get a normalized job score based on usage data

    This function utilizes the constant ideal_score for mean score normalization
    
    Args:
        data (dict): usage data to normalize
        all_scores (bool, optional): Return all individual scores, along with 
            the total
        by_date (bool, optional): Only used in the case that the usage data
            is a collection of dates. Return scores by date, instead of 
            condensing all data

    Returns:
        float: Total score, if the ''all_scores'' and ''by_date'' flags are 
               not set

        dict: If the ''all_scores'' flag is set, dictionary of all scores, of 
              the form::

            {
                'total': 0,
                'cpu-score': 0,
                'mem-score': 0,
                'tlimit-score': 0
            }

        dict: Dictionary of dictionaries, if the ''by_date'' flag is set, of
              the form::

            {
                '1/1/19': {
                    'total': 0
                    'cpu-score': 0,
                    'mem-score': 0,
                    'tlimit-score': 0
                },
                ...
            }
    """
    # Data is a single point
    if 'memuse' in data:
        memory = None
        time   = None
        cpu    = None
        
        try:
            memory = data['memuse']  / data['memreq']
            memory *= 100

        except:
            pass

        try:
            time = data['timeuse'] / data['timereq']
            time *= 100

        except:
            pass

        try:
            cpu = data['cputime']  / data['idealcpu']
            cpu *= 100

        except:
            pass

        applicable_scores = [i for i in [memory, time, cpu] if i and i != 0]

        score = 0
        if len(applicable_scores) != 0:
            score = (statistics.mean(applicable_scores) / ideal_score) * 100

        if all_scores:
            data['total']        = round(score, 2) if score else None
            data['cpu-score']    = round(cpu, 2) if cpu else None
            data['mem-score']    = round(memory, 2) if memory else None
            data['tlimit-score'] = round(time, 2) if time else None
            return data

        else:
            return score

    # Data is a collection of scores by date ({'1/1/18': {...}})
    else:
        # Normalize each day
        if by_date:
            scores = {}
            for day in data:
                scores[day] = normalize(data[day], all_scores=all_scores)

            return scores

        # Sum each day together and get one big score
        else:
            data_total = {
                'memuse'   : 0,
                'memreq'   : 0,
                'timeuse'  : 0,
                'timereq'  : 0,
                'cputime'  : 0,
                'idealcpu' : 0,
                'jobsum'   : 0
            }
            
            # add the current day to the total
            for day in data:
                for val in data[day]:
                    data_total[val] += data[day][val]

            return normalize(data_total, all_scores=all_scores)


def getScore(account=None, user=None, since=None, by_date=False):
    """Get the score for a given user, account, or the enitre cluster

    This is the function to use for retrieving scores. It utilizes 
    ''normalize'' as a helper function

    Args:
        account (string, optional): account name
        user (string, optional): username
        since (datetime, optional): beginning date to check. Defaults to 
            yesterday
        by_date (bool, optional): organize scores by day, instead of a total 
            score for a date range

    Returns:
        dict: Dictionary of all scores, of the form::

            {
                'total': 0,
                'cpu-score': 0,
                'mem-score': 0,
                'tlimit-score': 0
            }

        dict: Dictionary of dictionaries, if the ''by_date'' flag is set, of
              the form::

            {
                '1/1/19': {
                    'total': 0
                    'cpu-score': 0,
                    'mem-score': 0,
                    'tlimit-score': 0
                },
                ...
            }
    """
    data_raw = db.getStats(account=account, user=user, since=since, by_date=by_date)
    score    = normalize(data_raw, all_scores=True, by_date=by_date)

    return score


def scoreSortKey(user=None, account=None, since=None):
    """Key function for sorting accounts and users by their efficiency score

    This is a helper function for ''getTop()''

    Args:
        user (string, optional): username
        account (string, optional): account name
        since (datetime.datetime, optional): get the total score since a date
    """
    score = getScore(user=user, account=account, since=since)

    if not score['total']:
        return 0

    else:
        return score['total']


def getTop(account_type, num, since):
    """Get a list of the top N users in a given timeframe

    Args:
        account_type (string): 'users' or 'accounts'
        num (int): get top N users
        since (datetime): Min date to search from present to

    Returns:
        List of max top N efficient users on the cluster.
    """
    all_data_points = []
    key_func        = None

    if account_type == 'users':
        all_data_points = db.getUsers(since=since)
        key_func = lambda user: scoreSortKey(user=user, since=since) 

    elif account_type == 'accounts':
        all_data_points = db.getAccounts(since=since)
        key_func = lambda account: scoreSortKey(account=account, since=since) 
        
    return list(reversed(sorted(all_data_points, key=key_func)))[:num]
    

def getTimeframe(days):
    """Get a timeframe in day count from character

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


@app.route('/accountsboxplot.svg')
def renderAccountsBoxPlot():
    """Endpoint for the account lising box plot on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    return renderGraph(pygal.Box, 'Account')


@app.route('/usersboxplot.svg')
def renderUsersBoxPlot():
    """Endpoint for the user listing box plot on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    return renderGraph(pygal.Box, 'User')


@app.route('/userslinegraph.svg')
def renderUsersLineGraph():
    """Endpoint for the user listing line graph on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    return renderGraph(pygal.Line, 'User')


@app.route('/accountslinegraph.svg')
def renderAccountsLineGraph():
    """Endpoint for account listing line graph on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    return renderGraph(pygal.Line, 'Account')


@app.route('/clusterlinegraph.svg')
def renderClusterLineGraph():
    """Endpoint for cluster line graph on the home page

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    return renderGraph(pygal.Line, 'Cluster')


@app.route('/clusterjobsgraph.svg')
def renderClusterJobsGraph():
    """Endpoint for cluster job concentration over time graph

    Args:
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    return renderGraph(pygal.Line, 'jobs')


def renderGraph(graph_function, data_set):
    """Render pygal SVG graphs for various data sets and timelines

    This is the primary graphing function, that all graph endpoints utilize.
    Graphing methods are passed in through ''graph_function'', and the data
    requested in ''data_set'' is pulled and rendered

    Timeline arguments are presented through the URL argumented sent to the
    web request via one of the graph endpoints, called ''days''. ''days'' can
    be ''W'', ''M'', or ''Q''. If no argument for days is found, the default
    view is the weekly view.

    Args:
        graph_function (function): Pygal function for generating the graph 
            (box and line currently officially supported)
        data_set (string): string representation of what data set to pull from
            (supports 'cluster', 'user', and 'account')
    """
    days       = getTimeframe(request.args.get('days'))
    days_delta = 1
   
    # Only display one data point per week for timeframes above a month
    if data_set.lower() in ['user', 'account'] and days > 31:
        days_delta = 7

    # Render the line graph
    graph = graph_function(range=[0, 100], show_x_labels=False)
 
    if days == 7:
        graph.title = data_set + ' Efficiency for the Week'
    elif days == 31:
        graph.title = data_set + ' Efficiency for the Month'
    elif days == 100:
        graph.title = data_set + ' Efficiency for the Quarter'
    else:
        graph.title = data_set + ' Efficiency'

    graph.x_labels    = [date.today() - timedelta(i) for i in range(days, 0, (days_delta * -1))]
    data_points       = {}

    if data_set.lower() == 'account':
        # Get the top ten accounts
        top_accounts = getTop('accounts', 10, date.today()-timedelta(days))

        # Retrieve usage data for each top account
        for account in top_accounts:
            data = getScore(account=account,
                            since=(date.today()-timedelta(days)),
                            by_date=True)

            data_points[account] = data

    if data_set.lower() == 'user':
        # Get the top ten users
        top_users = getTop('users', 10, date.today()-timedelta(days))

        # Retrieve usage data for each top account
        for user in top_users:
            data = getScore(user=user,
                               since=(date.today()-timedelta(days)),
                               by_date=True)

            data_points[user] = data

    elif data_set.lower() == 'cluster':
        data = getScore(since=date.today()-timedelta(days), by_date=True)

        data_points = {
            'cores': [],
            'memory': [],
            'time limit': [],
            'total efficiency': []
        }
      
        for i in range(days, 0, -1):
            current = date.today() - timedelta(i)
            if current in data:
                score = data[current]
               
                data_points['cores'].append(score['cpu-score'])
                data_points['memory'].append(score['mem-score'])
                data_points['time limit'].append(score['tlimit-score'])
                data_points['total efficiency'].append(score['total'])

            else:
                data_points['cores'].append(None)
                data_points['memory'].append(None)
                data_points['time limit'].append(None)
                data_points['total efficiency'].append(None)


        # Add each account in alphabetical order
        for i in sorted(data_points.keys()):
            graph.add(i, [j for j in data_points[i]])

        return graph.render_response()

    elif data_set.lower() == 'jobs':
        graph = graph_function(show_x_labels=False, fill=True)
        
        graph.x_labels = [date.today() - timedelta(i) for i in range(days, 0, days_delta * -1)]

        data = db.getJobSum(since=(date.today() - timedelta(days)), by_date=True)
        
        data_points = []
        for i in range(days, 0, -1):
            current = date.today() - timedelta(i)

            if current in data:
                data_points.append(data[current])

            else:
                data_points.append(0)
           

        graph.add('jobs', data_points)

        graph.range = [0, max([int(i) for i in data_points])]
        
        return graph.render_response()


    for user in sorted(data_points.keys()):
        user_scores = []

        for i in range(days, 0, -1):
            current = date.today() - timedelta(i)

            if current in data_points[user]:
                user_scores.append(normalize(data_points[user][current]))
            
            else:
                user_scores.append(None)
       
        graph.add(user, user_scores)

    return graph.render_response()


@app.route('/')
@app.route('/home')
def home():
    """Endpoint for home page

    URL arguments for this page include ''view'', and ''time''. ''view''
    informs the page what view to show the user::
        
        {
            'cluster': view the main cluster page, with summaries and graphs,
            'accounts': view the accounts ranks list,
            'users': view the users ranks list
        }

    ''time'' emforces a timeline for grabbing scores, and rendering graphs::

        {
            'W': weekly,
            'M': monthly,
            'Q': Quarterly
        }
    """
    view      = request.args.get('view')
    time      = getTimeframe(request.args.get('time'))
    timeframe = request.args.get('time')

    data_points = []

    template = 'home.html'

    template_args = {}

    if not view or view == 'cluster':
        template = 'cluster.html'

        total_usage = db.getStats(since=(date.today() - timedelta(time)))
        total_score = normalize(total_usage, all_scores=True)

        active_users = db.getUsers(since=(date.today() - timedelta(time)))
        total_users  = db.getUsers()

        active_accounts  = db.getAccounts(since=(date.today() - timedelta(time)))
        total_accounts   = db.getAccounts()

        template_args['total_usage']     = total_usage
        template_args['total_score']     = total_score
        template_args['active_users']    = len(active_users)
        template_args['total_users']     = len(total_users)
        template_args['active_accounts'] = len(active_accounts)
        template_args['total_accounts']  = len(total_accounts)
        template_args['view']            = view
        template_args['time']            = timeframe

        return render_template(template, **template_args)

    # Retrieve stats for all accounts/users in the given timeframe
    # Default to accounts view
    if view in ['cluster', 'accounts']:
        data_points = db.getAccounts(since=(date.today() - timedelta(time)))

    else:
        data_points = db.getUsers(since=(date.today() - timedelta(time)))

    job_data = []

    # Gather use data for all users/accounts. Remove from array empty ones
    for i in data_points:
        data = None
        if not view or view in ['cluster', 'accounts']:
            data = db.getStats(account=i, 
                               since=(date.today() - timedelta(time)))

        else:
            data = db.getStats(user=i, 
                               since=(date.today() - timedelta(time)))
       
        # If there is user data available for the timeframe, add them 
        if data and data['jobsum'] and data['jobsum'] > 0:
            # Add in the account/user name
            data['owner'] = i
            job_data.append(data)

    # Organize job data
    job_data = reversed(sorted(job_data, key=lambda x: normalize(x)))

    account_ranks = []

    for i in job_data:
        account_name = None
        if not view or view in ['cluster', 'accounts']:
            account_name = i['account']

        else:
            account_name = i['user']

        scores = normalize(i, all_scores=True)

        total = int(scores['total']) if scores['total'] else '-'

        cores   = scores['cpu-score'] if scores['cpu-score'] else '-'
        memory  = scores['mem-score'] if scores['mem-score'] else '-'
        t_limit = scores['tlimit-score'] if scores['tlimit-score'] else '-'
        total   = scores['total'] if scores['total'] else '-'
        job_sum = scores['jobsum'] if scores['jobsum'] else '-'

        core_hours = getCoreHours(i)
      
        account_ranks.append([len(account_ranks)+1, account_name, cores,
                              memory, t_limit, total, job_sum, core_hours])

    return render_template(template, graph=renderGraph, box=pygal.Box,
                           line=pygal.Line, account_ranks=account_ranks, 
                           view=view, time=timeframe)


@app.route('/account/<account_name>/linegraph.svg')
def renderAccountLineGraph(account_name):
    """Endpoint for the account-centric line graph

    This endoint supports The ''days'' argument, for timeframe constraints.

    Args:
        account_name (string): name of the account to query
    """
    days = int(request.args.get('days'))
 
    data = db.getStats(account=account_name, since=(date.today() - timedelta(days)), by_date=True)
    # Render the line graph
    line_graph = pygal.Line(x_label_rotation=20, range=[0, 100], show_x_labels=False)

    if days == 7:
        line_graph.title = account_name + ' Efficiency for the Week'
    elif days == 31:
        line_graph.title = account_name + ' Efficiency for the Month'
    elif days == 100:
        line_graph.title = account_name + ' Efficiency for the Quarter'
    else:
        line_graph.title = account_name + ' Efficiency'

    line_graph.x_labels = [date.today() - timedelta(i) for i in range(days, 1, -1)]

    data_points = {
        'cores': [],
        'memory': [],
        'time limit': [],
        'total efficiency': [],
    }

    for i in range(days, 1, -1):
        current = date.today() - timedelta(i)
        if current in data:
            score = normalize(data[current], all_scores=True)

            data_points['cores'].append(score['cpu-score'])
            data_points['memory'].append(score['mem-score'])
            data_points['time limit'].append(score['tlimit-score'])
            data_points['total efficiency'].append(score['total'])

        else:
            data_points['cores'].append(None)
            data_points['memory'].append(None)
            data_points['time limit'].append(None)
            data_points['total efficiency'].append(None)

    for data in sorted(data_points.keys()):
        line_graph.add(data, data_points[data])

    return line_graph.render_response()


@app.route('/account/<account_name>/userpiegraph.svg')
def renderAccountUsersGraph(account_name):
    """Endpoint for the accont users job distribution pie graph

    This endoint supports The ''days'' URL argument, for timeframe constraints.
    
    Args:
        account_name (string): Account to query
    """
    days = int(request.args.get('days'))

    users = db.getUsers(account=account_name)
    
    data = {}

    for user in users:
        data[user] = db.getUserJobCount(user, since=date.today()-timedelta(days))

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
    """Endpoint for the account view page
    
    URL arguments for the endpoint include ''account'', which is added
    for search queries. This name will be searched in the database, and the
    page will be redirected to the closest match.

    This endoint supports The ''time'' URL argument, for timeframe constraints.

    Args:
        account (string) (optional): Account to query, extracted from URL
                                     args.
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
        accounts = db.getAccounts()
        start    = time.time()

        similarities = [SequenceMatcher(None, search, i).ratio() for i in accounts]
        account_name = accounts[similarities.index(max(similarities))]

    days      = getTimeframe(request.args.get('time'))
    timeframe = request.args.get('time')
    
    since = date.today() - timedelta(days)

    total_scores = normalize(db.getStats(account=account_name, since=since), 
                             all_scores=True)

    total = {
        'total': total_scores['total'],
        'cores': total_scores['cpu-score'],
        'memory': total_scores['mem-score'],
        'tlimit': total_scores['tlimit-score']
    }

    for i in total:
        if total[i] == 0:
            total[i] = '-'

    users = {}
    user_list = db.getUsers(account=account_name)

    for user in user_list:
        stats = db.getStats(account=account_name, user=user, since=since)
        user_score = normalize(stats, all_scores=True)

        users[user] = {
            'cores': user_score['cpu-score'],
            'memory': user_score['mem-score'],
            'tlimit': user_score['tlimit-score'],
            'total': user_score['total'],
            'jobsum': user_score['jobsum'],
            'core hours': getCoreHours(stats)
        }

        for element in users[user].keys():
            if users[user][element] == 0 or not users[user][element]:
                users[user][element] = '-'

    # Render the account view template
    return render_template('account.html', account_name=account_name, 
                           users=users, total=total, time=timeframe, 
                           timeframe=days)


@app.route('/user/<user_name>/linegraph.svg')
def renderUserAccountLineGraph(user_name, account=None):
    """Endpoint for the account line graph, displaying indiviual user efficiencies

    URL arguments for the endpoint include ''search'', which is added
    for search queries. This name will be searched in the database, and the
    page will be redirected to the closest match.

    This endoint supports The ''days'' URL argument, for timeframe constraints.

    Args:
        user_name (string): Username to query
        account (string) (optional): Account to query, used to narrow
                                     down search for users with multiple
                                     slurm accounts
        days (char) (optional): Timeframe in [W, M, Q], extracted from URL
                                arguments
    """
    days    = int(request.args.get('days'))
    account = request.args.get('account')

    data = normalize(db.getStats(user=user_name, account=account, 
                                 since=(date.today() - timedelta(days)), 
                                 by_date=True), 
                     by_date=True, all_scores=True)

    # Render the line graph
    line_graph = pygal.Line(x_label_rotation=20, range=[0, 100], show_x_labels=False)
    
    if days == 7:
        line_graph.title = user_name + ' Efficiency for the Week'
    elif days == 31:
        line_graph.title = user_name + ' Efficiency for the Month'
    elif days == 100:
        line_graph.title = user_name + ' Efficiency for the Quarter'
    else:
        line_graph.title = user_name + ' Efficiency'


    line_graph.x_labels = [date.today() - timedelta(i) for i in range(days)]

    data_points = {
        'cores': [],
        'memory': [],
        'time limit': [],
        'total efficiency': [],
    }

    for i in range(days, 1, -1):
        current = date.today() - timedelta(i)
        if current in data:
            score = normalize(data[current], all_scores=True)
            
            data_points['cores'].append(score['cpu-score'])
            data_points['memory'].append(score['mem-score'])
            data_points['time limit'].append(score['tlimit-score'])
            data_points['total efficiency'].append(score['total'])

        else:
            data_points['cores'].append(None)
            data_points['memory'].append(None)
            data_points['time limit'].append(None)
            data_points['total efficiency'].append(None)
    
    for data in sorted(data_points.keys()):
        line_graph.add(data, data_points[data])


    return line_graph.render_response()


@app.route('/user')
@app.route('/user/<user_name>')
def viewUser(user_name=None):
    """Endpoint for the user view page 

    This endoint supports The ''time'' URL argument, for timeframe constraints.

    Args:
        user_name (string) (optional): Username to query
        search (string) (optional): Username to query, extracted from URL args
    """
    # Make sure we have an account name from either the url or the args
    # It will be in the args if we're coming from a search
    if not user_name:
        # Find the most similar account to the searched name
        search = request.args.get('search')

        if not search:
            return redirect(url_for('home'))

        users        = db.getUsers()
        similarities = [SequenceMatcher(None, search, i).ratio() for i in users]
        user_name    = users[similarities.index(max(similarities))]
 
    days      = getTimeframe(request.args.get('time'))
    timeframe = request.args.get('time')

    since = date.today() - timedelta(days)

    accounts = {}

    for account in db.getAccounts(username=user_name):
        stats = normalize(db.getStats(user=user_name, account=account, 
                                      since=since), 
                          all_scores=True)

        accounts[account] = {
            'memory':     round(stats['mem-score'], 2) if stats['mem-score'] else '-',
            'cores':      round(stats['cpu-score'], 2) if stats['cpu-score'] else '-',
            'tlimit':     round(stats['tlimit-score'], 2) if stats['tlimit-score'] else '-',
            'total':      round(stats['total'], 2) if stats['tlimit-score'] else '-',
            'core hours': getCoreHours(stats)
        }

    # Render the account view template
    return render_template('user.html', user_name=user_name, accounts=accounts, time=timeframe, timeframe=days)


if __name__ == '__main__':
    if '--debug' in sys.argv:
        app.run(debug=True, threaded=True)

    else:
        app.run(threaded=True, host='0.0.0.0')
