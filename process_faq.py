import sys
import math
import pandas as pd
from anytree import Node, PreOrderIter
from chatdialogflow import BaseNode, ButtonCaseIdListNode, JumpToNode, LeafNode, DialogFlowForest, WorkspaceCaseId, NodeToDrlRulePrinterSingleton, isBlank, InputTableValidator

myValidator = InputTableValidator()

df = pd.read_excel('faq.xlsx') # or read_sql()

###############################################################################
# This is a demo/test of happy flow on a well formed input table

###############################################################################
# Validation pass

myValidator.preScanPass(df)
myValidator.validationPass(df)

###############################################################################
# main pass building tree
# loop through the rows using iterrows()

dialogFlowForest = DialogFlowForest()

dialogFlowForest.buildForrestFromInputTable(df)

# TODO: tree verifier

##############################################
# tree visualization dump
dialogFlowForest.printForest(sys.stdout)
dialogFlowForest.printMermaid(sys.stdout)

NodeToDrlRulePrinterSingleton().printHeader(sys.stdout)
#print(dialogFlowForest.getTreeRootsList())
for root in dialogFlowForest.getTreeRootsList():
    for node in PreOrderIter(root):
        NodeToDrlRulePrinterSingleton().printRuleCommentForNode(node, sys.stdout)
        NodeToDrlRulePrinterSingleton().printRuleForNode(node, sys.stdout)
        print("##############", file=sys.stdout)
        