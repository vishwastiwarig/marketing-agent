import os
import json
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from neo4j import GraphDatabase
import asyncpg
from typing import Dict, Any, List, Optional

class DatabaseConfig:
    def __init__(self):
        # Connection strings
        self.postgres_url = os.getenv('POSTGRES_URL', 'postgresql://marketing_user:marketing_password@localhost:5432/marketing_system')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.neo4j_url = os.getenv('NEO4J_URL', 'bolt://localhost:7687')
        self.neo4j_auth = ('neo4j', 'marketing_password')
        
        print(f"DEBUG: Connecting to PostgreSQL with URL: {self.postgres_url}")

class PostgreSQLManager:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
        
    async def connect(self):
        """Connect to PostgreSQL"""
        try:
            self.connection = await asyncpg.connect(self.config.postgres_url)
            print("✅ Connected to PostgreSQL")
            return True
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            return False
    
    async def store_lead_profile(self, profile):
        """Store lead profile in PostgreSQL"""
        try:
            query = """
            INSERT INTO lead_profiles (lead_id, region, industry, preferences_json, rfm_score, last_updated)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (lead_id) DO UPDATE SET
                region = $2,
                industry = $3,
                preferences_json = $4,
                rfm_score = $5,
                last_updated = NOW()
            """
            
            await self.connection.execute(
                query,
                profile.lead_id,
                profile.region,
                profile.industry,
                json.dumps(profile.preferences),
                profile.rfm_score
            )
            return True
        except Exception as e:
            print(f"❌ Error storing lead profile: {e}")
            return False
    
    async def get_lead_profile(self, lead_id: str):
        """Retrieve lead profile from PostgreSQL"""
        try:
            query = "SELECT * FROM lead_profiles WHERE lead_id = $1"
            row = await self.connection.fetchrow(query, lead_id)
            
            if row:
                return {
                    'lead_id': row['lead_id'],
                    'region': row['region'],
                    'industry': row['industry'],
                    'preferences': json.loads(row['preferences_json']) if row['preferences_json'] else {},
                    'rfm_score': float(row['rfm_score']),
                    'last_updated': row['last_updated']
                }
            return None
        except Exception as e:
            print(f"❌ Error retrieving lead profile: {e}")
            return None

class RedisManager:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.client = None
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.from_url(self.config.redis_url, decode_responses=True)
            # Test connection
            self.client.ping()
            print("✅ Connected to Redis")
            return True
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            return False
    
    async def store_conversation_context(self, context, ttl_seconds=3600):
        """Store conversation context in Redis with TTL"""
        try:
            key = f"conversation:{context.conversation_id}"
            data = {
                'lead_id': context.lead_id,
                'last_utterance_summary': context.last_utterance_summary,
                'active_intent': context.active_intent,
                'extracted_slots': json.dumps(context.extracted_slots),
                'emotional_state': context.emotional_state,
                'engagement_level': context.engagement_level
            }
            
            # Store with expiration
            self.client.hmset(key, data)
            self.client.expire(key, ttl_seconds)
            
            return True
        except Exception as e:
            print(f"❌ Error storing conversation context: {e}")
            return False
    
    async def get_conversation_context(self, conversation_id: str):
        """Retrieve conversation context from Redis"""
        try:
            key = f"conversation:{conversation_id}"
            data = self.client.hgetall(key)
            
            if data:
                return {
                    'conversation_id': conversation_id,
                    'lead_id': data.get('lead_id'),
                    'last_utterance_summary': data.get('last_utterance_summary'),
                    'active_intent': data.get('active_intent'),
                    'extracted_slots': json.loads(data.get('extracted_slots', '{}')),
                    'emotional_state': data.get('emotional_state'),
                    'engagement_level': float(data.get('engagement_level', 0.5))
                }
            return None
        except Exception as e:
            print(f"❌ Error retrieving conversation context: {e}")
            return None

class Neo4jManager:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.driver = None
        
    async def connect(self):
        """Connect to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(self.config.neo4j_url, auth=self.config.neo4j_auth)
            
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                list(result)
            
            print("✅ Connected to Neo4j")
            return True
        except Exception as e:
            print(f"❌ Neo4j connection failed: {e}")
            return False
    
    async def add_semantic_relation(self, subject: str, predicate: str, object: str, weight: float):
        """Add semantic relation to knowledge graph"""
        try:
            with self.driver.session() as session:
                query = """
                MERGE (s:Concept {name: $subject})
                MERGE (o:Concept {name: $object})
                MERGE (s)-[r:RELATES {predicate: $predicate}]->(o)
                SET r.weight = $weight
                """
                session.run(query, subject=subject, predicate=predicate, object=object, weight=weight)
            return True
        except Exception as e:
            print(f"❌ Error adding semantic relation: {e}")
            return False
    
    async def query_semantic_relations(self, concept: str, min_weight: float = 0.5):
        """Query semantic relations for a concept"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (c:Concept {name: $concept})-[r:RELATES]->(related:Concept)
                WHERE r.weight >= $min_weight
                RETURN related.name as concept, r.predicate as relation, r.weight as weight
                ORDER BY r.weight DESC
                LIMIT 10
                """
                result = session.run(query, concept=concept, min_weight=min_weight)
                
                relations = []
                for record in result:
                    relations.append({
                        'concept': record['concept'],
                        'relation': record['relation'], 
                        'weight': record['weight']
                    })
                return relations
        except Exception as e:
            print(f"❌ Error querying semantic relations: {e}")
            return []

# Database Manager - Coordinates all databases
class DatabaseManager:
    def __init__(self):
        self.config = DatabaseConfig()
        self.postgres = PostgreSQLManager(self.config)
        self.redis = RedisManager(self.config)
        self.neo4j = Neo4jManager(self.config)
        
    async def connect_all(self):
        """Connect to all databases"""
        print("🔗 Connecting to all databases...")
        
        postgres_ok = await self.postgres.connect()
        redis_ok = await self.redis.connect()
        neo4j_ok = await self.neo4j.connect()
        
        if postgres_ok and redis_ok and neo4j_ok:
            print("✅ All databases connected successfully!")
            return True
        else:
            print("❌ Some database connections failed")
            return False