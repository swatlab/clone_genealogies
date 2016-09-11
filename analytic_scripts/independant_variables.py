from __future__ import division
import sys, csv, json, os, subprocess, re
from datetime import datetime
from collections import OrderedDict
import pandas as pd
import statistics

# Run shell command from a string
def shellCommand(command_str):
    cmd =subprocess.Popen(command_str.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

def computeCommonPathDepth(signature):
    path1 = signature.split('+')[0].split('^')[0]
    start1 = int(signature.split('+')[0].split('^')[1])
    end1 = int(signature.split('+')[0].split('^')[2])
    path2 = signature.split('+')[1].split('^')[0]
    start2 = int(signature.split('+')[1].split('^')[1])
    end2 = int(signature.split('+')[1].split('^')[2])
    depth1 = path1.split('/') 
    depth2 = path2.split('/')
    for i in range(len(depth1)):
        folder1 = depth1[i]
        if i < len(depth2):
            folder2 = depth2[i]
            if folder1 != folder2:
                return i, path1, path2, start1, end1, start2, end2
    return len(depth1), path1, path2, start1, end1, start2, end2

def makeCloneSignature(clone):
    return '%s^%s^%s' %(clone[0], clone[1].split('-')[0], clone[1].split('-')[1])

def extractCloneClasses(clone_results):
    print 'Extracting clone classes ...'
    clone_class_dict = dict()
    for commit_id in clone_results:
        clone_class_list = clone_results[commit_id]
        clone_classes_in_commit = list()
        for clone_class in clone_class_list:
            clone_class_sibs = set()
            for a_clone in clone_class:
                clone_class_sibs.add(makeCloneSignature(a_clone))
            if len(clone_class_sibs):
                clone_classes_in_commit.append(clone_class_sibs)
        clone_class_dict[commit_id] = clone_classes_in_commit
    return clone_class_dict
    
def loadBugFixingCommits(filename):
    bug_fixing_commits = set()
    with open(filename, 'r') as f:
        csvreader = csv.reader(f)
        for row in csvreader:
            bug_fixing_commits.add(row[1])
    return bug_fixing_commits

def loadCommitInfo(filename):
    commit_info_dict = dict()
    # extract committer and date
    with open('../raw_data/%s_logs.txt' %project, 'r') as f:
        reader = f.read().split('\n')
        for row in reader:
            elems = row.split(',', 3)
            commit_id = elems[0]
            committer = elems[1]
            commit_date = re.sub(r'[^0-9]', '', elems[2][:-6])
            commit_info_dict[commit_id] = {'committer':committer, 'date':commit_date}
    # calculate committers' experience
    experience_dict = dict()
    with open('../raw_data/%s_commit_sequence.txt' %project, 'r') as f:
        reader = f.read().split('\n')
        for commit_id in reader:
            if commit_id in commit_info_dict:
                committer = commit_info_dict[commit_id]['committer']
                if committer in experience_dict:
                    experience_dict[committer] += 1
                else:
                    experience_dict[committer] = 1
                commit_info_dict[commit_id]['experience'] = experience_dict[committer]
    return commit_info_dict

def countLines(line_range, start, end):
    return len(set(line_range) & set(range(start, end+1)))

# Compute date interval between two date strings
def dateDiff(d1_str, d2_str):
    d1 = datetime.strptime(d1_str, '%Y%m%d%H%M%S')
    d2 = datetime.strptime(d2_str, '%Y%m%d%H%M%S')
    return (d2 - d1).total_seconds()/3600/24

def countBursts(commit_sequence, commit_info_dict):
    burst_list = list()
    sequence_len = len(commit_sequence)
    burst_start_commit = commit_sequence[0]
    burst_cnt = 0
    commits_in_last_burst = 0
    for i in range(1, sequence_len):
        date1 = commit_info_dict[commit_sequence[i-1]]['date']
        date2 = commit_info_dict[commit_sequence[i]]['date']
        date_burst_start = commit_info_dict[burst_start_commit]['date']
        if dateDiff(date_burst_start, date2) <= 1:
            commits_in_last_burst += 1
            if i == 1:
                burst_cnt += 1
        elif dateDiff(date1, date2) <= 1:
            commits_in_last_burst = 1
            burst_cnt += 1
            burst_start_commit = commit_sequence[i-1]            
    return burst_cnt, commits_in_last_burst

def countSiblings(gen_sig, commit_id, clone_class_dict):
    clone1 = gen_sig.split('+')[0]
    clone2 = gen_sig.split('+')[1]    
    for clone_class in clone_class_dict[commit_id]:
        for a_clone in clone_class:
            if clone1 == a_clone or clone2 == a_clone:
                return len(clone_class) - 2
    return

def loadGenealogies(project, tool, bug_fixing_commits, commit_info_dict):
    metric_table = list()
    '''gen_dict = dict()'''
    df = pd.read_csv('../statistics/%s/%s_basic.csv' %(tool,project))
    for idx,row in df.iterrows():
        # CLOC, CPathDepth
        cloc = row['size']
        gen_sig = row['signature']
        cpath_depth = computeCommonPathDepth(gen_sig)[0]
        # check whether a clone change is buggy
        commit_list = row['commits'].split('^')
        '''sib_cnt = countSiblings(gen_sig, commit_list[0], clone_class_dict)'''        
        state_fault_list = row['state+fault'].split('^')
        commit_history = list()
        state_history = list()
        bug_fixing_history = list()
        change_type_history = list()
        bug_in_history_cnt = 0
        for i in range(len(state_fault_list)):
            current_commit = commit_list[i+1]
            commit_history.append(current_commit)
            # current state of a clone pair
            current_state = state_fault_list[i].split('_')[0]
            state_history.append(current_state)            
            # change type
            if state_history == 1:
                change_type = statistics.changeType('C', current_state)
            else:
                change_type = statistics.changeType(state_history[i-1], current_state)
            change_type_history.append(change_type)
            con_type_num = change_type_history.count('CON')
            inc_type_num = change_type_history.count('INC')
            resync_type_num = change_type_history.count('RESYNC')
            div_type_num = change_type_history.count('DIV')
            # count consistent and inconsiste state
            gen_pattern = statistics.genealogyPattern(''.join(state_history))
            consistent_cnt = state_history.count('C')
            inconsistent_cnt = state_history.count('I')
            # committer's experience
            committer_exp = commit_info_dict[current_commit]['experience']
            # count bursts and count commits in the last burst 
            burst_cnt, commits_in_last_burst = countBursts([commit_list[0]] + commit_history, commit_info_dict)
            # total changed lines in a snapshot of the clone
            churn = row['churn'].split('^')[i]
            # total number of changes of a clone
            tpc = len(state_history)
            # whether it is a bug fixing commit
            if current_commit in bug_fixing_commits:
                is_bug_fixing = True
            else:
                is_bug_fixing = False
            bug_fixing_history.append(is_bug_fixing)
            # bug fixing density
            e_flt_dens = round(bug_fixing_history.count(True) / len(bug_fixing_history), 3)
            # change interval in day
            last_commit_date = commit_info_dict[commit_list[i]]['date']
            current_commit_date = commit_info_dict[current_commit]['date']
            change_interval = round(dateDiff(last_commit_date, current_commit_date), 1)
            # buggy in history
            if i == 0:
                bug_rate_in_history = 0
            else:
                bug_rate_in_history = round(bug_in_history_cnt / i, 3)
            # whether the change is buggy
            buggy = (state_fault_list[i].split('_')[1]) == 'Y'
            if buggy:
                bug_in_history_cnt += 1
            metrics_in_snapshot = [is_bug_fixing, cloc, cpath_depth, current_state, committer_exp, \
                                e_flt_dens, churn, tpc, burst_cnt, commits_in_last_burst, bug_rate_in_history, \
                                gen_pattern, consistent_cnt, inconsistent_cnt, con_type_num, inc_type_num, resync_type_num, div_type_num, change_interval,
                                buggy]
            metric_table.append(metrics_in_snapshot)
    return metric_table

if __name__ == '__main__':
    if len(sys.argv) != 3:
            print 'Please input [project] & [tool]!'
    else:
        project = sys.argv[1]
        tool = sys.argv[2]
        '''with open('../output_data/%s/%s.json' %(tool, project), 'r') as jsonfile:
            print 'Loading clone results ...'
            clone_results = json.load(jsonfile, object_pairs_hook=OrderedDict)
            clone_class_dict = extractCloneClasses(clone_results)'''
        commit_info_dict = loadCommitInfo(project)
        bug_fixing_commits = loadBugFixingCommits('../output_data/szz/%s/bug_commit_mapping.csv' %project)
        metrics_in_snapshot = loadGenealogies(project, tool, bug_fixing_commits, commit_info_dict)
        # output results
        metric_names = ['CFltFix', 'cloc', 'CPathDepth', 'CCurSt', 'experience',\
                    'EFltDens', 'TChurn', 'TPC', 'NumOfBursts', 'SLBurst', 'CFltRate',\
                    'EEvPattern', 'EConChg', 'EIncChg', 'EConStChg', 'EIncStChg', 'EFltsConStChg', 'EFltIncStChg', 'EChgTimeInt',
                    'buggy']
        df = pd.DataFrame(metrics_in_snapshot, columns=metric_names)
        df.to_csv('../statistics/%s/%s_metrics.csv' %(tool,project), index=False)

               