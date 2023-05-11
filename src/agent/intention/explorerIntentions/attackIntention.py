from data.coreData import Coordinate, MapValueEnum, MapValueEnum, MapcRole

from data.intention import Observation
from agent.intention.explorerIntentions import ExploreIntention
from agent.intention.agentIntention import AgentIntention
from agent.intention.mainAgentIntention import MainAgentIntention
from agent.intention.commonIntentions import TravelIntention, DetachBlocksIntention, AdoptRoleIntention

from agent.action import AgentAction, ClearAction, SkipAction

import random

class AttackIntention(AgentIntention):
    """
    Intention to search out an enemy agent to disable them.
    It is finished if it is able to disable one enemy agent.
    This is different from clearTargetIntention and clearZoneIntention
    as the agent will go out of its way looking for agents to deactivate
    """
    
    currentTravelIntention: TravelIntention | None
    detachBlocksIntention: DetachBlocksIntention | None
    adoptRoleIntention: AdoptRoleIntention | None
    relocation: bool  
    

    def __init__(self) -> None:
        self.currentTravelIntention  = None
        self.detachBlocksIntention = None
        self.adoptRoleIntention = None
        self.finished = False
        self.relocation = False
        self.targetCoordinate = Coordinate(0,0)

    def getPriority(self) -> float:
        return 6.0

    async def planNextAction(self, observation: Observation) -> AgentAction:
        enemyCoord = self.getClearableEnemy(observation)
        if(enemyCoord is not None):
            self.finished = True
            return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate,enemyCoord))
        else:
            # return await ExploreIntention.planNextAction(self, observation)
            # if the given area is unknown then travel there to get info about that area
            if observation.map.getMapValueEnum(self.targetCoordinate) == MapValueEnum.UNKNOWN:
                if self.travelIntention is None:
                    self.travelIntention = TravelIntention(self.targetCoordinate)
            
                return await self.travelIntention.planNextAction(observation)
                #  If carrying a block and it regulates a norm then drop it
            maxBlockCount = observation.simDataServer.getMaxBlockRegulation()
            if len(observation.agentData.attachedEntities) > 1 or (maxBlockCount is not None and maxBlockCount < len(observation.agentData.attachedEntities)):
                if self.detachBlocksIntention is None:
                    self.detachBlocksIntention = DetachBlocksIntention()
                
                return await self.detachBlocksIntention.planNextAction(observation)

            # If there are reserved roles for the Agent and it is not already adopted
            # then adopt it. It is important because of the Norms
            agentRoles = observation.simDataServer.getReservedRolesForAgent(observation.agentData.id)
            if any(agentRoles) and observation.agentMapcRole != agentRoles[0]:
                return await self.planRoleAdoptPlan(observation, agentRoles[0])

            # If just initialized or reached target or target became known (and not relocating) then search for a new target
            if (self.currentTravelIntention is None or self.currentTravelIntention.checkFinished(observation)
                or (not self.relocation and observation.map.getMapValueEnum(self.currentTravelIntention.coordinate) != MapValueEnum.UNKNOWN)):

                # Try to search for a close unknown Coordinate
                self.relocation = False
                newDestination = observation.map.findClosestUnknownFromStartingLocation(
                        observation.agentStartingCoordinate, observation.agentCurrentCoordinate, observation.agentMapcRole.vision)

                # If not found a close unknown Coordinate then move to a 
                # random close Coordinate and try later there
                if newDestination is None:
                    newDestination = observation.map.findRandomFarCoordinate(
                        observation.agentCurrentCoordinate, observation.agentMapcRole.vision)
                    self.relocation = True
                
                self.currentTravelIntention = TravelIntention(newDestination)

            return await self.currentTravelIntention.planNextAction(observation)

            # return SkipAction()
            
    def getClearableEnemy(self, observation: Observation) -> Coordinate:
        """
        Returns an enemy `Agent's` `Coordinate` within shooting range.
        """

        clearableCoords = list(
            filter(lambda coord: observation.map.getMapValueEnum(coord) == MapValueEnum.AGENT and  
                observation.map.getMapValue(coord).details != observation.simDataServer.teamName and
                coord not in observation.map.goalZones,
                observation.agentCurrentCoordinate.neighbors(True, observation.agentMapcRole.clearMaxDistance)))
        
        if len(clearableCoords) > 1:
            return min([coord for coord in clearableCoords],
                key = lambda coord: Coordinate.manhattanDistance(coord,observation.agentCurrentCoordinate),
                default = None)
        elif len(clearableCoords) == 1:
            if random.randint(1,10) <= 7:
                return min([coord for coord in clearableCoords],
                key = lambda coord: Coordinate.manhattanDistance(coord,observation.agentCurrentCoordinate),
                default = None)
        else:
            return None
    
    def checkFinished(self, observation: Observation) -> bool:
        return observation.simDataServer.getMapCount() == 1 and observation.map.isMapExplored()
        
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.currentTravelIntention is not None:
            self.currentTravelIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.detachBlocksIntention is not None:
            self.detachBlocksIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.adoptRoleIntention is not None:
            self.adoptRoleIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.currentTravelIntention is not None:
            self.currentTravelIntention.normalizeCoordinates()
        
        if self.detachBlocksIntention is not None:
            self.detachBlocksIntention.normalizeCoordinates()
        
        if self.adoptRoleIntention is not None:
            self.adoptRoleIntention.normalizeCoordinates()

    def explain(self) -> str:
        if self.currentTravelIntention is not None:
            return "exploring to " + str(self.currentTravelIntention.coordinate) + " " + self.currentTravelIntention.explain()
        else:
            return "exploring to unknown"
    
    async def planRoleAdoptPlan(self, observation: Observation, role: MapcRole) -> AgentAction:
        """
        Returns the required `AgentAction` to adopt
        the given `MapcRole`
        """

        if self.adoptRoleIntention is None:
            self.adoptRoleIntention = AdoptRoleIntention(role)
        
        return await self.adoptRoleIntention.planNextAction(observation)