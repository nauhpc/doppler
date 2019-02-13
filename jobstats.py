"""
Desc: Library for extracting and parsing information from the jobstats MySQL 
      database

Authors:
    - Chance Nelson <chance-nelson@nau.edu>
    - Ian Otto <iso-ian@nau.edu>
"""


import datetime
import statistics
from functools import reduce

import mysql.connector.pooling as mysql


class Jobstats:
    def __init__(self, host, username, password, db='jobstats'):
        self.cnx_pool = mysql.MySQLConnectionPool(pool_name='jobstats-site',
                                                  pool_size=5, host=host, 
                                                  user=username,
                                                  password=password,
                                                  database=db)

        self.yesterday = datetime.date.today() - datetime.timedelta(1)
        self.last_week = datetime.date.today() - datetime.timedelta(7)


    def getUsers(self, account=None, since=None):
        """
        Desc: Get a list of all users in the database

        Args:
            account (string) (optional): specify an account to get a user list 
                                         of
            since (datetime) (optional): filter out accounts with no activity
                                         from date specified to the present

        Returns: 
            List of all users present in the database
        """
        query = "SELECT DISTINCT username FROM jobs"
        args  = []

        if account:
            query += " WHERE account=%s"
            args.append(account)

        if since:
            if 'WHERE' in query[0]:
                query += " AND date >= %s"

            else:
                query += " WHERE date >= %s"

            args.append(since)

        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query, args)

        users = [i for i in cursor]

        conn.close()
        return users


    def getAccounts(self, username=None, since=None):
        """
        Desc: Get a list of all slurm accounts in the database
        
        Args:
            username (string) (optional): specify a user to get the account
                                          list of
            since (datetime) (optional): filter out users with no activity
                                         within the set date range
        
        Returns: 
            List of all slurm accounts in the database
        """
        query = "SELECT DISTINCT account FROM jobs"
        args  = []

        if username:
            query += " WHERE username = %s"

        if since:
            if 'WHERE' in query[0]:
                query += " AND date >= %s"

            else:
                query += " WHERE date >= %s"

            args.append(since)

        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query, args)

        accounts = [i for i in cursor]

        conn.close()
        return accounts


    def getUserJobCount(self, user, since=None):
        """
        Desc: Get a count of a user's jobs between the current day and some
              date

        Args:
            user (string): username
            since (dateime): beginning date to check. Default is one day ago

        Returns:
            Count of all jobs within specified time frame
        """
        if not since:
            since = self.yesterday
    
        query = ("SELECT SUM(jobsum) FROM jobs WHERE username = %s AND date >= %s")
 
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query, (username, since))
        
        job_sum = cursor[0]

        conn.close()
        return job_sum


    def getAccountJobCount(self, account, since=None):
        """
        Desc: Get a count of a user's jobs between the current day and some
              date

        Args:
            account (string): account name
            since (dateime): beginning date to check. Default is one day ago

        Returns:
            Count of all jobs within specified time frame
        """
        if not since:
            since = self.yesterday
    
        query = ("SELECT SUM(jobsum) FROM jobs WHERE account = %s AND date >= %s")
 
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query, (username, since))
        
        job_sum = cursor[0]

        conn.close()
        return job_sum


    def getStats(self, account=None, user=None, since=None, 
                 by_date=False):
        """
        Desc: Get the stats for a user in a given timeframe. Specify both 
              account and use to narrow search to a specific user/account 
              combination

        Args:
            account (string): account name. Default None
            user (string): username. Default none
            since (datetime): beginning date to check. Default yesterday
            by_date (bool): Organize scores by day, for plotting on graphs

        Returns:
            Dict of resource usages of form {memreq, memuse, cpureq, cputime, 
                                             timereq, timeuse}

            If the user/account combination does not exist in the db, None
        """
        if not since:
            since = self.yesterday
    
        query = "SELECT date, SUM(coresreq), SUM(memoryreq), SUM(tlimitreq), " + \
                "SUM(cputime), SUM(tlimituse), SUM(memoryuse) FROM jobs"

        args = ()

        # Format query based on what username/account name we want
        if account and user:
            query += " WHERE username = %s AND account = %s"
            args.append(account, user)

        elif user:
            query += " WHERE username = %s"
            args.append(user)

        elif account:
            query += " WHERE account = %s"
            args.append(account)


        # If we want stats by date, we need to do multiple queries based on
        # the date
        if 'WHERE' not in query:
            query += " WHERE date >= %s"

        else:
            query += " AND date >= %s"

        
        if by_date:
            query += " GROUP BY date ORDER BY date"


        args.append(since)
             
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute((query), args)

        if by_date:
            user_stats = {}
            for day_stats in cursor:
                (date, coresreq, memoryreq, tlimitreq, cputime, tlimituse, memoryuse) = day_stats
                user_stats[date] = {
                    'memreq': memoryreq,
                    'memuse': memoryuse,
                    'cpureq': coresreq,
                    'cputime': cputime,
                    'timereq': tlimitreq,
                    'timeuse': tlimituse,
                }

        else:
            (date, coresreq, memoryreq, tlimitreq, cputime, tlimituse, memoryuse) = cursor[0]

            user_stats = {
                'memreq': memoryreq,
                'memuse': memoryuse,
                'cpureq': coresreq,
                'cputime': cputime,
                'timereq': tlimitreq,
                'timeuse': tlimituse,
            }

            if account:
                user_stats['account'] = account

            if user:
                user_stats['user'] = user

        conn.close()
        return user_stats
