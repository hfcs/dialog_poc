import sys
import math
import pandas as pd
from io import TextIOBase
from anytree import Node, NodeMixin, RenderTree, AsciiStyle, find, PreOrderIter, SymlinkNode
from anytree.exporter import MermaidExporter

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

root_reserved_case_id = "MIN_START"

class WorkspaceCaseId:
    __workspace = ""
    __caseId = ""

    def __init__(self, workspace, caseId):
        self.__workspace = workspace
        self.__caseId = caseId

    def __eq__(self, other):
        return (self.__workspace == other.getWorkspace()) and (self.__caseId == other.getCaseId())
    
    def __str__(self):
        return self.__workspace + ":" + self.__caseId
    
    def getWorkspace(self):
        return self.__workspace
    
    def getCaseId(self):
        return self.__caseId
    
class BaseNode (NodeMixin):
    __workspaceCaseId = None
    __respondIdList = None
    
    def __init__(self, workspaceCaseId: WorkspaceCaseId, respondIdList: list[str]):
        super(BaseNode, self).__init__()
        self.name = str(workspaceCaseId)
        self.__workspaceCaseId = workspaceCaseId
        self.__respondIdList = respondIdList
    
    def getWorkspaceCaseId(self):
        return self.__workspaceCaseId
    
    def getRespondIdList(self):
        return self.__respondIdList

class JumpToNode (BaseNode):
    __jumpToCaseId = None

    def __init__(self, workspaceCaseId: WorkspaceCaseId, respondIdList: list[str], jumpToCaseId: str):
        super(JumpToNode, self).__init__(workspaceCaseId, respondIdList)
        self.__jumpToCaseId = jumpToCaseId

    def getJumptToCaseId(self):
        return self.__jumpToCaseId

class ButtonCaseIdListNode(BaseNode):
    __buttonCaseIdList = None
    __actionButtonIdList = None

    def __init__(self, workspaceCaseId: WorkspaceCaseId, respondIdList: list[str], buttonCaseIdList: list[str], actionButtonIdList: list[str]):
        super(ButtonCaseIdListNode, self).__init__(workspaceCaseId, respondIdList)
        self.__buttonCaseIdList = buttonCaseIdList
        self.__actionButtonIdList = actionButtonIdList

    def getButtonCaseIdList(self):
        return self.__buttonCaseIdList
    
    def getActionButtonIdList(self):
        return self.__actionButtonIdList


class LeafNode (BaseNode):
    __procedureAdvisoryIdList = None

    def __init__(self, workspaceCaseId: WorkspaceCaseId, respondIdList: list[str], procedureAdvisoryIdList: list[str]):
        super(LeafNode, self).__init__(workspaceCaseId, respondIdList)
        self.__procedureAdvisoryIdList = procedureAdvisoryIdList

    def getProcedureAdvisoryIdList(self):
        return self.__procedureAdvisoryIdList 

