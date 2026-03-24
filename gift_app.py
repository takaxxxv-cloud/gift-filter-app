import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Data Nexus", layout="wide", initial_sidebar_state="expanded")

def load_csv_safe(file):
    encodings = ['utf-8', 'cp932', 'utf-8-sig', 'shift_jis', 'mac_japanese', 'utf-16']
    for enc in encodings:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc)
        except:
            continue
    file.seek(0)
    return pd.read_csv(file, encoding='cp932', encoding_errors='replace')

# --- タイトル ---
st.title("🌐 Data Nexus - 総合ギフト配布リスト作成ツール")
st.markdown("Amazonギフトとデジタルギフトの複数キャンペーンを統合処理。複雑な条件を自動照合し、瞬時にリストを生成します。")

# --- 左側のサイドバー ---
with st.sidebar:
    st.header("⚙️ コントロールパネル")
    st.write("必要なCSVファイルをアップロードしてください。")
    
    uploaded_file_members = st.file_uploader("1. 投資家一覧CSV（★複数選択OK）", type="csv", accept_multiple_files=True)
    uploaded_file_investors = st.file_uploader("2. 出資者一覧CSV（★複数選択OK）\n※ファイル名は「1.csv」「17.csv」等に", type="csv", accept_multiple_files=True)
    uploaded_file_solmina = st.file_uploader("3. SOLMINA投資家リストCSV（必須）", type="csv")
    uploaded_file_gifts = st.file_uploader("4. 過去の全配布済みリストCSV（任意）", type="csv")
    
    st.divider()
    st.caption("🟧 【Amazonギフト】\n"
               "①既存C (MAX4000円)\n"
               "②SOLMINA C (MAX4000円)\n"
               "※①と②は高い方を適用\n"
               "③20号限定ボーナス (出資額別 MAX2万円)\n"
               "※③は別途加算\n\n"
               "🟦 【デジタルギフト】\n"
               "④17号限定ボーナス (出資額別 MAX2万円)\n"
               "⑤20~24号の新規投資家ボーナス (4000円)\n"
               "※1~19号未投資かつ20~24号投資で適用")

