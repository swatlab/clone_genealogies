from __future__ import division
import sys, csv, os, subprocess, re
from datetime import datetime
import pandas as pd

# Run shell command from a string
def shellCommand(command_str):
    cmd =subprocess.Popen(command_str.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

def computeCloneSize(clone_pair):
    size1 = int(clone_pair.split('+')[0].split('^')[2]) - int(clone_pair.split('+')[0].split('^')[1]) + 1
    size2 = int(clone_pair.split('+')[1].split('^')[2]) - int(clone_pair.split('+')[1].split('^')[1]) + 1
    return max(size1, size2)

def raw_genealogies(project, tool):
    raw_genealogy_dict = dict()
    end_commit_set = set()
    with open('../output_data/%s/%s_genealogies.csv' %(tool,project), 'r') as f:
        csvreader = csv.reader(f)
        next(csvreader, None)
        for row in csvreader:
            genealogy = row[3]
            if len(genealogy):
                clone_pair = row[0]
                size = computeCloneSize(clone_pair)
                path1 = clone_pair.split('+')[0].split('^')[0]
                path2 = clone_pair.split('+')[1].split('^')[0]
                start_commit = row[1]
                end_commit = row[2]
                end_commit_set.add(end_commit)
                raw_genealogy_dict[(path1, path2)] = {'size':size, 'start':start_commit, 'end': end_commit, 'gen':genealogy, 'sig':clone_pair}
    return raw_genealogy_dict, end_commit_set

def renamedFiles(end_commit_set):
    rename_dict = dict()
    # directory paths (global variables)
    current_dir = os.getcwd()
    repo_dir = '../src_code/%s' %project
    # change to the code repository directory
    os.chdir(repo_dir)
    for commit_id in end_commit_set:
        #print commit_id
        diff_list = list()
        diff_res = shellCommand('git diff %s^ %s --name-status -M' %(commit_id,commit_id))
        for line in diff_res.split('\n'):
            if line.startswith('R099') or line.startswith('R100'):
                old_path = line.split('\t')[1]
                new_path = line.split('\t')[2]
                diff_list.append((old_path, new_path))
        if len(diff_list):
            rename_dict[commit_id] = diff_list
    # go back to the script directory
    os.chdir(current_dir)
    return rename_dict

def loadCommitDate(file_name):
    commit_date_dict = dict()
    with open(file_name, 'r') as f:
        reader = f.read().split('\n')
        for line in reader:
            if len(line):
                elems = line.split(',')
                rev = elems[0]
                date = re.sub(r'[^0-9]', '', elems[2][:-6])
                commit_date_dict[rev] = date
    return commit_date_dict

# Compute date interval between two date strings
def dateDiff(d1_str, d2_str):
    d1 = datetime.strptime(d1_str, '%Y%m%d%H%M%S')
    d2 = datetime.strptime(d2_str, '%Y%m%d%H%M%S')
    return (d2 - d1).total_seconds()/3600/24

def categoriseInterval(last_date, current_date):
    interval = dateDiff(last_date, current_date)
    if interval > 365:
        return 'YY'
    elif interval > 30:
        return 'Y'
    elif interval > 7:
        return 'M'
    elif interval > 1:
        return 'W'
    return 'D'

def combineRenamedPair(raw_genealogy_dict, rename_dict):
    for paths in raw_genealogy_dict:
        end_commit = raw_genealogy_dict[paths]['end']
        if end_commit in rename_dict:
            for renamed_paths in rename_dict[end_commit]:
                if paths == renamed_paths:
                    print 'renamed!'
                    break
    return

def loadFaultInducingCommits(project):
    fault_inducing_dict = dict()
    with open('../output_data/szz/%s/fault_inducing.csv' %project, 'r') as f:
        csvreader = csv.reader(f)
        next(csvreader, None)
        for row in csvreader:
            inducing_commit = row[0]
            fixing_commit = row[1]
            if inducing_commit in fault_inducing_dict:
                fault_inducing_dict[inducing_commit].add(fixing_commit)
            else:
                fault_inducing_dict[inducing_commit] = set([fixing_commit])
    return fault_inducing_dict

def genealogyFeatures(raw_genealogy_dict, fault_inducing_dict, commit_date_dict):
    output_list = list()
    for paths in raw_genealogy_dict:
        genealogy_list = raw_genealogy_dict[paths]['gen'].split('-')
        # compute time interval between changes
        start_commit_date = commit_date_dict[raw_genealogy_dict[paths]['start']]
        end_commit_date = commit_date_dict[raw_genealogy_dict[paths]['end']]
        last_date = start_commit_date
        interval_list = list()
        churn_list = list()
        # check whether a clone modification is faulty        
        fault_proneness_list = list()
        buggy_gen = False
        commit_list = [raw_genealogy_dict[paths]['start']]
        for mod in genealogy_list:
            state = mod.split(',')[0]
            commit_id = mod.split(',')[1]
            churn = mod.split(',')[2]
            commit_list.append(commit_id)
            current_date = commit_date_dict[commit_id]
            interval = categoriseInterval(last_date, current_date)
            last_date = current_date
            if commit_id in fault_inducing_dict:
                buggy = 'Y'
                # check whether a whole genealogy is faulty
                fixing_commits = fault_inducing_dict[commit_id]
                for f_c in fixing_commits:
                    if commit_date_dict[f_c] > end_commit_date:
                        buggy_gen = True
                        break
            else:
                buggy = 'N'
            fault_proneness_list.append('%s_%s' %(state,buggy))
            interval_list.append('%s_%s' %(interval,buggy))
            churn_list.append(churn)
        fault_proneness_str = '^'.join(fault_proneness_list)
        interval_str = '^'.join(interval_list)
        commit_str = '^'.join(commit_list)
        churn_str = '^'.join(churn_list)
        # signature and size
        sig = raw_genealogy_dict[paths]['sig']
        clone_size = raw_genealogy_dict[paths]['size']
        # output results
        output_list.append([sig, clone_size, buggy_gen, fault_proneness_str, interval_str, commit_str, churn_str])
        df = pd.DataFrame(output_list, columns=['signature', 'size', 'buggy_gen', 'state+fault', 'interval', 'commits', 'churn'])
        df.to_csv('../statistics/%s/%s_basic.csv' %(tool,project), index=False)
    return

if __name__ == '__main__':
    if len(sys.argv) != 3:
            print 'Please input [project] & [tool]!'
    else:
        project = sys.argv[1]
        tool = sys.argv[2]
        raw_genealogy_dict, end_commit_set = raw_genealogies(project, tool)
        rename_dict = renamedFiles(end_commit_set)
        combineRenamedPair(raw_genealogy_dict, rename_dict)
        commit_date_dict = loadCommitDate('../raw_data/%s_logs.txt' %project)
        fault_inducing_dict = loadFaultInducingCommits(project)
        genealogyFeatures(raw_genealogy_dict, fault_inducing_dict, commit_date_dict)
    
    