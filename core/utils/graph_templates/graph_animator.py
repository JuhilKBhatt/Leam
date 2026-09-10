import os
import sys
import pandas as pd
import yfinance as yf
from pathlib import Path
import subprocess
import json

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from core.api.llm import gpt_request

def generate_animated_graph(ticker, save_path, graph_type="line"):
    print(f"Fetching data for {ticker} to generate animated graph of type {graph_type}...")
    try:
        hist = yf.Ticker(ticker).history(period="6mo")
        if hist.empty:
            return False
            
        # Simplify data to pass to LLM to save context
        hist = hist.reset_index()
        hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')
        data_subset = hist[['Date', 'Close']].tail(60) # Last 60 days
        
        csv_data = data_subset.to_csv(index=False)
        
        prompt = f"""
I need a Python script to generate an animated stock chart MP4 video for {ticker} using matplotlib.animation.
Here is the raw CSV data:
{csv_data}

Requirements:
1. Parse this CSV data string directly within the script (use io.StringIO).
2. Create a modern, dark-themed chart (e.g., plt.style.use('dark_background')).
3. The graph type must be '{graph_type}'. (If 'line', animate line drawing; if 'bar', animate bar growth; if 'area', animate area fill; if 'scatter', animate points appearing).
4. Save the animation as an MP4 file to the exact path: '{save_path}'
5. Use `matplotlib.animation.FuncAnimation`.
6. Use `writer = matplotlib.animation.FFMpegWriter(fps=30)`.
7. DO NOT use plt.show(), just save the file.
8. Output ONLY the raw Python code. Do not include markdown codeblocks, just the raw code.
9. CRITICAL: Ensure the top of the graph is not cut off by adding 15% padding to the maximum y-value (e.g. ax.set_ylim(min, max * 1.15)) and using plt.tight_layout(pad=2.0).
"""
        print(f"Asking LLM to write animation script for {ticker}...")
        code = gpt_request(prompt).strip()
        
        # Clean up markdown if LLM includes it
        if code.startswith("```python"):
            code = code.replace("```python", "", 1)
        if code.startswith("```"):
            code = code.replace("```", "", 1)
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]
            
        script_path = str(Path(save_path).parent / f"temp_anim_{ticker}.py")
        with open(script_path, 'w') as f:
            f.write(code.strip())
            
        print(f"Executing LLM generated animation script for {ticker}...")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error executing graph script:\n{result.stderr}")
            return False
            
        print(f"Successfully generated animated graph: {save_path}")
        return True
        
    except Exception as e:
        print(f"Failed to generate animated graph: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 2:
        generate_animated_graph(sys.argv[1], sys.argv[2])
