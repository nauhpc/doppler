# Slurm Jobstats Site

## Overview

Provides a web frontend for cluster users to view their batch job usage stats.

## Installation

### Requirements
1. Slurm
2. jobstats-cmd
3. jobstats-db
4. WSGI-compatible web server (gunicon recommended)
5. Parent web server (nginx recommended)

### Install
1. Clone and enter repository `git clone https://github.com/nauhpc/jobstats-site.git  && cd jobstats-site`
2. Install dependencies `pip install -r requirements.txt`

### Running behind a WSGI Server (ex. gunicorn)
1. Run WSGI server
```
gunicorn -w 4 app:app
```
2. Set your web server to be a reverse-proxy for the WSGI server
```
server {
    listen 80;
    server_name example.org;
    access_log  /var/log/nginx/example.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```
Reference yout WSGI server's [guide](http://gunicorn.org/#quickstart) for more information
