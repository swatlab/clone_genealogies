from __future__ import division
import json, os, subprocess, re, csv, sys, gc, whatthepatch
from collections import OrderedDict

# Run shell command from a string
def shellCommand(command_str):
    cmd =subprocess.Popen(command_str.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

# Format clone groups (clone classes)
def formatCloneGroup(clone_group):
    formatted_group = list()
    for snippet in clone_group:
        formatted_group.append((snippet[0], int(snippet[1].split('-')[0]), int(snippet[1].split('-')[1])))
    return formatted_group

# Extract clone pairs from clone classes (clone groups)
def clonePairs(clone_dict):
    print 'Extracting clone pairs ...'    
    clone_pair_dict = OrderedDict()
    idx_debug = 0
    for commit_id in clone_dict:
        idx_debug += 1
        if DEBUG:
            if idx_debug > TOTAL_COMMIT:
                break
        clone_pair_list = list()
        clone_list = clone_dict[commit_id]
        for clone_group in clone_list:
            formatted_group = formatCloneGroup(clone_group)
            sorted_clone_group = sorted(formatted_group)
            group_size = len(sorted_clone_group)
            for i in range(group_size):
                snippet1 = sorted_clone_group[i]
                for j in range(i+1, group_size):
                    snippet2 = sorted_clone_group[j]
                    clone_pair_list.append([snippet1, snippet2, 0])
        # add clone pairs to the pair dict
        clone_pair_dict[commit_id] = clone_pair_list    
    return clone_pair_dict

# Extract changed file paths and their changed ranges
def extractChangedFiles(commit_id):
    # extract changed files
    changed_file_dict = dict()
    raw_str = shellCommand('git log %s -n 1 --name-status' %commit_id)
    modified_files = re.findall(r'M{1,2}\t(.+?\.java)', raw_str, re.MULTILINE)
    deleted_files = re.findall(r'D\t(.+?\.java)', raw_str, re.MULTILINE)
    return modified_files, deleted_files

# map line number from old commit to new commit
def mapLineNumber(line_mapping, old_start, old_end):
    begin_to_count = False
    churn_cnt = 0
    new_start, new_end = old_start, old_end
    for line_pair in line_mapping:
        old_line = line_pair[0]
        new_line = line_pair[1]
        if old_line > old_end:
            return churn_cnt, new_start, new_end
        if old_line and new_line:
            # find the new start line
            if old_line <= old_start:
                new_start = (new_line - old_line) + old_start
                new_end = (new_line - old_line) + old_end                    
            # calculate the new end line
            elif old_line <= old_end:
                begin_to_count = True
                new_end = (new_line - old_line) + old_end 
        else:
            if old_line == old_start:
                begin_to_count = True
            # if last line deleted in the clone boundary
            if begin_to_count:
                if new_line == None:
                    new_end -= 1
                churn_cnt += 1
    return churn_cnt, new_start, new_end

# compute expected range of a clone snippet
def expectedRange(start_line, end_line, diff_str, file_path):
    in_diff = False
    for diff in whatthepatch.parse_patch(diff_str):
        diff_path = diff[0].old_path
        if diff_path == file_path:
            in_diff = True
            line_mapping = diff[1]        
            churn_cnt, new_start, new_end = mapLineNumber(line_mapping, start_line, end_line)
            return churn_cnt, new_start, new_end
    return 0, start_line, end_line

# Analyse a clone file's modification in the new commit
def cloneModification(commit_id, file_path, start_line, end_line, diff_dict):
    # change to the code repository directory
    os.chdir(repo_dir)
    # perform Git Diff command
    diff_str = diff_dict[commit_id]    
    # calculate expected range
    range_res = expectedRange(start_line, end_line, diff_str, file_path)
    # go back to the script directory
    os.chdir(current_dir)
    return range_res

# match clone range in the new commit
def matchClone(clone_pair_dict, commit_id, path1, start1, end1, path2, start2, end2):
    pairs_in_commit = clone_pair_dict[commit_id]
    for clone_pair in pairs_in_commit:
        if clone_pair[2] == 0:
            snippet1, snippet2 = clone_pair[0], clone_pair[1]
            s1_path, s1_start, s1_end = snippet1[0], snippet1[1], snippet1[2]
            s2_path, s2_start, s2_end = snippet2[0], snippet2[1], snippet2[2]
            if (path1 == s1_path) and (path2 == s2_path):
                if (start1 >= s1_start) and (end1 <= s1_end):
                    if (start2 >= s2_start) and (end2 <= s2_end):
                        clone_pair[2] = 1
                        return True
    return False

# Analyse the genealogy for a clone pair
def clone_genealogy(clone_pair, start_commit, clone_pair_dict, changed_file_dict, diff_dict):
    if clone_pair[2] == 0:
        genealogy_list = list()
        clone_pair[-1] = 1          # marked as this clone snippet has been analysed
        path1 = clone_pair[0][0]    # original path of the 1st snippet
        path2 = clone_pair[1][0]    # original path of the 2nd snippet
        start1 = clone_pair[0][1]   # original start line of the 1st snippet
        start2 = clone_pair[1][1]   # original start line of the 2nd snippet
        end1 = clone_pair[0][2]     # original end line of the 1st snippet
        end2 = clone_pair[1][2]     # original end line of the 2nd snippet
        genealogy_started = False
        for commit_id in clone_pair_dict:
            if genealogy_started == False:
                if commit_id == start_commit:
                    genealogy_started = True
            else:                                
                modified_files, deleted_files = changed_file_dict[commit_id]
                # if one or two of the clone snippet (in a pair) is deleted, then stop track this pair
                if (path1 in deleted_files) or (path2 in deleted_files):
                    return (genealogy_list, start_commit, commit_id)
                if (start1 >= end1) or (start2 >= end2):
                    return (genealogy_list, start_commit, commit_id)
                # if one or two of the clone files (in a pair) is changed
                if (path1 in modified_files) or (path2 in modified_files):
    #                    print ' ', commit_id
    #                    print '   ', start1, end1, '\t', start2, end2                    
                    churn1, churn2 = 0, 0
                    if path1 in modified_files:
                        churn1, start1, end1 = cloneModification(commit_id, path1, start1, end1, diff_dict)
                    if path2 in modified_files:
                        churn2, start2, end2 = cloneModification(commit_id, path2, start2, end2, diff_dict)
                    # if one or two of the clone files (in a pair) is modified (+/- in the clone boundaries)
                    if (churn1 > 0) or (churn2 > 0):
                        if matchClone(clone_pair_dict, commit_id, path1, start1, end1, path2, start2, end2):
                            state = 'C'
                        else:
                            state = 'I'
                        churn_cnt = churn1 +churn2
                    # none of the clone files is modified
                    else:
                        state = 'na'
                # none of the clone files is changed
                else:
                    state = 'na'
                if state != 'na':
                    genealogy_list.append('%s,%s,%s' %(state,commit_id,churn_cnt))
        return (genealogy_list, start_commit, commit_id)
    else:
        return 'old_pair'

# Make a signature for each clone pair
def makeCloneSignature(clone_pair):
    snippet1 = '%s^%d^%d' %(clone_pair[0][0], clone_pair[0][1], clone_pair[0][2])
    snippet2 = '%s^%d^%d' %(clone_pair[1][0], clone_pair[1][1], clone_pair[1][2])
    return snippet1 + '+' + snippet2

if __name__ == '__main__':
    DEBUG = False
    if len(sys.argv) != 3:
            print 'Please input [project] & [tool]!'
    else:
        project = sys.argv[1]
        tool = sys.argv[2]
        project_list = ['ant', 'argouml', 'jedit', 'maven']
        tool_list = ['nicad', 'iclones']
        with open('../output_data/%s/%s_genealogies.csv' %(tool,project), 'w') as output_file:
            output_writer = csv.writer(output_file)
            output_writer.writerow(['clone_pair', 'start_commit', 'end_commit', 'genealogy'])
            if (project in project_list) and (tool in tool_list):
                # set debug parameters
                TOTAL_COMMIT = 500
                COMMIT_ROUND = 300
                PAIR_PER_COMMIT = 200
                # directory paths (global variables)
                current_dir = os.getcwd()
                repo_dir = '../src_code/%s' %project
                # load clone classes
                print 'Loading clone classes in each commit ...'
                genealogy_set = set()
                with open('../output_data/%s/%s.json' %(tool, project), 'r') as jsonfile:
                    clone_class_dict = json.load(jsonfile, object_pairs_hook=OrderedDict)
                    modified_file_dict = dict()
                    clone_pair_dict = clonePairs(clone_class_dict)
                # extract changed files for each commit
                print 'Extracting changed files and diff ...'
                # change to the code repository directory
                os.chdir(repo_dir)
                diff_dict = dict()
                changed_file_dict = dict()
                for commit_id in clone_pair_dict:
                    modified_files, deleted_files = extractChangedFiles(commit_id)
                    changed_file_dict[commit_id] = (modified_files, deleted_files)
                    # perform Git Diff command
                    diff_str = shellCommand('git diff %s^ %s' %(commit_id,commit_id))
                    diff_dict[commit_id] = unicode(diff_str, errors='replace')
                # go back to the script directory
                os.chdir(current_dir)
                # analyse clone genealogies
                print 'Analysing clone genealogy for each pair ...'
                finished_cnt = 0
                commit_debug = 0
                for commit_id in clone_pair_dict:
                    print commit_id
                    commit_debug += 1
                    if DEBUG:
                        pair_debug = 0
                        if commit_debug > COMMIT_ROUND:
                            break
                    print '  pair #:', len(clone_pair_dict[commit_id])
                    if DEBUG:
                        print '  %.1f%% completed' %(commit_debug / COMMIT_ROUND * 100)
                    else:
                        print '  %.1f%% completed' %(commit_debug / len(clone_pair_dict) * 100) 
                    for clone_pair in clone_pair_dict[commit_id]:
                        if DEBUG:
                            pair_debug += 1
                            if pair_debug > PAIR_PER_COMMIT:
                                break
                        clone_sig = makeCloneSignature(clone_pair)
                        if clone_sig in genealogy_set:
                            if DEBUG:
                                print '  Already analysed'
                        else:
                            genealogy_res = clone_genealogy(clone_pair, commit_id, clone_pair_dict, changed_file_dict, diff_dict)
                            if genealogy_res != 'old_pair':
                                genealogy_set.add(clone_sig)
                                print '\tGenealogy:', genealogy_res
                                genealogy_str = '-'.join(genealogy_res[0])
                                start_commit, end_commit = genealogy_res[1], genealogy_res[2]
                                output_writer.writerow([clone_sig, start_commit, end_commit, genealogy_str])
                            else:
                                print '  Old pair!'
