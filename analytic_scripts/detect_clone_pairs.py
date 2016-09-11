from __future__ import division
import sys, os, re, subprocess, shutil
import pandas as pd

# Run shell command from a string
def shellCommand(command_str):
    cmd =subprocess.Popen(command_str.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

# Sort commits by their date in ascending order
def sortCommitsByDate(project):
    commit_list = list()
    with open('../raw_data/%s_logs.txt' %project, 'r') as f:
        reader = f.read().split('\n')
        for row in reader:
            elems = row.split(',', 3)
            commit_id = elems[0]
            commit_date = re.sub(r'[^0-9]', '', elems[2][:-6])
            if commit_date < '201608010000':
                commit_list.append([commit_id, commit_date])
    df = pd.DataFrame(commit_list, columns=['commit_id', 'commit_date'])
    sorted_commits = list(df.sort_values('commit_date')['commit_id'])
    return sorted_commits


if __name__ == '__main__':
    DEBUG = False
    
    if len(sys.argv) != 3:
            print 'Please input [project] & [tool]!'
    else:
        project = sys.argv[1]
        tool = sys.argv[2]
        project_list = ['ant', 'argouml', 'jedit', 'swt']
        tool_list = ['nicad', 'iclones']
        if (project in project_list) and (tool in tool_list):
            # get the current directory
            current_dir = os.getcwd()
            # sort commits by date in ascending order
            sorted_commits = sortCommitsByDate(project)
            # total number of commits
            num_commits = len(sorted_commits)
            # initialisation
            if tool == 'nicad':
                # clean previous clone results and make the results' directory
                subprocess.Popen('rm -rf ../src_code/%s_functions*' %project, shell=True)
                subprocess.Popen('mkdir -p ../clone_results/nicad/%s' %project, shell=True)
            elif tool == 'iclones':
                subprocess.Popen('mkdir -p ../clone_results/iclones/%s' %project, shell=True)
            i = 0
            for commit_id in sorted_commits:
                i += 1
                if DEBUG:
                    if i > 50:
                        break
                print commit_id
                print '  %.1f%%' %(i/num_commits*100)
                # checkout a specific commit
                os.chdir('../src_code/%s' %project)
                shellCommand('git checkout %s' %commit_id)
                os.chdir(current_dir)
                # clone detection
                if tool == 'nicad':
                    # perform clone detection by NiCad
                    shellCommand('nicad4 functions java ../src_code/%s' %project)
                    # move the results to the result folder
                    src_path = '../src_code/%s_functions-clones/%s_functions-clones-0.30-classes.xml' %(project,project)
                    dest_path = '../clone_results/nicad/%s/%s.xml' %(project,commit_id)
                    shutil.move(src_path, dest_path)
                    # delete NiCad output files
                    subprocess.Popen('rm -rf ../src_code/%s_functions*' %project, shell=True)
                elif tool == 'iclones':
                    input_path = '../src_code/%s' %project
                    output_path = '../clone_results/iclones/%s/%s.txt' %(project,commit_id)
                    shellCommand('iclones -input %s -output %s' %(input_path,output_path))
                # clean memory
                shellCommand('sudo sysctl -w vm.drop_caches=3')
    
