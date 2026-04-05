import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 终极调试版")

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在读取并调试解析 Excel..."):
        try:
            df = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=5)
            df = df.dropna(how='all').reset_index(drop=True)
            
            new_count = 0
            debug = []
            
            for idx, row in df.iterrows():
                main_part = str(row.get('Main Part Num', '')).strip()
                subpart = str(row.get('Subpart Part Num', '')).strip()
                
                if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                    continue
                
                item_id = f"{main_part}_{subpart}"
                
                # === 调试输出：看看这一行有哪些非空列 ===
                non_empty = []
                for col_idx in range(len(row)):
                    cell = str(row.iloc[col_idx]).strip()
                    if cell and cell.lower() != 'nan' and cell != '':
                        non_empty.append(f"Col{col_idx}: {cell}")
                
                debug.append(f"Row {idx} - Main: {main_part}, Sub: {subpart}, Non-empty cells: {len(non_empty)}")
                
                # 强力抓取 Step（从右往左）
                workflow = []
                for col_idx in range(len(row)-1, 5, -1):
                    cell = str(row.iloc[col_idx]).strip()
                    if cell and cell.lower() != 'nan' and cell != '' and len(cell) > 2:
                        workflow.insert(0, {"dept": cell, "est_hours": 8.0})
                
                if len(workflow) == 0:
                    debug.append(f"Row {idx} - No workflow found")
                    continue
                
                debug.append(f"Row {idx} - Found {len(workflow)} steps: { [s['dept'] for s in workflow[:5]] }")
                
                # 添加数据
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
            
            if new_count > 0:
                st.success(f"🎉 成功导入 {new_count} 个 Subpart！")
            else:
                st.error("仍然未能解析出 Subpart。")
                st.subheader("调试信息（前10行）")
                for d in debug[:10]:
                    st.write(d)
                st.info("请把上面的调试信息截图发给我，我会根据实际抓到的内容继续调整。")
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")

st.subheader("当前状态")
count = len(st.session_state.get('items', pd.DataFrame()))
st.write(f"已导入 Subpart 数量： **{count}**")
