import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 显示修复最终版")

# 强制初始化
if 'items' not in st.session_state or not isinstance(st.session_state.get('items'), pd.DataFrame):
    st.session_state.items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow'])
if 'progress' not in st.session_state or not isinstance(st.session_state.get('progress'), pd.DataFrame):
    st.session_state.progress = pd.DataFrame(columns=['item_id', 'dept', 'status', 'arrival_time'])

uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])

if uploaded_file:
    with st.spinner("正在导入数据..."):
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
                    
                    workflow = []
                    for col_idx in range(len(row)-1, 15, -1):
                        cell = str(row.iloc[col_idx]).strip()
                        if cell and cell.lower() != 'nan' and cell != '' and len(cell) > 2:
                            if not any(x in cell for x in ['/2026', '4501', 'New Awarded', 'Normal', 'No Job']):
                                workflow.insert(0, {"dept": cell, "est_hours": 8.0})
                    
                    if len(workflow) == 0:
                        continue
                    
                    new_row = pd.DataFrame([{
                        'item_id': item_id,
                        'main_part': main_part,
                        'subpart': subpart,
                        'qty': 1,
                        'workflow': json.dumps(workflow)
                    }])
                    
                    # 安全合并 + 立即保存
                    try:
                        st.session_state.items = pd.concat([st.session_state.items, new_row], ignore_index=True)
                    except:
                        st.session_state.items = new_row.copy()
                    
                    first_dept = workflow[0]['dept']
                    prog_row = pd.DataFrame([{
                        'item_id': item_id,
                        'dept': first_dept,
                        'status': 'pending',
                        'arrival_time': datetime.now().isoformat()
                    }])
                    
                    try:
                        st.session_state.progress = pd.concat([st.session_state.progress, prog_row], ignore_index=True)
                    except:
                        st.session_state.progress = prog_row.copy()
                    
                    new_count += 1
                    debug.append(f"✅ 成功: {item_id} ({len(workflow)} steps)")
            
            if new_count > 0:
                st.success(f"🎉 **成功导入 {new_count} 个 Subpart！**")
                st.write("最后成功记录:", debug[-5:])
                st.rerun()   # ← 关键：导入成功后强制刷新页面，显示当前状态
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")

# ==================== 当前状态显示 ====================
st.subheader("当前状态")
item_count = len(st.session_state.items) if isinstance(st.session_state.items, pd.DataFrame) else 0
st.metric("已导入 Subpart 数量", item_count)

if item_count > 0:
    st.dataframe(st.session_state.items[['main_part', 'subpart', 'qty']].head(10), use_container_width=True)
    
    st.subheader("Workflow 示例（前3个）")
    for i in range(min(3, item_count)):
        item = st.session_state.items.iloc[i]
        steps = json.loads(item['workflow'])
        st.write(f"**{item['item_id']}** → {len(steps)} 个步骤")
        st.write([s['dept'] for s in steps[:8]])   # 显示前8个部门
else:
    st.info("请上传 Excel 文件开始导入")

st.caption("系统已成功解析你的 Epicor BAQ Report（交错 Main/Subpart 结构）")
