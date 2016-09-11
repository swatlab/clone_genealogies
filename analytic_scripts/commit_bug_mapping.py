import sys, csv, re, time, urllib2
from datetime import datetime

def loadConfiguration(project):
    config_dict = dict()
    with open('../raw_data/%s_config.txt' %project) as f:
        reader = f.read().split('\n')
        for line in reader:
            if len(line):
                elems = line.split('=', 1)
                config_dict[elems[0]] = elems[1]
    return config_dict

def downloadReport(bug_id, issue_tracker, issue_link, creation_flag, error_flag):
    time.sleep(1)
    opened_date = None
    urlItem = None
    opened_date, fixed_date = None, None
    if issue_tracker == 'jira':
        url = issue_link %(bug_id, bug_id)
    else:
        url = issue_link %bug_id
    try:
        urlItem = urllib2.urlopen(url)
    except:
        print '%s: wrong bug link!' %bug_id
    if(urlItem):
        page_bytes = urlItem.read()
        page_txt = page_bytes.decode('utf-8', 'ignore')
        ascii_str = page_txt.encode('ascii','ignore')
        if not (error_flag in ascii_str):
            if re.search(r'\<type.+?\>Bug\<\/type\>', ascii_str):
                opened_str = re.findall(r'\<%s\>(.+?)\<\/%s\>' %(creation_flag, creation_flag), ascii_str)[0]
                if issue_tracker == 'jira':
                    opened_date = datetime.strptime(opened_str[:-6], '%a, %d %b %Y %H:%M:%S').strftime('%Y%m%d')
                else:
                    opened_date = re.sub(r'[^0-9]', '', opened_str[:10])
            else:
                return None
        else:
            print 'Error bug ID %s' %bug_id
    return opened_date

def loadCommitLogs(project, config_dict):
    bug_dict = dict()
    bug_commit_mapping = dict()
    issue_tracker = config_dict['tracker']
    issue_pattern = config_dict['pattern']
    issue_link = config_dict['link']
    creation_flag = config_dict['creation_flag']
    error_flag = config_dict['error_flag']
    with open('../raw_data/%s_logs.txt' %project, 'r') as f:
        reader = f.read().split('\n')
        i = 0
        for line in reader:
            if debug:
                i += 1
                if i > 20:
                    break
            elems = line.split(',', 3)
            rev = elems[0]
            message = elems[3]
            print rev
            # map a commit to its bug(s) and note the bugs' opened date
            if issue_tracker == 'bugzilla':
                bugs = re.findall(issue_pattern, message, re.IGNORECASE)
            else:
                bugs = re.findall(issue_pattern, message)
            if len(bugs):
                for bug_id in bugs:
                    if bug_id in bug_dict:
                        bug_commit_mapping[bug_id].add(rev)
                    else:
                        opened_date = downloadReport(bug_id, issue_tracker, issue_link, creation_flag, error_flag)
                        if opened_date:
                            bug_dict[bug_id] = opened_date
                            bug_commit_mapping[bug_id] = set([rev])
    return bug_dict, bug_commit_mapping

if __name__ == '__main__':
    debug = False
    if len(sys.argv) == 1:
        print 'Please input the project name!\n'
    else:
        project = sys.argv[1]
        config_dict = loadConfiguration(project)
        bug_dict, bug_commit_mapping = loadCommitLogs(project, config_dict)
        # output results
        with open('../output_data/szz/%s/bug_open_date.csv' %project, 'w') as f:
            csvwriter = csv.writer(f)
            for bug_id in bug_dict:
                csvwriter.writerow([bug_id, bug_dict[bug_id]])
        with open('../output_data/szz/%s/bug_commit_mapping.csv' %project, 'w') as f:
            csvwriter = csv.writer(f)
            for bug_id in bug_commit_mapping:
                csvwriter.writerow([bug_id, '^'.join(bug_commit_mapping[bug_id])])
        print 'Done.'
    