# A class for global object that handle everything about the dialog flow tree operation
class DialogFlowForest:
    # Notice Python dictionary are pass by reference so we are actually playing around real node elements created

    __nodeDictByWorkspace = {}
    __workspaceTreeRootDict = {}

    def __init__(self):
        # dictionary of workspace (key) and all nodes in their trees (value as set)
        self.__nodeDictByWorkspace = {}
        ## dictionary of workspace (key) and their tree root (value)
        self.__workspaceTreeRootDict = {}

    def __insertNode(self, workspace:str, node:Node):
        if workspace in self.__nodeDictByWorkspace.keys():
            workspaceNodeSet = self.__nodeDictByWorkspace.get(workspace)
            workspaceNodeSet.add(node)
        else:
            self.__nodeDictByWorkspace.update({workspace:{node}})

    # Use the fact that WorkspaceCaseId is matched by workspace:case_id as equality
    def __findNodeInWorkspace(self, workspaceCaseId: WorkspaceCaseId):
        nodeSetinWorkspace = self.__nodeDictByWorkspace.get(workspaceCaseId.getWorkspace())
        if nodeSetinWorkspace == None:
            raise Exception("workspace " + workspaceCaseId.getWorkspace() + " does not exist")
        for node in nodeSetinWorkspace:
            if node.name == str(workspaceCaseId):
                return node
        raise Exception(str(workspaceCaseId) + " does not exist")
    
    def createJumpToNode(self, workspaceCaseId: WorkspaceCaseId, respondIdList: list, jumpToCaseId: str):
        #print("createJumpToNode " + str(workspaceCaseId))
        node = JumpToNode(workspaceCaseId, respondIdList, jumpToCaseId)
        self.__insertNode(workspaceCaseId.getWorkspace(), node)

    def createButtonCaseIdListNode (self, workspaceCaseId: WorkspaceCaseId, respondIdList: list, buttonCaseIdList : list, actionButtonIdList : list):
        #print("createButtonCaseIdListNode " + str(workspaceCaseId))
        node = ButtonCaseIdListNode(workspaceCaseId, respondIdList, buttonCaseIdList, actionButtonIdList)
        if _isReservedCaseId(workspaceCaseId.getCaseId()):
            self.__workspaceTreeRootDict.update({workspaceCaseId.getWorkspace(): node})
        self.__insertNode(workspaceCaseId.getWorkspace(), node)

    def createLeafNode (self, workspaceCaseId: WorkspaceCaseId, respondIdList: list, procedureAdvisoryIdList: list):
        #print("createLeafNode " + str(workspaceCaseId))
        node = LeafNode(workspaceCaseId, respondIdList, procedureAdvisoryIdList)
        self.__insertNode(workspaceCaseId.getWorkspace(), node)

    def createSwitchWorkspaceNode (self, workspaceCaseId: WorkspaceCaseId, respondIdList: str):
        #print("createLeafNode " + str(workspaceCaseId))
        raise Exception("not yet implemented")

    def connectParentChildren (self):
        #print("***** tree root dictionary *****")
        #print(self.__workspaceTreeRootDict)
        #print("***** forest dictionary *****")
        #print(self.__nodeDictByWorkspace)
        #print("***** all nodes created *****")
        for workspaceNodeSet in self.__nodeDictByWorkspace.values():
            #print(workspaceNodeSet)
            for node in workspaceNodeSet:

                if isinstance(node, ButtonCaseIdListNode):
                    buttonList = list()
                    for buttonCaseId in node.getButtonCaseIdList():
                        childNode = self.__findNodeInWorkspace(WorkspaceCaseId(node.getWorkspaceCaseId().getWorkspace(), buttonCaseId))
                        # Anytree workaround for multiple parents 
                        # Requires cloning a symlink child to articulate multiple parent relationship
                        if childNode.parent != None:
                            childNode = SymlinkNode(childNode)

                            #TODO: we cannot properly track symlinked nodes in main symbol table without messing up our tree, likely from hitting the symlinked node
                            #TODO: may need to review Anytree lifecycle if we wanted to track symlinked node
                            #self.__insertNode(node.WORKSPACECASEID.getWorkspace(), childNode)
                        buttonList.append(childNode)
                    node.children = buttonList
                    for childNode in buttonList:
                        childNode.parent = node
                else:
                    # jump to is really a backward jump into a loop, that doesn't work well in a tree structure and cannot be handled in Anytree
                    # We are going to handle JUMP_TO as leaf nodes that contains a jump target
                    if isinstance(node, JumpToNode) == False and isinstance(node, LeafNode) == False:
                        raise Exception ("switch context not yet implemented")
                        
    def getTreeRootsList(self):
        return list(self.__workspaceTreeRootDict.values())

    def printForest (self, fileStream):                
        # tree dump
        for root in self.__workspaceTreeRootDict.values():
            print(RenderTree(root, style=AsciiStyle()).by_attr(), file=fileStream)

    def printMermaid(self, fileStream):
        for root in self.__workspaceTreeRootDict.values():
            for line in MermaidExporter(root):
                print(line, file=fileStream)

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
# Utility functions

def _isBlank(label):
    return pd.isna(label)


