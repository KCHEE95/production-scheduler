import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 精确修复版")

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在精确解析（已根据你的列名调试）..."):
        try:
            # 读取原始数据，不自动设置header
            df_raw = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=None)
            
            # 找到 header 行（第6行，索引5）
            header_row_idx = 5
            df = df_raw.iloc[header_row_idx + 1:].reset_index(drop=True)  # 数据从第7行开始
            df.columns = df_raw.iloc[header_row_idx]                     # 使用第6行作为列名
            
            # 清理完全空的行
            df = df.dropna(how='all').reset_index(drop=True)
            
            new_count = 0
            debug = []
            
            # 找到关键列的位置
            main_col = None
            sub_col = None
            for c_idx, col_name in enumerate(df.columns):
                col_str = str(col_name).strip() if pd.notna(col_name) else ""
                if col_str == "Main Part Num":
                    main_col = c_idx
                if col_str == "Subpart Part Num":
                    sub_col = c_idx
            
            if main_col is None or sub_col is None:
                st.error("无法定位 Main Part Num 或 Subpart Part Num 列")
                st.write("实际列名:", [str(c) for c in df.columns[:30]])
            else:
                st.success(f"找到列: Main Part Num 在第 {main_col} 列, Subpart Part Num 在第 {sub_col} 列")
                
                for idx, row in df.iterrows():
                    main_part = str(row.iloc[main_col]).strip() if pd.notna(row.iloc[main_col]) else ''
                    subpart = str(row.iloc[sub_col]).strip() if pd.notna(row.iloc[sub_col]) else ''
                    
                    if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                        continue
                    
                    item_id = f"{main_part}_{subpart}"
                    
                    # 强力抓取 Step（从右往左）
                    workflow = []
                    for col_idx in range(len(row)-1, 10, -1):
                        cell = str(row.iloc[col_idx]).strip()
                        if cell and cell.lower() != 'nan' and cell != '' and len(cell) > 2:
                            workflow.insert(0, {"dept": cell, "est_hours": 8.0})
                    
                    if len(workflow) == 0:
                        debug.append(f"Row {idx}: 有 Main/Sub 但无 Step")
                        continue
                    
                    # 添加数据
                    new_row = pd.DataFrame([{
                        'item_id': item_id,
                        'main_part': main_part,
                        'subpart': subpart,
                        'qty': float(row.iloc[15]) if len(row) > 15 and pd.notna(row.iloc[15]) else 1,  # Subpart Qty 大概位置
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
                    debug.append(f"成功导入: {item_id} ({len(workflow)} steps)")
            
            if new_count > 0:
                st.success(f"🎉 **成功导入 {new_count} 个 Subpart！**")
                st.write("示例:", debug[:5])
            else:
                st.error("仍然未能解析出 Subpart。")
                st.subheader("调试信息")
                st.write("列名示例:", [str(c) for c in df.columns[:30]])
                for d in debug[:15]:
                    st.write(d)
                st.info("请把上面的调试信息完整截图或复制发给我。")
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")

st.subheader("当前状态")
count = len(st.session_state.get('items', pd.DataFrame()))
st.write(f"已导入 Subpart 数量： **{count}**")
