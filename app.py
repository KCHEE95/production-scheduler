import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="K.K. Metal AI排产系统", layout="wide", page_icon="🏭")

st.title("🏭 K.K. Metal AI 自动排产系统 - 最终稳定版")

ITEMS_CSV = "items.csv"

# 加载已有数据
if os.path.exists(ITEMS_CSV):
    try:
        items = pd.read_csv(ITEMS_CSV)
    except:
        items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow'])
else:
    items = pd.DataFrame(columns=['item_id', 'main_part', 'subpart', 'qty', 'workflow'])

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
            
            all_items = items.copy()
            
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
                    
                    all_items = pd.concat([all_items, new_row], ignore_index=True)
                    new_count += 1
                    debug.append(f"✅ 成功: {item_id} ({len(workflow)} steps)")
            
            # 保存到 CSV
            all_items.to_csv(ITEMS_CSV, index=False)
            
            if new_count > 0:
                st.success(f"🎉 **成功导入 {new_count} 个 Subpart！**")
                st.write("最后成功记录:", debug[-5:])
                
        except Exception as e:
            st.error(f"读取失败: {str(e)}")

# ==================== 显示部分 ====================
st.subheader("当前状态")
item_count = len(items) if 'items' in locals() and isinstance(items, pd.DataFrame) else 0
st.metric("已导入 Subpart 数量", item_count)

if item_count > 0:
    st.success(f"✅ 数据已加载！共 {item_count} 个 Subpart")
    st.dataframe(items[['main_part', 'subpart', 'qty']].head(10), use_container_width=True)
    
    st.subheader("Workflow 示例（前 3 个）")
    for i in range(min(3, item_count)):
        item = items.iloc[i]
        steps = json.loads(item['workflow'])
        st.write(f"**{item['item_id']}** → {len(steps)} 个步骤")
        st.write([s['dept'] for s in steps[:10]])
else:
    st.info("请上传 Excel 文件开始导入")

if st.button("🔄 手动刷新显示"):
    st.rerun()

st.caption("数据已保存到 CSV 文件（极简稳定版）")