def _isReservedCaseId(caseId: str):
    return caseId == root_reserved_case_id


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
    
    if _isBlank(caseId):
        raise Exception ("Case ID cannot be blank")
    
    if _isBlank(workspace):
        raise Exception ("Workspace cannot be blank")      

    if _isBlank(respond_id_list):
        raise Exception ("Respond ID List cannot be blank")      
    else:
        respondIdList = [item.strip() for item in respond_id_list.split(",")]

    if _isBlank(button_case_id_list) == False:
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
    if _isBlank(jumpToCase) == False:
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
    #if _isBlank(caseId):
    #    raise Exception ("Case ID cannot be blank")
    #
    #if _isBlank(workspace):
    #    raise Exception ("Workspace cannot be blank")      
    #
    #if _isBlank(respond_id_list):
    #    raise Exception ("Respond ID List cannot be blank")  

    respondIdList = [item.strip() for item in respond_id_list.split(",")]
        
    if _isBlank(jumpToCase) == False:
        dialogFlowForest.createJumpToNode (WorkspaceCaseId(workspace, caseId), respondIdList, jumpToCase)
    else:
        if _isBlank(button_case_id_list) == False:
            buttonCaseIdList = [item.strip() for item in button_case_id_list.split(",")]
            actionButtonIdList = [item.strip() for item in action_button_id_list.split(",")]
            dialogFlowForest.createButtonCaseIdListNode (WorkspaceCaseId(workspace, caseId), respondIdList, buttonCaseIdList, actionButtonIdList)
        else:
            # if switch workspace:
            # TODO: switch workspace
            # else:
            procedureAdvisoryIdList = []
            if _isBlank(procedure_advisory_id_list) == False:
                procedureAdvisoryIdList = [item.strip() for item in procedure_advisory_id_list.split(",")]
            dialogFlowForest.createLeafNode (WorkspaceCaseId(workspace, caseId), respondIdList, procedureAdvisoryIdList)

dialogFlowForest.connectParentChildren()

# TODO: tree verifier

##############################################
# tree visualization dump
dialogFlowForest.printForest(sys.stdout)
dialogFlowForest.printMermaid(sys.stdout)

###############################################################################
# Code emmition pass, iterate tree and generate rules
#
# Well known keys in dialog context
#
# domain (e.g. SLF)
# jump_to
# va_command (callWorkpace)
#
# well known dialog functions
#
# uiCommand
# responds
#
# Drools structure
#
# import xxx.group.pa.dialog.flow.*
# import org.apache.commons.collections.CollectionUtils;
#
# global xxx.group.pa.dialog.service.DialogService ds
#
#rule <CASE_ID>
#// Attributes
#when
#   $dialog: Dialog(current case_id == <CASE_ID>)
#then
#   $dialog.getContext().put("key", "value");
#   ...
#   $dialog.responds(XXX)  // optional
#   $dialog.uiCommand(...) // optional
#    // Call stub functions according to type 1/2a, 2b, and 3 with data from node
#end
#
#   Try  to mimic GeneralFaqService.java.processCase()
# dialog.setNextCase(new DialogCase(caseId))
# process jump_to_case
# navBtns = RuleUtil.setButtons(commonService.getButtonCases(dialog.getnext().getCase(), channel, dialog.getLanguage());
# dialog.getOutput.setButtons(navBtns)
# dialog.getOutput.setTexts(respondId)
#
# actBtinIds = hitRule.getActionIdList()
# dialog.getOutput.setActionButtonIds(actBtnIds)
# carousels = hitRule.getProcedureAdvisoryIdList()
# dialog.getOutput.setProcedureAdvisoryIds(carousels)
# dialog.getContext().put("business_scope", hitRule.getBusinessScope())
# dialog.getContext().put("enquiry_catergory". hitRule.getEnquiryCategory())
# dialog.getContext().put("product_type", hitRule.getProductType())
#
# jump_to rules in FAQ seems to have executing MVEL as the only purpose
#
################################
# Execution engine
#
# Input: context(current node), intents, selection input
# Output: response code, new conetxt(next node), buttons
#
#         ┌──────────────┐                 ┌────────────────┐               ┌────────────────┐
#         │              │               ┌────┐             │               │                │
#         │ Bot context  │──────────────>│API │ Rule Engine │──────────────>│ Action for bot │──────────────>
#         │ (node state) │               └────┘             │               │                │ Return to bot  
#         └──────────────┘                 └────────────────┘               └────────────────┘
# 
# -Each iteratiion to the dialog flow engine will start from the chat context (current node), the engine will evaluate matching rule (to currenrt node) for executing action of that single node
# -At the end of iteration the dialog flow engine returns 1) respond dode, 2) new context (next node for iteration), 3) optionally required action for this node (e.g. custom logic, button to render, jump to case)
# -If a call is triggered by intent, or a selection input, the chat context (current node) is first set as the selected node, before executing the node
# -A node execution 
#   -Jump to node and button list node
#       -Action button list, advisory ID list are provisioned as output
#       -Return to bot waiting for next input
#   -Leaf node
#       -Required content, custom logic from SET_CONTEXT_EXPRESSION is provisioned as output
#       -Return to bot waiting for next input
# -Tranlate above in Drools DRL
#   
#   The rule execution can be implemented as Drools rules where each row is a business rule, each node have it's own dedicated rules filtered by CASE_ID

class NodeToDrlRulePrinterSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NodeToDrlRulePrinterSingleton, cls).__new__(cls)
        return cls._instance

    def printHeader(self, fileStream: TextIOBase):
        print("##############", file=fileStream)
        print("import xxx.group.pa.dialog.flow.*;", file=fileStream)
        print("import org.apache.commons.collections.CollectionUtils;", file=fileStream)
        print("", file=fileStream)
        print("global xxx.group.pa.dialog.service.DialogService ds", file=fileStream)
        print("", file=fileStream)
        print("##############", file=fileStream)

    def printRuleCommentForNode (self, node: Node, fileStream: TextIOBase):
        print("# " + str(node), file=fileStream)

    def __generateUiCommandFromButtonList(self, buttonCaseIdList: list):
        return str(buttonCaseIdList)
    
    def __generateProcedureAdvisoryList(self, buttonCaseIdList: list):
        return str(buttonCaseIdList)

    def printRuleForNode(self, node: BaseNode, fileStream: TextIOBase):
        print("rule \"" + node.name + "\"", file=fileStream)
        print("when", file=fileStream)
        print("    $dialog: Dialog(current_case_id == " + node.getWorkspaceCaseId().getCaseId() + ")", file=fileStream)
        print("then", file=fileStream)
        
        if isinstance(node, ButtonCaseIdListNode):
            print("    $dialog.getOutput().setButtons(RuleUtil.setButtons(" + self.__generateUiCommandFromButtonList(node.getButtonCaseIdList()) + "))", file=fileStream)
        else:
            if isinstance(node, JumpToNode):
                print("    $dialog.getContext().put(\"jump_to\", \"" + node.getJumptToCaseId() + "\");", file=fileStream)
            else:
                if isinstance(node, LeafNode):
                    if len(node.getProcedureAdvisoryIdList()) > 0:
                        print("    dialog.getOutput().setProcedureAdvisoryIds(\"" + self.__generateProcedureAdvisoryList(node.getProcedureAdvisoryIdList()) +"\")", file=fileStream)
                    else:
                        print("    #TODO: leaf node", file=fileStream)
                else:
                    if isinstance(node, SymlinkNode) == False: # rule is already emitted by true node, symlink does not need a rule
                        raise Exception("type " + str(type(node)) + " is not yet implemented")
                
        print("    $dialog.responds(" + node.getRespondIdList()[0] +")")
        print("end", file=fileStream)

NodeToDrlRulePrinterSingleton().printHeader(sys.stdout)
#print(dialogFlowForest.getTreeRootsList())
for root in dialogFlowForest.getTreeRootsList():
    for node in PreOrderIter(root):
        NodeToDrlRulePrinterSingleton().printRuleCommentForNode(node, sys.stdout)
        NodeToDrlRulePrinterSingleton().printRuleForNode(node, sys.stdout)
        print("##############", file=sys.stdout)