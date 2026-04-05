import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 测试版")

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在读取 Excel 文件，请稍等..."):
        try:
            # 更强壮的读取方式：跳过前6行，并强制读取所有列
            df = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=None, skiprows=5)
            
            # 设置正确的列名（根据你的 screenshot）
            df.columns = df.iloc[0]   # 把第6行作为列名
            df = df[1:].reset_index(drop=True)   # 去掉列名行
            
            # 清理空行
            df = df.dropna(how='all').reset_index(drop=True)
            
            new_count = 0
            added_list = []
            
            for idx, row in df.iterrows():
                main_part = str(row.get('Main Part Num', '')).strip()
                subpart = str(row.get('Subpart Part Num', '')).strip()
                
                if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                    continue
                
                item_id = f"{main_part}_{subpart}"
                
                # 检查是否已存在
                if 'items' in st.session_state and not st.session_state.items.empty:
                    if item_id in st.session_state.items.get('item_id', pd.Series()).values:
                        continue
                
                workflow = []
                for i in range(1, 21):
                    col = f"Step {i}" if f"Step {i}" in row else f"Step{i}"
                    step = str(row.get(col, "")).strip()
                    if step and step.lower() != "nan" and step != "":
                        workflow.append({"dept": step, "est_hours": 8.0})
                
                if not workflow:
                    continue
                
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
                
                if 'items' not in st.session_state:
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
                
                if 'progress' not in st.session_state:
                    st.session_state.progress = prog_row
                else:
                    st.session_state.progress = pd.concat([st.session_state.progress, prog_row], ignore_index=True)
                
                new_count += 1
                added_list.append(item_id)
            
            if new_count > 0:
                st.success(f"🎉 成功导入 **{new_count}** 个 Subpart！")
                st.write("导入的 Item ID 示例：", added_list[:5])
            else:
                st.warning("未找到有效 Subpart 数据。请检查文件是否正确，或把文件发给我我帮你诊断。")
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")
            st.info("提示：如果一直失败，请把 Excel 文件前 20 行截图发给我。")

st.subheader("当前状态")
count = len(st.session_state.get('items', pd.DataFrame())) 
st.write(f"已导入 Subpart 数量： **{count}**")

if count > 0:
    st.dataframe(st.session_state.items[['main_part', 'subpart']].head(10), use_container_width=True)
else:
    st.info("上传文件后会在这里显示结果。")

st.caption("当前为强壮读取测试版")
