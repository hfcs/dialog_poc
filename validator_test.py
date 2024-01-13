import sys
import math
import pandas as pd
from anytree import Node, PreOrderIter
from chatdialogflow import BaseNode, ButtonCaseIdListNode, JumpToNode, LeafNode, DialogFlowForest, WorkspaceCaseId, NodeToDrlRulePrinterSingleton, isBlank, InputTableValidator

myValidator = InputTableValidator()

df = pd.read_excel('validator_test.xlsx') # or read_sql()

myValidator.preScanPass(df)
myValidator.validationPass(df)
myIssueSet = myValidator.getIssueSet()

for issue in myIssueSet:
    print(issue)