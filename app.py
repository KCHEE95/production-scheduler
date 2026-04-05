import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统")

ITEMS_CSV = "items.csv"

# 加载数据
if os.path.exists(ITEMS_CSV):
    try:
        items = pd.read_csv(ITEMS_CSV)
    except:
        items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow'])
else:
    items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow'])

st.subheader("当前状态")
item_count = len(items)
st.metric("已导入 Subpart 数量", item_count)

col1, col2 = st.columns([4, 1])
with col1:
    uploaded_file = st.file_uploader("📤 上传 Epicor BAQ Report 文件", type=["xlsx"])
with col2:
    if st.button("🗑️ 清空所有数据"):
        if os.path.exists(ITEMS_CSV):
            os.remove(ITEMS_CSV)
        st.success("数据已清空！")
        st.rerun()

if uploaded_file:
    if item_count > 0:
        st.warning("⚠️ 系统已存在数据。如需重新导入，请先点击【清空所有数据】")
    else:
        with st.spinner("正在导入数据..."):
            try:
                df_raw = pd.read_excel(uploaded_file, sheet_name="sAMPLE", header=None)
                
                header_idx = 5
                df = df_raw.iloc[header_idx + 1:].reset_index(drop=True)
                df.columns = df_raw.iloc[header_idx]
                
                df = df.dropna(how='all').reset_index(drop=True)
                df = df.dropna(thresh=3).reset_index(drop=True)
                
                new_count = 0
                current_main = None
                all_items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow'])
                
                main_col = sub_col = None
                for c_idx, col_name in enumerate(df.columns):
                    col_str = str(col_name).strip() if pd.notna(col_name) else ""
                    if col_str == "Main Part Num":
                        main_col = c_idx
                    if col_str == "Subpart Part Num":
                        sub_col = c_idx
                
                for _, row in df.iterrows():
                    main_candidate = str(row.iloc[main_col]).strip() if pd.notna(row.iloc[main_col]) else ''
                    sub_candidate = str(row.iloc[sub_col]).strip() if pd.notna(row.iloc[sub_col]) else ''
                    
                    if main_candidate and main_candidate.lower() != 'nan':
                        current_main = main_candidate
                    
                    if sub_candidate and sub_candidate.lower() != 'nan' and current_main:
                        item_id = f"{current_main}_{sub_candidate}"
                        
                        workflow = []
                        for i in range(1, 21):
                            col_name = f"Step {i}"
                            if col_name in df.columns:
                                step = str(row.get(col_name, "")).strip()
                                if step and step.lower() != "nan" and step != "":
                                    workflow.append({"dept": step, "est_hours": 8.0})
                        
                        if len(workflow) < 3:
                            workflow = []
                            for col_idx in range(len(row)-1, 10, -1):
                                cell = str(row.iloc[col_idx]).strip()
                                if cell and cell.lower() != 'nan' and cell != '' and len(cell) > 2:
                                    if not any(x in cell for x in ['/2026', '4501', 'New Awarded', 'Normal', 'No Job']):
                                        workflow.insert(0, {"dept": cell, "est_hours": 8.0})
                        
                        if len(workflow) == 0:
                            continue
                        
                        new_row = pd.DataFrame([{
                            'item_id': item_id,
                            'main_part': current_main,
                            'subpart': sub_candidate,
                            'qty': 1,
                            'workflow': json.dumps(workflow)
                        }])
                        
                        all_items = pd.concat([all_items, new_row], ignore_index=True)
                        new_count += 1
                
                all_items.to_csv(ITEMS_CSV, index=False)
                st.success(f"🎉 成功导入 {new_count} 个 Subpart！")
                st.rerun()
                
            except Exception as e:
                st.error(f"导入失败: {str(e)}")

# 显示数据
if item_count > 0:
    st.success(f"✅ 数据已加载！共 {item_count} 个 Subpart")
    st.dataframe(items[['main_part', 'subpart', 'qty']].head(20), use_container_width=True)

st.caption("已防止重复导入。如需重新导入，请先清空数据。")
