import json
from typing import Dict, List
import uuid
from app.config import Config
from pathlib import Path
from datetime import datetime, timedelta

class Planner:
    def __init__(self):
        self.templates = self._load_templates()
        self.capability_index = self._load_capability_index()
    
    def _load_capability_index(self) -> Dict:
        """Load capability index for dynamic planning"""
        index_path = Path(Config.CAPABILITY_INDEX_PATH)
        if index_path.exists():
            with open(index_path, 'r') as f:
                return json.load(f)
        return {"capabilities": []}
    
    def _load_templates(self) -> Dict:
        """Load DAG templates"""
        return {
            "flow_plot": {
                "nodes": [
                    {
                        "id": "sql",
                        "type": "tool",
                        "server": "srv_sql",
                        "tool": "sql.query",
                        "args": {"sql": "1=1"}  # Will be replaced
                    },
                    {
                        "id": "tfm",
                        "type": "tool",
                        "server": "srv_pandas",
                        "tool": "dataframe.transform",
                        "args": {"script": "head(20)"},
                        "input_bindings": {"dataframe_data": "artifact://sql/output.json"}
                    },
                    {
                        "id": "spec",
                        "type": "agent",
                        "agent": "viz_spec_agent",
                        "input_bindings": {"dataframe_data": "artifact://tfm/output.json"}
                    },
                    {
                        "id": "render",
                        "type": "tool",
                        "server": "srv_plotly",
                        "tool": "plotly.render",
                        "args": {"format": "png"},
                        "input_bindings": {"spec": "artifact://spec/output.json"}
                    },
                    {
                        "id": "validate",
                        "type": "agent",
                        "agent": "validator",
                        "input_bindings": {"image_ref": "artifact://render/output.png"}
                    },
                    {
                        "id": "reduce",
                        "type": "agent",
                        "agent": "reducer",
                        "args": {"type": "plot"}
                    }
                ],
                "edges": [
                    ["sql", "tfm"],
                    ["tfm", "spec"],
                    ["spec", "render"],
                    ["render", "validate"],
                    ["validate", "reduce"]
                ]
            },
            "flow_pdf_tracking": {
                "nodes": [
                    {
                        "id": "read",
                        "type": "tool",
                        "server": "srv_fs",
                        "tool": "file.read",
                        "args": {"path": "./samples/sample1-pdf.pdf"}
                    },
                    {
                        "id": "extract",
                        "type": "agent",
                        "agent": "extraction_agent",
                        "input_bindings": {"file_ref": "artifact://read/output.json"}
                    },
                    {
                        "id": "upsert",
                        "type": "tool",
                        "server": "srv_tracking",
                        "tool": "tracking.upsert",
                        "input_bindings": {"fields": "artifact://extract/output.json"}
                    },
                    {
                        "id": "validate",
                        "type": "agent",
                        "agent": "validator",
                        "input_bindings": {"tracking_ref": "artifact://upsert/output.json"}
                    },
                    {
                        "id": "reduce",
                        "type": "agent",
                        "agent": "reducer",
                        "args": {"type": "file_update"}
                    }
                ],
                "edges": [
                    ["read", "extract"],
                    ["extract", "upsert"],
                    ["upsert", "validate"],
                    ["validate", "reduce"]
                ]
            }
        }
    
    def plan(self, flow_type: str, query: str, context: Dict) -> Dict:
        """Build DAG plan - template-based or dynamic"""
        plan_id = f"pln_{uuid.uuid4().hex[:8]}"
        
        if flow_type == "flow_dynamic":
            result = self._build_dynamic_plan(plan_id, query, context)
        elif flow_type in self.templates:
            result = self._build_template_plan(plan_id, flow_type, context)
        else:
            raise ValueError(f"Unknown flow type: {flow_type}")
        
        return result
    
    def _build_template_plan(self, plan_id: str, flow_type: str, context: Dict) -> Dict:
        """Build plan from predefined template"""
        template = self.templates[flow_type]
        
        # Deep copy template
        plan = json.loads(json.dumps(template))
        
        if flow_type == "flow_plot":
            sql_conditions = []
            
            outlet = context.get("outlet")
            if outlet:
                sql_conditions.append(f"outlet_id = {outlet}")
            
            week_count = context.get("week_count")
            if week_count:
                current_date = datetime.now()
                start_date = current_date - timedelta(weeks=week_count - 1)
                start_year, start_week, start_day = start_date.isocalendar()
                start_week_str = f"{start_year}-W{start_week:02d}"
                sql_conditions.append(f"week >= '{start_week_str}'")
            
            if sql_conditions:
                sql_where = " AND ".join(sql_conditions)
            else:
                sql_where = "1=1"
            
            sql_node = next(n for n in plan["nodes"] if n["id"] == "sql")
            sql_node["args"]["sql"] = sql_where
        
        elif flow_type == "flow_pdf_tracking":
            # Update file path
            file_path = context.get("file_path")
            if file_path:
                read_node = next(n for n in plan["nodes"] if n["id"] == "read")
                read_node["args"]["path"] = file_path
            else:
                read_node = next(n for n in plan["nodes"] if n["id"] == "read")
                read_node["args"]["path"] = "./samples/sample1-pdf.pdf"
        
        return {
            "plan_id": plan_id,
            "flow_type": flow_type,
            "nodes": plan["nodes"],
            "edges": plan["edges"],
            "budgets": {"latency_ms": 30000, "cost_usd": 1.5}
        }
    
    def _build_dynamic_plan(self, plan_id: str, query: str, context: Dict) -> Dict:
        """Build DAG dynamically from capability index"""
        candidates = context.get("candidates", [])
        
        if not candidates:
            # Fallback to simple plan
            return {
                "plan_id": plan_id,
                "flow_type": "flow_dynamic",
                "nodes": [],
                "edges": [],
                "budgets": {"latency_ms": 30000, "cost_usd": 1.5}
            }
        
        # Build nodes from capabilities
        nodes = []
        edges = []
        
        # Group capabilities by type
        tools = [c for c in candidates if c.get("type") == "tool"]
        agents = [c for c in candidates if c.get("type") == "agent"]
        
        # Create nodes for top tools
        for i, tool in enumerate(tools[:3]):  # Limit to top 3 tools
            node = {
                "id": tool["id"],
                "type": "tool",
                "server": tool["server"],
                "tool": tool["tool"],
                "args": self._generate_tool_args(tool, context)
            }
            
            # Add input bindings for chaining
            if i > 0:
                prev_tool = tools[i-1]
                node["input_bindings"] = {
                    "input_data": f"artifact://{prev_tool['id']}/output.json"
                }
            
            nodes.append(node)
            
            # Create edge to previous node
            if i > 0:
                edges.append([tools[i-1]["id"], tool["id"]])
        
        # Add validation and reduction agents
        for agent in agents:
            if agent["id"] in ["validator", "reducer"]:
                node = {
                    "id": agent["id"],
                    "type": "agent",
                    "agent": agent["agent"],
                    "args": {"type": "dynamic"}
                }
                
                # Connect to last tool
                if tools:
                    last_tool = tools[-1] if len(tools) <= 3 else tools[2]
                    node["input_bindings"] = {
                        "input_ref": f"artifact://{last_tool['id']}/output.json"
                    }
                    edges.append([last_tool["id"], agent["id"]])
                
                nodes.append(node)
        
        return {
            "plan_id": plan_id,
            "flow_type": "flow_dynamic",
            "nodes": nodes,
            "edges": edges,
            "budgets": {"latency_ms": 30000, "cost_usd": 1.5}
        }
    
    def _generate_tool_args(self, tool: Dict, context: Dict) -> Dict:
        """Generate appropriate args for a tool based on context"""
        tool_name = tool.get("tool", "")
        
        if "sql.query" in tool_name:
            outlet = context.get("outlet")
            if outlet:
                return {"sql": f"outlet_id = {outlet}"}
            return {"sql": "1=1"}
        
        elif "file.read" in tool_name:
            file_path = context.get("file_path", "./samples/sample1-pdf.pdf")
            return {"path": file_path}
        
        elif "dataframe.transform" in tool_name:
            time_period = context.get("time_period", "weekly")
            if time_period == "weekly":
                return {"script": "groupby('week').sum()"}
            return {"script": "head(20)"}
        
        elif "plotly.render" in tool_name:
            return {"format": "png"}
        
        return {}