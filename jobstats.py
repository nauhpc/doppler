"""
Desc: Library for extracting and parsing information from the jobstats MySQL 
      database

Authors:
    - Chance Nelson <chance-nelson@nau.edu>
"""


import time
import datetime 
import mysql.connector.pooling as mysql
import operator
from functools import reduce


class Jobstats:
    def __init__(self, host, username, password, db='jobstats'):
        self.cnx_pool = mysql.MySQLConnectionPool(pool_name='jobstats-site', 
                                                  pool_size=32, user=username, 
                                                  password=password,
                                                  database=db)

        self.yesterday = datetime.date.today() - datetime.timedelta(1)
        self.last_week = datetime.date.today() - datetime.timedelta(7)


    def getTopUsers(self, since=None, normalize=None):
        users = self.getUserList()

        stats = []

        for i in users:
            stats.append(self.getUserStats(i, since=since)['total'])

        users = zip(users, stats)

        if normalize:
            jobs = dict(self.getUsersJobCounts(since=since))

            users = [i for i in users if i[0] in jobs.keys()]

            return list(reversed(sorted(users, 
                                        key=lambda user:   
                                                normalize(user[1], 
                                                          since=since, 
                                                          job_count=jobs[user[0]]
                                                         )
                                        )))

        else:
            return list(reversed(sorted(users, key=lambda user: user[1])))


    def getTopAccounts(self, since=None, normalize=None):
        accounts = self.getAccountList()

        stats = []

        for i in accounts:
            stats.append(self.getAccountTotalScore(i, since=since)['total'])

        accounts = zip(accounts, stats)

        if normalize:
            jobs = dict(self.getAccountsJobCounts(since=since))

            accounts = [i for i in accounts if i[0] in jobs.keys()]

            return list(reversed(sorted(accounts, 
                                        key=lambda account:   
                                                normalize(account[1], 
                                                          since=since, 
                                                          job_count=jobs[account[0]]
                                                         )
                                        )))

        else:
            return list(reversed(sorted(accounts, key=lambda account: account[1])))


    def getUserJobCount(self, user, since=None):
        if not since:
            since = self.yesterday

        query = ("SELECT jobsum FROM jobs WHERE user = %s AND date >= %s")

        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, (account, since))

        jobsTotal = 0

        for (jobSum) in cursor:
            jobsTotal += jobSum

        return jobsTotal


    def getAccountUserJobCounts(self, account, since=None):
        if not since:
            since = self.yesterday

        users  = {}
        query  = ("SELECT username, jobsum FROM jobs WHERE account = %s AND date >= %s")

        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, (account, since))

        for (username, jobsum) in cursor:
            if username in users.keys():
                users[username] += jobsum

            else:
                users[username] = jobsum

        conn.close()

        return users


    def getAccountUserJobCountsOnDay(self, account, date):
        users = {}
        query = ("SELECT username, jobsum FROM jobs WHERE account = %s AND date = %s")

        conn = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query, (account, date))

        for (username, job_sum) in cursor:
            users[username] = job_sum

        conn.close()

        return users


    def getUsersJobCounts(self, since=None):
        if not since:
            since = self.yesterday

        users = {}

        query  = ("SELECT username, jobsum FROM jobs WHERE date >= %s")
 
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, (since,))

        for (user, jobsum) in cursor:
            if user in users.keys():
                users[user] += jobsum

            else:
                users[user] = jobsum

        conn.close()

        return users


    def getAccountsJobCounts(self, since=None):
        if not since:
            since = self.yesterday

        accounts = {}

        query  = ("SELECT account, jobsum FROM jobs WHERE date >= %s")
 
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, (since,))

        for (account, jobsum) in cursor:
            if account in accounts.keys():
                accounts[account] += jobsum

            else:
                accounts[account] = jobsum

        conn.close()

        return accounts


    def getFullAccountList(self, date, users=False):
        accounts = {}
        query    = ("SELECT * FROM jobs WHERE date = %s")
        
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query, (date,))

        # (username, account, date, cores, memory, timelimit, total, jobsum)
        for i in cursor:
            account = None
            if users:
                account = i[0]

            else:
                account = i[1]

            cores   = i[3]
            memory  = i[4]
            tLimit  = i[5]
            total   = i[6]
            jobSum  = i[7]

            if account in accounts.keys():
                oldCores  = accounts[account]['cores']
                oldMemory = accounts[account]['memory']
                oldTLimit = accounts[account]['tlimit']
                oldJobSum = accounts[account]['jobsum']
                
                if oldCores and cores:
                    cores = ((oldCores * oldJobSum) + (cores * jobSum)) / \
                            (oldJobSum + jobSum)
                
                if oldMemory and memory:
                    memory = ((oldMemory * oldJobSum) + (memory * jobSum)) / \
                             (oldJobSum + jobSum)
                
                if oldTLimit and tLimit:
                    tLimit = ((oldTLimit * oldJobSum) + (tLimit * jobSum)) / \
                             (oldJobSum + jobSum)

                jobSum += oldJobSum

            accounts[account] = {'cores': cores, 'memory': memory,
                                 'tlimit': tLimit, 'total': total,
                                 'jobsum': jobSum}

        conn.close()

        return accounts


    def getClusterStats(self, since=None):
        if not since:
            since = self.last_week

        stats  = {}
        query  = ("SELECT * FROM jobs WHERE date >= %s")
        
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, (since,))

        for i in cursor:
            date   = i[2]
            cores  = i[3]
            memory = i[4]
            tLimit = i[5]
            total  = i[6]
            jobSum = i[7]


            if date in stats.keys():
                oldCores  = stats[date]['cores']
                oldMemory = stats[date]['memory']
                oldTLimit = stats[date]['tlimit']
                oldJobSum = stats[date]['jobsum']
                
                if oldCores:
                    if cores:
                        cores = ((oldCores * oldJobSum) + (cores * jobSum)) / \
                                (oldJobSum + jobSum)

                    else:
                        cores = oldCores
                
                if oldMemory:
                    if memory:
                        memory = ((oldMemory * oldJobSum) + (memory * jobSum)) / \
                                 (oldJobSum + jobSum)

                    else:
                        memory = oldMemory
                
                if oldTLimit:
                    if tLimit:
                        tLimit = ((oldTLimit * oldJobSum) + (tLimit * jobSum)) / \
                                 (oldJobSum + jobSum)

                    else:
                        tLimit = oldTLimit

                jobSum += oldJobSum

            stats[date] = {'cores': cores, 'memory': memory,
                           'tlimit': tLimit, 'total': total,
                           'jobsum': jobSum}
        
        conn.close()

        return stats


    def getAccountStats(self, account, since=None):
        if not since:
            since = self.last_week

        stats = {}
        query = ("SELECT * FROM jobs WHERE account = %s AND date >= %s")
        
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, (account, since))

        for i in cursor:
            date   = i[2]
            cores  = i[3]
            memory = i[4]
            tLimit = i[5]
            total  = i[6]
            jobSum = i[7]

            if date in stats.keys():
                oldCores  = stats[date]['cores']
                oldMemory = stats[date]['memory']
                oldTLimit = stats[date]['tlimit']
                oldJobSum = stats[date]['jobsum']
                
                if oldCores:
                    if cores:
                        cores = ((oldCores * oldJobSum) + (cores * jobSum)) / \
                                (oldJobSum + jobSum)

                    else:
                        cores = oldCores
                
                if oldMemory:
                    if memory:
                        memory = ((oldMemory * oldJobSum) + (memory * jobSum)) / \
                                 (oldJobSum + jobSum)

                    else:
                        memory = oldMemory
                
                if oldTLimit:
                    if tLimit:
                        tLimit = ((oldTLimit * oldJobSum) + (tLimit * jobSum)) / \
                                 (oldJobSum + jobSum)

                    else:
                        tLimit = oldTLimit

                jobSum += oldJobSum

            stats[date] = {'cores': cores, 'memory': memory,
                           'tlimit': tLimit, 'total': total,
                           'jobsum': jobSum}

        conn.close()

        return stats


    def getAccountTotalScore(self, account, since=None):
        stats = self.getAccountStats(account, since=since)

        cores  = 0
        memory = 0
        tLimit = 0
        total  = 0
        jobSum = 0

        for date in stats:
            oldCores  = stats[date]['cores']
            oldMemory = stats[date]['memory']
            oldTLimit = stats[date]['tlimit']
            oldJobSum = stats[date]['jobsum']
            
            if oldCores:
                if cores:
                    cores = ((oldCores * oldJobSum) + (cores * jobSum)) / \
                            (oldJobSum + jobSum)

                else:
                    cores = oldCores
            
            if oldMemory:
                if memory:
                    memory = ((oldMemory * oldJobSum) + (memory * jobSum)) / \
                             (oldJobSum + jobSum)

                else:
                    memory = oldMemory
            
            if oldTLimit:
                if tLimit:
                    tLimit = ((oldTLimit * oldJobSum) + (tLimit * jobSum)) / \
                             (oldJobSum + jobSum)

                else:
                    tLimit = oldTLimit

            jobSum += oldJobSum

        if jobSum > 0:
            total = (cores + memory + tLimit) / 3

        return {'cores': round(cores, 2), 'memory': round(memory, 2), 
                'tlimit': round(tLimit, 2), 'total': round(total, 2), 
                'jobsum': round(jobSum, 2)}


    def getAccountUsers(self, account):
        query = ("SELECT username FROM jobs WHERE account = %s")
        
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query, (account,))
        
        users = [i[0] for i in cursor]
        users = list(set(users))

        conn.close()

        return users


    def getUserStats(self, user, account=None, since=None, as_list=False):
        if not since:
            since = self.yesterday

        if not account:
            account = ''

        query  = ("SELECT * FROM jobs WHERE username = %s AND date >= %s AND (account = %s OR %s = '')")
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, (user, since, account, account))

        if as_list:
            data = [i for i in cursor]
            conn.close()
            return data

        cores  = 0
        memory = 0
        tLimit = 0
        total  = 0
        jobSum = 0

        for date in cursor:
            oldCores  = date[3]
            oldMemory = date[4]
            oldTLimit = date[5]
            oldJobSum = date[7]
            
            if oldCores:
                if cores:
                    cores = ((oldCores * oldJobSum) + (cores * jobSum)) / \
                            (oldJobSum + jobSum)

                else:
                    cores = oldCores
            
            if oldMemory:
                if memory:
                    memory = ((oldMemory * oldJobSum) + (memory * jobSum)) / \
                             (oldJobSum + jobSum)

                else:
                    memory = oldMemory
            
            if oldTLimit:
                if tLimit:
                    tLimit = ((oldTLimit * oldJobSum) + (tLimit * jobSum)) / \
                             (oldJobSum + jobSum)

                else:
                    tLimit = oldTLimit

            jobSum += oldJobSum

        if jobSum > 0:
            total = (cores + memory + tLimit) / 3

        conn.close()

        return {'cores': round(cores, 2), 'memory': round(memory, 2), 
                'tlimit': round(tLimit, 2), 'total': round(total, 2), 
                'jobsum': round(jobSum, 2)}


    def getUserAccounts(self, user):
        query = ("SELECT account FROM jobs WHERE username = %s")

        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query, (user,))
    
        accounts = [i for i in cursor]

        conn.close()

        return accounts


    def getAccountList(self):
        query = ("SELECT account FROM jobs")
        
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query)

        accounts = [i[0] for i in cursor]
        accounts = list(set(accounts))

        conn.close()

        return accounts


    def getAverageJobCount(self, since=None):
        if not since:
            since = self.last_week

        query = ("SELECT jobsum FROM jobs WHERE date >= %s")

        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query, (since,))

        jobs = [i[0] for i in cursor]
        average = reduce(lambda x, y: x + y, jobs) 

        conn.close()

        average = average

        return average


    def getUserList(self):
        query  = ("SELECT username FROM jobs")
        conn   = self.cnx_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(query)

        users = list(set([i[0] for i in cursor]))
        
        conn.close()

        return users
