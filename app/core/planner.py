import json
from typing import Dict, List
import uuid

class Planner:
    def __init__(self):
        self.templates = self._load_templates()
    
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
                        "args": {"path": "./samples/invoice.pdf"}
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
        """Build DAG plan from template"""
        if flow_type not in self.templates:
            raise ValueError(f"Unknown flow type: {flow_type}")
        
        template = self.templates[flow_type]
        plan_id = f"pln_{uuid.uuid4().hex[:8]}"
        
        # Deep copy template
        plan = json.loads(json.dumps(template))
        
        # Inject context-specific args
        if flow_type == "flow_plot":
            # Update SQL WHERE clause
            outlet = context.get("outlet")
            if outlet:
                sql_node = next(n for n in plan["nodes"] if n["id"] == "sql")
                sql_node["args"]["sql"] = f"outlet_id = {outlet}"
        
        elif flow_type == "flow_pdf_tracking":
            # Update file path
            file_path = context.get("file_path")
            if file_path:
                read_node = next(n for n in plan["nodes"] if n["id"] == "read")
                read_node["args"]["path"] = file_path
            else:
                # Default to sample1-pdf.pdf if no file path provided
                read_node = next(n for n in plan["nodes"] if n["id"] == "read")
                read_node["args"]["path"] = "./samples/sample1-pdf.pdf"
        
        return {
            "plan_id": plan_id,
            "flow_type": flow_type,
            "nodes": plan["nodes"],
            "edges": plan["edges"],
            "budgets": {
                "latency_ms": 30000,
                "cost_usd": 1.5
            }
        }