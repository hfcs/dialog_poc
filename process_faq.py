import sys
import math
import pandas as pd
from anytree import Node, RenderTree, AsciiStyle, find, PreOrderIter

##############################################
# TODO: move hard coded config into config file and read from there

faq_column = {"CASE_ID": 1,
              "CASE_PARENT": 2, 
              "INTENT_LIST": 3,
              "EXPRESSION_CASE": 4, 
              "JUMP_TO_CASE": 5, 
              "RESPONSE_ID_LIST": 6,
              "ACTION_BUTTON_ID_LIST": 7,
              "PROCEDURE_ADVISORY_ID_LIST": 8, 
              "SET_CONTEXT_EXPRESSION": 9}

##############################################
# globals 

df = pd.read_excel('faq.xlsx')
root = None
parentSet = set()
caseIdSet = set()

##############################################
# Utility functions

def handleRootNodeTypeExcelRow(label, respond_id, action_button_id, procedure_advisory_id):
    global root
    root = Node(label, nodetype="type1", RESPONSE_ID_LIST=respond_id, ACTION_BUTTON_ID_LIST=action_button_id, PROCEDURE_ADVISORY_ID_LIST=procedure_advisory_id)

def handleNonLeafType2AOptionEntryExeclRow(parent, label, respond_id, action_button_id, procedure_advisory_id):
    # TODO: A validator for type 2a
    node = Node(label, parent, nodetype="type2A", RESPONSE_ID_LIST=respond_id, ACTION_BUTTON_ID_LIST=action_button_id, PROCEDURE_ADVISORY_ID_LIST=procedure_advisory_id)
    return node

def handleNonLeafType2BJumpToCaseExeclRow(parent, label, respond_id, jump_to_case):
    # TODO: A validator for type 2b
    node = Node(label, parent, nodetype="type2B", RESPONSE_ID_LIST=respond_id, JUMP_TO_CASE=jump_to_case)
    return node

def handleLeafType3ExeclRow(parent, label, respond_id):
    # TODO: A validator for type3 
    node = Node(label, parent, nodetype="type3", RESPONSE_ID_LIST=respond_id, SET_CONTEXT_EXPRESSION=set_context_expression)
    return node

def isBlank(label):
    return pd.isna(label)

def isParent(label):
    global parentSet
    return label in parentSet

##############################################
# prescan pass for forward reference and other validations
for index, row in df.iterrows():
    parentSet.add(row.iloc[faq_column.get("CASE_PARENT")-1])
    
    caseId = row.iloc[faq_column.get("CASE_ID")-1]
    if caseId == None:
        raise Exception ("Case ID cannot be blank")
    if caseId in caseIdSet:
        raise Exception ("Duplicated Case ID " + caseId)
    else:
        caseIdSet.add(caseId)

##############################################
# main pass
# loop through the rows using iterrows()
for index, row in df.iterrows():
    caseId = row.iloc[faq_column.get("CASE_ID")-1]
    parentCaseId = row.iloc[faq_column.get("CASE_PARENT")-1]
    respond_id = row.iloc[faq_column.get("RESPONSE_ID_LIST")-1]
    jump_to_case = row.iloc[faq_column.get("JUMP_TO_CASE")-1]
    action_button_id = row.iloc[faq_column.get("ACTION_BUTTON_ID_LIST")-1]
    if math.isnan(action_button_id):
        action_button_id = "<blank>"
    procedure_advisory_id = row.iloc[faq_column.get("PROCEDURE_ADVISORY_ID_LIST")-1]
    if math.isnan(procedure_advisory_id):
        procedure_advisory_id = "<blank>"
    set_context_expression = row.iloc[faq_column.get("SET_CONTEXT_EXPRESSION")-1]
    if math.isnan(set_context_expression):
        set_context_expression = "<blank>"

