import sqlite3
import pandas as pd
import google.generativeai as genai
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox, scrolledtext
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from fastapi import FastAPI
from pydantic import BaseModel
import threading
import uvicorn
import time
from dotenv import load_dotenv
import os
# -------------------- Configure Gemini API --------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-pro")

# -------------------- SQLite Connection --------------------
conn = sqlite3.connect("ecommerce.db", check_same_thread=False)

# -------------------- Prompt to SQL --------------------
def question_to_sql(prompt):
    full_prompt = f"""
You are a helpful assistant that generates SQL queries for an SQLite database.

Here is the database schema:

Table: AdSales
- date
- item_id
- ad_sales
- impressions
- ad_spend
- clicks
- units_sold

Table: TotalSales
- date
- item_id
- total_sales
- total_units_ordered

Table: Eligibility
- eligibility_datetime_utc
- item_id
- eligibility
- message

Question: "{prompt}"

Write a syntactically correct SQL query using only the columns above.
Only return the raw SQL query.
Do NOT use triple backticks or markdown formatting.
"""
    response = model.generate_content(full_prompt)
    sql = response.text.strip()
    if sql.startswith("```"):
        sql = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("```"))
    return sql.strip()

# -------------------- Execute SQL --------------------
def execute_sql(query):
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return pd.DataFrame(rows, columns=columns)
    except Exception as e:
        return f"Error: {e}"

# -------------------- GUI Plot --------------------
def clear_plot_frame():
    for widget in plot_frame.winfo_children():
        widget.destroy()

def plot_if_possible(df):
    clear_plot_frame()
    if isinstance(df, pd.DataFrame) and not df.empty:
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)

        if df.shape[1] == 2:
            x_col, y_col = df.columns
            if pd.api.types.is_numeric_dtype(df[y_col]):
                ax.plot(df[x_col].astype(str), df[y_col], color='blue', marker='o', linewidth=2)
                ax.set_title(f"{y_col} by {x_col}")
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
                ax.tick_params(axis='x', rotation=45)
                ax.grid(True, linestyle='--', alpha=0.5)
        elif df.shape[1] == 1 and pd.api.types.is_numeric_dtype(df.iloc[:, 0]):
            value = df.iloc[0, 0]
            label = df.columns[0]
            ax.plot([label], [value], color='red', marker='o')
            ax.set_title(label)

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack()

# -------------------- Typing Effect --------------------
def stream_insert(text):
    for char in text:
        result_text.insert(tk.END, char)
        result_text.see(tk.END)
        result_text.update()
        time.sleep(0.01)

# -------------------- GUI Ask Logic --------------------
def ask_question():
    question = question_entry.get()
    if not question.strip():
        messagebox.showwarning("Input Required", "Please enter a question.")
        return

    result_text.insert(tk.END, f"\n\n🔍 Question: {question}\n")
    result_text.update()

    sql_query = question_to_sql(question)
    stream_insert(f"🧠 SQL Query: {sql_query}\n")

    result = execute_sql(sql_query)
    if isinstance(result, pd.DataFrame):
        stream_insert("✅ Result:\n")
        stream_insert(result.to_string(index=False))
        plot_if_possible(result)
    else:
        stream_insert(f"❌ Error:\n{result}")
    question_entry.delete(0, tk.END)

# -------------------- GUI Setup --------------------
root = tk.Tk()
root.title("🛒 E-commerce SQL Chatbot")
root.geometry("800x600")
root.configure(bg="#f0f4f7")
root.resizable(True, True)

header_frame = tk.Frame(root, bg="#004c99")
header_frame.pack(fill=tk.X)

header_label = tk.Label(header_frame, text="🛒 E-commerce AI Agent",
                        font=("Times New Roman", 18, "bold"), bg="#004c99", fg="white", pady=10)
header_label.pack(side=tk.LEFT, padx=20)

close_button = tk.Button(header_frame, text="Close", font=("Times New Roman", 10, "bold"),
                         bg="#cc0000", fg="white", padx=10, pady=3, command=root.destroy)
close_button.pack(side=tk.RIGHT, padx=20, pady=10)

main_frame = tk.Frame(root, bg="#f0f4f7")
main_frame.pack(fill=tk.BOTH, expand=True)

input_frame = tk.Frame(main_frame, bg="#f0f4f7")
input_frame.pack(pady=10)

question_entry = tk.Entry(input_frame, font=("Times New Roman", 12), width=60, relief=tk.GROOVE, bd=4)
question_entry.pack(side=tk.LEFT, padx=10)

ask_button = tk.Button(input_frame, text="Ask", font=("Times New Roman", 11, "bold"),
                       bg="#cc0000", fg="white", command=ask_question, padx=15, pady=5)
ask_button.pack(side=tk.LEFT)

result_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, width=100, height=10,
                                        font=("Times New Roman", 10), relief=tk.SUNKEN, bd=2, bg="white")
result_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

plot_frame = tk.Frame(main_frame, bg="#f0f4f7", height=200)
plot_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=False)

# -------------------- FastAPI Setup --------------------
app = FastAPI(title="E-commerce SQL API with Gemini")

class QueryInput(BaseModel):
    question: str

@app.post("/ask")
def api_ask(data: QueryInput):
    sql = question_to_sql(data.question)
    result = execute_sql(sql)
    if isinstance(result, pd.DataFrame):
        return {
            "question": data.question,
            "sql": sql,
            "result": result.to_dict(orient="records")
        }
    else:
        return {
            "question": data.question,
            "sql": sql,
            "error": result
        }

# ✅ Root route to fix 404
@app.get("/")
def read_root():
    return {"message": "Welcome to the E-commerce SQL API. Use POST /ask with your question."}

# -------------------- Run FastAPI in Background Thread --------------------
def run_api():
    uvicorn.run(app, host="127.0.0.1", port=8000)

api_thread = threading.Thread(target=run_api, daemon=True)
api_thread.start()

# -------------------- Run GUI --------------------
root.mainloop()
