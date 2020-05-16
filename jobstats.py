"""Library for extracting and parsing information from the jobstats MySQL database

Authors:
    - Chance Nelson <chance-nelson@nau.edu>
    - Ian Otto <iso-ian@nau.edu>
"""


import datetime
import statistics
from functools import reduce
import sys

import mysql.connector as mysql
import os

class Jobstats:
    """Object instantiated for interacting with the Jobstats MySQL database
    """
    def __init__(self, host, username, password, db='jobstats'):
        """Constructor
        
        Args:
            host (string): hostname of the server where the db is located
            username (string): username of the db user with read permissions to
                the jobstats db
            password (string): password for ''username''
            db (string, optional): name of the database to use. Defaults to 
                'jobstats'

        """
        self.db_host = host
        self.db_user = username
        self.db_password = password
        self.db_name = db
        cnx = mysql.connect(host=self.db_host, user=self.db_user,
                            password=self.db_password, database=self.db_name)
        cursor = cnx.cursor()
        self.data = self.queryDatabase(cursor)
        self.yesterday = datetime.date.today() - datetime.timedelta(1)
        self.last_week = datetime.date.today() - datetime.timedelta(7)

    def update(self):
        cnx = mysql.connect(host=self.db_host, user=self.db_user,
                            password=self.db_password, database=self.db_name)
        cursor = cnx.cursor()        
        self.data = self.queryDatabase(cursor)

    def getTimeSlice(self, fromDate, toDate):
        """
        Desc: Retrieve job data from the database for the given time range

        Args:
            fromDate (string): Add a start date
            toDate (string): Add an end date

        Returns:
            List with a dictionary for each unique username for the time slice.
        """
        user_data = dict()
        account_data = dict()

        # add together all stats for each unique user
        count = 0
        for row in data:
            if not (fromDate <= row['date'] <= toDate):
                continue
            count += 1
            username = row['username']
            account = row['account']
            memory_req  = row['memreq']
            memory_use = row['memuse']
            ideal_cpu = row['idealcpu']
            cpu_time = row['cputime']
            tlimit_req = row['timereq']
            tlimit_use = row['timeuse']
            if username not in user_data:
                user_data[username] = {'memreq': memory_req if memory_req else 0,
                                       'memuse': memory_use if memory_use else 0,
                                       'idealcpu' : ideal_cpu if ideal_cpu else 0,
                                       'cputime'  : cpu_time if cpu_time else 0,
                                       'timereq': tlimit_req if tlimit_req else 0,
                                       'timeuse': tlimit_use if tlimit_use else 0}
            else:
                user_data[username]['memreq'] += memory_req if memory_req else 0
                user_data[username]['memuse'] += memory_use if memory_use else 0
                user_data[username]['idealcpu']  += ideal_cpu if ideal_cpu else 0
                user_data[username]['cputime']   += cpu_time if cpu_time else 0
                user_data[username]['timereq'] += tlimit_req if tlimit_req else 0
                user_data[username]['timeuse'] += tlimit_use if tlimit_use else 0

            if account not in account_data:
                account_data[account] = dict()
                account_data[account][username] = {'memreq': memory_req if memory_req else 0,
                                                   'memuse': memory_use if memory_use else 0,
                                                   'idealcpu' : ideal_cpu if ideal_cpu else 0,
                                                   'cputime'  : cpu_time if cpu_time else 0,
                                                   'timereq': tlimit_req if tlimit_req else 0,
                                                   'timeuse': tlimit_use if tlimit_use else 0}
            else:
                if username not in account_data[account]:
                    account_data[account][username] = {'memreq': memory_req if memory_req else 0,
                                                       'memuse': memory_use if memory_use else 0,
                                                       'idealcpu' : ideal_cpu if ideal_cpu else 0,
                                                       'cputime'  : cpu_time if cpu_time else 0,
                                                       'timereq': tlimit_req if tlimit_req else 0,
                                                       'timeuse': tlimit_use if tlimit_use else 0}                
                else:
                    account_data[account][username]['memreq'] += memory_req if memory_req else 0
                    account_data[account][username]['memuse'] += memory_use if memory_use else 0
                    account_data[account][username]['idealcpu']  += ideal_cpu if ideal_cpu else 0
                    account_data[account][username]['cputime']   += cpu_time if cpu_time else 0
                    account_data[account][username]['timereq'] += tlimit_req if tlimit_req else 0
                    account_data[account][username]['timeuse'] += tlimit_use if tlimit_use else 0

        # for each account calculate "TOTAL"

        user_metrics = []
        account_metrics = []
        for username in user_data:
            # doppler refers to cpu effiency as "cores" efficiency

            core_req = user_data[username]['idealcpu'];
            core_used = user_data[username]['cputime'];
            core_eff = 100 * core_used / core_req if core_req != 0 else 0.0

            memory_req = user_data[username]['memreq']
            memory_used = user_data[username]['memuse']
            memory_eff = 100 * memory_used / memory_req if memory_req != 0 else 0.0

            time_req = user_data[username]['timereq']
            time_used = user_data[username]['timeuse']
            time_eff = 100 * time_used / time_req if time_req != 0 else 0.0

            try:
                total_eff = sum([i for i in [core_eff, memory_eff, time_eff]]) / (3 - [core_eff, memory_eff, time_eff].count(0.0))
            except:
                total_eff = 0.0

            user_metrics.append({'username'    : username,
                                 'cores'       : round(core_eff, 2),
                                 'memory'      : round(memory_eff, 2),
                                 'time'        : round(time_eff, 2),
                                 'core hours'  : round(core_used / 3600.0, 2),
                                 'total'       : round(total_eff, 2)})

        for account in account_data:
            account_dict = dict()
            core_sum = 0.0
            memory_sum = 0.0
            time_sum = 0.0
            core_hours_sum = 0.0
            total_sum = 0.0
            for username in account_data[account]:
                # doppler refers to cpu effiency as "cores" efficiency

                core_req = account_data[account][username]['idealcpu'];
                core_used = account_data[account][username]['cputime'];
                core_eff = 100 * core_used / core_req if core_req != 0 else 0.0

                memory_req = account_data[account][username]['memreq']
                memory_used = account_data[account][username]['memuse']
                memory_eff = 100 * memory_used / memory_req if memory_req != 0 else 0.0

                time_req = account_data[account][username]['timereq']
                time_used = account_data[account][username]['timeuse']
                time_eff = 100 * time_used / time_req if time_req != 0 else 0.0

                try:
                    total_eff = sum([i for i in [core_eff, memory_eff, time_eff]]) / (3 - [core_eff, memory_eff, time_eff].count(0.0))
                except:
                    total_eff = 0.0
                account_dict[username] = {'cores'      : round(core_eff, 2),
                                          'memory'     : round(memory_eff, 2),
                                          'time'       : round(time_eff, 2),
                                          'core hours' : round(core_used / 3600.0, 2),
                                          'total'      : round(total_eff, 2)}
                core_sum += core_eff
                memory_sum += memory_eff
                time_sum += time_eff
                core_hours_sum += (core_used / 3600.0)
                total_sum += total_eff
            denom = len(account_dict)
            account_dict['TOTAL'] = {'cores'      : round(core_sum / denom, 2),
                                     'memory'     : round(memory_sum / denom, 2),
                                     'time'       : round(time_sum / denom, 2),
                                     'core hours' : round(core_hours_sum / denom, 2),
                                     'total'      : round(total_sum / denom, 2)}
            account_metrics.append({'account': account, 'data': account_dict})
        return user_metrics, account_metrics        

    def queryDatabase(self, cursor):
        """
        Desc: Retrieve all job data from the database

        Args:
            cursor (mysql.connector): Reuse a mysql connection instead of
                                      initializing a new one
        Returns:
            List where each entry is a row in the database
        """

        query = "SELECT username,account,date,memoryreq,memoryuse,idealcpu,cputime,tlimitreq,tlimituse,jobsum from jobs "
        query += "ORDER BY date"
        args = tuple()
        cursor.execute(query, tuple(args))
        result = []
        for username, account, date, memory_req, memory_use, ideal_cpu, cpu_time, tlimit_req, tlimit_use, jobsum in cursor:
            inner_dict = {
                'username': username,
                'account': account,
                'date': date,
                'memreq': memory_req,
                'memuse': memory_use,
                'idealcpu': ideal_cpu,
                'cputime': cpu_time,
                'timereq': tlimit_req,
                'timeuse': tlimit_use,
                'jobsum': jobsum
            }
            result.append(inner_dict)
        return result

    def getUsers(self, account=None, since=None):
        """Get a list of all users in the database

        Args:
            account (string, optional): specify an account to get a user list 
                of
            since (datetime, optional): filter out accounts with no activity
                from date specified to the present

        Returns: 
            list: all users present in the database
        """
        users_set = set()
        for row in self.data:
            if (since is None) or (row['date'] >= since):
                if account:
                    if row['account'] == account:
                        users_set.add(row['username'])
                else:
                    users_set.add(row['username'])
        return list(users_set)

    def getAccounts(self, username=None, since=None):
        """Get a list of all slurm accounts in the database
        
        Args:
            username (string, optional): specify a user to get the account
                list of
            since (datetime, optional): filter out users with no activity
                within the set date range
        
        Returns: 
            list: all slurm accounts in the database
        """
        accounts_set = set()
        for row in self.data:
            if (since is None) or (row['date'] >= since):
                if username:
                    if row['username'] == username:
                        accounts_set.add(row['account'])
                else:
                    accounts_set.add(row['account'])
        return list(accounts_set)    

    def getUserCoreHours(self, username, account, since=None):
        """Get a count of a user's jobs between the current day and some date

        Args:
            user (string): username
            account (string): account
            since (dateime): beginning date to check. Default is one day ago

        Returns:
            int: Count of all jobs within specified time frame
        """
        if not since:
            since = self.yesterday

        cpu_time_sum = 0.0
        for row in self.data:
            if (since is None) or (row['date'] >= since):
                if row['username'] == username and row['account'] == account and row['cputime'] is not None:
                    cpu_time_sum += row['cputime']
        
        return cpu_time_sum / 3600.0

    def getStats(self, account=None, user=None, since=None, by_date=False):
        """Get the stats for a user/account in a given timeframe. 

        Specify both account and use to narrow search to a specific 
        user/account combination.

        Args:
            account (string, optional): account name. Default None
            user (string, optional): username. Default none
            since (datetime, optional): beginning date to check. Default 
                yesterday
            by_date (bool, optional): Organize scores by day, for plotting on 
                graphs

        Returns:
            dict: resource usages of form::
            
                {
                    memreq:  ., 
                    memuse:  ., 
                    cpureq:  ., 
                    cputime: ., 
                    timereq: ., 
                    timeuse: .
                }

            If the user/account combination does not exist in the db, None
        """
        if not since:
            since = self.yesterday

        user_stats = {'memreq': 0,
                      'memuse': 0,
                      'cputime': 0.0,
                      'idealcpu': 0.0,
                      'timereq': 0,
                      'timeuse': 0,
                      'jobsum': 0}
        date_dict = dict()
        last_date = None
        count = 0
        for row in self.data:
            if (since is None) or (row['date'] >= since):
                if by_date:
                    if last_date is None:
                        last_date = row['date']
                    if row['date'] != last_date or row  == self.data[-1]:
                        if user_stats != {'memreq': 0, 'memuse': 0, 'cputime': 0.0, 'idealcpu': 0.0, 'timereq': 0, 'timeuse': 0, 'jobsum': 0}:
                            date_dict[last_date] = user_stats
                        last_date = row['date']
                        user_stats = {'memreq': 0,
                                      'memuse': 0,
                                      'cputime': 0.0,
                                      'idealcpu': 0.0,
                                      'timereq': 0,
                                      'timeuse': 0,
                                      'jobsum': 0}
                if user and account:
                    if row['username'] == user and row['account'] == account:
                        user_stats['memreq'] += row['memreq'] if row['memreq'] is not None else 0.0
                        user_stats['memuse'] += row['memuse'] if row['memuse'] is not None else 0.0
                        user_stats['cputime'] += row['cputime'] if row['cputime'] is not None else 0.0
                        user_stats['idealcpu'] += row['idealcpu'] if row['idealcpu'] is not None else 0.0
                        user_stats['timereq'] += row['timereq'] if row['timereq'] is not None else 0.0
                        user_stats['timeuse'] += row['timeuse'] if row['timeuse'] is not None else 0.0
                        user_stats['jobsum'] += row['jobsum'] if row['jobsum'] is not None else 0.0
                elif user and row['username'] == user:
                        user_stats['memreq'] += row['memreq'] if row['memreq'] is not None else 0.0
                        user_stats['memuse'] += row['memuse'] if row['memuse'] is not None else 0.0
                        user_stats['cputime'] += row['cputime'] if row['cputime'] is not None else 0.0
                        user_stats['idealcpu'] += row['idealcpu'] if row['idealcpu'] is not None else 0.0
                        user_stats['timereq'] += row['timereq'] if row['timereq'] is not None else 0.0
                        user_stats['timeuse'] += row['timeuse'] if row['timeuse'] is not None else 0.0
                        user_stats['jobsum'] += row['jobsum'] if row['jobsum'] is not None else 0.0
                elif account and row['account'] == account:
                        user_stats['memreq'] += row['memreq'] if row['memreq'] is not None else 0.0
                        user_stats['memuse'] += row['memuse'] if row['memuse'] is not None else 0.0
                        user_stats['cputime'] += row['cputime'] if row['cputime'] is not None else 0.0
                        user_stats['idealcpu'] += row['idealcpu'] if row['idealcpu'] is not None else 0.0
                        user_stats['timereq'] += row['timereq'] if row['timereq'] is not None else 0.0
                        user_stats['timeuse'] += row['timeuse'] if row['timeuse'] is not None else 0.0
                        user_stats['jobsum'] += row['jobsum'] if row['jobsum'] is not None else 0.0
                elif user is None and account is None:
                        user_stats['memreq'] += row['memreq'] if row['memreq'] is not None else 0.0
                        user_stats['memuse'] += row['memuse'] if row['memuse'] is not None else 0.0
                        user_stats['cputime'] += row['cputime'] if row['cputime'] is not None else 0.0
                        user_stats['idealcpu'] += row['idealcpu'] if row['idealcpu'] is not None else 0.0
                        user_stats['timereq'] += row['timereq'] if row['timereq'] is not None else 0.0
                        user_stats['timeuse'] += row['timeuse'] if row['timeuse'] is not None else 0.0
                        user_stats['jobsum'] += row['jobsum'] if row['jobsum'] is not None else 0.0
                
        if account:
            user_stats['account'] = account
        if user:
            user_stats['user'] = user

        if by_date:
            return date_dict
        else:
            return user_stats
