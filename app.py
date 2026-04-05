import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 终极不依赖列名版")

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在强力读取（完全按列位置解析）..."):
        try:
            # 读取时不使用 header，跳过前5行，手动设置第6行作为列名
            df_raw = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=None, skiprows=5)
            
            # 第0行（原第6行）作为列名
            df = df_raw.iloc[1:].reset_index(drop=True)  # 数据从第2行开始
            df.columns = df_raw.iloc[0]                  # 设置列名
            
            # 清理空行
            df = df.dropna(how='all').reset_index(drop=True)
            
            new_count = 0
            debug = []
            
            # 找到 Main Part Num 和 Subpart Part Num 的列位置（不依赖名称）
            main_col = None
            sub_col = None
            for c_idx, col_name in enumerate(df.columns):
                col_str = str(col_name).strip()
                if 'Main Part Num' in col_str:
                    main_col = c_idx
                if 'Subpart Part Num' in col_str:
                    sub_col = c_idx
            
            if main_col is None or sub_col is None:
                st.error("无法找到 Main Part Num 或 Subpart Part Num 列")
                st.write("实际列名:", [str(c) for c in df.columns[:30]])
            else:
                for idx, row in df.iterrows():
                    main_part = str(row.iloc[main_col]).strip() if pd.notna(row.iloc[main_col]) else ''
                    subpart = str(row.iloc[sub_col]).strip() if pd.notna(row.iloc[sub_col]) else ''
                    
                    if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                        continue
                    
                    item_id = f"{main_part}_{subpart}"
                    
                    # 强力抓取 Step：从右往左扫描非空单元格
                    workflow = []
                    for col_idx in range(len(row)-1, 10, -1):   # 从右往左，跳过前面信息列
                        cell = str(row.iloc[col_idx]).strip()
                        if cell and cell.lower() != 'nan' and cell != '' and len(cell) > 2:
                            workflow.insert(0, {"dept": cell, "est_hours": 8.0})
                    
                    if len(workflow) == 0:
                        debug.append(f"Row {idx}: 有 Main/Sub 但无 Step")
                        continue
                    
                    # 添加 item
                    new_row = pd.DataFrame([{
                        'item_id': item_id,
                        'main_part': main_part,
                        'subpart': subpart,
                        'qty': 1,  # 默认值
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
                    debug.append(f"成功: {item_id} ({len(workflow)} steps)")
            
            if new_count > 0:
                st.success(f"🎉 **成功导入 {new_count} 个 Subpart！**")
                st.write("调试:", debug[:5])
            else:
                st.error("仍然未能解析出 Subpart。")
                st.subheader("调试信息")
                st.write("找到的列名示例:", [str(c) for c in df.columns[:30]])
                for d in debug[:10]:
                    st.write(d)
                st.info("请把上面的调试信息完整截图发给我。")
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")

st.subheader("当前状态")
count = len(st.session_state.get('items', pd.DataFrame()))
st.write(f"已导入 Subpart 数量： **{count}**")
