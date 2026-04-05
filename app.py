import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 测试版")

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在强力解析 Excel（处理合并单元格 + 空列）..."):
        try:
            # 读取时不指定 header，先读取所有行
            df = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=None)
            
            # 找到 header 行（第6行，索引5）
            header_row = 5
            df.columns = df.iloc[header_row]
            df = df[header_row + 1:].reset_index(drop=True)
            
            # 清理空行
            df = df.dropna(how='all').reset_index(drop=True)
            
            new_count = 0
            added = []
            
            for _, row in df.iterrows():
                main_part = str(row.get('Main Part Num', '')).strip()
                subpart = str(row.get('Subpart Part Num', '')).strip()
                
                if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                    continue
                
                item_id = f"{main_part}_{subpart}"
                
                # === 关键：按列位置读取 Step（避开合并和空列）===
                workflow = []
                # Step 列通常在后面，我们从右边开始找非空值作为 Step
                for col_idx in range(len(row) - 1, 10, -1):   # 从右往左扫描，跳过前面信息列
                    cell = str(row.iloc[col_idx]).strip()
                    if cell and cell.lower() != 'nan' and cell != '' and len(cell) > 2:
                        workflow.insert(0, {"dept": cell, "est_hours": 8.0})
                
                if len(workflow) < 3:  # 如果没找到足够 Step，尝试传统方式
                    workflow = []
                    for i in range(1, 21):
                        col_name = f"Step {i}"
                        step = str(row.get(col_name, "")).strip()
                        if step and step.lower() != "nan" and step != "":
                            workflow.append({"dept": step, "est_hours": 8.0})
                
                if not workflow:
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
                
                # 添加 progress
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
                st.error("仍然未能解析出 Subpart。请把文件前30行截图或整个文件发给我，我再继续调整。")
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")

st.subheader("当前状态")
count = len(st.session_state.get('items', pd.DataFrame()))
st.write(f"已导入 Subpart 数量： **{count}**")

if count > 0:
    st.dataframe(st.session_state.items[['main_part', 'subpart']].head(10), use_container_width=True)

st.caption("已优化合并单元格和空列读取 | 如仍为0，请提供更多截图")
