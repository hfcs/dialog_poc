import sys
import math
import pandas as pd
from anytree import Node, PreOrderIter, RenderTree, AsciiStyle
from anytree.exporter import MermaidExporter
from chatdialogflow import BaseNode, ButtonCaseIdListNode, JumpToNode, LeafNode, DialogFlowForest, WorkspaceCaseId, NodeToDrlRulePrinterSingleton, isBlank, InputTableValidator, ClonedDialogTree

myValidator1 = InputTableValidator()
myValidator2 = InputTableValidator()


df1 = pd.read_excel('faq.xlsx') # or read_sql()
df2 = pd.read_excel('faq_mod.xlsx')

myValidator1.preScanPass(df1)
myValidator1.validationPass(df1)
myValidator2.preScanPass(df2)
myValidator2.validationPass(df2)

###############################################################################
# main pass building tree
# loop through the rows using iterrows()

dialogFlowForest1 = DialogFlowForest()
dialogFlowForest1.buildForrestFromInputTable(df1)

dialogFlowForest2 = DialogFlowForest()
dialogFlowForest2.buildForrestFromInputTable(df2)


clonedTree1 = ClonedDialogTree(dialogFlowForest1.getTreeRootsList()[0])
clonedTree2 = ClonedDialogTree(dialogFlowForest2.getTreeRootsList()[0])

clonedTree1.markMyDelta(clonedTree2)
clonedTree2.markMyDelta(clonedTree1)

def nodefunc(node):
    if node.isComparedSame():
        return '["%s"]' % (node.name)
    else:
        return '[\\"%s"/]' % (node.name)        

with open('tree1.md', mode='w') as file_object:
    clonedTree1.printMermaid(file_object)
print("***********************")
with open('tree2.md', mode='w') as file_object:
    clonedTree2.printMermaid(file_object)