# Types of rows
# 1. root node
#   -blank parent
#   -A special case of 2a
# 2. non-leaf nodes
#   -is a parent
#   -2a. no jump to case => a parent case that render multiple options to choose from
#       -Action button, navigation button
#   -2b. have jump to case => a choosen option to jump to next case
# 3. leaf node
#   -Not a parent
#   -Most likely hook up to content or custom logic (SET_CONTEXT_EXPRESION)
# leaf nodes are attached to one parent node, while non-leaf nodes may jump to leaf nodes with CASE_ID already defined
# 
#
# Execution engine
#
# Input: context(current node), intents, selection input
# Output: response code, new conetxt(next node), buttons
#
#         ┌──────────────┐                 ┌────────────────┐               ┌────────────────┐
#         │              │               ┌────┐             │               │                │
#         │ Bot context  │──────────────>│API │ Rule Engine │──────────────>│ Action for bot │──────────────>
#      ┌->│ (node state) │               └────┘             │  type 1/2b/3  │                │ Return to bot  
#      │  └──────────────┘                 └────────────────┘               └────────────────┘
#      │                                           │ type 2b
#      └───────────────────────────────────────────┘
# 
# -Each iteratiion to the dialog flow engine will start from the chat context (current node), the engine will evaluate matching rule (to currenrt node) for executing action of that single node
# -At the end of iteration the dialog flow engine returns 1) respond dode, 2) new context (next node for iteration), 3) optionally required action for this node (e.g. custom logic, button to render, jump to case)
# -If a call is triggered by intent, or a selection input, the chat context (current node) is first set as the selected node, before executing the node
# -A node execution 
#   -Type 1 & type 2a node
#       -Action button list, advisory ID list are provisioned as output
#       -Return to bot waiting for next input
#   -Type 2b node
#       -Jump to case -> set context (node) to jump target
#       -Next iteration of rule engine
#   -Type 3 node
#       -Required content, custom logic from SET_CONTEXT_EXPRESSION is provisioned as output
#       -Return to bot waiting for next input
# -Tranlate above in Drools DRL
#   
#   The rule execution can be implemented as Drools rules where each row is a business rule, each node have it's own dedicated rules filtered by CASE_ID

    if type (row.iloc[faq_column.get("CASE_PARENT")-1]) != str:
        # type 1, root node
        if root != None:
            raise Exception("Bad FAQ file, multiple root nodes")
        else:
            handleRootNodeTypeExcelRow(caseId, respond_id, action_button_id, procedure_advisory_id)
    else:
        # find parent node
        # create node to parent
        parentNode =  find(root, filter_=lambda node: node.name == parentCaseId)
        # TODO: Watch out we cannot handle forward reference yet
        if parentNode == None:
            raise Exception("Parent Node does not exist")
                
        if isParent(caseId):
            # type 2a/2b, parent node
            if isBlank(jump_to_case):
                handleNonLeafType2AOptionEntryExeclRow(parentNode, caseId, respond_id, action_button_id, procedure_advisory_id)
            else:
                handleNonLeafType2BJumpToCaseExeclRow(parentNode, caseId, respond_id, jump_to_case)
        else:
            if isBlank(jump_to_case):
                handleLeafType3ExeclRow(parentNode, caseId, respond_id)
            #else:
            #    raise Exception("Bad non-leaf entry at CASE_ID " + caseId)

    # if non-leaf create jump to case (TODO: forward reference)
    # if jump to case does not name myself as parent, use a symlink node
    # eles create respond ID

# TODO: tree verifier

##############################################
# tree visualization dump
#print(RenderTree(root, style=AsciiStyle()).by_attr())

##############################################
# Iterate tree and generate rules

#rule <CASE_ID>
#// Attributes
#when
#    getChatContext() == <CASE_ID> 
#then
#    // Call stub functions according to type 1/2a, 2b, and 3 with data from node
#end

def printRuleForNode(node, fileStream):
    print("rule \"" + node.name + "\"", file=fileStream)
    print("  when", file=fileStream)
    print("    chatContext() == " + node.name)
    print("  then", file=fileStream)
    if (node.nodetype == "type1"):
        print("      //System.out.println(\"type1,RESPONSE_ID_LIST=" + node.RESPONSE_ID_LIST + ",ACTION_BUTTON_ID_LIST=" + node.ACTION_BUTTON_ID_LIST + ",PROCEDURE_ADVISORY_ID_LIST=" + node.PROCEDURE_ADVISORY_ID_LIST + "\")")
    else:
        if (node.nodetype == "type2A"):
            print("      //System.out.println(\"type2A,RESPONSE_ID_LIST=" + node.RESPONSE_ID_LIST + ",ACTION_BUTTON_ID_LIST=" + node.ACTION_BUTTON_ID_LIST + ",PROCEDURE_ADVISORY_ID_LIST=" + node.PROCEDURE_ADVISORY_ID_LIST + "\")" )
        else:
            if (node.nodetype == "type2B"):
                print("      //System.out.println(\"type2B,RESPONSE_ID_LIST=" + node.RESPONSE_ID_LIST + ",JUMP_TO_CASE=" + node.JUMP_TO_CASE + "\")" )
            else:
                print("      //System.out.println(\"type3,RESPONSE_ID_LIST=" + node.RESPONSE_ID_LIST + ",SET_CONTEXT_EXPRESSION=" + node.SET_CONTEXT_EXPRESSION + "\")" )
    print("end //" + node.name, file=fileStream)
    print("", file=fileStream)
    print("##############", file=fileStream)
    print("", file=fileStream)

for node in PreOrderIter(root):
#    print(node)
   printRuleForNode(node, sys.stdout)