# --- メイン画面 ---
if uploaded_file_members and uploaded_file_investors and uploaded_file_solmina:
    
    mem_dfs = [load_csv_safe(f) for f in uploaded_file_members]
    df_mem = pd.concat(mem_dfs, ignore_index=True)
    
    df_sol = load_csv_safe(uploaded_file_solmina)
    
    inv_dfs = []
    for file in uploaded_file_investors:
        tmp_df = load_csv_safe(file)
        fund_id = file.name.rsplit('.', 1)[0].strip().lower()
        tmp_df['fundID'] = fund_id
        inv_dfs.append(tmp_df)
    df_inv = pd.concat(inv_dfs, ignore_index=True)
    
    missing_mem = ['メールアドレス'] if 'メールアドレス' not in df_mem.columns else []
    missing_inv = [col for col in ['ID', 'メールアドレス'] if col not in df_inv.columns]
    missing_sol = ['メールアドレス'] if 'メールアドレス' not in df_sol.columns else []
    
    if missing_mem or missing_inv or missing_sol:
        if missing_mem: st.error("エラー: 投資家一覧CSVに「メールアドレス」が見つかりません。")
        if missing_inv: st.error(f"エラー: 出資者一覧CSVに不足項目があります: {missing_inv}")
        if missing_sol: st.error("エラー: SOLMINA投資家リストCSVに「メールアドレス」が見つかりません。")
        st.info("※すべてのファイルの照合キーとして「メールアドレス」の列を使用します。")
    else:
        # 出資金額の読み取りとクリーンアップ（17号と20号用）
        if '出資金額' in df_inv.columns:
            df_inv['出資金額'] = df_inv['出資金額'].astype(str).str.replace(',', '', regex=False).str.replace('¥', '', regex=False).str.replace('円', '', regex=False)
            df_inv['出資金額'] = pd.to_numeric(df_inv['出資金額'], errors='coerce').fillna(0)
            df_inv['fund17_amount'] = df_inv.apply(lambda x: x['出資金額'] if x['fundID'] == '17' else 0, axis=1)
            df_inv['fund20_amount'] = df_inv.apply(lambda x: x['出資金額'] if x['fundID'] == '20' else 0, axis=1)
        else:
            df_inv['fund17_amount'] = 0
            df_inv['fund20_amount'] = 0
            st.warning("⚠️ 出資者一覧CSVに「出資金額」列が見つかりません。17号・20号の金額別キャンペーンは0円で計算されます。")

        gift_summary = pd.DataFrame(columns=['メールアドレス', '配布済金額'])
        if uploaded_file_gifts is not None:
            df_gift = load_csv_safe(uploaded_file_gifts)
            if '受取人様Eメール' in df_gift.columns and '金額' in df_gift.columns:
                df_gift['金額'] = df_gift['金額'].astype(str).str.replace(',', '', regex=False).str.replace('¥', '', regex=False).str.replace('円', '', regex=False)
                df_gift['金額'] = pd.to_numeric(df_gift['金額'], errors='coerce').fillna(0)
                gift_summary = df_gift.groupby('受取人様Eメール')['金額'].sum().reset_index()
                gift_summary = gift_summary.rename(columns={'受取人様Eメール': 'メールアドレス', '金額': '配布済金額'})

        st.write("### 📊 計算結果レポート")
        
        df_inv = df_inv.dropna(subset=['fundID']).copy() 
        df_inv['fundID'] = df_inv['fundID'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df_inv = df_inv[df_inv['fundID'].str.lower() != 'nan'] 
        
        emails_mem = set(df_mem['メールアドレス'].dropna())
        emails_inv = set(df_inv['メールアドレス'].dropna())
        emails_sol = set(df_sol['メールアドレス'].dropna())
        
        all_emails = list(emails_mem | emails_inv | emails_sol)
        master_df = pd.DataFrame({'メールアドレス': all_emails})
        
        master_df['is_solmina'] = master_df['メールアドレス'].isin(emails_sol)
        master_df['is_registered'] = master_df['メールアドレス'].isin(emails_mem)
        
        grouped_inv = df_inv.groupby('メールアドレス').agg(
            fund_list=('fundID', list),
            fund17_amount=('fund17_amount', 'sum'),
            fund20_amount=('fund20_amount', 'sum')
        ).reset_index()
        
        master_df = master_df.merge(grouped_inv, on='メールアドレス', how='left')
        master_df['fund17_amount'] = master_df['fund17_amount'].fillna(0)
        master_df['fund20_amount'] = master_df['fund20_amount'].fillna(0)
        
        id_mapping_inv = df_inv.groupby('メールアドレス')['ID'].first()
        master_df['ID'] = master_df['メールアドレス'].map(id_mapping_inv)
        if 'ID' in df_mem.columns:
            id_mapping_mem = df_mem.groupby('メールアドレス')['ID'].first()
            master_df['ID'] = master_df['ID'].fillna(master_df['メールアドレス'].map(id_mapping_mem))
            
        master_df = master_df.merge(gift_summary, on='メールアドレス', how='left')
        master_df['配布済金額'] = master_df['配布済金額'].fillna(0)

        def calculate_all_rewards(row):
            funds = row['fund_list']
            if not isinstance(funds, list): funds = []
                
            has_1_to_4 = False
            has_5_or_6 = False
            has_5_to_19 = False 
            has_invested_up_to_13 = False
            has_1_to_19 = False # 1~19号(6r含む)への投資履歴
            has_20_to_24 = False # 20~24号への投資履歴
            
            for f in funds:
                f_lower = f.lower()
                
                if f_lower in ['1', '2', '3', '4']: has_1_to_4 = True
                if f_lower in ['5', '6']: has_5_or_6 = True
                
                if f_lower == '6r':
                    has_5_to_19 = True
                    has_invested_up_to_13 = True
                    has_1_to_19 = True
                else:
                    try:
                        f_num = float(f)
                        if 5 <= f_num <= 19: has_5_to_19 = True
                        if f_num <= 13: has_invested_up_to_13 = True
                        if 1 <= f_num <= 19: has_1_to_19 = True
                        if 20 <= f_num <= 24: has_20_to_24 = True
                    except:
                        pass
            
            # --- 【Amazonギフト計算】 ---
            reward_existing = 0
            if has_1_to_4 and has_5_or_6: reward_existing = 4000
            elif not has_1_to_4 and has_5_to_19: reward_existing = 2000
            
            reward_solmina = 0
            if row['is_solmina'] and row['is_registered']:
                reward_solmina += 2000 
                if has_invested_up_to_13: reward_solmina += 2000 
                    
            amount_20 = row['fund20_amount']
            reward_20 = 0
            if amount_20 >= 5000000: reward_20 = 20000
            elif amount_20 >= 2000000: reward_20 = 10000
            elif amount_20 >= 1000000: reward_20 = 6000
            elif amount_20 >= 500000: reward_20 = 3000
            elif amount_20 >= 100000: reward_20 = 1000

            amazon_total = max(reward_existing, reward_solmina) + reward_20

            # --- 【デジタルギフト計算】 ---
            amount_17 = row['fund17_amount']
            reward_dg_17 = 0
            if amount_17 >= 5000000: reward_dg_17 = 20000
            elif amount_17 >= 2000000: reward_dg_17 = 10000
            elif amount_17 >= 1000000: reward_dg_17 = 6000
            elif amount_17 >= 500000: reward_dg_17 = 3000
            elif amount_17 >= 100000: reward_dg_17 = 1000

            reward_dg_new = 0
            if not has_1_to_19 and has_20_to_24:
                reward_dg_new = 4000
                
            digital_total = reward_dg_17 + reward_dg_new

            # --- 総合計 ---
            grand_total = amazon_total + digital_total
            
            return pd.Series([
                amazon_total, digital_total, grand_total,
                reward_existing, reward_solmina, reward_20,
                reward_dg_17, reward_dg_new
            ])

        master_df[[
            'Amazon対象額', 'デジタル対象額', '総合対象金額',
            '既存C対象額', 'SOLMINAC対象額', '20号C対象額',
            '17号DGC対象額', '新規20_24DGC対象額'
        ]] = master_df.apply(calculate_all_rewards, axis=1)
        
        master_df['今回配布金額'] = master_df['総合対象金額'] - master_df['配布済金額']
        master_df['今回配布金額'] = master_df['今回配布金額'].apply(lambda x: max(0, x))
        master_df['保有fundID一覧'] = master_df['fund_list'].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')

        target_df = master_df[master_df['総合対象金額'] > 0].copy()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="🎯 今回の新規配布対象者数", value=f"{len(target_df[target_df['今回配布金額'] > 0])} 名")
        with col2:
            st.metric(label="💰 今回の配布予定総額", value=f"¥ {int(target_df['今回配布金額'].sum()):,}")
        with col3:
            st.metric(label="（参考）本来の総合対象総額", value=f"¥ {int(target_df['総合対象金額'].sum()):,}")

        st.write("")
        tab1, tab2 = st.tabs(["🎁 今回配布するリスト", "📋 全員の計算結果（詳細・確認用）"])
        
        with tab1:
            distribute_df = target_df[target_df['今回配布金額'] > 0]
            display_columns = ['ID', 'メールアドレス', '保有fundID一覧', 'Amazon対象額', 'デジタル対象額', '総合対象金額', '配布済金額', '今回配布金額']
            
            if len(distribute_df) > 0:
                st.dataframe(distribute_df[display_columns], use_container_width=True)
                csv_data = distribute_df[display_columns].to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 今回配布リストをダウンロード", data=csv_data, file_name="ギフト総合配布リスト.csv", mime="text/csv")
            else:
                st.info("全員に配布済みか、新たに対象となる人がいません。")
                
        with tab2:
            st.write("各キャンペーンの個別の計算結果（Amazon枠・デジタルギフト枠の内訳）も確認できます。")
            all_display_columns = [
                'ID', 'メールアドレス', '保有fundID一覧', 
                'fund17_amount', 'fund20_amount',
                '既存C対象額', 'SOLMINAC対象額', '20号C対象額', 'Amazon対象額',
                '17号DGC対象額', '新規20_24DGC対象額', 'デジタル対象額',
                '総合対象金額', '配布済金額', '今回配布金額'
            ]
            
            display_df = master_df[all_display_columns].rename(columns={
                'fund17_amount': '17号出資総額',
                'fund20_amount': '20号出資総額'
            })
            st.dataframe(display_df, use_container_width=True)

else:
    pass
