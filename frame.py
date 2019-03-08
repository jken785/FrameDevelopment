import random
from node import *
import generateMatrices
from solver import *
from generateMatrices import *
from objectiveFunction import *
from plotter import *


class Frame:

    def __init__(self):
        self.tubes = []
        self.nodes = []
        self.torStiffness = None
        self.weight = None
        self.internalForces = None
        self.displacements = None
        self.reactions = None

    def getTorStiffness(self):
        return 0

    def solveAllLoadCases(self):
        score = 0
        scorePerWeight = 0
        avgDisp = 0
        for loadCase in LoadCases.listLoadCases:
            self.setLoadCase(loadCase)
            scorePerWeightToAdd, scoreToAdd, avgDisplacement = self.solve()
            scorePerWeight += scorePerWeightToAdd
            score += scoreToAdd
            avgDisp += avgDisplacement
        return scorePerWeight, score, avgDisp

    def solve(self):
        numTubes, numNodes, coord, con, fixtures, loads, dist, E, G, areas, I_y, I_z, J, St, be = generateMatrices(self, False)
        internalForces, displacements, reactions = Solver(numTubes, numNodes, coord, con, fixtures, loads, dist, E, G, areas, I_y, I_z, J, St, be)
        self.internalForces = internalForces
        self.displacements = displacements
        self.reactions = reactions
        scorePerWeight, score, maxDisp = ObjectiveFunction(self)
        return scorePerWeight, score, maxDisp

    def setLoadCase(self, loadCase):
        for node in self.nodes:
            node.setFixtures(0, 0, 0, 0, 0, 0)
            node.setForcesApplied(0, 0, 0, 0, 0, 0)
        for i in range(loadCase.nodeForceCases.__len__()):
            forceCase = loadCase.nodeForceCases.__getitem__(i)
            forces = forceCase.__getitem__(forceCase.__len__() - 1)
            x = forces.__getitem__(0)
            y = forces.__getitem__(1)
            z = forces.__getitem__(2)
            xMom = forces.__getitem__(3)
            yMom = forces.__getitem__(4)
            zMom = forces.__getitem__(5)
            for j in range(forceCase.__len__() - 1):
                index = forceCase.__getitem__(j)
                self.nodes.__getitem__(index).setForcesApplied(x, y, z, xMom, yMom, zMom)
        for index in loadCase.fixedNodes:
            self.nodes.__getitem__(index).setFixtures(1, 1, 1, 1, 1, 1)
        self.loadCase = loadCase

    def setFixtures(self, nodeIndex, x, y, z, xMom, yMom, zMom):
        fixNode = self.nodes.__getitem__(nodeIndex)
        fixNode.setFixtures(x, y, z, xMom, yMom, zMom)

    def getSymmetricTube(self, tube):
        if tube.nodeFrom.name.endswith("#m") and tube.nodeTo.name.endswith("#m"):
            symNodeFrom = tube.nodeFrom.name.split("#m")[0]
            symNodeTo = tube.nodeTo.name.split("#m")[0]
        else:
            symNodeFrom = tube.nodeFrom.name + "#m"
            symNodeTo = tube.nodeTo.name + "#m"
        for searchTube in self.tubes:
            if searchTube.nodeFrom.name == symNodeFrom and searchTube.nodeTo.name == symNodeTo:
                return searchTube
        return None

    def getSymmetricNode(self, node):
        if node.name.endswith("#m"):
            symName = node.name.split("#m")[0]
        else:
            symName = node.name + "#m"
        for searchNode in self.nodes:
            if searchNode.name == symName:
                return searchNode
        return None


    def changeTubeThickness(self, index, size):
        tube = self.tubes.__getitem__(index)
        tube.changeThickness(size)
        if tube.isSymmetric:
            symTube = self.getSymmetricTube(tube)
            symTube.changeThickness(size)
        self.getWeight()

    def randomizeThicknessOfRandomTube(self):
        randTube = random.choice(self.tubes)
        index = self.tubes.index(randTube)
        if randTube.isRound:
            sizeIndex = allRoundSizes.index(randTube.minSize)
            availableSizes = allRoundSizes[sizeIndex:len(allRoundSizes)]
            thickness = random.choice(availableSizes)
            self.changeTubeThickness(index, thickness)

    # will not allow changes to square tubes
    def randomizeThickness(self, index):
        tube = self.tubes.__getitem__(index)
        if tube.isRound:
            sizeIndex = allRoundSizes.index(tube.minSize)
            availableSizes = allRoundSizes[sizeIndex:len(allRoundSizes)]
            thickness = random.choice(availableSizes)
            self.changeTubeThickness(index, thickness)

    # optimization: should only randomize one tube in each symmetric pair -- also maybe implement lists of the symmetric
    # pair to prevent repeat look-ups
    def randomizeAllThicknesses(self):
        for i in range(len(self.tubes)):
            self.randomizeThickness(i)

    def addNode(self, name, x, y, z, isSymmetric, isRequired, maxXPosDev=None, maxXNegDev=None, maxYPosDev=None, maxYNegDev=None, maxZPosDev=None, maxZNegDev=None):
        node = Node(self, name, x, y, z, isSymmetric, isRequired, maxXPosDev, maxXNegDev, maxYPosDev, maxYNegDev, maxZPosDev, maxZNegDev)
        self.nodes.append(node)
        if isSymmetric:
            symName = name + "#m"
            symNode = Node(self, symName, x, -y, z, isSymmetric, isRequired, maxXPosDev, maxXNegDev, maxYNegDev, maxYPosDev, maxZPosDev, maxZNegDev)
            self.nodes.append(symNode)

    def removeNode(self, index):
        node = self.nodes.__getitem__(index)
        if node.isSymmetric:
            symNode = self.getSymmetricNode(node)
            for tube in symNode.tubes:
                self.tubes.remove(tube)
            self.nodes.remove(symNode)
        for tube in node.tubes:
            self.tubes.remove(tube)
        self.nodes.remove(node)
        for node in self.nodes:
            node.updateConnectingTubes()

    def addTube(self, size, minSize, nodeFrom, nodeTo, isSymmetric, isRequired):
        tube = Tube(self, size, minSize, nodeFrom, nodeTo, isSymmetric, isRequired)
        self.tubes.append(tube)
        tube.nodeFrom.tubes.append(tube)
        tube.nodeTo.tubes.append(tube)
        if isSymmetric:
            symNodeFrom = nodeFrom + "#m"
            symNodeTo = nodeTo + "#m"
            symTube = Tube(self, size, minSize, symNodeFrom, symNodeTo, isSymmetric, isRequired)
            self.tubes.append(symTube)
            symTube.nodeFrom.tubes.append(symTube)
            symTube.nodeTo.tubes.append(symTube)
        self.getWeight()

    def removeTube(self, index):
        tube = self.tubes.__getitem__(index)
        if tube.isSymmetric:
            symTube = self.getSymmetricTube(tube)
            self.tubes.remove(symTube)
        self.tubes.remove(tube)
        for node in self.nodes:
            node.updateConnectingTubes()
        self.getWeight()

    def getWeight(self):
        weight = 0
        for tube in self.tubes:
            weight += tube.weight
        self.weight = weight
        return weight

    def toString(self, printType=None, long=None):
        if printType == "all":
            self._printTubes(long)
            self._printNodes(long)
        if printType == "nodes":
            self._printNodes(long)
        if printType == "tubes":
            self._printTubes(long)
        print("\nTotal Weight:", '%.3f' % self.weight, "lbs")

    def _printTubes(self, long):
        print("\nTUBES:", self.tubes.__len__(), "total")
        print("----------\n")
        index = 0
        if long is 'long':
            for tube in self.tubes:
                print("\n#", index, "\n", tube.toString(), "going from", tube.nodeFrom.name, "to",
                      tube.nodeTo.name)
                print("  From:", tube.nodeFrom.coordsToString(), "to", tube.nodeTo.coordsToString())
                print("  Weight:", '%.3f' % tube.weight, "lbs\t\tLength:", '%.3f' % tube.length, "inches")
                if tube.isRequired and tube.isSymmetric:
                    print("  Required and Symmetric\n")
                elif tube.isRequired:
                    print("  Required\n")
                elif tube.isSymmetric:
                    print("  Symmetric\n")
                index += 1
        else:
            for tube in self.tubes:
                print("#", index, "-", tube.toString(), "going from", tube.nodeFrom.name, "to",
                      tube.nodeTo.name)
                index += 1

    def _printNodes(self, long):
        print("\nNODES:", self.nodes.__len__(), "total")
        print("----------\n")
        index = 0
        if long is 'long':
            for node in self.nodes:
                print("#", index, "Name:", node.name, "\tCoordinates:", node.coordsToString())
                print("\tHas forces:\t\t", node.forcesToString())
                print("\tWith fixtures:\t", node.fixturesToString())
                if node.isRequired and node.isSymmetric:
                    print("\tRequired and Symmetric")
                elif node.isRequired:
                    print("\tRequired")
                elif node.isSymmetric:
                    print("\tSymmetric")
                print("\tConnects tubes:")
                for tube in node.tubes:
                    print("\t  ", "Tube No.", self.tubes.index(tube), "-->", tube.toString())
                print("\n")
                index += 1
        else:
            for node in self.nodes:
                print("#", index, "Name:", node.name, "with coordinates:", node.coordsToString())
                index += 1

    def plot(self, displacedScaling):
        plotFrame(self, displacedScaling)



