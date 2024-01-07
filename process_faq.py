import sys
import math
import pandas as pd
from anytree import Node, PreOrderIter
from chatdialogflow import BaseNode, ButtonCaseIdListNode, JumpToNode, LeafNode, DialogFlowForest, WorkspaceCaseId, NodeToDrlRulePrinterSingleton, isBlank

##############################################
# TODO: move hard coded config into config file and read from there

faq_column = {"WORKSPACE": 2,
              "CASE_ID": 3, 
              "JUMP_TO_CASE": 5, 
              "RESPONSE_ID_LIST": 6,
              "ACTION_BUTTON_ID_LIST": 7,
              "PROCEDURE_ADVISORY_ID_LIST": 8,
              "BUTTON_CASE_ID_LIST": 9,
              "SET_CONTEXT_EXPRESSION": 16}

##############################################
# globals 

df = pd.read_excel('faq.xlsx') # or read_sql()

# "Symbol table", a dictionary of workspace (key) and their defined Case ID set (value as set of case ID)
_workspaceCaseIdDict = {}
# "Local reference table", a dictionary of workspace (key) and their referenced jump to Case ID set (value as set of case ID)
_workspaceJumpToDict = {}
# "Local reference table", a dictionary of workspace (key) and their referenced button Case ID List set (value as set of case ID)
_workspaceButtonCaseIdListDict = {}
# "Global reference table", a set of (workspace, case_id) of workspace switching reference
_switchWorkspaceSet = set()



##############################################
# Main function, with temporary function as test harness for now

# Types of rows
# 0. case ID MIN_START is a reserved name for root nodes
# 1. Have jump to case ID
# 2. Have button_case_id list
# 
# switching conext to another workspace also require that case ID define in that workspace
#
# Each workspace will hold a root of a dedicated tree in workspaceTreeDict
#
# * Pre-scan symbol pass
#   * Collect case id (symbols), known reference (jump to case, button case id, jump to case in another workspaces), workspace they belong to
#   * Build symbol table
# * Validation pass
#   * Validate known reference to ensure all case id referenced exist, and defined in referred workspace
# * Tree materialization pass
#   * From symbol table, build all nodes into a key, value dictionary using case ID as key
#   * Scan all symbols and create root node per workspace
#   * Going down the rows and connect all childrens to parents
#
# Each nodes have
# * case id
# * a) chlidren: button case ID list
# * b) leaf: jump to case is handled as leaf to avoid closed loop in a tree structure
#

###############################################################################
# Pre-scan pass for recording symbol tables for validation
for index, row in df.iterrows():

    workspace = row.iloc[faq_column.get("WORKSPACE")-1]
    caseId = row.iloc[faq_column.get("CASE_ID")-1]
    jumpToCase = row.iloc[faq_column.get("JUMP_TO_CASE")-1]
    respond_id_list = row.iloc[faq_column.get("RESPONSE_ID_LIST")-1]
    respondIdList = []
    action_button_id_list = row.iloc[faq_column.get("ACTION_BUTTON_ID_LIST")-1]
    actionButtonIdList = []
    button_case_id_list = row.iloc[faq_column.get("BUTTON_CASE_ID_LIST")-1]
    buttonCaseIdList = []
    
    if isBlank(caseId):
        raise Exception ("Case ID cannot be blank")
    
    if isBlank(workspace):
        raise Exception ("Workspace cannot be blank")      

    if isBlank(respond_id_list):
        raise Exception ("Respond ID List cannot be blank")      
    else:
        respondIdList = [item.strip() for item in respond_id_list.split(",")]

    if isBlank(button_case_id_list) == False:
        buttonCaseIdList = [item.strip() for item in button_case_id_list.split(",")]
        if len(set(buttonCaseIdList)) != len(buttonCaseIdList):
            raise Exception ("Button case ID list cannot contain duplicate entries")
        actionButtonIdList = [item.strip() for item in action_button_id_list.split(",")]
        if len(set(actionButtonIdList)) != len(actionButtonIdList):
            raise Exception ("Action Button case ID list cannot contain duplicate entries")
        if len(set(actionButtonIdList)) != len(set(buttonCaseIdList)):
            raise Exception ("Action button list must have same size as button case ID list")


    # "Symbol table", a dictionary of workspace (key) and their defined Case ID set (value as set of case ID)
    if workspace in _workspaceCaseIdDict:
        caseIdList = _workspaceCaseIdDict.get(workspace)
        if caseId not in caseIdList:
            caseIdList.add(caseId)
        else:
            raise Exception ("Case ID \'" + caseId + "\' is defined more than once in workspace \'" + workspace + "\'")
    else:
        _workspaceCaseIdDict.update({workspace:{caseId}})

    # "Local reference table", a dictionary of workspace (key) and their referenced jump to/button list Case ID set (value as set of case ID))
    if isBlank(jumpToCase) == False:
        if workspace in _workspaceJumpToDict:
            jumpToList = _workspaceJumpToDict.get(workspace)
            jumpToList.add(jumpToCase)
        else:
            _workspaceJumpToDict.update({workspace:{jumpToCase}})

    # "Local reference table", a dictionary of workspace (key) and their referenced button Case ID List set (value as set of case ID)    
    for buttonCaseId in buttonCaseIdList:
        if workspace in _workspaceButtonCaseIdListDict:
            jumpToList = _workspaceButtonCaseIdListDict.get(workspace)
            jumpToList.add(buttonCaseId)
        else:
            _workspaceButtonCaseIdListDict.update({workspace:{buttonCaseId}})

    # "Global reference table", a set of (workspace, case_id) of workspace switching reference
    #_switchWorkspaceSet = set()
    # TODO

