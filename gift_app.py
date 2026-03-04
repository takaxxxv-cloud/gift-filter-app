import streamlit as st
import pandas as pd

# ページの設定
st.set_page_config(page_title="GiftCalc Engine", layout="wide", initial_sidebar_state="expanded")

# --- タイトル ---
st.title(":orange[🎁 GiftCalc Engine]")
st.markdown("##### Amazonギフト配布対象者・金額の自動計算ツール（連携版）")

# --- 左側のサイドバー ---
with st.sidebar:
    st.header("⚙️ コントロールパネル")
    st.write("必要なCSVファイルをアップロードしてください。")
    
    uploaded_file_investors = st.file_uploader("1. 出資者一覧CSV（必須）", type="csv")
    uploaded_file_gifts = st.file_uploader("2. 配布済みリストCSV（任意）", type="csv")
    
    st.divider()
    st.caption("💡 【計算ルール】\n"
               "・1~4あり ＆ 5以降なし → 0円\n"
               "・1~4あり ＆ 5か6あり → 4,000円\n"
               "・1~4なし ＆ 5以降あり → 2,000円\n"
               "※「メールアドレス」を照合し、配布済金額を自動で差し引きます。")

# --- メイン画面 ---
if uploaded_file_investors is not None:
    
    # 💡 1. 出資者一覧の読み込み（最強の文字コード対策）
    try:
        df_inv = pd.read_csv(uploaded_file_investors, encoding='utf-8')
    except:
        try:
            uploaded_file_investors.seek(0)
            df_inv = pd.read_csv(uploaded_file_investors, encoding='cp932') # Shift-JISの強化版
        except:
            uploaded_file_investors.seek(0)
            df_inv = pd.read_csv(uploaded_file_investors, encoding='utf-8-sig') # Excel特有のUTF-8
        
    required_columns_inv = ['ID', 'fundID', 'メールアドレス']
    missing_columns_inv = [col for col in required_columns_inv if col not in df_inv.columns]
    
    if missing_columns_inv:
        st.error(f"エラー: 出資者一覧CSVに以下の必須項目が見つかりません: {', '.join(missing_columns_inv)}")
    else:
        
        # 2. 配布済みリストの読み込みと集計
        gift_summary = pd.DataFrame(columns=['メールアドレス', '配布済金額'])
        
        if uploaded_file_gifts is not None:
            # 💡 配布済みリストの読み込み（最強の文字コード対策）
            try:
                df_gift = pd.read_csv(uploaded_file_gifts, encoding='utf-8')
            except:
                try:
                    uploaded_file_gifts.seek(0)
                    df_gift = pd.read_csv(uploaded_file_gifts, encoding='cp932')
                except:
                    uploaded_file_gifts.seek(0)
                    df_gift = pd.read_csv(uploaded_file_gifts, encoding='utf-8-sig')
                
            required_columns_gift = ['受取人様Eメール', '金額']
            missing_columns_gift = [col for col in required_columns_gift if col not in df_gift.columns]
            
            if missing_columns_gift:
                st.warning(f"配布済みリストに必須項目が見つかりません: {', '.join(missing_columns_gift)}。今回は配布済金額0円として計算します。")
            else:
                df_gift['金額'] = df_gift['金額'].astype(str).str.replace(',', '', regex=False).str.replace('¥', '', regex=False).str.replace('円', '', regex=False)
                df_gift['金額'] = pd.to_numeric(df_gift['金額'], errors='coerce').fillna(0)
                
                gift_summary = df_gift.groupby('受取人様Eメール')['金額'].sum().reset_index()
                gift_summary = gift_summary.rename(columns={'受取人様Eメール': 'メールアドレス', '金額': '配布済金額'})
                st.toast("2つのファイルの読み込み・照合に成功しました！", icon="✅")
        else:
            st.toast("出資者一覧を読み込みました。（配布済みリストは未アップロードのため、0円として計算します）", icon="✅")


        # --- 3. データの前処理と集約 ---
        st.write("### 📊 計算結果レポート")
        df_inv['fundID'] = pd.to_numeric(df_inv['fundID'], errors='coerce')
        
        grouped = df_inv.groupby('ID').agg(
            fund_list=('fundID', lambda x: list(x.dropna())),
            メールアドレス=('メールアドレス', 'first')
        ).reset_index()

        # --- 4. 2つのデータを結合 ---
        merged_df = pd.merge(grouped, gift_summary, on='
