import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 精准对齐版")

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在精确对齐并解析..."):
        try:
            # 读取原始数据（不自动header）
            df_raw = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=None)
            
            # 精确设置 header（第6行 = 索引5）
            header_idx = 5
            df = df_raw.iloc[header_idx + 1:].reset_index(drop=True)
            df.columns = df_raw.iloc[header_idx]
            
            # 清理空行
            df = df.dropna(how='all').reset_index(drop=True)
            
            new_count = 0
            debug = []
            
            # 精确找到列位置
            main_col = sub_col = None
            for c_idx, col_name in enumerate(df.columns):
                col_str = str(col_name).strip() if pd.notna(col_name) else ""
                if col_str == "Main Part Num":
                    main_col = c_idx
                if col_str == "Subpart Part Num":
                    sub_col = c_idx
            
            st.success(f"列定位成功: Main Part Num 在第 {main_col} 列, Subpart Part Num 在第 {sub_col} 列")
            
            for idx, row in df.iterrows():
                main_part = str(row.iloc[main_col]).strip() if pd.notna(row.iloc[main_col]) else ''
                subpart = str(row.iloc[sub_col]).strip() if pd.notna(row.iloc[sub_col]) else ''
                
                if not main_part or not subpart or main_part.lower() == 'nan' or subpart.lower() == 'nan':
                    debug.append(f"Row {idx}: Main/Sub 为空或NaN → 跳过")
                    continue
                
                item_id = f"{main_part}_{subpart}"
                
                # 强力抓取 Step（从右往左，跳过前面信息列）
                workflow = []
                for col_idx in range(len(row)-1, 15, -1):   # 从右往左，跳过更多前面列以避免抓到日期/PO
                    cell = str(row.iloc[col_idx]).strip()
                    if cell and cell.lower() != 'nan' and cell != '' and len(cell) > 2:
                        # 过滤掉明显不是 Step 的内容（如日期、数字）
                        if not any(x in cell for x in ['/202', '4501', 'New Awarded', 'Normal']):
                            workflow.insert(0, {"dept": cell, "est_hours": 8.0})
                
                if len(workflow) == 0:
                    debug.append(f"Row {idx}: {item_id} 有 Main/Sub 但无有效 Step")
                    continue
                
                # 添加数据
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
            
            if new_count > 0:
                st.success(f"🎉 **成功导入 {new_count} 个 Subpart！**")
                st.write("示例:", debug[:5])
            else:
                st.error("仍然未能解析出 Subpart。")
                st.subheader("调试信息")
                for d in debug[:20]:
                    st.write(d)
                st.info("请把上面的调试信息完整复制或截图发给我。")
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")

st.subheader("当前状态")
count = len(st.session_state.get('items', pd.DataFrame()))
st.write(f"已导入 Subpart 数量： **{count}**")