###############################################################################
# validation pass for spotting malformed dialog flow input
# loop through the rows using iterrows()
            
#TODO: handle advisory procedure check against non-leaf

#for index, row in df.iterrows():
#   TODO: do something
            
# Validate all jump-to are defined
for workspace in _workspaceJumpToDict.keys():
    if workspace in _workspaceCaseIdDict:
        for jumpToCaseId in _workspaceJumpToDict.get(workspace):
            if jumpToCaseId not in _workspaceCaseIdDict.get(workspace):
                raise Exception ("Jump to case ID \'" + jumpToCaseId + "\' is not defined in workspace " + workspace)
    else:
        raise Exception ("No case ID are defined in workspace " + workspace)

# Validate all button case id list are defined
for workspace in _workspaceButtonCaseIdListDict.keys():
    if workspace in _workspaceCaseIdDict:
        for jumpToCaseId in _workspaceButtonCaseIdListDict.get(workspace):
            if jumpToCaseId not in _workspaceCaseIdDict.get(workspace):
                raise Exception ("Button case ID list \'" + jumpToCaseId + "\' is not defined in workspace " + workspace)
    else:
        raise Exception ("No case ID are defined in workspace " + workspace)

# Validate all switch workspace case id are defined   
for switchWorkspaceItem in _switchWorkspaceSet:
    if switchWorkspaceItem.value() not in _workspaceCaseIdDict.get(switchWorkspaceItem.key()):
        raise Exception ("Switch workspace case ID \'" + switchWorkspaceItem.value() + "\' is not defined in workspace " + switchWorkspaceItem.key())


###############################################################################
# main pass building tree
# loop through the rows using iterrows()

dialogFlowForest = DialogFlowForest()

for index, row in df.iterrows():
    workspace = row.iloc[faq_column.get("WORKSPACE")-1]
    caseId = row.iloc[faq_column.get("CASE_ID")-1]
    jumpToCase = row.iloc[faq_column.get("JUMP_TO_CASE")-1]
    respond_id_list = row.iloc[faq_column.get("RESPONSE_ID_LIST")-1]
    action_button_id_list = row.iloc[faq_column.get("ACTION_BUTTON_ID_LIST")-1]
    button_case_id_list = row.iloc[faq_column.get("BUTTON_CASE_ID_LIST")-1]
    procedure_advisory_id_list = row.iloc[faq_column.get("PROCEDURE_ADVISORY_ID_LIST")-1]
    
    # pre-scan already checked
    #if isBlank(caseId):
    #    raise Exception ("Case ID cannot be blank")
    #
    #if isBlank(workspace):
    #    raise Exception ("Workspace cannot be blank")      
    #
    #if isBlank(respond_id_list):
    #    raise Exception ("Respond ID List cannot be blank")  

    respondIdList = [item.strip() for item in respond_id_list.split(",")]
        
    if isBlank(jumpToCase) == False:
        dialogFlowForest.createJumpToNode (WorkspaceCaseId(workspace, caseId), respondIdList, jumpToCase)
    else:
        if isBlank(button_case_id_list) == False:
            buttonCaseIdList = [item.strip() for item in button_case_id_list.split(",")]
            actionButtonIdList = [item.strip() for item in action_button_id_list.split(",")]
            dialogFlowForest.createButtonCaseIdListNode (WorkspaceCaseId(workspace, caseId), respondIdList, buttonCaseIdList, actionButtonIdList)
        else:
            # if switch workspace:
            # TODO: switch workspace
            # else:
            procedureAdvisoryIdList = []
            if isBlank(procedure_advisory_id_list) == False:
                procedureAdvisoryIdList = [item.strip() for item in procedure_advisory_id_list.split(",")]
            dialogFlowForest.createLeafNode (WorkspaceCaseId(workspace, caseId), respondIdList, procedureAdvisoryIdList)

dialogFlowForest.connectParentChildren()

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