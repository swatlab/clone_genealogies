#An Investigation of the Fault-proneness of Clone Evolutionary Patterns

###Requirements
- Python 2.7 or newer
- R 3.1 or newer
- NiCad clone detection tool
- iClones clone detection tool

###File description
- **analytic_scripts** folder contains the scripts to mine software repositories.
	- **detect_clones.py**: detect clone classes from each of the commits from a Git repository. This script will output raw clone results of a subject system.
	- **extract_clone_results.py**: extract clone classes into a JSON file from the raw clone results.
	- **build_genealogies.py**: extract clone pairs from the results of clone classes, then built the clone genealogy for each clone pair.
	- **analyse_genealogies.py**: extract basic metrics from the results of clone genalogies.
	- **independant_variables.py**: extract explanatory metrics from the basic metrics of clone genealogies.
	- **commit_bug_mapping.py**: map bug-fixing commits to their corresponding bugs.
	- **fault_inducing.py**: identify bug-inducing commits based on the SZZ algorithm.
- **statistics** folder contains data extracted from software repositories and statistical analysis scripts. For each subject system, we extract its basic metrics; and from the basic metrics we further extract its metrics for modelling.
  - **modelling** folder contains R scripts to build the GLM model for each subject system using a specific clone detection tool.
- **raw_data** folder contains the commit logs and commit sequence for each subject system extracted from its Git repository.
- **output_data.zip** is a compressed folder that contains the results of clone classes, clone genealogies, and bug-inducing commits.

###How to user the analytic scripts
1. Clone a project's Git repository. For systems originally managed by SVN, please follow this tutorial to clone the repository as Git:
   https://www.atlassian.com/git/tutorials/migrating-convert/.
2. Use the following command to extract the project's commit logs:
	```git log --pretty=format:"%H,%ae,%ai,%s"```.
3. Uncompress the folder ```output_data.zip```.
4. Run **detect_clones.py** and **extract_clone_results.py** to detect clone classes for a subject system using a clone detection tool.
6. Run **build_genealogies.py** to extract clone pairs from the JSON file, then build clone genealogies for each clone pair.
7. Run **commit_bug_mapping.py** and **fault_inducing.py** to identify bug-inducing commits.
8. Run **statistics.py** to perform Fisher's exact test for RQ1 and RQ2.
9. Run **independant_variables.py** to extract explanatory variables for RQ3.
10. Build __GLM__ models with the R script in the **statistics/modelling** folder for RQ3.

###Data source
- Source code repositories:
  - ArgoUML: http://argouml-stats.stage.tigris.org/documentation/defaulthtml/cookbook/ch02s05.html
  - Ant: https://github.com/apache/ant
  - JEdit: https://sourceforge.net/p/jedit/svn/HEAD/tree/
  - Maven: https://github.com/apache/maven
- Bug tracking systems:
  - ArgoUML: http://argouml.tigris.org/project_bugs.html
  - Ant: https://bz.apache.org/bugzilla/
  - JEdit: https://sourceforge.net/p/jedit/bugs/
  - Maven: https://issues.apache.org/jira/browse/MNG

###For any questions###
Please send email to le.an@polymtl.ca