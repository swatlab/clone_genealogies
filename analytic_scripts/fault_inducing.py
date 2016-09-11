import sys, os, csv, re, subprocess
from collections import OrderedDict
import pandas as pd

# Execute a shell command
def shellCommand(command_str):
    cmd = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out
    
# Extract commit sequence
def loadCommitSequence(project):
    commit_seq_list = list()
    with open('../raw_data/%s_commit_sequence.txt' %project, 'r') as f:
        for line in f.read().split('\n'):
            if len(line):
                commit_seq_list.append(line)
    return commit_seq_list

def loadBugCommitMapping(file_name):
    bug_commit_mapping = dict()
    with open(file_name, 'r') as f:
        csvreader = csv.reader(f)
        for line in csvreader:
            bug_commit_mapping[line[0]] = set(line[1].split('^'))
    return OrderedDict(sorted(bug_commit_mapping.items(), key=lambda t: t[0]))

def loadCommitDate(file_name):
    commit_date_dict = dict()
    with open(file_name, 'r') as f:
        reader = f.read().split('\n')
        for line in reader:
            if len(line):
                elems = line.split(',')
                rev = elems[0]
                date = re.sub(r'[^0-9]', '', elems[2][:10])
                commit_date_dict[rev] = date
    return commit_date_dict

def loadBugDate(file_name):
    bug_opened_dict = dict()
    bug_resolved_dict = dict()
    with open(file_name, 'r') as f:
        csvreader = csv.reader(f)
        for line in csvreader:
            bug_opened_dict[line[0]] = line[1]
    return bug_opened_dict

# Extract changed Java files from bug fixing commits
def analyseChangedFiles(changed_file_str):
    changed_files = set()
    for line in changed_file_str.split('\n'):
        file_path = re.findall('^[MD]{1,2}\t(.+\.java)', line)
        if len(file_path):
            changed_files.add(file_path[0])
    return changed_files

def candidateCommitID(commit_date_dict, candidate_id):
    if candidate_id not in commit_date_dict:
        candidate_id = candidateCommitID(commit_date_dict, candidate_id[:-1])        
    return candidate_id

# Filter the blamed results, removing blank lines and comment lines   
def filterCandidates(bug_id, blamed_res, line_set):
    candidate_commits = set()
    comment_block = False
    reader = blamed_res.split('\n')
    for line in reader:
        content = re.findall(r'([0-9a-z]+)\s*\S*?\s+([0-9]+)\)\s+(.+)', line)
        if len(content):
            line_number = int(content[0][1])            
            candidate_id = candidateCommitID(commit_date_dict, content[0][0])   # cut long hash shorter
            commit_date = commit_date_dict[candidate_id]
            bug_opened_date = bug_opened_dict[bug_id]
            if line_number in line_set and commit_date < bug_opened_date:
                content_str = content[0][2].strip()
                if not content_str.startswith('//'): # line comment
                    # block comment
                    cleaned_str = re.sub('\/\/.+', '', content_str)
                    if re.search(r'\/\*', cleaned_str):
                        comment_block = True
                        if not cleaned_str.startswith('/*'):
                            candidate_commits.add(candidate_id)
                    elif re.search(r'\*\/', cleaned_str):
                        comment_block = False
                        if cleaned_str.startswith('*/') and len(cleaned_str) > 2:
                            candidate_commits.add(candidate_id)
                    elif comment_block == False:
                        candidate_commits.add(candidate_id)
    return candidate_commits

# extract changed line numbers in the parent of a bug fixing commit
def changedLines(commit_id, a_file, git_repo):
    del_offset = -1
    deleted_line_set = set()
    # extract diff between the bug fixing commit and its parent comment on a (deleted or modified) file 
    if project == 'argouml' or project == 'jedit':
        previous_commit = commit_seq_list[commit_seq_list.index(commit_id) - 1]
    else:
        previous_commit = '%s^' %commit_id
    diff_res = shellCommand('git --git-dir %s diff %s %s -- %s' %(git_repo,previous_commit,commit_id,a_file))
    # find deleted line numbers
    for line in diff_res.split('\n'):
        if re.search(r'@@[\+\-\,0-9\s]+@@', line):
            changed_range = re.findall(r'@@(.+)@@', line)[0].strip()
            del_range = changed_range.split(' ')[0][1:].split(',')
            del_start = int(del_range[0])
            del_offset = 0
        elif del_offset >= 0:
            if not line.startswith('+'):
                if line.startswith('-'):
                    deleted_line_set.add(del_start + del_offset)
                del_offset += 1
    return deleted_line_set    

# Execute Blame command and filter candidates
def gitBlame(bug_id, git_repo, rev, file, line_set):
    blamed_res = shellCommand('git --git-dir %s blame -s -w %s -- %s' %(git_repo,rev,file))
    candidate_commits = filterCandidates(bug_id, blamed_res, line_set)
    return candidate_commits

def buggyCommitCandidates(bug_id, rev, file, git_repo):
    deleted_line_set = changedLines(rev, file, git_repo)    
    candidate_commits = gitBlame(bug_id, git_repo, rev+'^', file, deleted_line_set)
    return candidate_commits

def identifyBugInducingCommits(project, bug_commit_mapping, bug_opened_dict):
    bug_inducing_list = list()
    git_repo = '../src_code/%s/.git' %project
    i = 0
    for bug_id in bug_commit_mapping:
        if debug:
            i += 1
            if i > 50:
                break
        print 'bug:', bug_id
        bug_fixing_commits = bug_commit_mapping[bug_id]
        for commit_id in bug_fixing_commits:
            changed_file_str = shellCommand('git --git-dir %s log %s -n 1 --name-status' %(git_repo,commit_id))
            changed_files = analyseChangedFiles(changed_file_str)
            for a_file in changed_files:
                candidates = buggyCommitCandidates(bug_id, commit_id, a_file, git_repo)
                print ' ', commit_id, candidates
                for candidate_id in candidates:
                    bug_inducing_list.append([candidate_id, commit_id])
    return bug_inducing_list

# Output results
def outputResults(bug_inducing_list):
    df = pd.DataFrame(bug_inducing_list, columns=['inducing_commit', 'fixing_commit']).drop_duplicates()
    if debug:
        print df
    df.to_csv('../output_data/szz/%s/fault_inducing.csv' %project, index=False)
    return

if __name__ == '__main__':
    debug = False
    if len(sys.argv) == 1:
        print 'Please input the project name!\n'
    else:
        project = sys.argv[1]
        # load data
        if project == 'argouml' or project == 'jedit':
            commit_seq_list = loadCommitSequence(project)
        else:
            commit_seq_list = []
        bug_commit_mapping = loadBugCommitMapping('../output_data/szz/%s/bug_commit_mapping.csv' %project)
        commit_date_dict = loadCommitDate('../raw_data/%s_logs.txt' %project)
        bug_opened_dict = loadBugDate('../output_data/szz/%s/bug_open_date.csv' %project)
        # analyse data
        bug_inducing_list = identifyBugInducingCommits(project, bug_commit_mapping, bug_opened_dict)
        outputResults(bug_inducing_list)
    
        print 'Done.'
    