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
