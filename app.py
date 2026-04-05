import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 测试版")

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在强力解析你的 Excel（已处理合并单元格和空列）..."):
        try:
            # 读取时跳过前5行，使用第6行作为列名
            df = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=5)
            df = df.dropna(how='all').reset_index(drop=True)
            
            new_count = 0
            added = []
            
            for _, row in df.iterrows():
                main_part = str(row.get('Main Part Num', '')).strip()
                subpart = str(row.get('Subpart Part Num', '')).strip()
                
                if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                    continue
                
                item_id = f"{main_part}_{subpart}"
                
                # === 强力解析 Step（按列位置 + 容错合并单元格）===
                workflow = []
                # 尝试从 Step 1 到 Step 20 抓取（容错空列和合并）
                for i in range(1, 21):
                    col_name = f"Step {i}"
                    step = str(row.get(col_name, "")).strip()
                    if step and step.lower() != "nan" and step != "":
                        workflow.append({"dept": step, "est_hours": 8.0})
                
                # 如果 Step 抓取失败，尝试从右边扫描非空单元格（应对合并和空列）
                if len(workflow) < 3:
                    workflow = []
                    for col_idx in range(len(row)-1, 10, -1):   # 从右往左扫描
                        cell = str(row.iloc[col_idx]).strip()
                        if cell and cell.lower() != 'nan' and cell != '' and len(cell) > 2:
                            workflow.insert(0, {"dept": cell, "est_hours": 8.0})
                
                if len(workflow) == 0:
                    continue
                
                # 添加 item
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
                
                if 'items' not in st.session_state or st.session_state.items.empty:
                    st.session_state.items = new_row
                else:
                    st.session_state.items = pd.concat([st.session_state.items, new_row], ignore_index=True)
                
                # 自动进入第一个步骤
                first_dept = workflow[0]['dept']
                prog_row = pd.DataFrame([{
                    'item_id': item_id,
                    'dept': first_dept,
                    'status': 'pending',
                    'arrival_time': datetime.now().isoformat()
                }])
                
                if 'progress' not in st.session_state or st.session_state.progress.empty:
                    st.session_state.progress = prog_row
                else:
                    st.session_state.progress = pd.concat([st.session_state.progress, prog_row], ignore_index=True)
                
                new_count += 1
                added.append(item_id)
            
            if new_count > 0:
                st.success(f"🎉 **成功导入 {new_count} 个 Subpart！**")
                st.write("示例:", added[:5])
            else:
                st.error("仍然未能解析出 Subpart。请把 Excel 文件前 30 行完整截图发给我。")
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")

st.subheader("当前状态")
count = len(st.session_state.get('items', pd.DataFrame()))
st.write(f"已导入 Subpart 数量： **{count}**")

if count > 0:
    st.dataframe(st.session_state.items[['main_part', 'subpart']].head(10), use_container_width=True)

st.caption("已针对合并单元格和空列进行优化")
