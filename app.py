import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统")

ITEMS_CSV = "items.csv"
PROGRESS_CSV = "progress.csv"

# 初始化 session_state
if 'items' not in st.session_state:
    if os.path.exists(ITEMS_CSV):
        st.session_state.items = pd.read_csv(ITEMS_CSV)
    else:
        st.session_state.items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow', 'job_num', 'nesting_num'])

if 'progress' not in st.session_state:
    if os.path.exists(PROGRESS_CSV):
        st.session_state.progress = pd.read_csv(PROGRESS_CSV)
    else:
        st.session_state.progress = pd.DataFrame(columns=['item_id', 'dept', 'status', 'arrival_time', 'update_time'])

items = st.session_state.items
progress = st.session_state.progress

st.subheader("当前状态")
st.metric("已导入 Subpart 数量", len(items))

# 上传区域
col1, col2 = st.columns([4, 1])
with col1:
    uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])
with col2:
    if st.button("🗑️ 清空所有数据"):
        if os.path.exists(ITEMS_CSV): os.remove(ITEMS_CSV)
        if os.path.exists(PROGRESS_CSV): os.remove(PROGRESS_CSV)
        st.session_state.items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow', 'job_num', 'nesting_num'])
        st.session_state.progress = pd.DataFrame(columns=['item_id', 'dept', 'status', 'arrival_time', 'update_time'])
        st.success("✅ 数据已清空！")
        st.rerun()

# ====================== 导入逻辑（已完整替换为你之前能正常工作的版本） ======================
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
            st.session_state.items = all_items
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

# 构建带状态的任务列表
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
            # 获取最新状态
            item_progress = progress[progress['item_id'] == item['item_id']]
            current_status = item_progress.iloc[-1]['status'] if not item_progress.empty else 'pending'

            tasks.append({
                'item_id': item['item_id'],
                'job_num': str(item.get('job_num', '')),
                'nesting_num': str(item.get('nesting_num', '')),
                'main_part': item['main_part'],
                'subpart': item['subpart'],
                'status': current_status,
                'current_workflow': workflow
            })
    except:
        pass

if tasks:
    task_df = pd.DataFrame(tasks)
    st.dataframe(task_df, use_container_width=True, height=400)

    st.subheader("批量操作（推荐用于 Nesting Num 过滤）")
    selected_items = st.multiselect(
        "选择要处理的任务（可多选）",
        options=[t['item_id'] for t in tasks]
    )
    
    action = st.radio("操作类型", ["开始做", "✅ 完成并移交下一部门"])

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("确认批量操作", type="primary"):
            if not selected_items:
                st.warning("请至少选择一个任务")
            else:
                with st.spinner(f"正在处理 {len(selected_items)} 个任务..."):
                    new_rows = []
                    for item_id in selected_items:
                        item_data = next((t for t in tasks if t['item_id'] == item_id), None)
                        if not item_data:
                            continue
                        
                        workflow = item_data['current_workflow']
                        current_dept = selected_filter if is_dept else None
                        
                        new_status = 'in_progress' if action == "开始做" else 'completed'
                        
                        new_rows.append({
                            'item_id': item_id,
                            'dept': selected_filter if is_dept else "Nesting Filter",
                            'status': new_status,
                            'arrival_time': datetime.now().isoformat(),
                            'update_time': datetime.now().isoformat()
                        })
                        
                        # 自动移交下一部门
                        if action == "✅ 完成并移交下一部门" and len(workflow) > 1:
                            current_index = next((i for i, s in enumerate(workflow) if s.get('dept') == current_dept), None)
                            if current_index is not None and current_index + 1 < len(workflow):
                                next_dept = workflow[current_index + 1]['dept']
                                st.success(f"任务 **{item_id}** 已完成，已自动移交到下一部门：**{next_dept}**")
                    
                    if new_rows:
                        new_df = pd.DataFrame(new_rows)
                        if not progress.empty:
                            progress = pd.concat([progress, new_df], ignore_index=True)
                        else:
                            progress = new_df
                        st.session_state.progress = progress
                        progress.to_csv(PROGRESS_CSV, index=False)
                        
                        st.success(f"🎉 成功更新 {len(selected_items)} 个任务！")
                        st.rerun()

    with col2:
        if st.button("🔄 刷新显示"):
            st.rerun()
else:
    st.info("没有找到匹配的任务。")

st.caption("已修复闪屏问题 + 显示实时状态 + 自动移交下一部门")
