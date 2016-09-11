import sys
from scipy import stats
import pandas as pd

def changeType(last_state, current_state):
    if last_state == 'C':
        if current_state == 'C':
            return 'CON'
        else:
            return 'DIV'
    else:
        if current_state == 'I':
            return 'INC'
        else:
            return 'RESYNC'
    return

def genealogyPattern(gen_str):
    gen_pattern_str = ''
    last_state = None
    for current_state in gen_str:
        if current_state != last_state:
            gen_pattern_str += current_state
        last_state = current_state
    if gen_pattern_str == 'C':
        return 'SYNC'
    elif gen_pattern_str == 'I':
        return 'INC'
    elif gen_pattern_str == 'CI':
        return 'DIV'
    elif gen_pattern_str == 'CIC' or gen_pattern_str == 'IC':
        return 'LP'
    elif gen_pattern_str.startswith('CICI') or gen_pattern_str.startswith('ICI'):
        return 'LPDIV'
    return

def loadGenealogies(project, tool):
    gen_stat_list = list()
    change_state_list = list()
    interval_list = list()
    gen_change_list = list()
    df = pd.read_csv('../statistics/%s/%s_basic.csv' %(tool,project))
    for idx,row in df.iterrows():
        # check whether a whole genealogy is buggy
        buggy_gen = False
        if row['buggy_gen']:
            buggy_gen = True
        # check whether a modification is buggy
        last_state = 'C'
        gen_str = ''
        for s in row['state+fault'].split('^'):
            current_state = s.split('_')[0]
            buggy = s.split('_')[1]
            # gen + change
            temp_gen = genealogyPattern(gen_str)
            if temp_gen:
                gen_change = '%s+%s' %(temp_gen,current_state)
                gen_change_list.append([gen_change, buggy])
            # change type only
            gen_str += current_state
            change_type = changeType(last_state, current_state)
            last_state = current_state
            change_state_list.append([change_type, buggy]) 
        gen_pattern = genealogyPattern(gen_str)             
        gen_stat_list.append([gen_pattern, buggy_gen, row['size']])
        # check whether a modification within a time interval is buggy
        for interval in row['interval'].split('^'):
            interval_category = interval.split('_')[0]
            interval_buggy = interval.split('_')[1]
            interval_list.append([interval_category, interval_buggy])
    return gen_stat_list, change_state_list, gen_change_list, interval_list

def countOccurrences(df, cond1, cond2):
    return len(df[(df.ix[:,0]==cond1) & (df.ix[:,1]==cond2)])

def computeFisherExact(df, input_list, output_list):
    table_list = list()
    for in_var in input_list:
        row_list = list()
        for out_var in output_list:
            row_list.append(countOccurrences(df, in_var, out_var))
        table_list.append(row_list)
    print table_list
    print '%10s%10s' %('odds_ratio', 'p-value')
    for i in range(1, len(table_list)):
        oddsratio, pvalue = stats.fisher_exact([table_list[i], [table_list[0]])
        if pvalue < 0.01:
            print '%10.2f%10s' %(round(oddsratio,2), '<0.01')
        else:
            print '%10.2f%10.2f' %(round(oddsratio,2), round(pvalue,2))
    return
    
def cloneSize(row, median_size):
    pattern = row['pattern']
    size = row['size']
    if size >= median_size:
        return pd.Series([pattern + '+big', row['buggy']])
    else:
        return pd.Series([pattern + '+small', row['buggy']])
    return
    

def statistics(gen_stat_list, change_state_list, gen_change_list, interval_list):
    ### genealogy's fault-proneness ###
    print 'Evolutionary patterns:'
    df_gen = pd.DataFrame(gen_stat_list, columns=['pattern', 'buggy', 'size'])
    gen_patterns = ['SYNC', 'INC', 'DIV', 'LP', 'LPDIV']
    buggy = [True, False]
    # perform Fisher exact test on a pattern against the SYNC pattern
    computeFisherExact(df_gen, gen_patterns, buggy)
    print '-'*30
    #### change's fault-proneness ###
    print 'Change types:'
    df_ch = pd.DataFrame(change_state_list, columns=['type', 'buggy'])
    ch_types = ['CON', 'DIV', 'INC', 'RESYNC']
    buggy = ['Y', 'N']
    # perform Fisher exact test on a change type against the CON type
    computeFisherExact(df_ch, ch_types, buggy)
    print '-'*30
    ### gen + change ###
    print 'Evolutionary patterns + change type:'
    df_g_c = pd.DataFrame(gen_change_list, columns=['type', 'buggy'])
    combined_types = list()
    gen_list =  ['INC', 'SYNC', 'DIV', 'LPDIV', 'LP']
    ch_list = ['I', 'C']
    for g in gen_list:
        for c in ch_list:
            combined_types.append('%s+%s' %(g,c))
    buggy = ['Y', 'N']
    # perform Fisher exact test on a combination against INC+I
    computeFisherExact(df_g_c, combined_types, buggy)
    print '-'*30
    ### change interval's fault-proneness ###
    print 'Change interval:'
    df_inter = pd.DataFrame(interval_list, columns=['time', 'buggy'])
    interval_types = ['D', 'W', 'M', 'Y', 'YY']
    buggy = ['Y', 'N']
    computeFisherExact(df_inter, interval_types, buggy)
    print '-'*30
    ### clone size ###
    print 'Clone size:'
    median_size = df_gen['size'].median()
    df_gen[['pattern+size','p_s_buggy']] = df_gen.apply(cloneSize, axis=1, args=(median_size,))
    pattern_size_list = list()
    size_type = ['small', 'big']
    for st in size_type:
        for gp in ['SYNC', 'DIV', 'INC', 'LPDIV', 'LP']:
            pattern_size_list.append('%s+%s' %(gp,st))
    buggy = [True, False]
    computeFisherExact(df_gen[['pattern+size','p_s_buggy']], pattern_size_list, buggy)
    return

if __name__ == '__main__':
    tool = 'nicad'
    project = 'argouml'
    gen_stat_list, change_state_list, gen_change_list, interval_list = loadGenealogies(project, tool)
    statistics(gen_stat_list, change_state_list, gen_change_list, interval_list)
