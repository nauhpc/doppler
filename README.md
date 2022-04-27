# Grafana Front-End For Jobstats Data

## Overview

This repository contains the grafana dashboards we use to display metrics from our MySQL database with grafana. These dashboards help us examine user and account efficiency for workloads researchers execute on the "Monsoon" cluster at NAU.

The purpose of this project is to gamify job efficiency, encouraging users to submit efficient workloads. The grafana dashboards make it easy for users to see different aspects of their cluster usage, and how their efficiency statistics compare to other users.

## Database Setup

The dashboard expects the MySQL database to have tables setup by our [jobstats](https://github.com/nauhpc/jobstats), [gpustats](https://github.com/nauhpc/gpustats), and [jobstats-db](https://github.com/nauhpc/jobstats-db) projects.

- [jobstats](https://github.com/nauhpc/jobstats)
  - Includes the [jobstats script](https://github.com/nauhpc/jobstats/blob/master/jobstats/jobstats) which is a wrapper for the [sacct](https://slurm.schedmd.com/sacct.html) command and includes data from [seff](https://bugs.schedmd.com/show_bug.cgi?id=1611). The primary advantage of the [jobstats script](https://github.com/nauhpc/jobstats/blob/master/jobstats/jobstats) is how it calculates job efficiency which makes it easier for end-users to more efficiently submit [Slurm](https://slurm.schedmd.com/) jobs.
- [gpustats](https://github.com/nauhpc/gpustats)
  - gpustats requires some setup on any gpu nodes, and additionally depends on the nvidia-smi binary. It edits the Comment field of slurm jobs to include JSON-formatted text, describing the efficiency of any GPU-enabled jobs.
- [jobstats-db](https://github.com/nauhpc/gpustats)
  - This project has scripts that manage the MySQL database tables for the grafana dashboards. The most important part is the [populateDatabase script](https://github.com/nauhpc/jobstats-db/blob/master/PopulateDatabase) which runs in a daily cronjob, ingesting new metrics.
  - The populateDatabase script expects to see a jobstats command, it will not work if you do not integrate the jobstats project.
    - The gpustats project is optional, but you'll be missing any gpu usage data without it.
  - Here is what the two dependent tables (jobs and gpuinfo) look like in MySQL:
```
(jobs)
+-----------+-------------+------+-----+---------+-------+
| Field     | Type        | Null | Key | Default | Extra |
+-----------+-------------+------+-----+---------+-------+
| username  | varchar(10) | NO   | PRI | NULL    |       |
| account   | varchar(20) | NO   | PRI | NULL    |       |
| date      | date        | NO   | PRI | NULL    |       |
| idealcpu  | float       | YES  |     | NULL    |       |
| memoryreq | int(11)     | YES  |     | NULL    |       |
| tlimitreq | int(11)     | YES  |     | NULL    |       |
| cputime   | float       | YES  |     | NULL    |       |
| tlimituse | int(11)     | YES  |     | NULL    |       |
| memoryuse | int(11)     | YES  |     | NULL    |       |
| jobsum    | int(11)     | NO   |     | NULL    |       |
+-----------+-------------+------+-----+---------+-------+
```
```
(gpuinfo)
+----------+-------------+------+-----+---------+-------+
| Field    | Type        | Null | Key | Default | Extra |
+----------+-------------+------+-----+---------+-------+
| username | varchar(10) | YES  |     | NULL    |       |
| account  | varchar(20) | YES  |     | NULL    |       |
| date     | date        | YES  |     | NULL    |       |
| jobid    | varchar(20) | YES  | UNI | NULL    |       |
| ngpu     | int(11)     | YES  |     | NULL    |       |
| gputime  | double      | YES  |     | NULL    |       |
| idealgpu | double      | YES  |     | NULL    |       |
+----------+-------------+------+-----+---------+-------+
```

## Software Requirements

1. RHEL/CENTOS
   - Our servers either run RHEL 8 or CentOS Stream release 8
2. MariaDB
3. Grafana
4. Apache

## How do I import these dashboards into grafana?

1. Download the JSON files in this repo

2. Click the plus tab in the left hand side of the page

3. From the drop down menu, click import

   ![import step 1](import-screenshot-p1.png)

4. Then click "Upload JSON file"

   ![import step 2](import-screenshot-p2.png)

Or refer to the official grafana [documentation](https://grafana.com/docs/grafana/latest/dashboards/export-import/).

## What do each of the dashboards show?

- Doppler (Main)

![doppler main dashboard](doppler-main-dashboard.png)

  - Panels:

    - Total Usage - Aggregate usage among scheduled workloads for the tim period (one week by default).

    - Cluster Efficiency 1 - Aggregate job efficiency, the sum of resource usage over the total amount of resources allocated requested by the slurm scheduler.

    - Cluster Efficiency 2 - Aggregate job efficiency, the sum of resource usage over the total amount of resources allocated requested by the slurm scheduler, for each day.

    - Account Ranking - A table, showing the efficiency and usage for workloads submitted by each research group's account. Ranks are based on the total_eff column by default.

    - User Ranking - A table, showing the efficiency and usage for workloads submitted by each user. Ranks are based on the total_eff column by default.

- Doppler (Account View)

![doppler account view dashboard](doppler-account-view-dashboard.png)

  - Panels:

    - Account Efficiency: the top left panel, is a graph showing the aggregate efficiency per day for all users that are a part of the selected account.

    - CPU Hours Per User: A pie chart, shows the breakdown of the cpu hours per user.

    - Average Efficiencies: a set of gauges that show the aggregate efficiency over the whole time period.

    - User Stats: A table, with one row for member of the account that has submitted a job within the time period (active), shows efficiency and usage metrics.

- Doppler (User View)

![doppler user view dashboard](doppler-user-view-dashboard.png)

  - Panels:

    - Efficiency: the top left panel, is a graph showing the aggregate efficiency per day for the selected user.

    - Average Efficiencies: a set of gauges that show the aggregate efficiency over the whole time period.

    - Account Stats: Table with one entry for each account for which the user is a member and has submitted jobs under within the selected time frame. The inverse of the User Stats table from the "Doppler (Account View)" dashboard.