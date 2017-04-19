library(car)
library(caret)
library(modEvA)
library(plyr)

project = 'maven'
tool = 'iclones'

# Load data as a data frame
df = as.data.frame(read.csv(file=sprintf('../%s/%s_metrics.csv', tool, project)), header=TRUE)
cols = c(2:3, 5:11, 13:19)
df.log = log(df[,cols] + 1)
df.log$CFltFix = df$CFltFix
df.log$CCurSt = df$CCurSt
df.log$EEvPattern = df$EEvPattern
df.log$buggy = df$buggy

head(df.log)

##### build model M(s) #####
xcol = c('cloc','CFltFix','CPathDepth','CCurSt','experience')
formula = as.formula(paste('buggy ~ ', paste(xcol, collapse= '+')))
fit1 = glm(formula, data = df.log, family = binomial())
# coefficients and p-value of M(s)
vif(fit1)
fit1
summary(fit1)
# deviance explained of M(s)
Dsquared(fit1)
# variable importance in M(s)
varImp(fit1, scale = FALSE)

##### build model M(s+e) #####
xcol = c(xcol, c('EFltDens','TChurn','TPC','NumOfBursts','SLBurst','CFltRate'))
formula = as.formula(paste('buggy ~ ', paste(xcol, collapse= '+')))
fit2 = glm(formula, data = df.log, family = binomial())
# VIF analysis
vif(fit2)
formula = update(formula, ~. -NumOfBursts)
fit2 = glm(formula, data = df.log, family = binomial())
vif(fit2)
# show coefficients and p-value of M(s+e)
fit2
summary(fit2)
# compare M(s+e) against M(s)
anova(fit1, fit2, test='Chisq')
# deviance explained of M(s+e)
Dsquared(fit2)


##### build model M(s+e+g) #####
xcol = c(xcol, c('EEvPattern','EConChg','EIncChg','EConStChg','EIncStChg','EFltsConStChg','EFltIncStChg','EChgTimeInt'))
formula = as.formula(paste('buggy ~ ', paste(xcol, collapse= '+')))
fit3 = glm(formula, data = df.log, family = binomial())
# VIF analysis
#alias(fit3)
#formula = update(formula, ~. -EEvPattern -EIncChg -EConStChg -EIncStChg -EFltsConStChg -EFltIncStChg)
#fit3 = glm(formula, data = df.log, family = binomial())
#alias(fit3)
vif(fit3)
formula = update(formula, ~. -NumOfBursts -EConChg -CCurSt -EEvPattern -EIncChg -EIncStChg)
fit3 = glm(formula, data = df.log, family = binomial())
vif(fit3)
# show coefficients and p-value of M(s+e+g)
fit3
summary(fit3)
# compare M(s+e+g) against M(s+e)
anova(fit2, fit3, test='Chisq')
# deviance explained of M(s+e+g)
Dsquared(fit3)
# variable importance in M(s+e+g)
imp = varImp(fit3)
imp$Variable = rownames(imp)
imp = imp[c('Variable', 'Overall')]
arrange(imp,desc(Overall))

