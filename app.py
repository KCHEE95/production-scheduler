import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统")

ITEMS_CSV = "items.csv"

if os.path.exists(ITEMS_CSV):
    items = pd.read_csv(ITEMS_CSV)
else:
    items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow', 'job_num', 'nesting_num'])

page = st.sidebar.selectbox("选择页面", ["🏠 总览 & 导入", "📋 部门视图"])

if page == "🏠 总览 & 导入":
    st.subheader("当前状态")
    st.metric("已导入 Subpart 数量", len(items))
    
    col1, col2 = st.columns([4, 1])
    with col1:
        uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])
    with col2:
        if st.button("🗑️ 清空所有数据"):
            if os.path.exists(ITEMS_CSV):
                os.remove(ITEMS_CSV)
            st.success("数据已清空！")
            st.rerun()

    if uploaded_file and len(items) == 0:
        # ... (保持你之前成功的导入代码，这里省略以节省空间，你可以保留之前导入部分的代码)
        pass   # 请把你之前能正常导入的导入逻辑粘贴在这里

    if len(items) > 0:
        st.dataframe(items[['main_part', 'subpart', 'job_num', 'nesting_num']].head(15), use_container_width=True)

elif page == "📋 部门视图":
    st.subheader("📋 部门视图 - 按部门或 Nesting Num 查看任务")
    
    # 提取所有部门和 Nesting Num
    all_depts = []
    all_nesting = items['nesting_num'].dropna().unique().tolist()
    
    for wf in items.get('workflow', []):
        try:
            steps = json.loads(wf)
            all_depts.extend([s['dept'] for s in steps])
        except:
            pass
    unique_depts = sorted(list(set(all_depts)))
    
    filter_type = st.radio("过滤方式", ["按部门过滤", "按 Nesting Num 过滤"])
    
    if filter_type == "按部门过滤":
        selected_dept = st.selectbox("选择部门", unique_depts)
        filter_value = selected_dept
        filter_column = 'dept'
    else:
        selected_nesting = st.selectbox("选择 Nesting Num", all_nesting)
        filter_value = selected_nesting
        filter_column = 'nesting_num'
    
    # 筛选任务
    tasks = []
    for _, item in items.iterrows():
        try:
            workflow = json.loads(item['workflow'])
            match = False
            if filter_column == 'dept':
                match = any(s['dept'] == filter_value for s in workflow)
            else:
                match = str(item.get('nesting_num', '')) == str(filter_value)
            
            if match:
                tasks.append({
                    'item_id': item['item_id'],
                    'job_num': item.get('job_num', ''),
                    'nesting_num': item.get('nesting_num', ''),
                    'main_part': item['main_part'],
                    'subpart': item['subpart'],
                    'status': 'pending'
                })
        except:
            pass
    
    if tasks:
        task_df = pd.DataFrame(tasks)
        st.dataframe(task_df, use_container_width=True)
    else:
        st.info(f"没有找到匹配的任务。")

st.sidebar.caption("已支持按部门或 Nesting Num 过滤")
