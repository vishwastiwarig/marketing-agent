"""
Purple Merit Technologies - MCP Server/Client Implementation
JSON-RPC 2.0 with WebSocket/HTTP Transport
"""

import json
import asyncio
import uuid
import time
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
from aiohttp import web  # FIXED: Added 'web' import
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol
import logging

# ================ MCP CORE MODELS ================

@dataclass
class JSONRPCRequest:
    jsonrpc: str = "2.0"
    method: str = ""
    params: Dict[str, Any] = None
    id: Union[str, int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            result["params"] = self.params
        if self.id is not None:
            result["id"] = self.id
        return result

@dataclass
class JSONRPCResponse:
    jsonrpc: str = "2.0"
    result: Any = None
    error: Dict[str, Any] = None
    id: Union[str, int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc}
        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error
        if self.id is not None:
            result["id"] = self.id
        return result

@dataclass
class MCPResource:
    uri: str
    name: str
    description: str
    mime_type: str
    access_permissions: List[str]

class MCPMethod(Enum):
    # ... (This whole Enum is correct, no changes needed)
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    AGENT_TRIAGE_LEAD = "agent/triage/lead"
    AGENT_ENGAGEMENT_EXECUTE = "agent/engagement/execute"
    AGENT_OPTIMIZATION_ANALYZE = "agent/optimization/analyze"
    MEMORY_STORE_SHORT_TERM = "memory/store/short-term"
    MEMORY_RETRIEVE_SHORT_TERM = "memory/retrieve/short-term"
    MEMORY_STORE_LONG_TERM = "memory/store/long-term"
    MEMORY_RETRIEVE_LONG_TERM = "memory/retrieve/long-term"
    MEMORY_STORE_EPISODIC = "memory/store/episodic"
    MEMORY_QUERY_EPISODIC = "memory/query/episodic"
    MEMORY_QUERY_SEMANTIC = "memory/query/semantic"
    CAMPAIGN_GET_METRICS = "campaign/get/metrics"
    CAMPAIGN_UPDATE_STRATEGY = "campaign/update/strategy"
    CAMPAIGN_GET_LEADS = "campaign/get/leads"
    INTERACTION_LOG = "interaction/log"
    INTERACTION_GET_HISTORY = "interaction/get/history"
    SYSTEM_HEALTH_CHECK = "system/health/check"
    SYSTEM_METRICS_GET = "system/metrics/get"

# ================ MCP SERVER IMPLEMENTATION ================

class MCPServer:
    # ... (This whole class is correct, no changes needed)
    def __init__(self, server_id: str = "mcp-server-001"):
        self.server_id = server_id
        self.resources: Dict[str, MCPResource] = {}
        self.method_handlers: Dict[str, Callable] = {}
        self.active_connections: Dict[str, Any] = {}
        self.call_metrics: List[Dict[str, Any]] = []
        self.setup_default_resources()
        self.setup_method_handlers()
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("MCPServer")
    
    def setup_default_resources(self):
        self.resources = {
            "db://leads": MCPResource(uri="db://leads", name="Lead Database", description="Access to lead records and triage data", mime_type="application/json", access_permissions=["read", "write", "search"]),
            "db://campaigns": MCPResource(uri="db://campaigns", name="Campaign Database", description="Campaign metadata and performance data", mime_type="application/json", access_permissions=["read", "write", "search"]),
            "db://interactions": MCPResource(uri="db://interactions", name="Interaction Database", description="Lead interaction and engagement history", mime_type="application/json", access_permissions=["read", "write", "search"]),
            "kg://semantic": MCPResource(uri="kg://semantic", name="Knowledge Graph", description="Semantic relationships and domain knowledge", mime_type="application/rdf+xml", access_permissions=["read", "search", "reasoning"]),
            "memory://episodic": MCPResource(uri="memory://episodic", name="Episodic Memory Store", description="Successful interaction patterns and outcomes", mime_type="application/json", access_permissions=["read", "write", "consolidate"])
        }
    
    def setup_method_handlers(self):
        self.method_handlers = {
            MCPMethod.RESOURCES_LIST.value: self.handle_resources_list, MCPMethod.RESOURCES_READ.value: self.handle_resources_read,
            MCPMethod.AGENT_TRIAGE_LEAD.value: self.handle_agent_triage_lead, MCPMethod.AGENT_ENGAGEMENT_EXECUTE.value: self.handle_agent_engagement_execute, MCPMethod.AGENT_OPTIMIZATION_ANALYZE.value: self.handle_agent_optimization_analyze,
            MCPMethod.MEMORY_STORE_SHORT_TERM.value: self.handle_memory_store_short_term, MCPMethod.MEMORY_RETRIEVE_SHORT_TERM.value: self.handle_memory_retrieve_short_term, MCPMethod.MEMORY_STORE_LONG_TERM.value: self.handle_memory_store_long_term, MCPMethod.MEMORY_RETRIEVE_LONG_TERM.value: self.handle_memory_retrieve_long_term, MCPMethod.MEMORY_STORE_EPISODIC.value: self.handle_memory_store_episodic, MCPMethod.MEMORY_QUERY_SEMANTIC.value: self.handle_memory_query_semantic,
            MCPMethod.CAMPAIGN_GET_METRICS.value: self.handle_campaign_get_metrics, MCPMethod.CAMPAIGN_GET_LEADS.value: self.handle_campaign_get_leads,
            MCPMethod.INTERACTION_LOG.value: self.handle_interaction_log, MCPMethod.INTERACTION_GET_HISTORY.value: self.handle_interaction_get_history,
            MCPMethod.SYSTEM_HEALTH_CHECK.value: self.handle_system_health_check, MCPMethod.SYSTEM_METRICS_GET.value: self.handle_system_metrics_get
        }
    
    async def handle_request(self, request_data: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        start_time = time.time()
        method = request_data.get("method")
        params = request_data.get("params", {})
        try:
            if not isinstance(request_data, dict) or request_data.get("jsonrpc") != "2.0":
                return self._create_error_response(None, -32600, "Invalid Request")
            request_id = request_data.get("id")
            handler = self.method_handlers.get(method)
            if not handler:
                return self._create_error_response(request_id, -32601, f"Method not found: {method}")
            result = await handler(params, connection_id)
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_call_metrics(method, params, duration_ms, 200, connection_id)
            response = JSONRPCResponse(result=result, id=request_id)
            return response.to_dict()
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_call_metrics(method, params, duration_ms, 500, connection_id)
            return self._create_error_response(request_data.get("id"), -32603, f"Internal error: {str(e)}")

    def _create_error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        return JSONRPCResponse(error={"code": code, "message": message}, id=request_id).to_dict()

    def _log_call_metrics(self, method: str, params: Dict[str, Any], duration_ms: int, status_code: int, connection_id: str = None):
        metric = {"rpc_id": str(uuid.uuid4()), "timestamp": datetime.now(), "method": method, "params_bytes": len(json.dumps(params).encode()), "duration_ms": duration_ms, "status_code": status_code, "connection_id": connection_id}
        self.call_metrics.append(metric)
        self.call_metrics = self.call_metrics[-1000:]

    async def handle_resources_list(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"resources": [asdict(resource) for resource in self.resources.values()]}

    async def handle_resources_read(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        uri = params.get("uri")
        if uri not in self.resources: raise ValueError(f"Resource not found: {uri}")
        # Mock implementation
        return {"data": [], "total": 0}

    async def handle_agent_triage_lead(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        lead_data = params.get("lead_data", {})
        score = (50 + (20 if lead_data.get("industry") == "Technology" else 0) + (25 if lead_data.get("company_size") == "Enterprise" else 0))
        category = "Campaign Qualified" if score >= 75 else "Cold Lead" if score >= 50 else "General Inquiry"
        return {"lead_id": lead_data.get("lead_id"), "triage_category": category, "lead_score": min(score, 100)}

    async def handle_agent_engagement_execute(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"status": "mock_engagement_executed"}

    async def handle_agent_optimization_analyze(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"status": "mock_optimization_analyzed"}

    async def handle_memory_store_short_term(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"stored": True}

    async def handle_memory_retrieve_short_term(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"data": "mock_short_term_data"}

    async def handle_memory_store_long_term(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"stored": True}

    async def handle_memory_retrieve_long_term(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"data": "mock_long_term_data"}

    async def handle_memory_store_episodic(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"stored": True}

    async def handle_memory_query_semantic(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"results": []}

    async def handle_campaign_get_metrics(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"metrics": "mock_metrics"}

    async def handle_campaign_get_leads(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"leads": []}

    async def handle_interaction_log(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"logged": True}

    async def handle_interaction_get_history(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"history": []}

    async def handle_system_health_check(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"status": "healthy"}

    async def handle_system_metrics_get(self, params: Dict[str, Any], connection_id: str = None) -> Dict[str, Any]:
        return {"metrics": "mock_system_metrics"}


# ================ WEBSOCKET SERVER ================

class MCPWebSocketServer:
    def __init__(self, mcp_server: MCPServer, host: str = "localhost", port: int = 8765):
        self.mcp_server = mcp_server
        self.host = host
        self.port = port
        self.server = None
        
    async def handle_connection(self, websocket: WebSocketServerProtocol, path : str):
        connection_id = str(uuid.uuid4())
        self.mcp_server.active_connections[connection_id] = {"type": "websocket", "websocket": websocket, "connected_at": datetime.now()}
        try:
            async for message in websocket:
                try:
                    request_data = json.loads(message)
                    response = await self.mcp_server.handle_request(request_data, connection_id)
                    await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    error_response = self.mcp_server._create_error_response(None, -32700, "Parse error")
                    await websocket.send(json.dumps(error_response))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if connection_id in self.mcp_server.active_connections:
                del self.mcp_server.active_connections[connection_id]
    
    async def start(self):
        self.server = await websockets.serve(self.handle_connection, self.host, self.port)
        print(f"🔌 MCP WebSocket Server started on ws://{self.host}:{self.port}")
        
    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("🔌 MCP WebSocket Server stopped.")

# ================ HTTP SERVER ================

# FIXED: The entire MCPHTTPServer class was rebuilt with the correct structure.
class MCPHTTPServer:
    def __init__(self, mcp_server: MCPServer, host: str = "localhost", port: int = 8766):
        self.mcp_server = mcp_server
        self.host = host
        self.port = port
        self.runner = None

    async def handle_post_request(self, request: web.Request) -> web.Response:
        connection_id = str(uuid.uuid4())
        try:
            request_data = await request.json()
            response = await self.mcp_server.handle_request(request_data, connection_id)
            return web.json_response(response)
        except json.JSONDecodeError:
            error_response = self.mcp_server._create_error_response(None, -32700, "Parse error")
            return web.json_response(error_response, status=400)
    
    async def start(self):
        app = web.Application()
        app.router.add_post('/mcp', self.handle_post_request)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        print(f"🌐 MCP HTTP Server started on http://{self.host}:{self.port}/mcp")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            print("🌐 MCP HTTP Server stopped.")

# ================ MCP CLIENT ================

class MCPClient:
    # ... (This whole class is correct, no changes needed)
    def __init__(self, server_url: str, transport: str = "websocket"):
        self.server_url = server_url
        self.transport = transport
        self.websocket = None
        self.session = None
        self.request_id = 0
        
    async def connect(self):
        if self.transport == "websocket":
            self.websocket = await websockets.connect(self.server_url)
        else:
            self.session = aiohttp.ClientSession()
    
    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
        if self.session:
            await self.session.close()
    
    async def call_method(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        self.request_id += 1
        request = JSONRPCRequest(method=method, params=params, id=self.request_id)
        if self.transport == "websocket":
            await self.websocket.send(json.dumps(request.to_dict()))
            response_data = await self.websocket.recv()
            return json.loads(response_data)
        else:
            async with self.session.post(self.server_url, json=request.to_dict()) as response:
                return await response.json()

    # Convenience methods can remain as they are
    async def triage_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.call_method(MCPMethod.AGENT_TRIAGE_LEAD.value, {"lead_data": lead_data})
    
    async def execute_engagement(self, lead_data: Dict[str, Any], strategy: str = "default") -> Dict[str, Any]:
        return await self.call_method(MCPMethod.AGENT_ENGAGEMENT_EXECUTE.value, {"lead_data": lead_data, "strategy": strategy})
    
    async def analyze_campaign(self, campaign_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        return await self.call_method(MCPMethod.AGENT_OPTIMIZATION_ANALYZE.value, {"campaign_id": campaign_id, "metrics": metrics})


print("✅ MCP Server/Client with JSON-RPC 2.0 Created!")
print("🔄 Next: Memory Systems Implementation")