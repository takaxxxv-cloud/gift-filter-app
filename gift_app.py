import streamlit as st
import pandas as pd

st.set_page_config(page_title="Data Nexus", layout="wide", initial_sidebar_state="expanded")

# どんなCSVでも読み込む無敵の関数
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
st.title("🌐Data Nexus - Amazonギフト配布リスト作成ツール")
st.markdown("複数のデータを統合し、対象者と配布金額を瞬時に算出。ファイルの読み込みからリスト生成まで、すべて全自動で実行されます。")

# --- 左側のサイドバー ---
with st.sidebar:
    st.header("⚙️ コントロールパネル")
    st.write("必要なCSVファイルをアップロードしてください。")
    uploaded_file_members = st.file_uploader("1. 投資家一覧CSV（必須）", type="csv")
    uploaded_file_investors = st.file_uploader("2. 出資者一覧CSV（必須）", type="csv")
    uploaded_file_solmina = st.file_uploader("3. SOLMINA投資家リストCSV（必須）", type="csv")
    uploaded_file_gifts = st.file_uploader("4. 配布済みリストCSV（任意）", type="csv")
    
    st.divider()
    st.caption("💡 【既存キャンペーン】\n"
               "・1~4あり ＆ 5以降なし → 0円\n"
               "・1~4あり ＆ 5か6あり → 4,000円\n"
               "・1~4なし ＆ 5以降あり → 2,000円\n\n"
               "💡 【SOLMINAキャンペーン】\n"
               "・TORCHES会員登録 → 2,000円\n"
               "・fundID=13までに初回投資 → ＋2,000円\n\n"
               "※両キャンペーンは併用不可（最大4,000円）です。高い方の対象金額を自動で採用します。")

