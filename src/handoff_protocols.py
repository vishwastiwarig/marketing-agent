"""
Purple Merit Technologies - Agent Handoff Protocols & System Integration
Seamless context preservation and multi-agent orchestration
"""

import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Callable, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
from contextlib import asynccontextmanager

# Import previous components
from .agent_framework import (
    BaseAgent, AgentType, ActionType, LeadTriageAgent, 
    EngagementAgent, CampaignOptimizationAgent
)

from .mcp_jsonrpc import MCPServer, MCPClient, MCPMethod, MCPWebSocketServer, MCPHTTPServer
from .memory_systems import (
    UnifiedMemoryManager, ConversationContext, LeadProfile, Episode
)

# ================ HANDOFF MODELS ================

class HandoffTrigger(Enum):
    TASK_COMPLETION = "task_completion"
    ESCALATION_REQUIRED = "escalation_required"
    SPECIALIZATION_NEEDED = "specialization_needed"
    PERFORMANCE_THRESHOLD = "performance_threshold"
    TIME_BASED = "time_based"
    MANUAL_OVERRIDE = "manual_override"

class HandoffPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class HandoffContext:
    handoff_id: str
    source_agent_id: str
    source_agent_type: AgentType
    target_agent_type: AgentType
    target_agent_id: Optional[str] = None
    trigger: HandoffTrigger = HandoffTrigger.TASK_COMPLETION
    priority: HandoffPriority = HandoffPriority.MEDIUM
    
    # Context preservation
    conversation_state: Dict[str, Any] = field(default_factory=dict)
    lead_context: Dict[str, Any] = field(default_factory=dict)
    campaign_context: Dict[str, Any] = field(default_factory=dict)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)
    memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # Handoff metadata
    reason: str = ""
    confidence_score: float = 1.0
    expected_completion_time: Optional[datetime] = None
    escalation_reason: Optional[str] = None
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Quality assurance
    context_completeness_score: float = 0.0
    handoff_success: Optional[bool] = None
    performance_impact: Optional[Dict[str, float]] = None

@dataclass
class HandoffResult:
    handoff_id: str
    success: bool
    target_agent_id: str
    processing_time_ms: int
    context_preserved: bool
    quality_score: float
    next_actions: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

# ================ CONTEXT PRESERVATION ENGINE ================

