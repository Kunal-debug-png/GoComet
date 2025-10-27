# MCP Stdio Servers - Complete Examples

This folder contains complete examples for testing all 5 MCP stdio servers.

## Quick Start

```powershell
cd agent-orchestrator/examples_stdio

# Test all servers at once
.\test_all.ps1

# Or test individually (see below)
```

---

## 1. SQL Server (srv_sql)

Query CSV data using SQL.

### Example 1: Last 4 Weeks
```powershell
type sql\last_4_weeks.json | python ..\app\mcp\servers\srv_sql_stdio.py
```

### Example 2: High Sales Only
```powershell
type sql\high_sales.json | python ..\app\mcp\servers\srv_sql_stdio.py
```

### Example 3: Widget Products Only
```powershell
type sql\widget_only.json | python ..\app\mcp\servers\srv_sql_stdio.py
```

### Example 4: Specific Outlet
```powershell
type sql\outlet_42.json | python ..\app\mcp\servers\srv_sql_stdio.py
```

### Example 5: Recent Weeks
```powershell
type sql\recent_weeks.json | python ..\app\mcp\servers\srv_sql_stdio.py
```

---

## 2. Pandas Server (srv_pandas)

Transform dataframes with pandas operations.

### Example 1: Get First 3 Rows
```powershell
type pandas\head_3.json | python ..\app\mcp\servers\srv_pandas_stdio.py
```

### Example 2: Sort by Sales
```powershell
type pandas\sort_by_sales.json | python ..\app\mcp\servers\srv_pandas_stdio.py
```

### Example 3: Group by Product
```powershell
type pandas\group_by_product.json | python ..\app\mcp\servers\srv_pandas_stdio.py
```

### Example 4: Filter High Sales
```powershell
type pandas\filter_high_sales.json | python ..\app\mcp\servers\srv_pandas_stdio.py
```

### Example 5: Get Last 2 Rows
```powershell
type pandas\tail_2.json | python ..\app\mcp\servers\srv_pandas_stdio.py
```

---

## 3. Plotly Server (srv_plotly)

Generate charts and save as PNG images.

### Example 1: Line Chart
```powershell
python plotly\line_chart.py
# Creates: plotly\line_chart.png
```

### Example 2: Bar Chart
```powershell
python plotly\bar_chart.py
# Creates: plotly\bar_chart.png
```

### Example 3: Sales Trend
```powershell
python plotly\sales_trend.py
# Creates: plotly\sales_trend.png
```

### Example 4: Product Comparison
```powershell
python plotly\product_comparison.py
# Creates: plotly\product_comparison.png
```

### Example 5: Weekly Performance
```powershell
python plotly\weekly_performance.py
# Creates: plotly\weekly_performance.png
```

---

## 4. Tracking Server (srv_tracking)

Track invoice processing and status updates.

### Example 1: Create New Tracking
```powershell
type tracking\create_new.json | python ..\app\mcp\servers\srv_tracking_stdio.py
```

### Example 2: Update Status
```powershell
type tracking\update_status.json | python ..\app\mcp\servers\srv_tracking_stdio.py
```

### Example 3: Mark as Completed
```powershell
type tracking\mark_completed.json | python ..\app\mcp\servers\srv_tracking_stdio.py
```

### Example 4: Add Payment Info
```powershell
type tracking\add_payment.json | python ..\app\mcp\servers\srv_tracking_stdio.py
```

### Example 5: Update Notes
```powershell
type tracking\update_notes.json | python ..\app\mcp\servers\srv_tracking_stdio.py
```

---

## 5. FileSystem Server (srv_fs)

Read files (PDF, CSV, etc.) as base64-encoded data.

### Example 1: Read PDF
```powershell
type fs\read_pdf.json | python ..\app\mcp\servers\srv_fs_stdio.py
```

### Example 2: Read CSV
```powershell
type fs\read_csv.json | python ..\app\mcp\servers\srv_fs_stdio.py
```

### Example 3: Read Orders CSV
```powershell
type fs\read_orders.json | python ..\app\mcp\servers\srv_fs_stdio.py
```

### Example 4: Read Test Orders
```powershell
type fs\read_test_orders.json | python ..\app\mcp\servers\srv_fs_stdio.py
```

### Example 5: Read Tracking JSON
```powershell
type fs\read_tracking.json | python ..\app\mcp\servers\srv_fs_stdio.py
```

---

## Test All Servers

Run the automated test script:

```powershell
.\test_all.ps1
```

This will test all 5 servers and show you the results.

---

## File Structure

```
examples_stdio/
├── README.md                 ← This file
├── test_all.ps1             ← Test all servers
├── sql/                     ← SQL server examples
│   ├── last_4_weeks.json
│   ├── high_sales.json
│   ├── widget_only.json
│   ├── outlet_42.json
│   └── recent_weeks.json
├── pandas/                  ← Pandas server examples
│   ├── head_3.json
│   ├── sort_by_sales.json
│   ├── group_by_product.json
│   ├── filter_high_sales.json
│   └── tail_2.json
├── plotly/                  ← Plotly server examples
│   ├── line_chart.py
│   ├── bar_chart.py
│   ├── sales_trend.py
│   ├── product_comparison.py
│   └── weekly_performance.py
├── tracking/                ← Tracking server examples
│   ├── create_new.json
│   ├── update_status.json
│   ├── mark_completed.json
│   ├── add_payment.json
│   └── update_notes.json
└── fs/                      ← FileSystem server examples
    ├── read_pdf.json
    ├── read_csv.json
    ├── read_orders.json
    ├── read_test_orders.json
    └── read_tracking.json
```

---

## Get Manifests

To see what tools each server provides:

```powershell
python ..\app\mcp\servers\srv_sql_stdio.py --manifest
python ..\app\mcp\servers\srv_pandas_stdio.py --manifest
python ..\app\mcp\servers\srv_plotly_stdio.py --manifest
python ..\app\mcp\servers\srv_tracking_stdio.py --manifest
python ..\app\mcp\servers\srv_fs_stdio.py --manifest
```
