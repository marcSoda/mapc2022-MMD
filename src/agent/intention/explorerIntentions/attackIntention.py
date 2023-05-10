from data.coreData import Coordinate, MapValueEnum, MapValueEnum

from data.map import DynamicMap

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention
from agent.intention.mainAgentIntention import MainAgentIntention
from agent.intention.commonIntentions import clearTargetIntention, clearZoneIntention, SkipIntention, TravelIntention

from agent.pathfinder import PathFinder, PathFinderData

from agent.action import AgentAction, ClearAction

class AttackIntention(MainAgentIntention):
    """
    Intention to search out an enemy agent to disable them.
    It is finished if it is able to disable one enemy agent.
    This is different from clearTargetIntention and clearZoneIntention
    as the agent will go out of its way looking for agents to deactivate
    """

    travelIntention: TravelIntention | None
    targetCoordinate: Coordinate
    finished : bool
    relocation : bool

    def __init__(self) -> None:
        self.travelIntention  = None
        self.targetCoordinate = Coordinate(0,0)
        self.finished = False
        self.relocation = False

    def getPriority(self) -> float:
        return 6.0
    
    def initialize_pathfinder(self, observation: Observation) -> PathFinderData:
        pathFinderParams = PathFinderData(
            map=observation.map,
            start=observation.agentCurrentCoordinate,
            agentSpeed=observation.agentMapcRole.getSpeed(len(observation.agentData.attachedEntities)),
            clearEnergyCost=observation.simDataServer.getClearEnergyCost(),
            agentEnergy=observation.agentData.energy,
            agentMaxEnergy=observation.simDataServer.getAgentMaxEnergy(),
            clearChance=observation.agentMapcRole.clearChance,
            clearConstantCost=observation.simDataServer.getClearConstantCost(),
            maxIteration=observation.simDataServer.pathFindingMaxIteration,
            agentVision=observation.agentMapcRole.vision,
            attachedCoordinates=[e.relCoord for e in observation.agentData.attachedEntities]
        )
        return pathFinderParams

    async def planNextAction(self, observation: Observation) -> AgentAction:
        if observation.agentMapcRole.clearMaxDistance > 1:
            enemyCoord = self.getClearableEnemy(observation)
            if(enemyCoord is not None):
                self.finished = True
                return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate,enemyCoord))
            else:
                if self.travelIntention is None or self.travelIntention.checkFinished(observation):
                    nearestEnemy = self.findNearestEnemy(observation)
                    if nearestEnemy is not None:
                        self.travelIntention = TravelIntention(nearestEnemy)
                return await self.travelIntention.planNextAction(observation)
    
    def findNearestEnemy(self, observation: Observation) -> Coordinate:
        """
        Returns the nearest enemy `Agent's` `Coordinate` using the pathfinder.
        """
        enemyCoords = []
        for i in range(observation.map.getMaxWidth()):
            for j in range(observation.map.getMaxHeight()):
                if observation.map.getMapValueEnum(Coordinate(i,j)) == MapValueEnum.AGENT and observation.map.getMapValue(Coordinate(i,j)).details != observation.simDataServer.teamName and Coordinate(i,j) not in observation.map.goalZones:
                    enemyCoords.append(Coordinate(i,j))

        if not enemyCoords:
            return None

        pathFinderParams = self.initialize_pathfinder(observation)
        pathFinder = PathFinder()

        minPathLength = float('inf')
        nearestEnemy = None
        for enemyCoord in enemyCoords:
            path = pathFinder.findNextAction(pathFinderParams, enemyCoord)
            if path is not None and len(path) < minPathLength:
                minPathLength = len(path)
                nearestEnemy = enemyCoord

        return nearestEnemy
    
    def calculate_path_length(path: list[Coordinate]) -> float:
        return sum(Coordinate.euclideanDistance(path[i], path[i+1]) for i in range(len(path)-1))

    def getClearableEnemy(self, observation: Observation) -> Coordinate:
        """
        Returns an enemy `Agent's` `Coordinate` within shooting range.
        """

        clearableCoords = list(
            filter(lambda coord: observation.map.getMapValueEnum(coord) == MapValueEnum.AGENT and  
                observation.map.getMapValue(coord).details != observation.simDataServer.teamName and
                coord not in observation.map.goalZones,
                observation.agentCurrentCoordinate.neighbors(True, observation.agentMapcRole.clearMaxDistance)))
        
        return min([coord for coord in clearableCoords],
            key = lambda coord: Coordinate.manhattanDistance(coord,observation.agentCurrentCoordinate),
            default = None)


    def checkFinished(self, observation: Observation) -> bool:
        return self.finished

    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.travelIntention is not None:
            self.travelIntention.updateCoordinatesByOffset(offsetCoordinate)

        # self.targetCoordinate.updateByOffsetCoordinate(offsetCoordinate)

    def normalizeCoordinates(self) -> None:
        if self.travelIntention is not None:
            self.travelIntention.normalizeCoordinates()

        self.targetCoordinate.normalize()

    def explain(self) -> str:
        return "Attacking " + str(self.targetCoordinate)