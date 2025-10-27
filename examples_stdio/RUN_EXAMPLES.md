# How to Run Examples

## Important: Run from the Correct Directory!

Different servers need to be run from different directories because of file paths.

---

## SQL Server - Run from `agent-orchestrator` folder

```powershell
cd C:\Users\KUNAL\Desktop\Gocomet\v1\agent-orchestrator

# Example 1: Last 4 weeks
type examples_stdio\sql\last_4_weeks.json | python app\mcp\servers\srv_sql_stdio.py

# Example 2: High sales
type examples_stdio\sql\high_sales.json | python app\mcp\servers\srv_sql_stdio.py

# Example 3: Widget only
type examples_stdio\sql\widget_only.json | python app\mcp\servers\srv_sql_stdio.py

# Example 4: Outlet 42
type examples_stdio\sql\outlet_42.json | python app\mcp\servers\srv_sql_stdio.py

# Example 5: Recent weeks
type examples_stdio\sql\recent_weeks.json | python app\mcp\servers\srv_sql_stdio.py
```

---

## Pandas Server - Run from `examples_stdio` folder

```powershell
cd C:\Users\KUNAL\Desktop\Gocomet\v1\agent-orchestrator\examples_stdio

# Example 1: First 3 rows
type pandas\head_3.json | python ..\app\mcp\servers\srv_pandas_stdio.py

# Example 2: Sort by sales
type pandas\sort_by_sales.json | python ..\app\mcp\servers\srv_pandas_stdio.py

# Example 3: Group by product
type pandas\group_by_product.json | python ..\app\mcp\servers\srv_pandas_stdio.py

# Example 4: Filter high sales
type pandas\filter_high_sales.json | python ..\app\mcp\servers\srv_pandas_stdio.py

# Example 5: Last 2 rows
type pandas\tail_2.json | python ..\app\mcp\servers\srv_pandas_stdio.py
```

---

## Plotly Server - Run from `examples_stdio` folder

```powershell
cd C:\Users\KUNAL\Desktop\Gocomet\v1\agent-orchestrator\examples_stdio

# Example 1: Line chart
python plotly\line_chart.py

# Example 2: Bar chart
python plotly\bar_chart.py

# Example 3: Sales trend
python plotly\sales_trend.py

# Example 4: Product comparison
python plotly\product_comparison.py

# Example 5: Weekly performance
python plotly\weekly_performance.py
```

Charts will be saved in the `plotly` folder as PNG files.

---

## Tracking Server - Run from `agent-orchestrator` folder

```powershell
cd C:\Users\KUNAL\Desktop\Gocomet\v1\agent-orchestrator

# Example 1: Create new
type examples_stdio\tracking\create_new.json | python app\mcp\servers\srv_tracking_stdio.py

# Example 2: Update status
type examples_stdio\tracking\update_status.json | python app\mcp\servers\srv_tracking_stdio.py

# Example 3: Mark completed
type examples_stdio\tracking\mark_completed.json | python app\mcp\servers\srv_tracking_stdio.py

# Example 4: Add payment
type examples_stdio\tracking\add_payment.json | python app\mcp\servers\srv_tracking_stdio.py

# Example 5: Update notes
type examples_stdio\tracking\update_notes.json | python app\mcp\servers\srv_tracking_stdio.py
```

---

## FileSystem Server - Run from `agent-orchestrator` folder

```powershell
cd C:\Users\KUNAL\Desktop\Gocomet\v1\agent-orchestrator

# Example 1: Read PDF
type examples_stdio\fs\read_pdf.json | python app\mcp\servers\srv_fs_stdio.py

# Example 2: Read CSV
type examples_stdio\fs\read_csv.json | python app\mcp\servers\srv_fs_stdio.py

# Example 3: Read orders
type examples_stdio\fs\read_orders.json | python app\mcp\servers\srv_fs_stdio.py

# Example 4: Read test orders
type examples_stdio\fs\read_test_orders.json | python app\mcp\servers\srv_fs_stdio.py

# Example 5: Read tracking JSON
type examples_stdio\fs\read_tracking.json | python app\mcp\servers\srv_fs_stdio.py
```

---

## Quick Summary

| Server | Run From | Command Pattern |
|--------|----------|-----------------|
| **SQL** | `agent-orchestrator` | `type examples_stdio\sql\*.json \| python app\mcp\servers\srv_sql_stdio.py` |
| **Pandas** | `examples_stdio` | `type pandas\*.json \| python ..\app\mcp\servers\srv_pandas_stdio.py` |
| **Plotly** | `examples_stdio` | `python plotly\*.py` |
| **Tracking** | `agent-orchestrator` | `type examples_stdio\tracking\*.json \| python app\mcp\servers\srv_tracking_stdio.py` |
| **FileSystem** | `agent-orchestrator` | `type examples_stdio\fs\*.json \| python app\mcp\servers\srv_fs_stdio.py` |

---

## Test One of Each (Copy & Paste)

```powershell
# Go to main folder
cd C:\Users\KUNAL\Desktop\Gocomet\v1\agent-orchestrator

# Test SQL
type examples_stdio\sql\outlet_42.json | python app\mcp\servers\srv_sql_stdio.py

# Test Tracking
type examples_stdio\tracking\create_new.json | python app\mcp\servers\srv_tracking_stdio.py

# Test FileSystem
type examples_stdio\fs\read_csv.json | python app\mcp\servers\srv_fs_stdio.py

# Go to examples folder for pandas and plotly
cd examples_stdio

# Test Pandas
type pandas\head_3.json | python ..\app\mcp\servers\srv_pandas_stdio.py

# Test Plotly
python plotly\line_chart.py
```