# --- メイン画面 ---
# 必須の3ファイルが揃ったら計算スタート
if uploaded_file_members and uploaded_file_investors and uploaded_file_solmina:
    
    df_mem = load_csv_safe(uploaded_file_members)
    df_inv = load_csv_safe(uploaded_file_investors)
    df_sol = load_csv_safe(uploaded_file_solmina)
    
    # ⚠️ 各CSVに「メールアドレス」という列名があることを前提としています
    missing_mem = ['メールアドレス'] if 'メールアドレス' not in df_mem.columns else []
    missing_inv = [col for col in ['ID', 'fundID', 'メールアドレス'] if col not in df_inv.columns]
    missing_sol = ['メールアドレス'] if 'メールアドレス' not in df_sol.columns else []
    
    if missing_mem or missing_inv or missing_sol:
        if missing_mem: st.error("エラー: 投資家一覧CSVに「メールアドレス」が見つかりません。")
        if missing_inv: st.error(f"エラー: 出資者一覧CSVに不足項目があります: {missing_inv}")
        if missing_sol: st.error("エラー: SOLMINA投資家リストCSVに「メールアドレス」が見つかりません。")
        st.info("※すべてのファイルの照合キーとして「メールアドレス」の列を使用します。列名が異なる場合はCSVの列名を変更してください。")
    else:
        # 配布済みリストの読み込み
        gift_summary = pd.DataFrame(columns=['メールアドレス', '配布済金額'])
        if uploaded_file_gifts is not None:
            df_gift = load_csv_safe(uploaded_file_gifts)
            if '受取人様Eメール' in df_gift.columns and '金額' in df_gift.columns:
                df_gift['金額'] = df_gift['金額'].astype(str).str.replace(',', '', regex=False).str.replace('¥', '', regex=False).str.replace('円', '', regex=False)
                df_gift['金額'] = pd.to_numeric(df_gift['金額'], errors='coerce').fillna(0)
                gift_summary = df_gift.groupby('受取人様Eメール')['金額'].sum().reset_index()
                gift_summary = gift_summary.rename(columns={'受取人様Eメール': 'メールアドレス', '金額': '配布済金額'})
            else:
                st.warning("配布済みリストの列名（受取人様Eメール, 金額）が不正です。今回は0円として計算します。")

        st.write("### 📊 計算結果レポート")
        
        # 1. 出資者一覧のクリーンアップ
        df_inv = df_inv.dropna(subset=['fundID']).copy() 
        df_inv['fundID'] = df_inv['fundID'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df_inv = df_inv[df_inv['fundID'].str.lower() != 'nan'] 
        
        # 2. 全員のメールアドレスをかき集めて「マスターデータ」を作る
        emails_mem = set(df_mem['メールアドレス'].dropna())
        emails_inv = set(df_inv['メールアドレス'].dropna())
        emails_sol = set(df_sol['メールアドレス'].dropna())
        
        # 重複を排除して全員分のリストを作成
        all_emails = list(emails_mem | emails_inv | emails_sol)
        master_df = pd.DataFrame({'メールアドレス': all_emails})
        
        # 3. 各種フラグ（条件）を付与
        master_df['is_solmina'] = master_df['メールアドレス'].isin(emails_sol)
        master_df['is_registered'] = master_df['メールアドレス'].isin(emails_mem)
        
        # 保有fundIDをリスト化して結合
        grouped_inv = df_inv.groupby('メールアドレス')['fundID'].apply(list).reset_index(name='fund_list')
        master_df = master_df.merge(grouped_inv, on='メールアドレス', how='left')
        
        # IDを引っ張ってくる（出資者一覧から優先し、無ければ投資家一覧から）
        id_mapping_inv = df_inv.groupby('メールアドレス')['ID'].first()
        master_df['ID'] = master_df['メールアドレス'].map(id_mapping_inv)
        if 'ID' in df_mem.columns:
            id_mapping_mem = df_mem.groupby('メールアドレス')['ID'].first()
            master_df['ID'] = master_df['ID'].fillna(master_df['メールアドレス'].map(id_mapping_mem))
            
        # 配布済金額を結合
        master_df = master_df.merge(gift_summary, on='メールアドレス', how='left')
        master_df['配布済金額'] = master_df['配布済金額'].fillna(0)

        # 4. 【本丸】両キャンペーンの判定ロジック
        def calculate_all_rewards(row):
            funds = row['fund_list']
            if not isinstance(funds, list):
                funds = []
                
            has_1_to_4 = False
            has_5_or_6 = False
            has_5_or_more = False
            has_invested_up_to_13 = False
            
            for f in funds:
                f_lower = f.lower()
                
                if f_lower in ['1', '2', '3', '4']: has_1_to_4 = True
                if f_lower in ['5', '6']: has_5_or_6 = True
                
                # 6rは5以降かつ13以下のファンドとして判定
                if f_lower == '6r':
                    has_5_or_more = True
                    has_invested_up_to_13 = True
                else:
                    try:
                        f_num = float(f)
                        if f_num >= 5: has_5_or_more = True
                        if f_num <= 13: has_invested_up_to_13 = True
                    except:
                        pass
            
            # 【A】既存キャンペーンの対象金額
            reward_existing = 0
            if has_1_to_4 and not has_5_or_more: reward_existing = 0
            elif has_1_to_4 and has_5_or_6: reward_existing = 4000
            elif not has_1_to_4 and has_5_or_more: reward_existing = 2000
            
            # 【B】SOLMINAキャンペーンの対象金額
            reward_solmina = 0
            if row['is_solmina'] and row['is_registered']:
                reward_solmina += 2000 # 会員登録完了
                if has_invested_up_to_13:
                    reward_solmina += 2000 # 13までに初回投資完了
                    
            # 併用不可のため、金額が高い方を採用する（どちらも最大4000円）
            final_reward = max(reward_existing, reward_solmina)
            
            return pd.Series([reward_existing, reward_solmina, final_reward])

        # 計算を実行し、新しい列を追加
        master_df[['既存C対象額', 'SOLMINAC対象額', '最終対象金額']] = master_df.apply(calculate_all_rewards, axis=1)
        
        # 5. 今回配布額の計算
        master_df['今回配布金額'] = master_df['最終対象金額'] - master_df['配布済金額']
        master_df['今回配布金額'] = master_df['今回配布金額'].apply(lambda x: max(0, x))
        master_df['保有fundID一覧'] = master_df['fund_list'].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')

        # --- 画面表示 ---
        target_df = master_df[master_df['最終対象金額'] > 0].copy()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="🎯 今回の新規配布対象者数", value=f"{len(target_df[target_df['今回配布金額'] > 0])} 名")
        with col2:
            st.metric(label="💰 今回の配布予定総額", value=f"¥ {int(target_df['今回配布金額'].sum()):,}")
        with col3:
            st.metric(label="（参考）本来の対象総額", value=f"¥ {int(target_df['最終対象金額'].sum()):,}")

        st.write("")
        tab1, tab2 = st.tabs(["🎁 今回配布するリスト", "📋 全員の計算結果（詳細・確認用）"])
        
        with tab1:
            distribute_df = target_df[target_df['今回配布金額'] > 0]
            display_columns = ['ID', 'メールアドレス', 'is_solmina', '保有fundID一覧', '既存C対象額', 'SOLMINAC対象額', '最終対象金額', '配布済金額', '今回配布金額']
            
            if len(distribute_df) > 0:
                st.dataframe(distribute_df[display_columns], use_container_width=True)
                csv_data = distribute_df[display_columns].to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 今回配布リストをダウンロード", data=csv_data, file_name="ギフト今回配布リスト.csv", mime="text/csv")
            else:
                st.info("全員に配布済みか、新たに対象となる人がいません。")
                
        with tab2:
            st.write("各キャンペーンの個別の計算結果（既存C対象額・SOLMINAC対象額）なども確認できます。")
            all_display_columns = ['ID', 'メールアドレス', 'is_solmina', 'is_registered', '保有fundID一覧', '既存C対象額', 'SOLMINAC対象額', '最終対象金額', '配布済金額', '今回配布金額']
            st.dataframe(master_df[all_display_columns], use_container_width=True)
