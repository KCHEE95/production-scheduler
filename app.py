import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 测试版")

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在强力读取 Excel（处理合并单元格和空列）..."):
        try:
            # 读取时不使用 header，让我们手动处理
            df = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=None, skiprows=5)
            
            # 设置第6行作为列名
            df.columns = df.iloc[0]
            df = df[1:].reset_index(drop=True)
            
            # 清理完全空的行
            df = df.dropna(how='all').reset_index(drop=True)
            
            new_count = 0
            added = []
            
            for _, row in df.iterrows():
                main_part = str(row.get('Main Part Num', '')).strip()
                subpart = str(row.get('Subpart Part Num', '')).strip()
                
                if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                    continue
                
                item_id = f"{main_part}_{subpart}"
                
                # === 强力解析 Step（按位置读取，最后20列左右）===
                workflow = []
                # 从后往前找 Step 列（因为 Step 18-20 在右边，且有合并）
                for col_idx in range(len(row)-1, 0, -1):   # 从右往左扫描
                    cell_value = str(row.iloc[col_idx]).strip()
                    if cell_value and cell_value.lower() != 'nan' and cell_value != '':
                        # 如果是 Step 格式的字符串，就加入 workflow
                        if len(cell_value) > 2 and not cell_value[0].isdigit():  # 简单过滤
                            workflow.insert(0, {"dept": cell_value, "est_hours": 8.0})  # 倒序插入，保持正确顺序
                
                # 如果没找到足够 Step，尝试传统方式
                if len(workflow) < 3:
                    workflow = []
                    for i in range(1, 21):
                        col_name = f"Step {i}" if f"Step {i}" in row else f"Step{i}"
                        step = str(row.get(col_name, "")).strip()
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
                
                # 自动进入第一个部门
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
                added.append(item_id)
            
            if new_count > 0:
                st.success(f"🎉 成功导入 **{new_count}** 个 Subpart！")
                st.write("示例 Item ID:", added[:5])
            else:
                st.error("仍然未找到有效 Subpart。请把 Excel 文件前 30 行截图发给我，我帮你调整读取逻辑。")
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")

st.subheader("当前状态")
count = len(st.session_state.get('items', pd.DataFrame()))
st.write(f"已导入 Subpart 数量： **{count}**")

if count > 0:
    st.dataframe(st.session_state.items[['main_part', 'subpart']].head(10), use_container_width=True)

st.caption("当前版本已优化合并单元格和空列读取")
