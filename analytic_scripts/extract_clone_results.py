import os, subprocess, re, json, sys
from collections import OrderedDict
import pandas as pd

# Run shell command from a string
def shellCommand(command_str):
    cmd = subprocess.Popen(command_str.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

# Extract commit sequence
def commitSequence(project):
    print 'Extracting commit sequence ...'
    commit_list = list()
    with open('../raw_data/%s_logs.txt' %project, 'r') as f:
        reader = f.read().split('\n')
        # For Git projects, recursively find each commit's parent
        if project == 'ant' or project == 'maven':
            last_commit = list(reader)[0].split(',')[0]
            # change to the code repository
            current_dir = os.getcwd()
            os.chdir('../src_code/%s' %project)
            # recursively get a commit's parent commit
            commit_list.append(last_commit)
            parent_commit = shellCommand('git log --pretty=%%p -n 1 %s' %last_commit).strip() 
            while len(parent_commit):
                child_commit = parent_commit.split(' ')[0]                
                commit_list.append(child_commit)
                parent_commit = shellCommand('git log --pretty=%%p -n 1 %s' %child_commit).strip()
            # change back to the script directory
            os.chdir(current_dir)
            # reverse the list
            return commit_list[::-1]
        # For SVN projects, just reverse the commit list 
        elif project == 'argouml' or project == 'jedit':
            for row in reader:
                elems = row.split(',', 3)
                commit_id = elems[0]
                commit_date = re.sub(r'[^0-9]', '', elems[2][:-6])
                commit_list.append([commit_id, commit_date])
            df = pd.DataFrame(commit_list, columns=['id','date']).sort_values(['date'])
            # reverse the list
            return list(df['id'])
        else:
            print 'Wrong project name!'
    return None

# Parse NiCad clone pair strings
def extractNicadInfo(project, info_str):
    clone_info = re.findall(r'file\=\"(.+?)\"\s+startline\=\"([0-9]+)\"\s+endline\=\"([0-9]+)\"', info_str)
    if len(clone_info):
        file_path = clone_info[0][0].split(project+'/', 1)[-1]
        startline = clone_info[0][1]
        endline = clone_info[0][2]
        return file_path, startline + '-' + endline
    return

# Parse clone result files
def parseCloneResults(tool, project, commit_id):
    result_list = list()
    if tool == 'nicad':
        filename = commit_id + '.xml'
    elif tool == 'iclones':
        filename = commit_id + '.txt'
    file_path = '../clone_results/%s/%s/%s' %(tool,project,filename)
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            reader = f.read()
            if tool == 'nicad':
                # extract a pair of clones
                group_list = re.findall(r'<class classid=\"[0-9]+\" nclones=\"[0-9]+\" nlines=\"[0-9]+\" similarity=\"[0-9]+\">(.+?)</class>', reader, re.DOTALL)
                for clone_pair in group_list:
                    # extract clone pair strings
                    clone_group = list()
                    clone_info = re.findall(r'<source (.+?)></source>', clone_pair, re.DOTALL)
                    for snippet in clone_info:
                        file_path, clone_range = extractNicadInfo(project, snippet)
                        clone_group.append([file_path, clone_range])
                    if len(clone_group):
                        result_list.append(clone_group)
            else:
                clone_group = list()
                for line in reader.split('\n'):
                    if re.search(r'^\tCloneClass\t[0-9]+$', line):
                        if len(clone_group):
                            result_list.append(clone_group)
                        clone_group = list()
                    else:
                        clone_info = re.findall(r'^\t\t[0-9]+\t(.+?\.java)\t([0-9]+)\t([0-9]+)$', line)
                        if len(clone_info):
                            file_path = clone_info[0][0].split(project+'/', 1)[-1]
                            startline = clone_info[0][1]
                            endline = clone_info[0][2]
                            range_str = startline + '-' + endline
                            clone_group.append([file_path, range_str]) 
                # add the last clone group
                result_list.append(clone_group)
    return result_list

def outputCommitSequence(commit_sequence):
    output_path = '../raw_data/%s_commit_sequence.txt' %project
    if not os.path.exists(output_path):
        df = pd.DataFrame(commit_sequence, columns=['commit_id'])
        df.to_csv(output_path, index=False, header=False)
    return

if __name__ == '__main__':
    DEBUG = False
    
    if len(sys.argv) != 3:
            print 'Please input [project] & [tool]!'
    else:
        project = sys.argv[1]
        tool = sys.argv[2]
        project_list = ['ant', 'argouml', 'jedit', 'maven']
        tool_list = ['nicad', 'iclones']
        if project in project_list and tool in tool_list:
            # extract commit sequence
            commit_sequence = commitSequence(project)
            outputCommitSequence(commit_sequence)
            # extract clone results
            if commit_sequence:
                print 'Extracting clone results ...'
                output_dir = '../output_data/%s' %tool
                subprocess.Popen('mkdir -p %s' %output_dir, shell=True)
                # parse each commit's clone results
                clone_dict = OrderedDict()
                i = 0
                for commit_id in commit_sequence:
                    if DEBUG:
                        i += 1
                        if i > 10:
                            break
                    print commit_id
                    result_list = parseCloneResults(tool, project, commit_id)
                    clone_dict[commit_id] = result_list
                # output results
                with open('%s/%s.json' %(output_dir, project), 'w') as jsonfile:
                    json.dump(clone_dict, jsonfile)
            
            