"""
Purple Merit Technologies - Adaptive Memory Systems
Short-term, Long-term, Episodic, and Semantic Memory with Consolidation
"""

import json
import asyncio
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import hashlib
import pickle
from collections import defaultdict, deque
import heapq
import pandas as pd
import numpy as np

# ================ MEMORY MODELS ================

class MemoryType(Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"

@dataclass
class MemoryEntry:
    entry_id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    importance_score: float = 0.0
    
    def update_access(self):
        """Update access statistics"""
        self.last_accessed = datetime.now()
        self.access_count += 1

@dataclass
class ConversationContext:
    conversation_id: str
    lead_id: str
    last_utterance_summary: str
    active_intent: str
    extracted_slots: Dict[str, Any]
    emotional_state: str
    engagement_level: float
    expires_at: datetime
    turn_count: int = 0

@dataclass
class LeadProfile:
    lead_id: str
    region: str
    industry: str
    company_size: str
    persona: str
    preferences: Dict[str, Any]
    behavioral_patterns: Dict[str, Any]
    rfm_score: float
    interaction_summary: Dict[str, Any]
    last_updated: datetime

@dataclass
class Episode:
    episode_id: str
    scenario: str
    context: Dict[str, Any]
    action_sequence: List[Dict[str, Any]]
    outcome: Dict[str, Any]
    success_score: float
    lessons_learned: List[str]
    reusability_score: float
    created_at: datetime

@dataclass
class SemanticNode:
    node_id: str
    concept: str
    properties: Dict[str, Any]
    embeddings: Optional[np.ndarray] = None

@dataclass
class SemanticRelation:
    subject: str
    predicate: str 
    object: str
    weight: float
    confidence: float
    source: str
    created_at: datetime

# ================ MEMORY INTERFACES ================

class MemoryStore(ABC):
    @abstractmethod
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def search(self, query: Dict[str, Any]) -> List[Any]:
        pass

# ================ SHORT-TERM MEMORY ================

class ShortTermMemory(MemoryStore):
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl  # seconds
        self.store: Dict[str, MemoryEntry] = {}
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        self.expiry_queue = []  # Min heap for TTL management
        
    async def store_conversation_context(self, context: ConversationContext) -> bool:
        """Store conversation context with TTL"""
        self.conversation_contexts[context.conversation_id] = context
        
        # Create memory entry
        entry = MemoryEntry(
            entry_id=f"conv-{context.conversation_id}",
            memory_type=MemoryType.SHORT_TERM,
            content={
                "conversation_id": context.conversation_id,
                "lead_id": context.lead_id,
                "last_utterance_summary": context.last_utterance_summary,
                "active_intent": context.active_intent,
                "extracted_slots": context.extracted_slots,
                "emotional_state": context.emotional_state,
                "engagement_level": context.engagement_level,
                "turn_count": context.turn_count
            },
            metadata={
                "expires_at": context.expires_at.isoformat(),
                "lead_id": context.lead_id
            },
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )
        
        await self.store(context.conversation_id, entry)
        
        # Add to expiry queue
        heapq.heappush(self.expiry_queue, (context.expires_at.timestamp(), context.conversation_id))
        
        return True
    
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Store entry with automatic cleanup"""
        await self._cleanup_expired()
        
        # Evict oldest if at capacity
        if len(self.store) >= self.max_size:
            await self._evict_oldest()
        
        if isinstance(value, MemoryEntry):
            self.store[key] = value
        else:
            entry = MemoryEntry(
                entry_id=key,
                memory_type=MemoryType.SHORT_TERM,
                content=value if isinstance(value, dict) else {"data": value},
                metadata=metadata or {},
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
            self.store[key] = entry
        
        return True
    
    async def retrieve(self, key: str) -> Optional[ConversationContext]:
        """Retrieve conversation context"""
        await self._cleanup_expired()
        
        if key in self.conversation_contexts:
            context = self.conversation_contexts[key]
            if datetime.now() < context.expires_at:
                return context
            else:
                # Expired, remove it
                del self.conversation_contexts[key]
                await self.delete(key)
        
        return None
    
    async def update_context(self, conversation_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing conversation context"""
        context = await self.retrieve(conversation_id)
        if not context:
            return False
        
        # Update fields
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        context.turn_count += 1
        
        # Re-store updated context
        await self.store_conversation_context(context)
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete memory entry"""
        if key in self.store:
            del self.store[key]
        if key in self.conversation_contexts:
            del self.conversation_contexts[key]
        return True
    
    async def search(self, query: Dict[str, Any]) -> List[ConversationContext]:
        """Search conversation contexts"""
        await self._cleanup_expired()
        
        results = []
        lead_id = query.get("lead_id")
        intent = query.get("intent")
        
        for context in self.conversation_contexts.values():
            if datetime.now() >= context.expires_at:
                continue
                
            match = True
            if lead_id and context.lead_id != lead_id:
                match = False
            if intent and context.active_intent != intent:
                match = False
                
            if match:
                results.append(context)
        
        return results
    
    async def _cleanup_expired(self):
        """Remove expired entries"""
        now = datetime.now().timestamp()
        
        while self.expiry_queue and self.expiry_queue[0][0] <= now:
            _, conversation_id = heapq.heappop(self.expiry_queue)
            if conversation_id in self.conversation_contexts:
                context = self.conversation_contexts[conversation_id]
                if context.expires_at.timestamp() <= now:
                    await self.delete(conversation_id)
    
    async def _evict_oldest(self):
        """Evict least recently used entry"""
        if not self.store:
            return
            
        oldest_key = min(self.store.keys(), 
                        key=lambda k: self.store[k].last_accessed)
        await self.delete(oldest_key)

# ================ LONG-TERM MEMORY ================

class LongTermMemory(MemoryStore):
    def __init__(self):
        self.lead_profiles: Dict[str, LeadProfile] = {}
        self.behavioral_patterns: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.preference_embeddings: Dict[str, np.ndarray] = {}

    async def initialize_with_historical_data(self):
        """Initialize memory with historical data from CSV files"""
        try:
            from .data_loader import data_loader
            datasets = data_loader.datasets
            
            print("🧠 Initializing memory with historical data...")
            
            # Load long-term memory data
            if 'memory_long_term' in datasets:
                print("📊 Loading long-term lead profiles...")
                for _, row in datasets['memory_long_term'].iterrows():
                    # Convert CSV row to LeadProfile object
                    try:
                        preferences = {}
                        if pd.notna(row.get('preferences_json')):
                            preferences = json.loads(row['preferences_json'])
                    except:
                        preferences = {}
                    
                    profile = LeadProfile(
                        lead_id=row['lead_id'],
                        region=row.get('region', 'Unknown'),
                        industry=row.get('industry', 'Unknown'),
                        company_size="Unknown",  # Not in memory CSV, will get from leads
                        persona="Unknown",
                        preferences=preferences,
                        behavioral_patterns={},
                        rfm_score=row.get('rfm_score', 0.5),
                        interaction_summary={},
                        last_updated=datetime.now()
                    )
                    
                    self.lead_profiles[profile.lead_id] = profile
                
                print(f"✅ Loaded {len(self.lead_profiles)} lead profiles")
            
            # Enhance with leads.csv data
            if 'leads' in datasets:
                print("🔗 Enhancing profiles with lead data...")
                leads_df = datasets['leads']
                
                for _, lead_row in leads_df.iterrows():
                    lead_id = lead_row['lead_id']
                    
                    if lead_id in self.lead_profiles:
                        # Update existing profile
                        profile = self.lead_profiles[lead_id]
                        profile.company_size = lead_row.get('company_size', 'Unknown')
                        profile.persona = lead_row.get('persona', 'Unknown')
                        profile.industry = lead_row.get('industry', profile.industry)
                        
                        # Add lead-specific preferences
                        profile.preferences.update({
                            'preferred_channel': lead_row.get('preferred_channel', 'Email'),
                            'gdpr_consent': lead_row.get('gdpr_consent', True),
                            'source': lead_row.get('source', 'unknown'),
                            'lead_score': lead_row.get('lead_score', 50),
                            'triage_category': lead_row.get('triage_category', 'General Inquiry')
                        })
                    else:
                        # Create new profile from leads data
                        profile = LeadProfile(
                            lead_id=lead_id,
                            region=lead_row.get('region', 'Unknown'),
                            industry=lead_row.get('industry', 'Unknown'),
                            company_size=lead_row.get('company_size', 'Unknown'),
                            persona=lead_row.get('persona', 'Unknown'),
                            preferences={
                                'preferred_channel': lead_row.get('preferred_channel', 'Email'),
                                'gdpr_consent': lead_row.get('gdpr_consent', True),
                                'source': lead_row.get('source', 'unknown'),
                                'lead_score': lead_row.get('lead_score', 50),
                                'triage_category': lead_row.get('triage_category', 'General Inquiry')
                            },
                            behavioral_patterns={},
                            rfm_score=0.5,
                            interaction_summary={'total_interactions': 0},
                            last_updated=datetime.now()
                        )
                        self.lead_profiles[lead_id] = profile
                
                print(f"✅ Enhanced/created {len(self.lead_profiles)} total profiles")
        
        except ImportError:
            print("⚠️  Data loader not available, skipping historical data initialization")
        except Exception as e:
            print(f"⚠️  Error loading historical data: {str(e)}")
    
        
    async def store_lead_profile(self, profile: LeadProfile) -> bool:
        """Store or update lead profile"""
        self.lead_profiles[profile.lead_id] = profile
        
        # Update behavioral pattern analysis
        await self._update_behavioral_patterns(profile)
        
        # Generate preference embeddings
        await self._generate_preference_embeddings(profile)
        
        return True
    
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Store long-term memory entry"""
        if isinstance(value, LeadProfile):
            return await self.store_lead_profile(value)
        
        # Generic storage for other long-term data
        self.behavioral_patterns[key] = {
            "data": value,
            "metadata": metadata or {},
            "last_updated": datetime.now()
        }
        
        return True
    
    async def retrieve_lead_profile(self, lead_id: str) -> Optional[LeadProfile]:
        """Retrieve lead profile with behavioral analysis"""
        if lead_id not in self.lead_profiles:
            return None
        
        profile = self.lead_profiles[lead_id]
        
        # Update behavioral patterns from recent interactions
        recent_patterns = await self._analyze_recent_behavior(lead_id)
        profile.behavioral_patterns.update(recent_patterns)
        
        return profile
    
    async def retrieve(self, key: str) -> Optional[LeadProfile]:
        """Retrieve long-term memory"""
        return await self.retrieve_lead_profile(key)
    
    async def delete(self, key: str) -> bool:
        """Delete long-term memory entry"""
        if key in self.lead_profiles:
            del self.lead_profiles[key]
        if key in self.behavioral_patterns:
            del self.behavioral_patterns[key]
        if key in self.preference_embeddings:
            del self.preference_embeddings[key]
        return True
    
    async def search(self, query: Dict[str, Any]) -> List[LeadProfile]:
        """Search lead profiles"""
        results = []
        
        industry = query.get("industry")
        region = query.get("region")
        company_size = query.get("company_size")
        min_rfm = query.get("min_rfm_score", 0.0)
        
        for profile in self.lead_profiles.values():
            match = True
            
            if industry and profile.industry != industry:
                match = False
            if region and profile.region != region:
                match = False
            if company_size and profile.company_size != company_size:
                match = False
            if profile.rfm_score < min_rfm:
                match = False
            
            if match:
                results.append(profile)
        
        return results
    
    async def find_similar_leads(self, lead_id: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Find similar leads using preference embeddings"""
        if lead_id not in self.preference_embeddings:
            return []
        
        target_embedding = self.preference_embeddings[lead_id]
        similarities = []
        
        for other_lead_id, other_embedding in self.preference_embeddings.items():
            if other_lead_id == lead_id:
                continue
            
            # Cosine similarity
            similarity = np.dot(target_embedding, other_embedding) / (
                np.linalg.norm(target_embedding) * np.linalg.norm(other_embedding)
            )
            similarities.append((other_lead_id, float(similarity)))
        
        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]
    
    async def _update_behavioral_patterns(self, profile: LeadProfile):
        """Update behavioral pattern analysis"""
        patterns = {
            "response_rate": self._calculate_response_rate(profile),
            "preferred_channels": self._analyze_channel_preferences(profile),
            "engagement_times": self._analyze_engagement_timing(profile),
            "content_preferences": self._analyze_content_preferences(profile),
            "decision_speed": self._calculate_decision_speed(profile)
        }
        
        profile.behavioral_patterns.update(patterns)
    
    async def _generate_preference_embeddings(self, profile: LeadProfile):
        """Generate vector embeddings for lead preferences"""
        # Simple feature engineering for embeddings
        features = []
        
        # Industry encoding (simplified)
        industry_map = {"Technology": 1, "Healthcare": 2, "Finance": 3, "Manufacturing": 4}
        features.append(industry_map.get(profile.industry, 0))
        
        # Company size encoding
        size_map = {"Startup": 1, "SMB": 2, "Mid-Market": 3, "Enterprise": 4}
        features.append(size_map.get(profile.company_size, 0))
        
        # RFM score
        features.append(profile.rfm_score)
        
        # Preference features
        preferences = profile.preferences
        features.extend([
            1 if preferences.get("email_preference", "low") == "high" else 0,
            1 if preferences.get("phone_preference", "low") == "high" else 0,
            1 if "morning" in preferences.get("preferred_times", []) else 0,
            1 if "technical" in preferences.get("content_types", []) else 0
        ])
        
        # Behavioral features
        patterns = profile.behavioral_patterns
        features.extend([
            patterns.get("response_rate", 0.0),
            patterns.get("engagement_score", 0.0),
            patterns.get("decision_speed", 0.5)
        ])
        
        # Create normalized embedding
        embedding = np.array(features, dtype=np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        self.preference_embeddings[profile.lead_id] = embedding
    
    def _calculate_response_rate(self, profile: LeadProfile) -> float:
        """Calculate response rate from interaction history"""
        interactions = profile.interaction_summary
        total = interactions.get("total_outreach", 1)
        responses = interactions.get("total_responses", 0)
        return responses / total
    
    def _analyze_channel_preferences(self, profile: LeadProfile) -> Dict[str, float]:
        """Analyze channel preferences from interaction history"""
        return {
            "email": 0.7,
            "phone": 0.3,
            "social": 0.1
        }
    
    def _analyze_engagement_timing(self, profile: LeadProfile) -> Dict[str, float]:
        """Analyze optimal engagement timing"""
        return {
            "morning": 0.4,
            "afternoon": 0.6,
            "weekday": 0.8,
            "weekend": 0.2
        }
    
    def _analyze_content_preferences(self, profile: LeadProfile) -> Dict[str, float]:
        """Analyze content type preferences"""
        return {
            "technical": 0.6,
            "business_case": 0.8,
            "industry_specific": 0.7
        }
    
    def _calculate_decision_speed(self, profile: LeadProfile) -> float:
        """Calculate decision-making speed (0=slow, 1=fast)"""
        return 0.6  # Mock calculation
    
    async def _analyze_recent_behavior(self, lead_id: str) -> Dict[str, Any]:
        """Analyze recent behavioral changes"""
        # Mock recent behavior analysis
        return {
            "recent_engagement_increase": True,
            "content_preference_shift": "more_technical",
            "response_time_trend": "faster"
        }

# ================ EPISODIC MEMORY ================

class EpisodicMemory(MemoryStore):
    def __init__(self):
        self.episodes: Dict[str, Episode] = {}
        self.scenario_index: Dict[str, List[str]] = defaultdict(list)
        self.success_patterns: Dict[str, List[Episode]] = defaultdict(list)
     
    async def initialize_with_historical_episodes(self):
        """Initialize with historical episodic data"""
        try:
            from .data_loader import data_loader
            datasets = data_loader.datasets
            
            print("🎭 Loading episodic memories...")
            
            if 'memory_episodic' in datasets:
                episodic_df = datasets['memory_episodic']
                
                for _, row in episodic_df.iterrows():
                    try:
                        # Parse action sequence
                        action_sequence = []
                        if pd.notna(row.get('action_sequence_json')):
                            action_sequence = json.loads(row['action_sequence_json'])
                    except:
                        action_sequence = []
                    
                    episode = Episode(
                        episode_id=row['episode_id'],
                        scenario=row.get('scenario', 'unknown'),
                        context={},
                        action_sequence=action_sequence,
                        outcome={'success': row.get('outcome_score', 0) > 0.7},
                        success_score=row.get('outcome_score', 0.5),
                        lessons_learned=row.get('notes', '').split(';') if pd.notna(row.get('notes')) else [],
                        reusability_score=row.get('outcome_score', 0.5),
                        created_at=datetime.now()
                    )
                    
                    await self.store_episode(episode)
                
                print(f"✅ Loaded {len(self.episodes)} episodic memories")
                
        except Exception as e:
            print(f"⚠️  Error loading episodic data: {str(e)}")

        
    async def store_episode(self, episode: Episode) -> bool:
        """Store successful interaction episode"""
        self.episodes[episode.episode_id] = episode
        
        # Index by scenario
        self.scenario_index[episode.scenario].append(episode.episode_id)
        
        # Index successful patterns
        if episode.success_score >= 0.7:  # High success threshold
            pattern_key = self._extract_pattern_key(episode)
            self.success_patterns[pattern_key].append(episode)
        
        return True
    
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Store episodic memory entry"""
        if isinstance(value, Episode):
            return await self.store_episode(value)
        
        # Convert dict to Episode if needed
        if isinstance(value, dict) and "scenario" in value:
            episode = Episode(
                episode_id=key,
                scenario=value["scenario"],
                context=value.get("context", {}),
                action_sequence=value.get("action_sequence", []),
                outcome=value.get("outcome", {}),
                success_score=value.get("success_score", 0.0),
                lessons_learned=value.get("lessons_learned", []),
                reusability_score=value.get("reusability_score", 0.0),
                created_at=datetime.now()
            )
            return await self.store_episode(episode)
        
        return False
    
    async def retrieve(self, key: str) -> Optional[Episode]:
        """Retrieve specific episode"""
        return self.episodes.get(key)
    
    async def delete(self, key: str) -> bool:
        """Delete episode"""
        if key in self.episodes:
            episode = self.episodes[key]
            
            # Remove from indexes
            if episode.scenario in self.scenario_index:
                self.scenario_index[episode.scenario].remove(key)
            
            pattern_key = self._extract_pattern_key(episode)
            if pattern_key in self.success_patterns:
                self.success_patterns[pattern_key] = [
                    e for e in self.success_patterns[pattern_key] 
                    if e.episode_id != key
                ]
            
            del self.episodes[key]
        
        return True
    
    async def search(self, query: Dict[str, Any]) -> List[Episode]:
        """Search episodes by criteria"""
        scenario = query.get("scenario")
        min_success = query.get("min_success_score", 0.0)
        context_match = query.get("context_match", {})
        
        results = []
        
        for episode in self.episodes.values():
            match = True
            
            if scenario and episode.scenario != scenario:
                match = False
            
            if episode.success_score < min_success:
                match = False
            
            if context_match:
                for key, value in context_match.items():
                    if episode.context.get(key) != value:
                        match = False
                        break
            
            if match:
                results.append(episode)
        
        # Sort by success score
        results.sort(key=lambda e: e.success_score, reverse=True)
        return results
    
    async def find_best_practices(self, scenario: str, context: Dict[str, Any]) -> List[Episode]:
        """Find best practice episodes for similar scenarios"""
        # Find episodes with similar scenarios and context
        similar_episodes = await self.search({
            "scenario": scenario,
            "min_success_score": 0.8,
            "context_match": context
        })
        
        # Score episodes by context similarity and success
        scored_episodes = []
        for episode in similar_episodes:
            context_similarity = self._calculate_context_similarity(context, episode.context)
            combined_score = (episode.success_score * 0.7) + (context_similarity * 0.3)
            scored_episodes.append((episode, combined_score))
        
        # Sort by combined score
        scored_episodes.sort(key=lambda x: x[1], reverse=True)
        
        return [episode for episode, score in scored_episodes[:5]]
    
    async def extract_action_patterns(self, scenario: str) -> Dict[str, Any]:
        """Extract common action patterns for a scenario"""
        episode_ids = self.scenario_index.get(scenario, [])
        if not episode_ids:
            return {}
        
        successful_episodes = [
            self.episodes[eid] for eid in episode_ids 
            if self.episodes[eid].success_score >= 0.7
        ]
        
        if not successful_episodes:
            return {}
        
        # Analyze action patterns
        action_frequency = defaultdict(int)
        sequence_patterns = defaultdict(int)
        
        for episode in successful_episodes:
            for action in episode.action_sequence:
                action_type = action.get("type", "unknown")
                action_frequency[action_type] += 1
            
            # Track action sequences
            action_types = [a.get("type", "unknown") for a in episode.action_sequence]
            for i in range(len(action_types) - 1):
                sequence = f"{action_types[i]} -> {action_types[i+1]}"
                sequence_patterns[sequence] += 1
        
        total_episodes = len(successful_episodes)
        
        return {
            "most_effective_actions": {
                action: freq / total_episodes 
                for action, freq in sorted(action_frequency.items(), 
                                          key=lambda x: x[1], reverse=True)[:5]
            },
            "common_sequences": {
                sequence: freq / total_episodes
                for sequence, freq in sorted(sequence_patterns.items(),
                                           key=lambda x: x[1], reverse=True)[:3]
            },
            "success_factors": self._extract_success_factors(successful_episodes)
        }
    
    def _extract_pattern_key(self, episode: Episode) -> str:
        """Extract pattern key for indexing"""
        context_keys = sorted([f"{k}:{v}" for k, v in episode.context.items()][:3])
        return f"{episode.scenario}|{'|'.join(context_keys)}"
    
    def _calculate_context_similarity(self, ctx1: Dict[str, Any], ctx2: Dict[str, Any]) -> float:
        """Calculate similarity between contexts"""
        if not ctx1 or not ctx2:
            return 0.0
        
        common_keys = set(ctx1.keys()) & set(ctx2.keys())
        if not common_keys:
            return 0.0
        
        matches = sum(1 for key in common_keys if ctx1[key] == ctx2[key])
        return matches / len(common_keys)
    
    def _extract_success_factors(self, episodes: List[Episode]) -> Dict[str, Any]:
        """Extract common success factors"""
        factor_frequency = defaultdict(int)
        
        for episode in episodes:
            for lesson in episode.lessons_learned:
                factor_frequency[lesson] += 1
        
        total = len(episodes)
        return {
            factor: freq / total 
            for factor, freq in sorted(factor_frequency.items(),
                                     key=lambda x: x[1], reverse=True)[:5]
        }

# ================ SEMANTIC MEMORY ================

class SemanticMemory(MemoryStore):
    def __init__(self):
        self.nodes: Dict[str, SemanticNode] = {}
        self.relations: List[SemanticRelation] = []
        self.relation_index: Dict[str, List[SemanticRelation]] = defaultdict(list)
        self.concept_embeddings: Dict[str, np.ndarray] = {}

    async def initialize_with_knowledge_graph(self):
        """Initialize with semantic knowledge from CSV"""
        try:
            from .data_loader import data_loader
            datasets = data_loader.datasets
            
            print("🕸️  Loading semantic knowledge graph...")
            
            if 'semantic_kg_triples' in datasets:
                triples_df = datasets['semantic_kg_triples']
                
                for _, row in triples_df.iterrows():
                    relation = SemanticRelation(
                        subject=row['subject'],
                        predicate=row['predicate'],
                        object=row['object'],
                        weight=row.get('weight', 1.0),
                        confidence=row.get('weight', 1.0),
                        source=row.get('source', 'historical_data'),
                        created_at=datetime.now()
                    )
                    
                    await self.add_relation(relation)
                
                print(f"✅ Loaded {len(self.relations)} semantic relations")
                
        except Exception as e:
            print(f"⚠️  Error loading semantic data: {str(e)}")

        
    async def add_node(self, node: SemanticNode) -> bool:
        """Add semantic node"""
        self.nodes[node.node_id] = node
        
        # Generate embeddings for the concept
        await self._generate_concept_embedding(node)
        
        return True
    
    async def add_relation(self, relation: SemanticRelation) -> bool:
        """Add semantic relation"""
        self.relations.append(relation)
        
        # Index for efficient querying
        self.relation_index[relation.subject].append(relation)
        self.relation_index[f"incoming_{relation.object}"].append(relation)
        
        return True
    
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Store semantic knowledge"""
        if isinstance(value, SemanticNode):
            return await self.add_node(value)
        elif isinstance(value, SemanticRelation):
            return await self.add_relation(value)
        elif isinstance(value, dict) and "subject" in value and "predicate" in value:
            # Create relation from dict
            relation = SemanticRelation(
                subject=value["subject"],
                predicate=value["predicate"],
                object=value["object"],
                weight=value.get("weight", 1.0),
                confidence=value.get("confidence", 1.0),
                source=value.get("source", "unknown"),
                created_at=datetime.now()
            )
            return await self.add_relation(relation)
        
        return False
    
    async def retrieve(self, key: str) -> Optional[SemanticNode]:
        """Retrieve semantic node"""
        return self.nodes.get(key)
    
    async def delete(self, key: str) -> bool:
        """Delete semantic knowledge"""
        if key in self.nodes:
            del self.nodes[key]
            # Remove related relations
            self.relations = [r for r in self.relations 
                            if r.subject != key and r.object != key]
            # Rebuild index
            await self._rebuild_relation_index()
        
        return True
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search semantic knowledge"""
        concept = query.get("concept")
        relation_type = query.get("relation_type")
        min_weight = query.get("min_weight", 0.0)
        
        results = []
        
        if concept:
            # Find related concepts
            related = await self.get_related_concepts(concept, min_weight)
            results.extend(related)
        
        if relation_type:
            # Find relations of specific type
            type_relations = [r for r in self.relations 
                            if r.predicate == relation_type and r.weight >= min_weight]
            results.extend([{
                "subject": r.subject,
                "predicate": r.predicate,
                "object": r.object,
                "weight": r.weight
            } for r in type_relations])
        
        return results
    
    async def get_related_concepts(self, concept: str, min_weight: float = 0.0) -> List[Dict[str, Any]]:
        """Get concepts related to given concept"""
        related = []
        
        # Outgoing relations
        for relation in self.relation_index.get(concept, []):
            if relation.weight >= min_weight:
                related.append({
                    "concept": relation.object,
                    "relation": relation.predicate,
                    "weight": relation.weight,
                    "direction": "outgoing"
                })
        
        # Incoming relations
        for relation in self.relation_index.get(f"incoming_{concept}", []):
            if relation.weight >= min_weight:
                related.append({
                    "concept": relation.subject,
                    "relation": relation.predicate,
                    "weight": relation.weight,
                    "direction": "incoming"
                })
        
        return related
    
    async def find_semantic_paths(self, start: str, end: str, max_depth: int = 3) -> List[List[str]]:
        """Find semantic paths between concepts"""
        paths = []
        visited = set()
        current_path = [start]
        
        await self._dfs_paths(start, end, current_path, paths, visited, max_depth)
        
        return paths
    
    async def reason_about_concept(self, concept: str) -> Dict[str, Any]:
        """Perform reasoning about a concept using the knowledge graph"""
        # Get direct relations
        related = await self.get_related_concepts(concept, min_weight=0.3)
        
        # Categorize relations
        categorized = {
            "properties": [],
            "related_concepts": [],
            "implications": []
        }
        
        for rel in related:
            if rel["relation"] in ["has_property", "is_characterized_by"]:
                categorized["properties"].append(rel)
            elif rel["relation"] in ["related_to", "similar_to"]:
                categorized["related_concepts"].append(rel)
            elif rel["relation"] in ["implies", "leads_to", "requires"]:
                categorized["implications"].append(rel)
        
        # Find concept clusters (highly connected concepts)
        clusters = await self._find_concept_clusters(concept)
        
        return {
            "concept": concept,
            "direct_relations": categorized,
            "semantic_clusters": clusters,
            "reasoning_confidence": self._calculate_reasoning_confidence(related)
        }
    
    async def _generate_concept_embedding(self, node: SemanticNode):
        """Generate vector embedding for concept"""
        # Simple embedding based on properties and relations
        features = []
        
        # Properties encoding
        for prop, value in node.properties.items():
            if isinstance(value, (int, float)):
                features.append(float(value))
            else:
                features.append(hash(str(value)) % 1000 / 1000.0)
        
        # Pad to fixed size
        while len(features) < 10:
            features.append(0.0)
        
        embedding = np.array(features[:10], dtype=np.float32)
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        self.concept_embeddings[node.concept] = embedding
    
    async def _rebuild_relation_index(self):
        """Rebuild relation index after deletions"""
        self.relation_index.clear()
        
        for relation in self.relations:
            self.relation_index[relation.subject].append(relation)
            self.relation_index[f"incoming_{relation.object}"].append(relation)
    
    async def _dfs_paths(self, current: str, target: str, path: List[str], 
                         all_paths: List[List[str]], visited: Set[str], max_depth: int):
        """Depth-first search for semantic paths"""
        if len(path) > max_depth:
            return
        
        if current == target:
            all_paths.append(path.copy())
            return
        
        if current in visited:
            return
        
        visited.add(current)
        
        # Explore outgoing relations
        for relation in self.relation_index.get(current, []):
            if relation.object not in visited:
                path.append(relation.object)
                await self._dfs_paths(relation.object, target, path, all_paths, visited, max_depth)
                path.pop()
        
        visited.remove(current)
    
    async def _find_concept_clusters(self, concept: str) -> List[Dict[str, Any]]:
        """Find clusters of highly connected concepts"""
        # Simple clustering based on relation weights
        clusters = []
        
        high_weight_relations = [
            r for r in self.relation_index.get(concept, [])
            if r.weight >= 0.7
        ]
        
        if high_weight_relations:
            cluster_concepts = [r.object for r in high_weight_relations]
            clusters.append({
                "cluster_type": "high_confidence",
                "concepts": cluster_concepts,
                "avg_weight": sum(r.weight for r in high_weight_relations) / len(high_weight_relations)
            })
        
        return clusters
    
    def _calculate_reasoning_confidence(self, relations: List[Dict[str, Any]]) -> float:
        """Calculate confidence in reasoning based on relation weights"""
        if not relations:
            return 0.0
        
        weights = [r["weight"] for r in relations]
        return sum(weights) / len(weights)

# ================ MEMORY CONSOLIDATION SYSTEM ================

class MemoryConsolidator:
    def __init__(self, short_term: ShortTermMemory, long_term: LongTermMemory, 
                 episodic: EpisodicMemory, semantic: SemanticMemory):
        self.short_term = short_term
        self.long_term = long_term
        self.episodic = episodic
        self.semantic = semantic
        
    async def consolidate_memories(self):
        """Run memory consolidation process"""
        print("🧠 Starting memory consolidation...")
        
        # Consolidate conversation contexts to long-term profiles
        await self._consolidate_conversation_to_profiles()
        
        # Extract episodic memories from successful interactions
        await self._extract_episodic_memories()
        
        # Update semantic knowledge from episodic patterns
        await self._update_semantic_knowledge()
        
        # Compress old short-term memories
        await self._compress_old_memories()
        
        print("✅ Memory consolidation completed")
    
    async def _consolidate_conversation_to_profiles(self):
        """Convert conversation contexts to long-term profile updates"""
        # Get all active conversations
        for conv_id, context in self.short_term.conversation_contexts.items():
            # Get or create lead profile
            profile = await self.long_term.retrieve_lead_profile(context.lead_id)
            
            if not profile:
                continue  # Skip if no profile exists
            
            # Update profile based on conversation
            updates = {
                "last_interaction": datetime.now(),
                "engagement_level": context.engagement_level,
                "recent_intents": profile.preferences.get("recent_intents", [])
            }
            
            # Track recent intents
            updates["recent_intents"].append(context.active_intent)
            updates["recent_intents"] = updates["recent_intents"][-5:]  # Keep last 5
            
            # Update emotional state tracking
            emotional_history = profile.behavioral_patterns.get("emotional_states", [])
            emotional_history.append({
                "state": context.emotional_state,
                "timestamp": datetime.now(),
                "engagement": context.engagement_level
            })
            
            profile.behavioral_patterns["emotional_states"] = emotional_history[-10:]  # Keep last 10
            profile.preferences.update(updates)
            
            await self.long_term.store_lead_profile(profile)
    
    async def _extract_episodic_memories(self):
        """Extract episodic memories from successful interaction patterns"""
        # Mock: In production, analyze interaction logs for successful patterns
        successful_interactions = [
            {
                "scenario": "enterprise_lead_conversion",
                "context": {"industry": "Technology", "company_size": "Enterprise"},
                "action_sequence": [
                    {"type": "personalized_email", "timing": 0},
                    {"type": "demo_scheduling", "timing": 24},
                    {"type": "technical_deep_dive", "timing": 72}
                ],
                "outcome": {"converted": True, "conversion_value": 50000},
                "success_score": 0.9
            }
        ]
        
        for interaction in successful_interactions:
            episode = Episode(
                episode_id=str(hashlib.md5(json.dumps(interaction).encode()).hexdigest()),
                scenario=interaction["scenario"],
                context=interaction["context"],
                action_sequence=interaction["action_sequence"],
                outcome=interaction["outcome"],
                success_score=interaction["success_score"],
                lessons_learned=[
                    "Technical deep-dive increases enterprise conversion",
                    "24-hour follow-up timing is optimal"
                ],
                reusability_score=0.8,
                created_at=datetime.now()
            )
            
            await self.episodic.store_episode(episode)
    
    async def _update_semantic_knowledge(self):
        """Update semantic knowledge from episodic patterns"""
        # Extract patterns from successful episodes
        episodes = await self.episodic.search({"min_success_score": 0.8})
        
        for episode in episodes:
            # Create semantic relations from successful patterns
            scenario_concepts = episode.scenario.split("_")
            
            for i, concept1 in enumerate(scenario_concepts[:-1]):
                concept2 = scenario_concepts[i + 1]
                
                relation = SemanticRelation(
                    subject=concept1,
                    predicate="leads_to_success_in",
                    object=concept2,
                    weight=episode.success_score,
                    confidence=episode.success_score,
                    source="episodic_consolidation",
                    created_at=datetime.now()
                )
                
                await self.semantic.add_relation(relation)
            
            # Add action effectiveness relations
            for action in episode.action_sequence:
                action_type = action.get("type")
                if action_type:
                    relation = SemanticRelation(
                        subject=episode.scenario,
                        predicate="benefits_from",
                        object=action_type,
                        weight=episode.success_score,
                        confidence=episode.success_score,
                        source="action_effectiveness",
                        created_at=datetime.now()
                    )
                    
                    await self.semantic.add_relation(relation)
    
    async def _compress_old_memories(self):
        """Compress or archive old short-term memories"""
        # Remove expired contexts (already handled in short-term cleanup)
        await self.short_term._cleanup_expired()
        
        # Optionally: Create compressed summaries of old contexts
        # and move to long-term storage
        pass

# ================ UNIFIED MEMORY MANAGER ================

class UnifiedMemoryManager:
    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.consolidator = MemoryConsolidator(
            self.short_term, self.long_term, self.episodic, self.semantic
        )
        
        # Start background consolidation
        self._consolidation_task = None

    # Add this import at the top
from .database_connections import DatabaseManager

class UnifiedMemoryManager:
    def __init__(self, use_real_databases: bool = False):
        self.use_real_databases = use_real_databases
        
        if use_real_databases:
            # Use real databases
            self.db_manager = DatabaseManager()
            print("🗄️  Using real databases (PostgreSQL, Redis, Neo4j)")
        else:
            # Use in-memory storage (current implementation)
            print("💾 Using in-memory storage")
            
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        
    async def initialize_databases(self):
        """Initialize database connections if using real databases"""
        if self.use_real_databases:
            success = await self.db_manager.connect_all()
            if success:
                # Set database connections for each memory system
                self.long_term.db_manager = self.db_manager
                self.short_term.db_manager = self.db_manager
                self.semantic.db_manager = self.db_manager
            return success
        return True

    async def initialize_all_memory_systems(self):
        """Initialize all memory systems with historical data"""
        print("🚀 Initializing all memory systems with historical data...")
        
        # Initialize each memory system
        await self.long_term.initialize_with_historical_data()
        await self.episodic.initialize_with_historical_episodes()
        await self.semantic.initialize_with_knowledge_graph()
        
        print("✅ All memory systems initialized!")
    
    async def start_consolidation_loop(self, interval_minutes: int = 60):
        """Start background memory consolidation"""
        self._consolidation_task = asyncio.create_task(
            self._consolidation_loop(interval_minutes)
        )
    
    async def stop_consolidation_loop(self):
        """Stop background consolidation"""
        if self._consolidation_task:
            self._consolidation_task.cancel()
    
    async def _consolidation_loop(self, interval_minutes: int):
        """Background consolidation loop"""
        while True:
            await asyncio.sleep(interval_minutes * 60)
            try:
                await self.consolidator.consolidate_memories()
            except Exception as e:
                print(f"Consolidation error: {e}")
    
    async def store_conversation_context(self, context: ConversationContext) -> bool:
        """Store conversation context in short-term memory"""
        return await self.short_term.store_conversation_context(context)
    
    async def get_conversation_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Retrieve conversation context"""
        return await self.short_term.retrieve(conversation_id)
    
    async def get_lead_profile(self, lead_id: str) -> Optional[LeadProfile]:
        """Get comprehensive lead profile"""
        return await self.long_term.retrieve_lead_profile(lead_id)
    
    async def get_best_practices(self, scenario: str, context: Dict[str, Any]) -> List[Episode]:
        """Get best practice recommendations"""
        return await self.episodic.find_best_practices(scenario, context)
    
    async def query_semantic_knowledge(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query semantic knowledge graph"""
        return await self.semantic.search(query)
    
    async def reason_about_lead(self, lead_id: str) -> Dict[str, Any]:
        """Comprehensive reasoning about a lead using all memory systems"""
        # Get lead profile
        profile = await self.get_lead_profile(lead_id)
        if not profile:
            return {"error": "Lead profile not found"}
        
        # Get similar leads for pattern matching
        similar_leads = await self.long_term.find_similar_leads(lead_id)
        
        # Get relevant episodes
        episodes = await self.episodic.search({
            "context_match": {
                "industry": profile.industry,
                "company_size": profile.company_size
            },
            "min_success_score": 0.7
        })
        
        # Get semantic insights
        semantic_insights = await self.semantic.reason_about_concept(profile.industry)
        
        return {
            "lead_profile": profile,
            "similar_leads": similar_leads,
            "success_patterns": episodes[:3],
            "semantic_insights": semantic_insights,
            "recommendations": await self._generate_recommendations(profile, episodes, semantic_insights)
        }
    
    async def _generate_recommendations(self, profile: LeadProfile, episodes: List[Episode], 
                                      semantic_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Generate action recommendations based on all memory systems"""
        recommendations = {
            "next_actions": [],
            "timing_suggestions": [],
            "content_suggestions": [],
            "channel_preferences": []
        }
        
        # From episodic memory
        if episodes:
            successful_actions = set()
            for episode in episodes:
                for action in episode.action_sequence:
                    successful_actions.add(action.get("type"))
            recommendations["next_actions"] = list(successful_actions)[:3]
        
        # From long-term profile
        if profile.behavioral_patterns:
            timing = profile.behavioral_patterns.get("engagement_times", {})
            best_time = max(timing.items(), key=lambda x: x[1])[0] if timing else "morning"
            recommendations["timing_suggestions"].append(best_time)
        
        # From semantic knowledge
        if semantic_insights.get("direct_relations"):
            implications = semantic_insights["direct_relations"].get("implications", [])
            for implication in implications[:2]:
                recommendations["content_suggestions"].append(implication["concept"])
        
        return recommendations

print("✅ Adaptive Memory Systems Created Successfully!")
print("🔄 Next: Agent Handoff Protocols & Integration")