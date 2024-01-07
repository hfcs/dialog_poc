import pandas as pd
from io import TextIOBase
from anytree import Node, NodeMixin, RenderTree, AsciiStyle, SymlinkNode
from anytree.exporter import MermaidExporter

##############################################
# Global

root_reserved_case_id = "MIN_START"

##############################################
# Utility functions

def isBlank(label):
    return pd.isna(label)


def _isReservedCaseId(caseId: str):
    return caseId == root_reserved_case_id

##############################################
# Classes

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

    def getJumpToCaseId(self):
        return self.__jumpToCaseId
    
    def clone(self):
        return JumpToNode(self.getWorkspaceCaseId(), self.getRespondIdList(), self.getJumpToCaseId())

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

    
    def clone(self):
        return ButtonCaseIdListNode(self.getWorkspaceCaseId(), self.getRespondIdList(), self.getButtonCaseIdList(), self.getActionButtonIdList())

class LeafNode (BaseNode):
    __procedureAdvisoryIdList = None

    def __init__(self, workspaceCaseId: WorkspaceCaseId, respondIdList: list[str], procedureAdvisoryIdList: list[str]):
        super(LeafNode, self).__init__(workspaceCaseId, respondIdList)
        self.__procedureAdvisoryIdList = procedureAdvisoryIdList

    def getProcedureAdvisoryIdList(self):
        return self.__procedureAdvisoryIdList 
    
    def clone(self):
        return JumpToNode(self.getWorkspaceCaseId(), self.getRespondIdList(), self.getProcedureAdvisoryIdList())

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

class ClonedDialogTree:

    __targetRoot = None
    __nodeSet = set()

    def __init__(self, sourceRoot: Node):
        self.__targetRoot = self.___cloneTreeRecursive(sourceRoot)

    def __insertNode(self, node: Node):
        self.__nodeSet.add(node)

    def ___cloneTreeRecursive(self, sourceNode: Node):
        # Recursive cloner that go root first, this is needed as we support multiple parent and used SymlinkNode as workaround
        # Hence a two pass implementing node creation pass and parent/children pass cannot be done

        # clone this node
        clonedNode = sourceNode.clone()

        # for each child clone recurive and set up parent/child
        if len(sourceNode.children) > 0:
            childrenList = list()

            for sourceChild in sourceNode.children:
                clonedChild = self.___cloneTreeRecursive(sourceChild)
                childrenList.append(clonedChild)
                clonedChild.parent = clonedNode
        
            clonedNode.children = childrenList

        return clonedNode

    def getRoot(self):
        return self.__targetRoot

###############################################################################
# Code emmission pass, iterate tree and generate rules
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
                print("    $dialog.getContext().put(\"jump_to\", \"" + node.getJumpToCaseId() + "\");", file=fileStream)
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
