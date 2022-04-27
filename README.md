# Grafana Front-End For Jobstats Data

## Overview

This repository contains the grafana dashboards we use to display metrics from our MySQL database with grafana. These dashboards help us examine user and account efficiency for workloads researchers execute on the "Monsoon" cluster at NAU.

## Database Setup

The dashboard expects the MySQL database to have tables setup by our [jobstats](https://github.com/nauhpc/jobstats) and [jobstats-db](https://github.com/nauhpc/jobstats-db) projects.

[jobstats](https://github.com/nauhpc/jobstats) is a wrapper for the [sacct](https://slurm.schedmd.com/sacct.html) command which includes data from the [seff](https://bugs.schedmd.com/show_bug.cgi?id=1611) command. The primary advantage of it is how it calculates job efficiency which makes it easier for end-users to more efficiently submit [Slurm](https://slurm.schedmd.com/) jobs.

The [jobstats-db](https://github.com/nauhpc/jobstats-db) project includes a populateDatabase script that we run daily in a cronjob to get new job efficiency metrics into our MySQL instance. The grafana dashboards listed here will not work without this data.

## Software Requirements

1. RHEL/CENTOS
   - Our servers either run RHEL 8 or Centos Stream release 8
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