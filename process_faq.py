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

def handleRootNodeTypeExcelRow(label):
    global root
    root = Node(label, nodetype="type1")

def handleNonLeafType2AOptionEntryExeclRow(parent, label, respond_id):
    # TODO: A validator for type 2a
    node = Node(label, parent, nodetype="type2A", RESPONSE_ID_LIST=respond_id)
    return node

def handleNonLeafType2BJumpToCaseExeclRow(parent, label, jump_to_case):
    # TODO: A validator for type 2b
    node = Node(label, parent, nodetype="type2B", JUMP_TO_CASE=jump_to_case)
    return node

def handleLeafType3ExeclRow(parent, label):
    # TODO: A validator for type3 
    node = Node(label, parent, nodetype="type3")
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
# Input: context(current node), intents, selection input
# Output: response code, buttons, new conetxt(next node)
# 
# Each call to the dialog flow engine will start from the chat context (current node) and carry out required evaluation, action of that single node
# -If a call is triggered by intent, or a selection input, the chat context (current node) is first set as the selected node, before executing the node
# -A node execution 
#   -Type 1 & type 2a node
#       -Action button list, advisory ID list are provisioned as outout
#       -return with respond ID
#   -Type 2b node
#       -Junp to case is identified and provisioned as output
#       -return with resspond ID
#   -Type 3 node
#       -Required content, custom logic from SET_CONTEXT_EXPRESSION is provisioned as output
#       -return with respond ID
# -Tranlate above in Drools DRL
#
#rule <CASE_ID>
#    // Attributes
#    when
#        getChatContext() == <CASE_ID> 
#    then
#        // Call stub functions according to type 1/2a, 2b, and 3 with data from node
#end
#   
#   The rule execution can be implemented as Drools rules where each row is a business rule, each node have it's own dedicated rules filtered by CASE_ID

    if type (row.iloc[faq_column.get("CASE_PARENT")-1]) != str:
        # type 1, root node
        if root != None:
            raise Exception("Bad FAQ file, multiple root nodes")
        else:
            handleRootNodeTypeExcelRow(caseId)
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
                handleNonLeafType2AOptionEntryExeclRow(parentNode, caseId, respond_id)
            else:
                handleNonLeafType2BJumpToCaseExeclRow(parentNode, caseId, jump_to_case)
        else:
            if isBlank(jump_to_case):
                handleLeafType3ExeclRow(parentNode, caseId)
            else:
                raise Exception("Bad non-leaf entry at CASE_ID " + caseId)

    # if non-leaf create jump to case (TODO: forward reference)
    # if jump to case does not name myself as parent, use a symlink node
    # eles create respond ID

##############################################
# tree visualization dump
print(RenderTree(root, style=AsciiStyle()).by_attr())

##############################################
# Iterate tree and generate rules

#for node in PreOrderIter(root):
#    print(node)
