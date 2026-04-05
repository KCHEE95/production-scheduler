import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

# ====================== 初始化 ======================
if 'items' not in st.session_state:
    st.session_state.items = pd.DataFrame()

if 'progress' not in st.session_state:
    st.session_state.progress = pd.DataFrame()

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
                
                # 最保守检查：直接尝试访问，避免属性错误
                already_exists = False
                try:
                    if not st.session_state.items.empty and 'item_id' in st.session_state.items.columns:
                        already_exists = item_id in st.session_state.items['item_id'].values
                except:
                    already_exists = False
                
                if already_exists:
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
try:
    item_count = len(st.session_state.items) if not st.session_state.items.empty else 0
except:
    item_count = 0

st.write(f"已导入 Subpart 数量：**{item_count}**")

if item_count > 0:
    try:
        st.dataframe(st.session_state.items[['main_part', 'subpart']].head(10), use_container_width=True)
    except:
        st.write("数据已导入，但显示出现小问题。")
else:
    st.info("请上传您的 Epicor Excel 文件进行测试。")

st.caption("超级保守测试版 | 已尽量避免所有属性错误")
