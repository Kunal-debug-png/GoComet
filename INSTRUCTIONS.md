
## Prerequisites
- Python 3.8+
- pip or conda for package management

## Installation

### 1. Clone/Navigate to Project
```bash
cd agent-orchestrator
```

### 2. Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create or edit `.env` file in the project root:
```env
# Optional: LlamaCloud API Key for advanced PDF extraction
LLAMA_CLOUD_API_KEY=your_api_key_here

# Optional: Custom paths
DATABASE_PATH=./orchestrator.db
ARTIFACTS_PATH=./artifacts
ORDERS_CSV_PATH=./samples/orders.csv
TRACKING_JSON_PATH=./samples/tracking.json
CAPABILITY_INDEX_PATH=./config/capability_index.json

# Server settings
HOST=0.0.0.0
PORT=8000
```

### 5. Prepare Sample Data
Ensure the following directories and files exist:
- `samples/orders.csv` - Sample sales data
- `samples/tracking.json` - Tracking database
- `samples/sample1-pdf.pdf` - Sample PDF for testing
- `config/capability_index.json` - Tool capability registry

## Running the Application

### Start the FastAPI Server
```bash
# Windows
python main.py

# Linux/Mac
python3 main.py
```

The server will start on `http://localhost:8000`


#### 2. Route Query (Create Execution Plan)
```bash
curl -X POST http://localhost:8000/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Plot sales for the last 4 weeks",
    "file_path": null
  }'
```

Response includes `run_id` and `plan_id`.

#### 3. Start Execution
```bash
curl -X POST http://localhost:8000/v1/runs/{run_id}/start
```

#### 4. Check Run Status
```bash
curl http://localhost:8000/v1/runs/{run_id}
```

#### 5. Get System Metrics
```bash
curl http://localhost:8000/v1/metrics
```
