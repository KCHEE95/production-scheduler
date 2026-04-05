import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

# ====================== 初始化 ======================
if 'items' not in st.session_state:
    st.session_state.items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'customer_po', 
                                                   'order_date', 'exwork_date', 'qty', 'workflow'])

if 'progress' not in st.session_state:
    st.session_state.progress = pd.DataFrame(columns=['item_id', 'dept', 'status', 'arrival_time', 
                                                      'actual_completion', 'delay_days'])

def save_data():
    st.session_state.items.to_csv('items.csv', index=False)
    st.session_state.progress.to_csv('progress.csv', index=False)

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
        return last.get('actual_completion', '')[:16] if pd.notna(last.get('actual_completion')) else "已完成"
    return "计算中..."

# ====================== 主界面 ======================
st.title("🏭 K.K. Metal AI 自动排产系统（测试版）")

uploaded_file = st.file_uploader("📤 上传您的 Epicor Excel 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在读取 Excel（header 从第6行开始）..."):
        try:
            # 关键：使用 header=5，并跳过前几行空行
            df = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=5)
            
            # 清理空行
            df = df.dropna(how='all').reset_index(drop=True)
            
            new_items = []
            new_progress = []
            
            for _, row in df.iterrows():
                main_part = str(row.get('Main Part Num', '')).strip()
                subpart = str(row.get('Subpart Part Num', '')).strip()
                
                if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                    continue
                
                item_id = f"{main_part}_{subpart}"
                
                # 安全检查是否已存在
                if not st.session_state.items.empty and item_id in st.session_state.items['item_id'].values:
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
                    'actual_completion': None,
                    'delay_days': 0
                })
            
            if new_items:
                st.session_state.items = pd.concat([st.session_state.items, pd.DataFrame(new_items)], ignore_index=True)
                st.session_state.progress = pd.concat([st.session_state.progress, pd.DataFrame(new_progress)], ignore_index=True)
                save_data()
                st.success(f"🎉 成功导入 **{len(new_items)}** 个 Subpart！")
                st.rerun()
            else:
                st.warning("未找到有效数据。请确认 Excel 文件的 header 是否在第 6 行左右。")
                
        except Exception as e:
            st.error(f"导入失败: {str(e)}")
            st.info("提示：您的 Excel 第1行是公司名，header 在第6行，这是正常的。我们已尝试处理。")

# ====================== 显示统计 ======================
st.subheader("当前数据统计")
col1, col2 = st.columns(2)
with col1:
    st.metric("已导入 Subpart 数量", len(st.session_state.items))
with col2:
    st.metric("进行中项目", len(st.session_state.progress))

if not st.session_state.items.empty:
    st.dataframe(st.session_state.items[['main_part', 'subpart', 'customer_po']].head(10), use_container_width=True)

st.caption("测试版：目前只完成导入功能。导入成功后我再帮您加上部门视图和仪表板。")
