import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 交错行修复版")

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在处理交错的 Main/Subpart 行..."):
        try:
            df_raw = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=None)
            
            header_idx = 5
            df = df_raw.iloc[header_idx + 1:].reset_index(drop=True)
            df.columns = df_raw.iloc[header_idx]
            
            df = df.dropna(how='all').reset_index(drop=True)
            df = df.dropna(thresh=3).reset_index(drop=True)
            
            new_count = 0
            debug = []
            current_main = None
            
            main_col = sub_col = None
            for c_idx, col_name in enumerate(df.columns):
                col_str = str(col_name).strip() if pd.notna(col_name) else ""
                if col_str == "Main Part Num":
                    main_col = c_idx
                if col_str == "Subpart Part Num":
                    sub_col = c_idx
            
            st.success(f"列定位成功: Main 在 {main_col} 列, Subpart 在 {sub_col} 列")
            st.info(f"清理后剩余行数: {len(df)}")
            
            for idx, row in df.iterrows():
                main_candidate = str(row.iloc[main_col]).strip() if pd.notna(row.iloc[main_col]) else ''
                sub_candidate = str(row.iloc[sub_col]).strip() if pd.notna(row.iloc[sub_col]) else ''
                
                if main_candidate and main_candidate.lower() != 'nan':
                    current_main = main_candidate
                
                if sub_candidate and sub_candidate.lower() != 'nan' and current_main:
                    main_part = current_main
                    subpart = sub_candidate
                    item_id = f"{main_part}_{subpart}"
                    
                    # 抓取 Step
                    workflow = []
                    for col_idx in range(len(row)-1, 15, -1):
                        cell = str(row.iloc[col_idx]).strip()
                        if cell and cell.lower() != 'nan' and cell != '' and len(cell) > 2:
                            if not any(x in cell for x in ['/2026', '4501', 'New Awarded', 'Normal', 'No Job']):
                                workflow.insert(0, {"dept": cell, "est_hours": 8.0})
                    
                    if len(workflow) == 0:
                        debug.append(f"Row {idx}: {item_id} 有 Main/Sub 但无 Step")
                        continue
                    
                    new_row = pd.DataFrame([{
                        'item_id': item_id,
                        'main_part': main_part,
                        'subpart': subpart,
                        'qty': 1,
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
                    debug.append(f"✅ 成功: {item_id} ({len(workflow)} steps)")
                else:
                    debug.append(f"Row {idx}: 等待配对 (Main='{main_candidate}', Sub='{sub_candidate}')")
            
            if new_count > 0:
                st.success(f"🎉 **成功导入 {new_count} 个 Subpart！**")
                st.write("示例:", debug[-5:])  # 显示最后几条成功记录
            else:
                st.error("仍然未能解析出 Subpart。")
                st.subheader("调试信息")
                for d in debug[:30]:
                    st.write(d)
                st.info("请把调试信息完整复制或截图发给我。")
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")

st.subheader("当前状态")
count = len(st.session_state.get('items', pd.DataFrame()))
st.write(f"已导入 Subpart 数量： **{count}**")
