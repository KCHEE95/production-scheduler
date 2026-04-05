import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统")

ITEMS_CSV = "items.csv"
PROGRESS_CSV = "progress.csv"

# 加载数据
if os.path.exists(ITEMS_CSV):
    try:
        items = pd.read_csv(ITEMS_CSV)
    except:
        items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow', 'job_num', 'nesting_num'])
else:
    items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow', 'job_num', 'nesting_num'])

if os.path.exists(PROGRESS_CSV):
    try:
        progress = pd.read_csv(PROGRESS_CSV)
    except:
        progress = pd.DataFrame(columns=['item_id', 'dept', 'status', 'arrival_time'])
else:
    progress = pd.DataFrame(columns=['item_id', 'dept', 'status', 'arrival_time'])

st.subheader("当前状态")
st.metric("已导入 Subpart 数量", len(items))

col1, col2 = st.columns([4, 1])
with col1:
    uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])
with col2:
    if st.button("🗑️ 清空所有数据"):
        if os.path.exists(ITEMS_CSV): os.remove(ITEMS_CSV)
        if os.path.exists(PROGRESS_CSV): os.remove(PROGRESS_CSV)
        st.success("数据已清空！")
        st.rerun()

if uploaded_file and len(items) == 0:
    with st.spinner("正在导入..."):
        try:
            df_raw = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=None)
            header_idx = 5
            df = df_raw.iloc[header_idx + 1:].reset_index(drop=True)
            df.columns = df_raw.iloc[header_idx]
            
            df = df.dropna(how='all').reset_index(drop=True)
            df = df.dropna(thresh=3).reset_index(drop=True)
            
            all_items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow', 'job_num', 'nesting_num'])
            current_main = None
            
            main_col = sub_col = job_col = nesting_col = None
            for c_idx, col_name in enumerate(df.columns):
                col_str = str(col_name).strip() if pd.notna(col_name) else ""
                if col_str == "Main Part Num":
                    main_col = c_idx
                if col_str == "Subpart Part Num":
                    sub_col = c_idx
                if "JobNum/Asm" in col_str:
                    job_col = c_idx
                if "Nesting Num" in col_str:
                    nesting_col = c_idx
            
            for _, row in df.iterrows():
                main_candidate = str(row.iloc[main_col]).strip() if pd.notna(row.iloc[main_col]) else ''
                sub_candidate = str(row.iloc[sub_col]).strip() if pd.notna(row.iloc[sub_col]) else ''
                
                if main_candidate and main_candidate.lower() != 'nan':
                    current_main = main_candidate
                
                if sub_candidate and sub_candidate.lower() != 'nan' and current_main:
                    item_id = f"{current_main}_{sub_candidate}"
                    job_num = str(row.iloc[job_col]).strip() if job_col is not None else ''
                    nesting_num = str(row.iloc[nesting_col]).strip().replace('.0', '') if nesting_col is not None else ''
                    
                    workflow = []
                    for i in range(1, 21):
                        col_name = f"Step {i}"
                        if col_name in df.columns:
                            step = str(row.get(col_name, "")).strip()
                            if step and step.lower() != "nan" and step != "":
                                workflow.append({"dept": step, "est_hours": 8.0})
                    
                    if len(workflow) < 3:
                        workflow = []
                        for col_idx in range(len(row)-1, 10, -1):
                            cell = str(row.iloc[col_idx]).strip()
                            if cell and cell.lower() != 'nan' and cell != '' and len(cell) > 2:
                                if not any(x in cell for x in ['/2026', '4501', 'New Awarded', 'Normal', 'No Job']):
                                    workflow.insert(0, {"dept": cell, "est_hours": 8.0})
                    
                    if len(workflow) == 0:
                        continue
                    
                    new_row = pd.DataFrame([{
                        'item_id': item_id,
                        'main_part': current_main,
                        'subpart': sub_candidate,
                        'qty': 1,
                        'workflow': json.dumps(workflow),
                        'job_num': job_num,
                        'nesting_num': nesting_num
                    }])
                    all_items = pd.concat([all_items, new_row], ignore_index=True)
            
            all_items.to_csv(ITEMS_CSV, index=False)
            st.success(f"🎉 成功导入 {len(all_items)} 个 Subpart！")
            st.rerun()
            
        except Exception as e:
            st.error(f"导入失败: {str(e)}")

# ====================== 部门视图 ======================
st.subheader("📋 部门视图 - 按部门或 Nesting Num 查看任务")

all_depts = []
for wf in items.get('workflow', []):
    try:
        steps = json.loads(wf)
        all_depts.extend([s['dept'] for s in steps])
    except:
        pass
unique_depts = sorted(list(set(all_depts)))

filter_mode = st.radio("过滤方式", ["按部门过滤", "按 Nesting Num 过滤"])

if filter_mode == "按部门过滤":
    selected_filter = st.selectbox("选择部门", unique_depts)
    is_dept = True
else:
    all_nesting = sorted(set(str(x).strip().replace('.0', '').replace(' ', '') for x in items['nesting_num'].dropna() if str(x).strip() != ''))
    selected_filter = st.selectbox("选择 Nesting Num", all_nesting)
    is_dept = False

# 筛选任务
tasks = []
for _, item in items.iterrows():
    try:
        workflow = json.loads(item['workflow'])
        match = False
        
        if is_dept:
            match = any(s['dept'] == selected_filter for s in workflow)
        else:
            item_nesting = str(item.get('nesting_num', '')).strip().replace('.0', '').replace(' ', '')
            filter_nesting = str(selected_filter).strip().replace('.0', '').replace(' ', '')
            match = item_nesting == filter_nesting
        
        if match:
            tasks.append({
                'item_id': item['item_id'],
                'job_num': str(item.get('job_num', '')),
                'nesting_num': str(item.get('nesting_num', '')),
                'main_part': item['main_part'],
                'subpart': item['subpart'],
                'status': 'pending'
            })
    except:
        pass

if tasks:
    task_df = pd.DataFrame(tasks)
    st.dataframe(task_df, use_container_width=True)
    
    selected_item = st.selectbox("选择要处理的任务", task_df['item_id'].tolist())
    action = st.radio("操作", ["开始做", "✅ 完成并移交下一部门"])
    
    if st.button("确认操作"):
        new_status = 'in_progress' if action == "开始做" else 'completed'
        new_row = pd.DataFrame([{
            'item_id': selected_item,
            'dept': selected_filter if is_dept else "Nesting Filter",
            'status': new_status,
            'arrival_time': datetime.now().isoformat()
        }])
        
        if not progress.empty:
            progress = pd.concat([progress, new_row], ignore_index=True)
        else:
            progress = new_row
        progress.to_csv(PROGRESS_CSV, index=False)
        
        st.success(f"✅ 已更新 {selected_item} 为 {action}")
        if action == "✅ 完成并移交下一部门":
            st.info("任务已完成并移交下一部门（下一版本会自动处理）")
        st.rerun()
else:
    st.info(f"没有找到匹配的任务。")

st.caption("已支持 JobNum / Nesting Num + 状态更新")
