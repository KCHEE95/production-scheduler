import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import time
import threading

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

# ====================== 初始化 ======================
if 'depts' not in st.session_state:
    unique_depts = [
        '2-LCMARK', '2-NP-A', '2-PK-A', 'ASSY-A', 'C-SAW', 'D-CSK', 'D-DRL', 'D-TAP-A',
        'E-CR', 'F-CAN1', 'F-CEP1', 'F-CZN6', 'F-INK', 'F-NAL2', 'F-NPV1', 'F-PT',
        'M-BD', 'M-LC-CO2', 'M-LC-FBR', 'M-PC', 'N-LT', 'N-MC', 'P-BF', 'P-DB',
        'P-DGR', 'P-DMK-A', 'P-FL', 'P-GRD', 'P-MK-A', 'P-PCKLNG', 'P-SB', 'P-TU-A',
        'Q-LKT', 'W-CDS-A', 'W-LWD', 'W-MIG', 'W-R-MIG', 'W-SWD-A', 'W-TIG'
    ]
    st.session_state.depts = pd.DataFrame({
        'dept_code': unique_depts,
        'name': unique_depts,
        'daily_capacity_hours': [10.5] * len(unique_depts)
    })

if 'items' not in st.session_state:
    st.session_state.items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'customer_po', 'order_date', 'exwork_date', 'qty', 'workflow'])

if 'progress' not in st.session_state:
    st.session_state.progress = pd.DataFrame(columns=['item_id', 'dept', 'status', 'arrival_time', 'start_time', 'actual_completion', 'delay_days'])

def load_data():
    if os.path.exists('items.csv'):
        st.session_state.items = pd.read_csv('items.csv')
    if os.path.exists('progress.csv'):
        st.session_state.progress = pd.read_csv('progress.csv')
    if os.path.exists('depts.csv'):
        st.session_state.depts = pd.read_csv('depts.csv')

load_data()

def save_data():
    st.session_state.items.to_csv('items.csv', index=False)
    st.session_state.progress.to_csv('progress.csv', index=False)
    st.session_state.depts.to_csv('depts.csv', index=False)

def parse_workflow(row):
    workflow = []
    for i in range(1, 21):
        col_name = f"Step {i}" if f"Step {i}" in row else f"Step{i}"
        step = str(row.get(col_name, "")).strip()
        if step and step.lower() != "nan" and step != "":
            workflow.append({"dept": step, "est_hours": 8.0})
    return workflow

def calculate_eta(item_id):
    progress = st.session_state.progress[st.session_state.progress['item_id'] == item_id]
    if progress.empty:
        return "待处理"
    last = progress.iloc[-1]
    if last['status'] == 'completed':
        return last['actual_completion'][:16]
    
    delay = float(last.get('delay_days', 0) or 0)
    dept = last['dept']
    
    pending = st.session_state.progress[
        (st.session_state.progress['dept'] == dept) & 
        (st.session_state.progress['status'] != 'completed')
    ]
    
    total_hours = 0.0
    for _, p in pending.iterrows():
        item_row = st.session_state.items[st.session_state.items['item_id'] == p['item_id']]
        if not item_row.empty:
            wf = json.loads(item_row.iloc[0]['workflow'])
            for step in wf:
                if step['dept'] == dept:
                    total_hours += step['est_hours']
                    break
    
    capacity = 10.5
    dept_row = st.session_state.depts[st.session_state.depts['dept_code'] == dept]
    if not dept_row.empty:
        capacity = float(dept_row.iloc[0]['daily_capacity_hours'])
    
    days_needed = (total_hours / capacity) + delay
    eta_date = datetime.now() + timedelta(days=days_needed)
    return eta_date.strftime("%Y-%m-%d")

# ====================== 导入页面（关键修复） ======================
st.title("从 Epicor 导入生产数据")
uploaded_file = st.file_uploader("上传 BAQ Report-JobStatByCust3 ASM.xlsx", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在解析 Excel 文件，请稍等..."):
        try:
            df = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=5)
            new_items = []
            new_progress = []
            
            for _, row in df.iterrows():
                main_part = str(row.get('Main Part Num', '')).strip()
                subpart = str(row.get('Subpart Part Num', '')).strip()
                if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                    continue
                
                item_id = f"{main_part}_{subpart}"
                
                # 关键修复：安全检查是否为空
                if len(st.session_state.items) > 0 and item_id in st.session_state.items['item_id'].values:
                    continue
                
                workflow = parse_workflow(row)
                if not workflow:
                    continue
                
                new_items.append({
                    'item_id': item_id,
                    'main_part': main_part,
                    'subpart': subpart,
                    'customer_po': str(row.get('PO - POLine', '')),
                    'order_date': str(row.get('Order Date', '')),
                    'exwork_date': str(row.get('Exwork Date', '')),
                    'qty': float(row.get('Subpart Qty', 0) or 0),
                    'workflow': json.dumps(workflow)
                })
                
                first_dept = workflow[0]['dept']
                new_progress.append({
                    'item_id': item_id,
                    'dept': first_dept,
                    'status': 'pending',
                    'arrival_time': datetime.now().isoformat(),
                    'start_time': None,
                    'actual_completion': None,
                    'delay_days': 0
                })
            
            if new_items:
                st.session_state.items = pd.concat([st.session_state.items, pd.DataFrame(new_items)], ignore_index=True)
                st.session_state.progress = pd.concat([st.session_state.progress, pd.DataFrame(new_progress)], ignore_index=True)
                save_data()
                st.success(f"✅ 成功导入 {len(new_items)} 个 Subpart！")
                st.rerun()
            else:
                st.warning("未找到有效数据，请检查Excel格式。")
                
        except Exception as e:
            st.error(f"导入失败: {str(e)}")

st.sidebar.title("K.K. Metal AI排产系统")
st.sidebar.caption("已加强空DataFrame防护 | 每个步骤固定8小时")
