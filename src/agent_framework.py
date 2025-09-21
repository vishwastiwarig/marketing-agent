"""
Marketing Multi-Agent System
Core Agent Framework with Data Models
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
import uuid
import asyncio
from abc import ABC, abstractmethod
from .data_loader import data_loader


# ================ ENUMS & TYPES ================

class TriageCategory(Enum):
    CAMPAIGN_QUALIFIED = "Campaign Qualified"
    COLD_LEAD = "Cold Lead" 
    GENERAL_INQUIRY = "General Inquiry"

class LeadStatus(Enum):
    NEW = "New"
    OPEN = "Open"
    QUALIFIED = "Qualified"
    UNQUALIFIED = "Unqualified"
    CONVERTED = "Converted"

class Channel(Enum):
    EMAIL = "Email"
    SMS = "SMS"
    SOCIAL = "Social"
    ADS = "Ads"
    WEB = "Web"
    CALL = "Call"

class EventType(Enum):
    EMAIL_SENT = "email_sent"
    EMAIL_OPEN = "email_open"
    EMAIL_CLICK = "email_click"
    EMAIL_REPLY = "email_reply"
    SMS_SENT = "sms_sent"
    SMS_REPLY = "sms_reply"
    CALL_ATTEMPTED = "call_attempted"
    CALL_CONNECTED = "call_connected"

class AgentType(Enum):
    LEAD_TRIAGE = "LeadTriage"
    ENGAGEMENT = "Engagement"
    OPTIMIZER = "Optimizer"
    MANAGER = "Manager"

class ActionType(Enum):
    TRIAGE = "triage"
    OUTREACH = "outreach"
    OPTIMIZE = "optimize"
    HANDOFF = "handoff"
    ESCALATE = "escalate"

class Transport(Enum):
    WEBSOCKET = "WebSocket"
    HTTP = "HTTP"

# ================ DATA MODELS ================

@dataclass
class Lead:
    lead_id: str
    created_at: datetime
    source: str
    campaign_id: str
    triage_category: TriageCategory
    lead_status: LeadStatus
    lead_score: int
    company_size: str
    industry: str
    persona: str
    region: str
    preferred_channel: Channel
    gdpr_consent: bool
    email: str
    phone: str
    assigned_engagement_agent: str
    last_active_at: datetime

@dataclass
class Conversation:
    conversation_id: str
    lead_id: str
    opened_at: datetime
    last_event_at: datetime
    status: str

@dataclass
class Interaction:
    interaction_id: str
    conversation_id: str
    lead_id: str
    campaign_id: str
    timestamp: datetime
    channel: Channel
    event_type: EventType
    agent_id: str
    variant_id: Optional[str]
    outcome: str
    metadata_json: Dict[str, Any]

@dataclass
class Campaign:
    campaign_id: str
    name: str
    objective: str
    start_date: datetime
    end_date: datetime
    channel_mix: List[str]
    daily_budget_usd: float
    total_budget_usd: float
    owner_email: str
    primary_region: str
    target_personas: List[str]
    kpi: str

@dataclass
class CampaignDailyMetrics:
    campaign_id: str
    date: datetime
    impressions: int
    clicks: int
    ctr: float
    leads_created: int
    conversions: int
    cost_usd: float
    revenue_usd: float
    cpl_usd: float
    roas: float

# ================ MEMORY MODELS ================

@dataclass
class ShortTermMemory:
    conversation_id: str
    lead_id: str
    last_utterance_summary: str
    active_intent: str
    slots_json: Dict[str, Any]
    expires_at: datetime

@dataclass
class LongTermMemory:
    lead_id: str
    region: str
    industry: str
    rfm_score: float
    preferences_json: Dict[str, Any]
    last_updated_at: datetime

@dataclass
class EpisodicMemory:
    episode_id: str
    scenario: str
    action_sequence_json: List[Dict[str, Any]]
    outcome_score: float
    notes: str

@dataclass
class SemanticTriple:
    subject: str
    predicate: str
    object: str
    weight: float
    source: str

# ================ MCP & JSON-RPC MODELS ================

@dataclass
class JSONRPCCall:
    rpc_id: str
    timestamp: datetime
    transport: Transport
    method: str
    params_bytes: int
    duration_ms: int
    status_code: int
    source_agent_type: AgentType
    target_resource: str

@dataclass
class AgentAction:
    action_id: str
    timestamp: datetime
    conversation_id: str
    lead_id: str
    action_type: ActionType
    source_agent: str
    source_agent_type: AgentType
    dest_agent_type: AgentType
    handoff_context_json: Dict[str, Any]
    escalation_reason: Optional[str]

# ================ CORE AGENT INTERFACE ================

class BaseAgent(ABC):
    def __init__(self, agent_id: str, agent_type: AgentType):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.memory_manager = None
        self.mcp_client = None
        
    @abstractmethod
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request and return response"""
        pass
        
    @abstractmethod
    async def handle_handoff(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle handoff from another agent"""
        pass
        
    async def log_action(self, action_type: ActionType, context: Dict[str, Any], 
                        dest_agent_type: Optional[AgentType] = None):
        """Log agent action for audit trail"""
        action = AgentAction(
            action_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            conversation_id=context.get("conversation_id", ""),
            lead_id=context.get("lead_id", ""),
            action_type=action_type,
            source_agent=self.agent_id,
            source_agent_type=self.agent_type,
            dest_agent_type=dest_agent_type or self.agent_type,
            handoff_context_json=context,
            escalation_reason=context.get("escalation_reason")
        )
        
        # Store action in database via MCP
        if self.mcp_client:
            await self.mcp_client.log_agent_action(action)

# ================ AGENT IMPLEMENTATIONS ================

class LeadTriageAgent(BaseAgent):
    def __init__(self, agent_id: str = "triage-001"):
        super().__init__(agent_id, AgentType.LEAD_TRIAGE)
        self.classification_model = self._load_classification_model()
        
    def _load_classification_model(self):  # 👈 REPLACE THIS ENTIRE METHOD
        """Load classification model with real data patterns"""
        # Import data loader
        try:
            from data_loader import data_loader
            
            # Get real patterns from your CSV data
            triage_patterns = data_loader.get_triage_patterns()
            interaction_patterns = data_loader.get_interaction_patterns()
            
            print(f"🎯 Loaded real triage patterns: {list(triage_patterns.keys())}")
            
        except ImportError:
            print("⚠️  Data loader not found, using default patterns")
            triage_patterns = {}
            interaction_patterns = {}
        
        return {
            "campaign_qualified_threshold": 70,
            "cold_lead_threshold": 30,
            "scoring_weights": {
                "source": 0.3,
                "company_size": 0.2,
                "industry": 0.25,
                "persona": 0.25
            },
            "real_patterns": triage_patterns,        # 👈 Your actual data patterns
            "interaction_patterns": interaction_patterns  # 👈 Channel effectiveness
        }
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Triage incoming lead"""
        lead_data = request.get("lead_data")
        print(f"\n[NARRATOR] LeadTriageAgent: Received lead {lead_data.get('lead_id')} for triage.")
        # Calculate lead score
        lead_score = await self._calculate_lead_score(lead_data)
        print(f"[NARRATOR] LeadTriageAgent: Calculated lead score {lead_score} for {lead_data.get('lead_id')}")
        # Classify lead
        triage_category = await self._classify_lead(lead_data, lead_score)
        print(f"[NARRATOR] LeadTriageAgent: Classified lead {lead_data.get('lead_id')} as {triage_category.value}")
        # Determine next agent
        next_agent = self._determine_next_agent(triage_category)
        print(f"[NARRATOR] LeadTriageAgent: Assigned agent {next_agent} for category {triage_category.value}")
        response = {
            "lead_id": lead_data.get("lead_id"),
            "triage_category": triage_category.value,
            "lead_score": lead_score,
            "assigned_agent": next_agent,
            "confidence": 0.85,
            "reasoning": f"Classified as {triage_category.value} based on score {lead_score}"
        }
        # Log triage action
        await self.log_action(ActionType.TRIAGE, {
            "lead_id": lead_data.get("lead_id"),
            "triage_category": triage_category.value,
            "lead_score": lead_score
        })
        print(f"[NARRATOR] LeadTriageAgent: Triage action logged for {lead_data.get('lead_id')}")
        return response

    async def _calculate_lead_score(self, lead_data: Dict[str, Any]) -> int:
        """Calculate lead score based on attributes"""
        model = self.classification_model
        weights = model["scoring_weights"]
        
        score = 0
         # Use real patterns if available
        real_patterns = model.get("real_patterns", {})
    
        if real_patterns:
            # Score based on actual conversion rates from your data
            lead_category = f"{lead_data.get('company_size', 'Unknown')}_{lead_data.get('industry', 'Unknown')}"
            
            for category, pattern in real_patterns.items():
                 if category in ["Campaign Qualified", "Cold Lead", "General Inquiry"]:
                     # Use actual average scores from your data
                     if lead_data.get('industry') in pattern.get('industries', {}):
                         score += pattern.get('avg_score', 50) * 0.4
                     
                     if lead_data.get('company_size') in pattern.get('company_sizes', {}):
                         score += pattern.get('avg_score', 50) * 0.6
                         break
        
        # Source scoring
        source_scores = {"organic": 80, "paid": 70, "referral": 90, "social": 60}
        score += source_scores.get(lead_data.get("source", "").lower(), 50) * weights["source"]
        
        # Company size scoring  
        size_scores = {"Enterprise": 90, "Mid-Market": 75, "SMB": 60, "Startup": 45}
        score += size_scores.get(lead_data.get("company_size"), 50) * weights["company_size"]
        
        # Industry scoring
        industry_scores = {"Technology": 85, "Healthcare": 80, "Finance": 75, "Manufacturing": 70}
        score += industry_scores.get(lead_data.get("industry"), 60) * weights["industry"]
        
        # Persona scoring
        persona_scores = {"Decision Maker": 90, "Influencer": 75, "End User": 60}
        score += persona_scores.get(lead_data.get("persona"), 50) * weights["persona"]
        
        return min(int(score), 100)
    
    async def _classify_lead(self, lead_data: Dict[str, Any], lead_score: int) -> TriageCategory:
        """Classify lead based on score and attributes"""
        model = self.classification_model
        
        if lead_score >= model["campaign_qualified_threshold"]:
            return TriageCategory.CAMPAIGN_QUALIFIED
        elif lead_score >= model["cold_lead_threshold"]:
            return TriageCategory.COLD_LEAD
        else:
            return TriageCategory.GENERAL_INQUIRY
    
    def _determine_next_agent(self, category: TriageCategory) -> str:
        """Determine which engagement agent should handle this lead"""
        if category == TriageCategory.CAMPAIGN_QUALIFIED:
            return "engagement-premium-001"
        elif category == TriageCategory.COLD_LEAD:
            return "engagement-nurture-001" 
        else:
            return "engagement-general-001"
    
    async def handle_handoff(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle re-classification requests"""
        return await self.process_request(context)

class EngagementAgent(BaseAgent):
    def __init__(self, agent_id: str = "engagement-001"):
        super().__init__(agent_id, AgentType.ENGAGEMENT)
        self.engagement_strategies = self._load_engagement_strategies()
        
    def _load_engagement_strategies(self):
        """Load engagement playbooks"""
        return {
            "Campaign Qualified": {
                "sequence": ["immediate_call", "personalized_email", "demo_booking"],
                "timing": [0, 24, 72],  # hours
                "channels": [Channel.CALL, Channel.EMAIL, Channel.EMAIL]
            },
            "Cold Lead": {
                "sequence": ["welcome_email", "educational_content", "soft_pitch"],
                "timing": [0, 168, 336],  # hours (1 week, 2 weeks)
                "channels": [Channel.EMAIL, Channel.EMAIL, Channel.EMAIL]
            },
            "General Inquiry": {
                "sequence": ["auto_response", "resource_sharing"],
                "timing": [0, 24],
                "channels": [Channel.EMAIL, Channel.EMAIL]
            }
        }
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute engagement sequence for lead"""
        lead_data = request.get("lead_data")
        triage_category = lead_data.get("triage_category")
        print(f"\n[NARRATOR] EngagementAgent: Received lead {lead_data.get('lead_id')} for engagement. Triage category: {triage_category}")
        # Get engagement strategy
        strategy = self.engagement_strategies.get(triage_category, 
                                                self.engagement_strategies["General Inquiry"])
        print(f"[NARRATOR] EngagementAgent: Selected strategy for {triage_category}: {strategy['sequence']}")
        # Generate personalized outreach
        outreach_plan = await self._create_outreach_plan(lead_data, strategy)
        print(f"[NARRATOR] EngagementAgent: Created outreach plan for {lead_data.get('lead_id')}")
        # Execute first touchpoint
        first_interaction = await self._execute_touchpoint(lead_data, outreach_plan[0])
        print(f"[NARRATOR] EngagementAgent: Executed first touchpoint: {first_interaction['action']} via {first_interaction['channel']}")
        response = {
            "lead_id": lead_data.get("lead_id"),
            "engagement_plan": outreach_plan,
            "first_interaction": first_interaction,
            "next_touchpoint": outreach_plan[1] if len(outreach_plan) > 1 else None
        }
        # Log engagement action
        await self.log_action(ActionType.OUTREACH, {
            "lead_id": lead_data.get("lead_id"),
            "strategy": triage_category,
            "touchpoint": first_interaction
        })
        print(f"[NARRATOR] EngagementAgent: Outreach action logged for {lead_data.get('lead_id')}")
        return response

    async def _create_outreach_plan(self, lead_data: Dict[str, Any], strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create personalized outreach sequence"""
        plan = []
        
        for i, (action, timing, channel) in enumerate(zip(
            strategy["sequence"], 
            strategy["timing"], 
            strategy["channels"]
        )):
            touchpoint = {
                "sequence_step": i + 1,
                "action": action,
                "channel": channel.value,
                "scheduled_at": datetime.now() + timedelta(hours=timing),
                "personalization": await self._personalize_content(lead_data, action, channel)
            }
            plan.append(touchpoint)
        
        return plan
    
    async def _personalize_content(self, lead_data: Dict[str, Any], action: str, channel: Channel) -> Dict[str, Any]:
        """Generate personalized content"""
        # In production: use LLM for personalization
        templates = {
            "immediate_call": f"Call {lead_data.get('company_size')} {lead_data.get('industry')} lead",
            "personalized_email": f"Email about {lead_data.get('industry')} solutions",
            "welcome_email": f"Welcome to our {lead_data.get('industry')} community"
        }
        
        return {
            "subject": templates.get(action, f"Follow-up for {lead_data.get('industry')}"),
            "tone": "professional",
            "personalization_tokens": {
                "company_size": lead_data.get("company_size"),
                "industry": lead_data.get("industry"),
                "region": lead_data.get("region")
            }
        }
    
    async def _execute_touchpoint(self, lead_data: Dict[str, Any], touchpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Execute immediate touchpoint"""
        return {
            "interaction_id": str(uuid.uuid4()),
            "timestamp": datetime.now(),
            "channel": touchpoint["channel"],
            "action": touchpoint["action"],
            "status": "executed",
            "personalization_applied": True
        }
    
    async def handle_handoff(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle handoff from triage agent"""
        return await self.process_request(context)

class CampaignOptimizationAgent(BaseAgent):
    def __init__(self, agent_id: str = "optimizer-001"):
        super().__init__(agent_id, AgentType.OPTIMIZER)
        self.optimization_thresholds = self._load_optimization_thresholds()
        
    def _load_optimization_thresholds(self):
        """Load optimization rules and thresholds"""
        return {
            "min_roas": 2.0,
            "min_ctr": 0.02,
            "max_cpl": 50.0,
            "optimization_triggers": {
                "low_performance": {"roas": 1.5, "ctr": 0.01},
                "high_cost": {"cpl": 75.0},
                "budget_utilization": {"threshold": 0.8}
            }
        }
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze campaign performance and optimize"""
        campaign_data = request.get("campaign_data")
        metrics = request.get("metrics")
        
        # Analyze performance
        analysis = await self._analyze_performance(campaign_data, metrics)
        
        # Generate optimization recommendations
        optimizations = await self._generate_optimizations(analysis)
        
        # Determine if escalation needed
        escalation = await self._check_escalation_needed(analysis)
        
        response = {
            "campaign_id": campaign_data.get("campaign_id"),
            "performance_analysis": analysis,
            "optimizations": optimizations,
            "escalation": escalation,
            "confidence": analysis.get("confidence", 0.8)
        }
        
        # Log optimization action
        await self.log_action(ActionType.OPTIMIZE, {
            "campaign_id": campaign_data.get("campaign_id"),
            "optimizations": len(optimizations),
            "escalation": escalation is not None
        }, dest_agent_type=AgentType.MANAGER if escalation else None)
        
        return response
    
    async def _analyze_performance(self, campaign_data: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze campaign performance against thresholds"""
        thresholds = self.optimization_thresholds
        
        current_roas = metrics.get("roas", 0)
        current_ctr = metrics.get("ctr", 0)
        current_cpl = metrics.get("cpl_usd", float('inf'))
        
        analysis = {
            "campaign_id": campaign_data.get("campaign_id"),
            "current_metrics": metrics,
            "performance_flags": [],
            "score": 0,
            "confidence": 0.85
        }
        
        # ROAS analysis
        if current_roas < thresholds["min_roas"]:
            analysis["performance_flags"].append("low_roas")
            analysis["score"] -= 20
        else:
            analysis["score"] += 10
            
        # CTR analysis  
        if current_ctr < thresholds["min_ctr"]:
            analysis["performance_flags"].append("low_ctr")
            analysis["score"] -= 15
        else:
            analysis["score"] += 5
            
        # CPL analysis
        if current_cpl > thresholds["max_cpl"]:
            analysis["performance_flags"].append("high_cpl")
            analysis["score"] -= 25
        else:
            analysis["score"] += 15
        
        analysis["overall_health"] = "good" if analysis["score"] > 0 else "needs_optimization"
        
        return analysis
    
    async def _generate_optimizations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific optimization recommendations"""
        optimizations = []
        flags = analysis.get("performance_flags", [])
        
        if "low_roas" in flags:
            optimizations.append({
                "type": "targeting_refinement",
                "action": "Narrow targeting to high-converting segments",
                "expected_impact": "15-25% ROAS improvement",
                "implementation": "automatic"
            })
            
        if "low_ctr" in flags:
            optimizations.append({
                "type": "creative_optimization", 
                "action": "A/B test new ad creatives",
                "expected_impact": "10-20% CTR improvement",
                "implementation": "manual_review"
            })
            
        if "high_cpl" in flags:
            optimizations.append({
                "type": "bid_adjustment",
                "action": "Reduce bids on low-performing keywords",
                "expected_impact": "20-30% CPL reduction",
                "implementation": "automatic"
            })
        
        return optimizations
    
    async def _check_escalation_needed(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if human escalation is needed"""
        flags = analysis.get("performance_flags", [])
        score = analysis.get("score", 0)
        
        # Escalate if multiple critical issues
        if len(flags) >= 2 or score < -30:
            return {
                "reason": "multiple_performance_issues",
                "urgency": "high",
                "flags": flags,
                "recommended_action": "immediate_human_review"
            }
            
        return None
    
    async def handle_handoff(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle handoff for campaign optimization"""
        return await self.process_request(context)

# ================ AGENT ORCHESTRATOR ================

class AgentOrchestrator:
    def __init__(self):
        self.agents = {
            AgentType.LEAD_TRIAGE: LeadTriageAgent(),
            AgentType.ENGAGEMENT: EngagementAgent(), 
            AgentType.OPTIMIZER: CampaignOptimizationAgent()
        }
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
    
    async def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to appropriate agent"""
        agent_type = AgentType(request.get("target_agent", "LeadTriage"))
        agent = self.agents.get(agent_type)
        
        if not agent:
            raise ValueError(f"Agent type {agent_type} not found")
        
        # Process request
        response = await agent.process_request(request)
        
        # Handle handoffs
        if response.get("handoff_required"):
            next_agent_type = AgentType(response.get("next_agent"))
            handoff_context = response.get("handoff_context", {})
            
            next_agent = self.agents.get(next_agent_type)
            if next_agent:
                response = await next_agent.handle_handoff(handoff_context)
        
        return response

print("✅ Core Agent Framework Created Successfully!")
print("🏗️  Next: MCP Server/Client Implementation")
