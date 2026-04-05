import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 部门视图版")

ITEMS_CSV = "items.csv"
PROGRESS_CSV = "progress.csv"

# 加载数据
if os.path.exists(ITEMS_CSV):
    items = pd.read_csv(ITEMS_CSV)
else:
    items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow'])

if os.path.exists(PROGRESS_CSV):
    progress = pd.read_csv(PROGRESS_CSV)
else:
    progress = pd.DataFrame(columns=['item_id', 'dept', 'status', 'arrival_time', 'start_time', 'complete_time'])

# Sidebar 导航
page = st.sidebar.selectbox("选择页面", 
    ["🏠 总览", "📋 部门视图", "📊 经理仪表板", "🔍 Sales 查询", "⚙️ 设置"])

# ====================== 总览页面 ======================
if page == "🏠 总览":
    st.subheader("当前状态")
    st.metric("已导入 Subpart 数量", len(items))
    
    if len(items) > 0:
        st.dataframe(items[['main_part', 'subpart', 'qty']].head(10), use_container_width=True)

# ====================== 部门视图 ======================
elif page == "📋 部门视图":
    st.subheader("部门视图")
    
    # 获取所有部门
    all_depts = []
    for wf in items['workflow']:
        try:
            steps = json.loads(wf)
            all_depts.extend([s['dept'] for s in steps])
        except:
            pass
    unique_depts = sorted(list(set(all_depts)))
    
    selected_dept = st.selectbox("选择部门", unique_depts)
    
    # 显示该部门待处理的任务
    dept_tasks = []
    for _, item in items.iterrows():
        try:
            workflow = json.loads(item['workflow'])
            for step in workflow:
                if step['dept'] == selected_dept:
                    # 检查当前状态
                    current_status = "pending"
                    task_progress = progress[progress['item_id'] == item['item_id']]
                    if not task_progress.empty:
                        latest = task_progress.iloc[-1]
                        current_status = latest['status']
                    
                    dept_tasks.append({
                        'item_id': item['item_id'],
                        'main_part': item['main_part'],
                        'subpart': item['subpart'],
                        'status': current_status
                    })
                    break
        except:
            pass
    
    if dept_tasks:
        dept_df = pd.DataFrame(dept_tasks)
        st.dataframe(dept_df, use_container_width=True)
        
        # 更新状态
        selected_item = st.selectbox("选择要更新的任务", dept_df['item_id'])
        action = st.radio("操作", ["开始做", "完成并移交下一部门"])
        
        if st.button("确认操作"):
            # 更新 progress
            new_progress = pd.DataFrame([{
                'item_id': selected_item,
                'dept': selected_dept,
                'status': 'in_progress' if action == "开始做" else 'completed',
                'arrival_time': datetime.now().isoformat(),
                'start_time': datetime.now().isoformat() if action == "开始做" else None,
                'complete_time': datetime.now().isoformat() if action == "完成并移交下一部门" else None
            }])
            
            global_progress = pd.concat([progress, new_progress], ignore_index=True) if not progress.empty else new_progress
            global_progress.to_csv(PROGRESS_CSV, index=False)
            
            st.success(f"已更新 {selected_item} 为 {action}")
            st.rerun()
    else:
        st.info(f"部门 {selected_dept} 目前没有待处理任务。")

# ====================== 其他页面占位 ======================
else:
    st.info("该页面正在开发中...")

st.sidebar.caption("当前版本：部门视图已可用")
