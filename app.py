import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

# ====================== 初始化 ======================
if 'items' not in st.session_state:
    st.session_state.items = pd.DataFrame(columns=['item_id','main_part','subpart','customer_po',
                                                   'order_date','exwork_date','qty','workflow'])

if 'progress' not in st.session_state:
    st.session_state.progress = pd.DataFrame(columns=['item_id','dept','status','arrival_time',
                                                      'actual_completion','delay_days'])

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
    with st.spinner("正在读取 Excel（header 从第6行开始）..."):
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
                
                # 最保守的检查：避免任何 len() 和 .empty
                already_exists = False
                if 'item_id' in st.session_state.items.columns and len(st.session_state.items) > 0:
                    already_exists = item_id in st.session_state.items['item_id'].values
                
                if already_exists:
                    continue
                
                workflow = parse_workflow(row)
                if not workflow:
                    continue
                
                # 添加新 item
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
                
                # 自动进入第一个部门
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
            st.info("如果一直失败，请把完整错误信息发给我。")

# ====================== 显示状态 ======================
st.subheader("当前导入状态")
item_count = len(st.session_state.items) if 'item_id' in st.session_state.items.columns else 0
st.write(f"已导入 Subpart 数量：**{item_count}**")

if item_count > 0:
    st.dataframe(st.session_state.items[['main_part', 'subpart', 'customer_po']].head(10), use_container_width=True)
else:
    st.info("请上传您的 Epicor Excel 文件进行测试。")

st.caption("极简测试版 | 只测试导入功能 | 如导入成功，我会马上帮您加上完整功能")
