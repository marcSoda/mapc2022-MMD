from data.coreData import Coordinate, MapValueEnum, MapValueEnum

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention
from agent.intention.mainAgentIntention import MainAgentIntention
from agent.intention.commonIntentions import clearTargetIntention, clearZoneIntention, SkipIntention, TravelIntention

from agent.action import AgentAction, ClearAction

class AttackIntention(AgentIntention):
    """
    Intention to search out an enemy agent to disable them.
    It is finished if it is able to disable one enemy agent.
    This is different from clearTargetIntention and clearZoneIntention
    as the agent will go out of its way looking for agents to deactivate
    """

    def __init__(self) -> None:
        self.travelIntention  = None
        self.finished = False
        self.relocation = False

    def getPriority(self) -> float:
        return 6.0

    async def planNextAction(self, observation: Observation) -> AgentAction:
        if observation.agentMapcRole.clearMaxDistance > 1:
            enemyCoord = self.getClearableEnemy(observation)
            if(enemyCoord is not None):
                self.finsihed = True
                return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate,enemyCoord))
            else:
                # if the given area is unknown then travel there to get info about that area
                if observation.map.getMapValueEnum(self.targetCoordinate) == MapValueEnum.UNKNOWN:
                    if self.travelIntention is None:
                        self.travelIntention = TravelIntention(self.targetCoordinate)
                
                    return await self.travelIntention.planNextAction(observation)

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

        self.targetCoordinate.updateByOffsetCoordinate(offsetCoordinate)

    def normalizeCoordinates(self) -> None:
        if self.travelIntention is not None:
            self.travelIntention.normalizeCoordinates()

        self.targetCoordinate.normalize()

    def explain(self) -> str:
        return "Attacking " + str(self.targetCoordinate)
        pass