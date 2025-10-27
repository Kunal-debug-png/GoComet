# Agent Orchestrator - System Design

## Architecture Overview
Multi-agent orchestration system using DAG-based execution with MCP (Model Context Protocol) stdio servers for tool integration.

## Core Components

### 1. Router (`app/core/router.py`)
- Classifies incoming queries using capability index (keyword matching)
- Extracts context: outlet numbers, time periods (weeks/months), file paths
- Returns flow type: `flow_plot`, `flow_pdf_tracking`, or `flow_dynamic`
- Uses regex patterns to parse query intent (e.g., "last 4 weeks" → week_count=4)

### 2. Planner (`app/core/planner.py`)
- Builds DAG execution plans from templates or dynamically
- Template-based: Pre-defined node graphs for common flows
- Dynamic: Constructs DAG from capability index matches
- Injects context into node args (SQL WHERE clauses, file paths, time filters)
- Calculates ISO week ranges for time-based queries

### 3. Executor (`app/core/executor_simple.py`)
- Executes DAG using topological sort (NetworkX)
- Node types: `tool` (MCP servers) or `agent` (internal functions)
- Features: idempotency keys, caching, timeout handling, artifact management
- Agents: viz_spec_agent, extraction_agent, validator, reducer

### 4. MCP Stdio Servers (`app/mcp/servers/`)
- **srv_sql**: DuckDB queries on CSV data (orders.csv)
- **srv_pandas**: DataFrame transformations (groupby, rolling, head)
- **srv_fs**: File reading with base64 encoding
- **srv_tracking**: JSON-based tracking DB (upsert by tracking_id or invoice_number)
- **srv_plotly**: Chart rendering (line/bar) to PNG

Each server has stdio wrapper (`*_stdio.py`) implementing JSON-RPC 2.0 protocol.

### 5. MCP Protocol (`app/mcp/protocol.py`)
- JSON-RPC 2.0 over stdin/stdout
- Redirects debug output to stderr to keep stdout clean
- Supports `--manifest` flag for tool discovery

### 6. Storage Layer
- **Database** (`app/storage/database.py`): SQLite for runs/nodes tracking
- **Artifacts** (`app/storage/artifacts.py`): File-based artifact storage by run_id/node_id

## PDF Extraction Strategy

### Hybrid Approach (LlamaExtract → pdfplumber fallback)
1. **Primary: LlamaExtract** (if `LLAMA_CLOUD_API_KEY` set)
   - Cloud-based structured extraction with Pydantic schemas
   - Returns typed data: invoice_number, date, vendor, line_items
   - Handles complex layouts and multi-page documents
   
2. **Fallback: pdfplumber** (local, no API key needed)
   - Text extraction via `extract_text()`
   - Table extraction via `extract_tables()`
   - Regex parsing for invoice fields
   - Flexible patterns for dates, amounts, vendors

**Why fallback?** Ensures system works without external dependencies/costs while offering premium extraction when available.

## Flow Examples

### Plot Flow (5 nodes)
sql → pandas_transform → viz_spec_agent → plotly_render → validator → reducer

### PDF Tracking Flow (5 nodes)
file_read → extraction_agent → tracking_upsert → validator → reducer

## Configuration
- `config/capability_index.json`: Tool registry with tags for routing
- Environment variables: DATABASE_PATH, ARTIFACTS_PATH, LLAMA_CLOUD_API_KEY
- Timeouts: 30s per node, 1 retry max

## Key Design Decisions
- **Stdio over HTTP**: Simpler process isolation, no port conflicts
- **Template + Dynamic**: Balance between predictability and flexibility
- **Idempotency**: SHA256 hash of (node_type, args, upstream_outputs) for caching
- **Artifact URIs**: `artifact://{node_id}/{filename}` for data passing
- **ISO weeks**: Standardized time filtering (YYYY-Www format)
