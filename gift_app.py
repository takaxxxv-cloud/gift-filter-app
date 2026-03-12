import streamlit as st
import pandas as pd

st.set_page_config(page_title="Data Nexus", page_icon="🥂", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 💎 カスタムCSS（ブラック＆ゴールド）
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400;600&display=swap');

    html, body, [class*="css"] { font-family: 'Noto Serif JP', serif !important; }
    .stApp { background-color: #0A0A0A; color: #F2F2F2; }
    [data-testid="stSidebar"] { background-color: #141414 !important; border-right: 1px solid #332918; }
    
    div[data-testid="stMetricValue"] { color: #C5A059 !important; font-weight: 600; }
    
    div[data-testid="stDownloadButton"] > button {
        background-color: transparent !important;
        color: #C5A059 !important;
        border: 1px solid #C5A059 !important;
        border-radius: 2px !important;
        transition: all 0.4s ease;
        padding: 0.5rem 1.5rem;
        letter-spacing: 1px;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #C5A059 !important;
        color: #0A0A0A !important;
        border-color: #C5A059 !important;
    }
    
    /* タブの装飾をゴールドに */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] {
        color: #8C8C8C;
        border-bottom-color: transparent !important;
        background-color: transparent !important;
    }
    .stTabs [aria-selected="true"] {
        color: #C5A059 !important;
        border-bottom-color: #C5A059 !important;
        font-weight: 600;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

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
st.markdown("<h1 style='color: #C5A059; font-weight: 300; letter-spacing: 2px;'>Data Nexus</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #8C8C8C; font-size: 1.1rem; letter-spacing: 1px;'>Amazonギフト配布リスト作成システム</p>", unsafe_allow_html=True)
st.divider()

# --- 左側のサイドバー ---
with st.sidebar:
    st.markdown("<h3 style='color: #C5A059; font-weight: 400;'>コントロールパネル</h3>", unsafe_allow_html=True)
    st.write("必要なCSVファイルをアップロードしてください。")
    uploaded_file_members = st.file_uploader("1. 投資家一覧CSV（必須）", type="csv")
    uploaded_file_investors = st.file_uploader("2. 出資者一覧CSV（必須）", type="csv")
    uploaded_file_solmina = st.file_uploader("3. SOLMINA投資家リストCSV（必須）", type="csv")
    uploaded_file_gifts = st.file_uploader("4. 配布済みリストCSV（任意）", type="csv")
    
    st.divider()
    
    # 💡 キャンペーンの案内文もシックなデザインに
    st.markdown("""
    <div style='color: #8C8C8C; font-size: 0.85rem; line-height: 1.6;'>
        <strong style='color: #C5A059;'>💡 【既存キャンペーン】</strong><br>
        ・1~4あり ＆ 5以降なし → 0円<br>
        ・1~4あり ＆ 5か6あり → 4,000円<br>
        ・1~4なし ＆ 5以降あり → 2,000円<br><br>
        <strong style='color: #C5A059;'>💡 【SOLMINAキャンペーン】</strong><br>
        ・TORCHES会員登録 → 2,000円<br>
        ・fundID=13までに初回投資 → ＋2,000円<br><br>
        ※両キャンペーンは併用不可（最大4,000円）です。高い方の対象金額を自動で採用します。
    </div>
    """, unsafe_allow_html=True)

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
        if missing_mem: st.markdown("<div style='color: #B35B5B; border-left: 3px solid #B35B5B; padding-left: 10px; margin-bottom: 10px;'>エラー: 投資家一覧CSVに「メールアドレス」が見つかりません。</div>", unsafe_allow_html=True)
        if missing_inv: st.markdown(f"<div style='color: #B35B5B; border-left: 3px solid #B35B5B; padding-left: 10px; margin-bottom: 10px;'>エラー: 出資者一覧CSVに不足項目があります: {missing_inv}</div>", unsafe_allow_html=True)
        if missing_sol: st.markdown("<div style='color: #B35B5B; border-left: 3px solid #B35B5B; padding-left: 10px; margin-bottom: 10px;'>エラー: SOLMINA投資家リストCSVに「メールアドレス」が見つかりません。</div>", unsafe_allow_html=True)
        st.markdown("<div style='border-left: 2px solid #C5A059; padding-left: 15px; color: #8C8C8C;'>※すべてのファイルの照合キーとして「メールアドレス」の列を使用します。列名が異なる場合はCSVの列名を変更してください。</div>", unsafe_allow_html=True)
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
                st.markdown("<div style='color: #D4AF37; border-left: 3px solid #D4AF37; padding-left: 10px; margin-bottom: 20px;'>⚠️ 警告: 配布済みリストの列名（受取人様Eメール, 金額）が不正です。今回は0円として計算します。</div>", unsafe_allow_html=True)

        st.markdown("<h3 style='color: #F2F2F2; font-weight: 300;'>📊 計算結果レポート</h3>", unsafe_allow_html=True)
        
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
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(label="📥 今回配布リストをダウンロード", data=csv_data, file_name="ギフト今回配布リスト.csv", mime="text/csv")
            else:
                st.markdown("<div style='border-left: 2px solid #C5A059; padding-left: 15px; color: #8C8C8C; margin-top: 20px;'>全員に配布済みか、新たに対象となる人がいません。</div>", unsafe_allow_html=True)
                
        with tab2:
            st.markdown("<div style='color: #8C8C8C; margin-bottom: 10px;'>各キャンペーンの個別の計算結果（既存C対象額・SOLMINAC対象額）なども確認できます。</div>", unsafe_allow_html=True)
            all_display_columns = ['ID', 'メールアドレス', 'is_solmina', 'is_registered', '保有fundID一覧', '既存C対象額', 'SOLMINAC対象額', '最終対象金額', '配布済金額', '今回配布金額']
            st.dataframe(master_df[all_display_columns], use_container_width=True)

else:
    # 💡 必須ファイルが揃っていない時の案内もリッチに
    st.markdown("""
    <div style='border-left: 2px solid #C5A059; padding-left: 15px; color: #8C8C8C; margin-top: 20px; line-height: 1.6;'>
        左側のパネルより、計算に必要なCSVファイル（投資家一覧、出資者一覧、SOLMINAリスト）をアップロードしてください。<br>
        すべての必須ファイルが揃うと、自動的に計算が開始されます。
    </div>
    """, unsafe_allow_html=True)
