import time

import csv
from flask import Flask, render_template, request, Response
import json
import requests
import re
import datetime

app = Flask(__name__)
rules = {}
log_file = "status_checks.log"


def load_rules():
    loaded_rules = {}
    with open('conf/urls_rules.tab', 'r') as csv_file:
        for row in csv.reader(csv_file, delimiter='\t'):
            loaded_rules[row[0]] = {"interval": row[1], "rules": row[2:]}
    return loaded_rules


rules = load_rules()


def lookup_rule(url):
    return rules[url]


def check_content(content, rule):
    print("Checking rule: ", rule)
    m = re.search(rule, content)
    print(m)
    if m is not None and m.group(0) is not None:
        print("Found hit for rule: ", m.group(0))
        return "ok"
    else:
        return "not ok"


@app.route("/healthCheck", methods=["GET"])
def healthcheck():
    resp = Response(status=200, mimetype='application/json')
    return resp


def check_url(url):
    print("Checking url:", url)
    rule_statuses = []
    start = time.time()
    interval = rules[url]["interval"]
    try:
        response = requests.get(url)
        status_code = response.status_code
        print(type(response.content), "-->", type(response.content.decode('ISO-8859-1')))
        rule_statuses = []
        for rule in rules[url]["rules"]:
            rule_status = check_content(response.content.decode('ISO-8859-1'), rule)
            rule_statuses.append({"rule": rule, "status": rule_status})
    except requests.exceptions.ConnectionError:
        status_code = 500

    end = time.time()

    response_time = end - start
    log_url_status(url, status_code, response_time)

    return status_code, rule_statuses, interval


def log_url_status(url, status_code, response_time):
    global log_file
    with open("logs/" + log_file, 'a') as logfile:
        logfile.write(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') + " ")
        logfile.write(url + " ")
        logfile.write(str(status_code) + " ")
        logfile.write(str(response_time) + "\n")


@app.route("/check", methods=["GET"])
def check():
    print(json.dumps(rules, indent=1))
    statuses = []
    rule_statuses = {}
    intervals = {}
    for url in rules:
        print("Checking url:", url)

        status_code, rules_responses, interval = check_url(url)
        statuses.append({"url": url, "status": status_code})
        rule_statuses[url] = rules_responses
        intervals[url] = interval

        print(json.dumps(statuses))
        print(json.dumps(rule_statuses))

    return render_template("crawl_results.html", statuses=statuses, rule_statuses=rule_statuses, intervals=intervals)


@app.route("/checkurl", methods=["GET"])
def checkurl():
    url = request.args.get('url')
    status, rules_responses, interval = check_url(url)
    return json.dumps({"status": status, "rules": rules_responses})