class ContextPreservationEngine:
    def __init__(self, memory_manager: UnifiedMemoryManager):
        self.memory_manager = memory_manager
        self.context_templates = self._load_context_templates()
        
    def _load_context_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load context preservation templates for different handoff scenarios"""
        return {
            "triage_to_engagement": {
                "required_fields": [
                    "lead_data", "triage_category", "lead_score", 
                    "classification_reasoning", "urgency_level"
                ],
                "optional_fields": [
                    "similar_leads", "historical_performance", "segment_insights"
                ],
                "memory_requirements": ["short_term", "long_term", "semantic"]
            },
            "engagement_to_optimization": {
                "required_fields": [
                    "campaign_data", "engagement_results", "response_metrics",
                    "current_sequence_step", "lead_engagement_level"
                ],
                "optional_fields": [
                    "a_b_test_results", "channel_performance", "cost_metrics"
                ],
                "memory_requirements": ["short_term", "episodic", "semantic"]
            },
            "any_to_manager": {
                "required_fields": [
                    "escalation_reason", "current_state", "attempted_actions",
                    "performance_metrics", "risk_assessment"
                ],
                "optional_fields": [
                    "recommended_actions", "resource_requirements", "timeline"
                ],
                "memory_requirements": ["all"]
            }
        }
    
    async def create_handoff_context(
        self, 
        source_agent: BaseAgent,
        target_agent_type: AgentType,
        current_state: Dict[str, Any],
        trigger: HandoffTrigger,
        reason: str = ""
    ) -> HandoffContext:
        """Create comprehensive handoff context"""
        
        handoff_id = str(uuid.uuid4())
        
        # Determine handoff scenario
        scenario = f"{source_agent.agent_type.value.lower()}_to_{target_agent_type.value.lower()}"
        template = self.context_templates.get(scenario, self.context_templates["any_to_manager"])
        
        # Extract conversation state
        conversation_state = await self._extract_conversation_state(current_state)
        
        # Extract lead context
        lead_context = await self._extract_lead_context(current_state)
        
        # Extract campaign context  
        campaign_context = await self._extract_campaign_context(current_state)
        
        # Get interaction history
        interaction_history = await self._get_interaction_history(current_state)
        
        # Create memory snapshot
        memory_snapshot = await self._create_memory_snapshot(
            current_state, template["memory_requirements"]
        )
        
        # Calculate context completeness
        completeness_score = self._calculate_context_completeness(
            {
                "conversation_state": conversation_state,
                "lead_context": lead_context,
                "campaign_context": campaign_context,
                "memory_snapshot": memory_snapshot
            },
            template
        )
        
        # Create handoff context
        context = HandoffContext(
            handoff_id=handoff_id,
            source_agent_id=source_agent.agent_id,
            source_agent_type=source_agent.agent_type,
            target_agent_type=target_agent_type,
            trigger=trigger,
            reason=reason,
            conversation_state=conversation_state,
            lead_context=lead_context,
            campaign_context=campaign_context,
            interaction_history=interaction_history,
            memory_snapshot=memory_snapshot,
            context_completeness_score=completeness_score
        )
        
        return context
    
    async def _extract_conversation_state(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract current conversation state"""
        conversation_id = current_state.get("conversation_id")
        if not conversation_id:
            return {}
        
        # Get conversation context from memory
        context = await self.memory_manager.get_conversation_context(conversation_id)
        if context:
            return {
                "conversation_id": context.conversation_id,
                "last_utterance_summary": context.last_utterance_summary,
                "active_intent": context.active_intent,
                "extracted_slots": context.extracted_slots,
                "emotional_state": context.emotional_state,
                "engagement_level": context.engagement_level,
                "turn_count": context.turn_count
            }
        
        return {}
    
    async def _extract_lead_context(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract lead-specific context"""
        lead_id = current_state.get("lead_id")
        if not lead_id:
            return {}
        
        # Get lead profile
        profile = await self.memory_manager.get_lead_profile(lead_id)
        if profile:
            return {
                "lead_id": profile.lead_id,
                "industry": profile.industry,
                "company_size": profile.company_size,
                "persona": profile.persona,
                "preferences": profile.preferences,
                "rfm_score": profile.rfm_score,
                "behavioral_patterns": profile.behavioral_patterns,
                "interaction_summary": profile.interaction_summary
            }
        
        return current_state.get("lead_data", {})
    
    async def _extract_campaign_context(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract campaign-specific context"""
        campaign_id = current_state.get("campaign_id")
        if campaign_id:
            return {
                "campaign_id": campaign_id,
                "current_metrics": current_state.get("metrics", {}),
                "optimization_history": current_state.get("optimization_history", []),
                "performance_trends": current_state.get("performance_trends", {})
            }
        
        return {}
    
    async def _get_interaction_history(self, current_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recent interaction history"""
        lead_id = current_state.get("lead_id")
        if not lead_id:
            return []
        
        # Mock: In production, query interaction database
        return current_state.get("interaction_history", [])[:10]  # Last 10 interactions
    
    async def _create_memory_snapshot(
        self, 
        current_state: Dict[str, Any], 
        memory_requirements: List[str]
    ) -> Dict[str, Any]:
        """Create snapshot of relevant memory states"""
        snapshot = {}
        
        if "short_term" in memory_requirements or "all" in memory_requirements:
            conversation_id = current_state.get("conversation_id")
            if conversation_id:
                context = await self.memory_manager.get_conversation_context(conversation_id)
                snapshot["short_term"] = asdict(context) if context else {}
        
        if "long_term" in memory_requirements or "all" in memory_requirements:
            lead_id = current_state.get("lead_id")
            if lead_id:
                profile = await self.memory_manager.get_lead_profile(lead_id)
                snapshot["long_term"] = asdict(profile) if profile else {}
        
        if "episodic" in memory_requirements or "all" in memory_requirements:
            # Get relevant episodes for current scenario
            scenario = current_state.get("scenario", "unknown")
            episodes = await self.memory_manager.episodic.search({
                "scenario": scenario,
                "min_success_score": 0.7
            })
            snapshot["episodic"] = [asdict(ep) for ep in episodes[:5]]
        
        if "semantic" in memory_requirements or "all" in memory_requirements:
            # Get semantic knowledge for lead's industry/context
            industry = current_state.get("industry")
            if industry:
                semantic_data = await self.memory_manager.query_semantic_knowledge({
                    "concept": industry
                })
                snapshot["semantic"] = semantic_data
        
        return snapshot
    
    def _calculate_context_completeness(
        self, 
        context_data: Dict[str, Any], 
        template: Dict[str, Any]
    ) -> float:
        """Calculate how complete the context is"""
        required_fields = template["required_fields"]
        optional_fields = template["optional_fields"]
        
        # Check required fields across all context components
        required_score = 0
        total_required = len(required_fields)
        
        all_data = {}
        for component in context_data.values():
            if isinstance(component, dict):
                all_data.update(component)
        
        for field in required_fields:
            if field in all_data and all_data[field] is not None:
                required_score += 1
        
        # Check optional fields
        optional_score = 0
        total_optional = len(optional_fields)
        
        for field in optional_fields:
            if field in all_data and all_data[field] is not None:
                optional_score += 1
        
        # Calculate weighted score (80% required, 20% optional)
        if total_required > 0:
            required_ratio = required_score / total_required
        else:
            required_ratio = 1.0
        
        if total_optional > 0:
            optional_ratio = optional_score / total_optional
        else:
            optional_ratio = 1.0
        
        return (required_ratio * 0.8) + (optional_ratio * 0.2)

# ================ HANDOFF ORCHESTRATOR ================

class HandoffOrchestrator:
    def __init__(
        self, 
        agents: Dict[AgentType, BaseAgent],
        memory_manager: UnifiedMemoryManager,
        mcp_client: MCPClient
    ):
        self.agents = agents
        self.memory_manager = memory_manager
        self.mcp_client = mcp_client
        self.context_engine = ContextPreservationEngine(memory_manager)
        
        # Handoff tracking
        self.active_handoffs: Dict[str, HandoffContext] = {}
        self.handoff_history: List[HandoffContext] = []
        self.performance_metrics: Dict[str, Any] = defaultdict(list)
        
        # Agent availability and load balancing
        self.agent_availability: Dict[str, Dict[str, Any]] = {}
        self.agent_workload: Dict[str, int] = defaultdict(int)
        
        # Quality assurance
        self.handoff_quality_threshold = 0.7
        self.max_handoff_attempts = 3
        
        # Setup logging
        self.logger = logging.getLogger("HandoffOrchestrator")
    
    async def initiate_handoff(
        self,
        source_agent: BaseAgent,
        target_agent_type: AgentType,
        current_state: Dict[str, Any],
        trigger: HandoffTrigger = HandoffTrigger.TASK_COMPLETION,
        reason: str = "",
        priority: HandoffPriority = HandoffPriority.MEDIUM
    ) -> HandoffResult:
        """Initiate agent handoff process"""
        print(f"\n[NARRATOR] HandoffOrchestrator: Initiating handoff from {source_agent.agent_id} to {target_agent_type.value}.")
        start_time = datetime.now()
        try:
            # Create comprehensive handoff context
            handoff_context = await self.context_engine.create_handoff_context(
                source_agent, target_agent_type, current_state, trigger, reason
            )
            handoff_context.priority = priority
            print(f"[NARRATOR] HandoffOrchestrator: Created handoff context with completeness score {handoff_context.context_completeness_score:.2f}")
            # Validate context quality
            if handoff_context.context_completeness_score < self.handoff_quality_threshold:
                print(f"[NARRATOR] HandoffOrchestrator: Context quality too low ({handoff_context.context_completeness_score:.2f}), aborting handoff.")
                return HandoffResult(
                    handoff_id=handoff_context.handoff_id,
                    success=False,
                    target_agent_id="",
                    processing_time_ms=0,
                    context_preserved=False,
                    quality_score=handoff_context.context_completeness_score,
                    errors=[f"Context quality too low: {handoff_context.context_completeness_score:.2f}"]
                )
            # Select target agent instance
            target_agent = await self._select_target_agent(target_agent_type, handoff_context)
            if not target_agent:
                print(f"[NARRATOR] HandoffOrchestrator: No available target agent for {target_agent_type.value}.")
                return HandoffResult(
                    handoff_id=handoff_context.handoff_id,
                    success=False,
                    target_agent_id="",
                    processing_time_ms=0,
                    context_preserved=False,
                    quality_score=handoff_context.context_completeness_score,
                    errors=["No available target agent"]
                )
            handoff_context.target_agent_id = target_agent.agent_id
            print(f"[NARRATOR] HandoffOrchestrator: Selected target agent {target_agent.agent_id} for handoff.")
            # Store handoff context
            self.active_handoffs[handoff_context.handoff_id] = handoff_context
            # Execute handoff
            handoff_result = await self._execute_handoff(handoff_context, target_agent)
            print(f"[NARRATOR] HandoffOrchestrator: Handoff executed. Success: {handoff_result.success}")
            # Update metrics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            handoff_result.processing_time_ms = int(processing_time)
            # Log handoff action via MCP
            await self._log_handoff_action(handoff_context, handoff_result)
            print(f"[NARRATOR] HandoffOrchestrator: Handoff action logged for {handoff_context.handoff_id}")
            # Update performance metrics
            await self._update_performance_metrics(handoff_context, handoff_result)
            # Cleanup active handoff
            if handoff_context.handoff_id in self.active_handoffs:
                handoff_context.completed_at = datetime.now()
                handoff_context.handoff_success = handoff_result.success
                self.handoff_history.append(handoff_context)
                del self.active_handoffs[handoff_context.handoff_id]
            print(f"[NARRATOR] HandoffOrchestrator: Handoff {handoff_context.handoff_id} completed and cleaned up.")
            return handoff_result
        except Exception as e:
            print(f"[NARRATOR] HandoffOrchestrator: Exception during handoff: {str(e)}")
            self.logger.error(f"Handoff failed: {str(e)}")
            return HandoffResult(
                handoff_id=handoff_context.handoff_id if 'handoff_context' in locals() else "unknown",
                success=False,
                target_agent_id="",
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                context_preserved=False,
                quality_score=0.0,
                errors=[f"Handoff exception: {str(e)}"]
            )
    
    async def _select_target_agent(
        self, 
        target_type: AgentType, 
        context: HandoffContext
    ) -> Optional[BaseAgent]:
        """Select best available target agent"""
        
        # Get agents of target type
        candidate_agents = [
            agent for agent_type, agent in self.agents.items() 
            if agent_type == target_type
        ]
        
        if not candidate_agents:
            return None
        
        # For this implementation, return first available agent
        # In production: implement load balancing, specialization matching, etc.
        return candidate_agents[0]
    
    async def _execute_handoff(
        self, 
        context: HandoffContext, 
        target_agent: BaseAgent
    ) -> HandoffResult:
        """Execute the actual handoff"""
        
        try:
            # Prepare handoff data
            handoff_data = {
                "handoff_context": asdict(context),
                "conversation_state": context.conversation_state,
                "lead_context": context.lead_context,
                "campaign_context": context.campaign_context,
                "memory_snapshot": context.memory_snapshot,
                "interaction_history": context.interaction_history
            }
            
            # Debug: Check type of target_agent and handle_handoff
            print(f"[DEBUG] target_agent type: {type(target_agent)}")
            print(f"[DEBUG] target_agent.handle_handoff: {getattr(target_agent, 'handle_handoff', None)}")
            if not callable(getattr(target_agent, 'handle_handoff', None)):
                raise TypeError(f"target_agent.handle_handoff is not callable. Value: {getattr(target_agent, 'handle_handoff', None)}")
            # Execute handoff on target agent
            result = await target_agent.handle_handoff(handoff_data)
            
            # Validate handoff success
            context_preserved = self._validate_context_preservation(context, result)
            quality_score = self._calculate_handoff_quality(context, result)
            
            # Extract next actions from result
            next_actions = result.get("next_actions", [])
            warnings = result.get("warnings", [])
            
            return HandoffResult(
                handoff_id=context.handoff_id,
                success=True,
                target_agent_id=target_agent.agent_id,
                processing_time_ms=0,  # Will be set by caller
                context_preserved=context_preserved,
                quality_score=quality_score,
                next_actions=next_actions,
                warnings=warnings
            )
            
        except Exception as e:
            return HandoffResult(
                handoff_id=context.handoff_id,
                success=False,
                target_agent_id=target_agent.agent_id,
                processing_time_ms=0,
                context_preserved=False,
                quality_score=0.0,
                errors=[f"Handoff execution failed: {str(e)}"]
            )
    
    def _validate_context_preservation(
        self, 
        context: HandoffContext, 
        result: Dict[str, Any]
    ) -> bool:
        """Validate that critical context was preserved"""
        
        # Check if key identifiers are preserved
        required_ids = ["lead_id", "conversation_id", "campaign_id"]
        
        for req_id in required_ids:
            original_value = context.conversation_state.get(req_id) or context.lead_context.get(req_id)
            result_value = result.get(req_id)
            
            if original_value and original_value != result_value:
                return False
        
        # Check if critical state is preserved
        if context.conversation_state.get("active_intent"):
            if not result.get("preserved_intent"):
                return False
        
        return True
    
    def _calculate_handoff_quality(
        self, 
        context: HandoffContext, 
        result: Dict[str, Any]
    ) -> float:
        """Calculate quality score for handoff"""
        
        quality_score = 0.0
        
        # Context completeness (30%)
        quality_score += context.context_completeness_score * 0.3
        
        # Processing success (40%)
        if result.get("success", False):
            quality_score += 0.4
        
        # Next actions provided (20%)
        if result.get("next_actions"):
            quality_score += 0.2
        
        # No errors (10%)
        if not result.get("errors", []):
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    async def _log_handoff_action(
        self, 
        context: HandoffContext, 
        result: HandoffResult
    ):
        """Log handoff action via MCP"""
        try:
            log_data = {
                "handoff_id": context.handoff_id,
                "source_agent": context.source_agent_id,
                "target_agent": result.target_agent_id,
                "trigger": context.trigger.value,
                "success": result.success,
                "quality_score": result.quality_score,
                "processing_time_ms": result.processing_time_ms
            }
            
            await self.mcp_client.call_method(
                MCPMethod.INTERACTION_LOG.value,
                {"interaction_data": log_data}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log handoff action: {e}")
    
    async def _update_performance_metrics(
        self, 
        context: HandoffContext, 
        result: HandoffResult
    ):
        """Update handoff performance metrics"""
        
        handoff_type = f"{context.source_agent_type.value}_to_{context.target_agent_type.value}"
        
        self.performance_metrics[handoff_type].append({
            "timestamp": datetime.now(),
            "success": result.success,
            "quality_score": result.quality_score,
            "processing_time_ms": result.processing_time_ms,
            "context_completeness": context.context_completeness_score,
            "trigger": context.trigger.value
        })
        
        # Keep only last 100 metrics per type
        if len(self.performance_metrics[handoff_type]) > 100:
            self.performance_metrics[handoff_type] = self.performance_metrics[handoff_type][-100:]
    
    async def get_handoff_analytics(self) -> Dict[str, Any]:
        """Get comprehensive handoff analytics"""
        
        analytics = {
            "active_handoffs": len(self.active_handoffs),
            "total_handoffs": len(self.handoff_history),
            "success_rate": 0.0,
            "average_quality": 0.0,
            "average_processing_time": 0.0,
            "handoff_types": {},
            "common_triggers": {},
            "performance_trends": {}
        }
        
        # Calculate overall metrics
        if self.handoff_history:
            successful = sum(1 for h in self.handoff_history if h.handoff_success)
            analytics["success_rate"] = successful / len(self.handoff_history)
            
            quality_scores = [h.context_completeness_score for h in self.handoff_history]
            analytics["average_quality"] = sum(quality_scores) / len(quality_scores)
        
        # Analyze by handoff type
        for handoff_type, metrics in self.performance_metrics.items():
            if metrics:
                type_success = sum(1 for m in metrics if m["success"]) / len(metrics)
                type_quality = sum(m["quality_score"] for m in metrics) / len(metrics)
                type_time = sum(m["processing_time_ms"] for m in metrics) / len(metrics)
                
                analytics["handoff_types"][handoff_type] = {
                    "count": len(metrics),
                    "success_rate": type_success,
                    "average_quality": type_quality,
                    "average_time_ms": type_time
                }
        
        # Trigger analysis
        trigger_counts = {}
        for handoff in self.handoff_history:
            trigger = handoff.trigger.value
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        
        analytics["common_triggers"] = dict(
            sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)
        )
        
        return analytics

# ================ INTEGRATED MARKETING SYSTEM ================

class IntegratedMarketingSystem:
    def __init__(self):
        # Initialize all components
        self.memory_manager = UnifiedMemoryManager()
        self.mcp_server = MCPServer()
        self.mcp_client = MCPClient("ws://localhost:8765")
        self.ws_server = MCPWebSocketServer(self.mcp_server) # The WebSocket server
        self.http_server = MCPHTTPServer(self.mcp_server)   # The HTTP server (optional but good to have)

        # Initialize agents
        self.agents = {
            AgentType.LEAD_TRIAGE: LeadTriageAgent("triage-001"),
            AgentType.ENGAGEMENT: EngagementAgent("engagement-001"),
            AgentType.OPTIMIZER: CampaignOptimizationAgent("optimizer-001")
        }
        
        # Initialize handoff orchestrator
        self.handoff_orchestrator = HandoffOrchestrator(
            self.agents, 
            self.memory_manager,
            self.mcp_client
        )
        
        # System state
        self.system_running = False
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
        
        # Performance monitoring
        self.system_metrics: Dict[str, Any] = {
            "total_requests": 0,
            "successful_handoffs": 0,
            "failed_handoffs": 0,
            "average_response_time": 0.0,
            "system_uptime": datetime.now()
        }
    
    # In src/handoff_protocols.py

    async def start_system(self):
        """Start the integrated marketing system"""
        print("🚀 Starting Integrated Marketing System...")

        # START THE SERVERS FIRST
        self.ws_server_task = asyncio.create_task(self.ws_server.start())
        self.http_server_task = asyncio.create_task(self.http_server.start())

        # Give the servers a moment to start up before connecting
        await asyncio.sleep(1) 

        # Now, connect the client
        await self.mcp_client.connect()
        
        # Start memory consolidation
        await self.memory_manager.start_consolidation_loop(60)  # Every hour
        
        # Initialize agent memory managers
        for agent in self.agents.values():
            agent.memory_manager = self.memory_manager
            agent.mcp_client = self.mcp_client
        
        self.system_running = True
        print("✅ System started successfully!")
    
    # In src/handoff_protocols.py

    async def stop_system(self):
        """Stop the integrated marketing system"""
        print("🛑 Stopping system...")
        
        self.system_running = False
        
        # Stop memory consolidation
        await self.memory_manager.stop_consolidation_loop()
        
        # Disconnect MCP client
        await self.mcp_client.disconnect()

        # ADD THIS BLOCK TO STOP THE SERVERS
        # Stop the servers
        if hasattr(self, 'ws_server_task'):
            await self.ws_server.stop()
            self.ws_server_task.cancel()
        # You would add similar logic for the http_server if needed
        
        print("✅ System stopped successfully!")
    
    async def process_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a new lead through the entire system"""
        
        if not self.system_running:
            return {"error": "System not running"}
        
        start_time = datetime.now()
        
        try:
            # Create conversation context
            conversation_id = str(uuid.uuid4())
            conversation_context = ConversationContext(
                conversation_id=conversation_id,
                lead_id=lead_data["lead_id"],
                last_utterance_summary="New lead intake",
                active_intent="lead_qualification",
                extracted_slots=lead_data,
                emotional_state="neutral",
                engagement_level=0.5,
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
            # Store conversation context
            await self.memory_manager.store_conversation_context(conversation_context)
            
            # Step 1: Lead Triage
            triage_agent = self.agents[AgentType.LEAD_TRIAGE]
            triage_result = await triage_agent.process_request({
                "lead_data": lead_data,
                "conversation_id": conversation_id
            })
            
            # Update conversation state
            current_state = {
                "conversation_id": conversation_id,
                "lead_id": lead_data["lead_id"],
                "lead_data": lead_data,
                "triage_result": triage_result,
                "scenario": "lead_processing"
            }
            
            # Step 2: Handoff to Engagement Agent
            handoff_result = await self.handoff_orchestrator.initiate_handoff(
                source_agent=triage_agent,
                target_agent_type=AgentType.ENGAGEMENT,
                current_state=current_state,
                trigger=HandoffTrigger.TASK_COMPLETION,
                reason="Lead triage completed, initiating engagement"
            )
            
            if not handoff_result.success:
                return {
                    "lead_id": lead_data["lead_id"],
                    "success": False,
                    "error": "Handoff to engagement failed",
                    "details": handoff_result.errors
                }
            
            # Step 3: Execute Engagement
            engagement_agent = self.agents[AgentType.ENGAGEMENT]
            engagement_result = await engagement_agent.process_request({
                "lead_data": {**lead_data, **triage_result},
                "conversation_id": conversation_id,
                "handoff_context": handoff_result
            })
            
            # Update metrics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.system_metrics["total_requests"] += 1
            self.system_metrics["successful_handoffs"] += 1
            
            # Store conversation in active conversations
            self.active_conversations[conversation_id] = {
                "lead_id": lead_data["lead_id"],
                "current_agent": AgentType.ENGAGEMENT,
                "state": "active_engagement",
                "triage_result": triage_result,
                "engagement_result": engagement_result,
                "processing_time_ms": processing_time,
                "created_at": start_time
            }
            
            return {
                "lead_id": lead_data["lead_id"],
                "conversation_id": conversation_id,
                "success": True,
                "triage_result": triage_result,
                "engagement_result": engagement_result,
                "handoff_quality": handoff_result.quality_score,
                "processing_time_ms": processing_time,
                "next_actions": handoff_result.next_actions
            }
            
        except Exception as e:
            self.system_metrics["failed_handoffs"] += 1
            return {
                "lead_id": lead_data.get("lead_id", "unknown"),
                "success": False,
                "error": f"System processing failed: {str(e)}",
                "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000
            }
    
    async def optimize_campaign(self, campaign_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize a campaign through the system"""
        
        if not self.system_running:
            return {"error": "System not running"}
        
        start_time = datetime.now()
        
        try:
            # Get optimizer agent
            optimizer_agent = self.agents[AgentType.OPTIMIZER]
            
            # Process optimization request
            optimization_result = await optimizer_agent.process_request({
                "campaign_data": {"campaign_id": campaign_id},
                "metrics": metrics,
                "scenario": "campaign_optimization"
            })
            
            # Check if escalation is needed
            if optimization_result.get("escalation"):
                # Create handoff context for manager escalation
                current_state = {
                    "campaign_id": campaign_id,
                    "metrics": metrics,
                    "optimization_result": optimization_result,
                    "scenario": "campaign_optimization"
                }
                
                handoff_result = await self.handoff_orchestrator.initiate_handoff(
                    source_agent=optimizer_agent,
                    target_agent_type=AgentType.MANAGER,
                    current_state=current_state,
                    trigger=HandoffTrigger.ESCALATION_REQUIRED,
                    reason=optimization_result["escalation"]["reason"],
                    priority=HandoffPriority.HIGH
                )
                
                optimization_result["escalation_handoff"] = handoff_result
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "campaign_id": campaign_id,
                "success": True,
                "optimization_result": optimization_result,
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            return {
                "campaign_id": campaign_id,
                "success": False,
                "error": f"Campaign optimization failed: {str(e)}",
                "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        # Get handoff analytics
        handoff_analytics = await self.handoff_orchestrator.get_handoff_analytics()
        
        # Get memory statistics
        memory_stats = {
            "short_term_contexts": len(self.memory_manager.short_term.conversation_contexts),
            "long_term_profiles": len(self.memory_manager.long_term.lead_profiles),
            "episodic_memories": len(self.memory_manager.episodic.episodes),
            "semantic_nodes": len(self.memory_manager.semantic.nodes),
            "semantic_relations": len(self.memory_manager.semantic.relations)
        }
        
        # Agent workload
        agent_status = {}
        for agent_type, agent in self.agents.items():
            agent_status[agent_type.value] = {
                "agent_id": agent.agent_id,
                "status": "active" if self.system_running else "stopped"
            }
        
        return {
            "system_running": self.system_running,
            "uptime_seconds": (datetime.now() - self.system_metrics["system_uptime"]).total_seconds(),
            "active_conversations": len(self.active_conversations),
            "system_metrics": self.system_metrics,
            "handoff_analytics": handoff_analytics,
            "memory_stats": memory_stats,
            "agent_status": agent_status
        }

# ================ SYSTEM FACTORY ================

async def create_marketing_system() -> IntegratedMarketingSystem:
    """Factory function to create and initialize the marketing system"""
    
    system = IntegratedMarketingSystem()
    await system.start_system()
    
    return system

# Example usage and testing
async def main():
    """Example system usage"""
    
    # Create and start system
    system = await create_marketing_system()
    
    try:
        # Test lead processing
        test_lead = {
            "lead_id": "lead-test-001",
            "email": "john.doe@techcorp.com",
            "company_size": "Enterprise",
            "industry": "Technology",
            "source": "organic",
            "persona": "Decision Maker"
        }
        
        print("Processing test lead...")
        result = await system.process_lead(test_lead)
        print(f"Result: {json.dumps(result, indent=2, default=str)}")
        
        # Test campaign optimization
        print("\nTesting campaign optimization...")
        campaign_result = await system.optimize_campaign(
            campaign_id="camp-001",
            metrics={
                "roas": 1.5,  # Low ROAS will trigger optimization
                "ctr": 0.015,  # Low CTR
                "cpl_usd": 55.0  # High CPL
            }
        )
        print(f"Campaign Result: {json.dumps(campaign_result, indent=2, default=str)}")
        
        # Get system status
        print("\nSystem Status:")
        status = await system.get_system_status()
        print(json.dumps(status, indent=2, default=str))
        
    finally:
        # Print full system status before stopping
        print("\n==== FINAL SYSTEM STATUS BEFORE STOP ====")
        final_status = await system.get_system_status()
        print(json.dumps(final_status, indent=2, default=str))
        print("\n==== ACTIVE CONVERSATIONS ====")
        print(json.dumps(system.active_conversations, indent=2, default=str))
        # Stop system
        await system.stop_system()

if __name__ == "__main__":
    asyncio.run(main())

print("✅ Agent Handoff Protocols & Integration Complete!")
print("🔄 Next: Production Deployment Configuration")