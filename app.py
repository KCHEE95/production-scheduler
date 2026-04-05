import streamlit as st
import pandas as pd
from datetime import datetime
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
        col = f"Step {i}" if f"Step {i}" in row else f"Step{i}"
        step = str(row.get(col, "")).strip()
        if step and step.lower() != "nan" and step != "":
            workflow.append({"dept": step, "est_hours": 8.0})
    return workflow

# ====================== 主界面 ======================
st.title("🏭 K.K. Metal AI 自动排产系统 - 测试版")

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在读取 Excel（header=5）..."):
        try:
            df = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=5)
            df = df.dropna(how='all').reset_index(drop=True)
            
            new_count = 0
            
            for _, row in df.iterrows():
                main_part = str(row.get('Main Part Num', '')).strip()
                subpart = str(row.get('Subpart Part Num', '')).strip()
                if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                    continue
                
                item_id = f"{main_part}_{subpart}"
                
                # 最保守的检查方式
                if len(st.session_state.items) > 0 and 'item_id' in st.session_state.items.columns:
                    if item_id in st.session_state.items['item_id'].values:
                        continue
                
                workflow = parse_workflow(row)
                if not workflow:
                    continue
                
                new_row = pd.DataFrame([{
                    'item_id': item_id,
                    'main_part': main_part,
                    'subpart': subpart,
                    'customer_po': str(row.get('PO - POLine', '')),
                    'order_date': str(row.get('Order Date', '')),
                    'exwork_date': str(row.get('Exwork Date', '')),
                    'qty': float(row.get('Subpart Qty', 0) or 0),
                    'workflow': json.dumps(workflow)
                }])
                
                st.session_state.items = pd.concat([st.session_state.items, new_row], ignore_index=True)
                
                first_dept = workflow[0]['dept']
                prog_row = pd.DataFrame([{
                    'item_id': item_id,
                    'dept': first_dept,
                    'status': 'pending',
                    'arrival_time': datetime.now().isoformat(),
                    'actual_completion': None,
                    'delay_days': 0
                }])
                st.session_state.progress = pd.concat([st.session_state.progress, prog_row], ignore_index=True)
                
                new_count += 1
            
            save_data()
            st.success(f"🎉 成功导入 **{new_count}** 个 Subpart！")
            st.rerun()
            
        except Exception as e:
            st.error(f"导入失败: {str(e)}")

# ====================== 显示状态 ======================
st.subheader("当前导入状态")
if len(st.session_state.items) == 0:
    st.info("尚未导入任何数据。请上传 Excel 文件测试。")
else:
    st.success(f"已成功导入 **{len(st.session_state.items)}** 个 Subpart")
    st.dataframe(st.session_state.items[['main_part', 'subpart', 'customer_po']].head(10), use_container_width=True)

st.caption("测试版 | 只测试导入功能 | 如导入成功，我会马上帮您加上完整部门视图")
