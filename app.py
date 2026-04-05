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
    items = pd.read_csv(ITEMS_CSV)
else:
    items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow'])

if os.path.exists(PROGRESS_CSV):
    progress = pd.read_csv(PROGRESS_CSV)
else:
    progress = pd.DataFrame(columns=['item_id', 'dept', 'status', 'arrival_time'])

# 侧边栏
page = st.sidebar.selectbox("选择页面", ["🏠 总览 & 导入", "📋 部门视图"])

# ====================== 总览 & 导入 ======================
if page == "🏠 总览 & 导入":
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

    if uploaded_file:
        if len(items) > 0:
            st.warning("⚠️ 已存在数据。请先清空后再导入。")
        else:
            with st.spinner("正在导入..."):
                try:
                    df_raw = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=None)
                    header_idx = 5
                    df = df_raw.iloc[header_idx + 1:].reset_index(drop=True)
                    df.columns = df_raw.iloc[header_idx]
                    
                    df = df.dropna(how='all').reset_index(drop=True)
                    df = df.dropna(thresh=3).reset_index(drop=True)
                    
                    all_items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow'])
                    current_main = None
                    
                    main_col = sub_col = None
                    for c_idx, col_name in enumerate(df.columns):
                        col_str = str(col_name).strip() if pd.notna(col_name) else ""
                        if col_str == "Main Part Num":
                            main_col = c_idx
                        if col_str == "Subpart Part Num":
                            sub_col = c_idx
                    
                    for _, row in df.iterrows():
                        main_candidate = str(row.iloc[main_col]).strip() if pd.notna(row.iloc[main_col]) else ''
                        sub_candidate = str(row.iloc[sub_col]).strip() if pd.notna(row.iloc[sub_col]) else ''
                        
                        if main_candidate and main_candidate.lower() != 'nan':
                            current_main = main_candidate
                        
                        if sub_candidate and sub_candidate.lower() != 'nan' and current_main:
                            item_id = f"{current_main}_{sub_candidate}"
                            
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
                                'workflow': json.dumps(workflow)
                            }])
                            all_items = pd.concat([all_items, new_row], ignore_index=True)
                    
                    all_items.to_csv(ITEMS_CSV, index=False)
                    st.success(f"🎉 成功导入 {len(all_items)} 个 Subpart！")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"导入失败: {str(e)}")

    if len(items) > 0:
        st.dataframe(items[['main_part', 'subpart']].head(15), use_container_width=True)

# ====================== 部门视图 ======================
elif page == "📋 部门视图":
    st.subheader("📋 部门视图 - 按部门查看待处理任务")
    
    # 提取所有部门
    all_depts = []
    for wf in items.get('workflow', []):
        try:
            steps = json.loads(wf)
            all_depts.extend([s['dept'] for s in steps])
        except:
            pass
    unique_depts = sorted(list(set(all_depts)))
    
    if not unique_depts:
        st.info("请先在【总览 & 导入】页面上传 Excel 文件")
    else:
        selected_dept = st.selectbox("选择你的部门", unique_depts)
        
        # 筛选该部门的任务
        tasks = []
        for _, item in items.iterrows():
            try:
                workflow = json.loads(item['workflow'])
                for step in workflow:
                    if step['dept'] == selected_dept:
                        tasks.append({
                            'item_id': item['item_id'],
                            'main_part': item['main_part'],
                            'subpart': item['subpart'],
                            'status': 'pending'
                        })
                        break
            except:
                pass
        
        if tasks:
            task_df = pd.DataFrame(tasks)
            st.dataframe(task_df, use_container_width=True)
            
            selected_item = st.selectbox("选择要处理的任务", task_df['item_id'].tolist())
            action = st.radio("操作", ["开始做", "✅ 完成并移交下一部门"])
            
            if st.button("确认操作"):
                st.success(f"已更新 {selected_item} 为 {action}")
                st.info("（状态更新功能正在开发中，下一步会加上自动移交）")
                st.rerun()
        else:
            st.info(f"部门 **{selected_dept}** 目前没有待处理任务。")

st.sidebar.caption("当前版本：导入 + 部门视图")
