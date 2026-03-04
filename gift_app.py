import streamlit as st
import pandas as pd

# ページの設定
st.set_page_config(page_title="GiftCalc Engine", layout="wide", initial_sidebar_state="expanded")

# --- 🛠️ 追加：絶対に止まらない無敵のCSV読み込み関数 ---
def load_csv_safe(file):
    # 考えられるすべての文字コードを順番に試す
    encodings = ['utf-8', 'cp932', 'utf-8-sig', 'shift_jis', 'mac_japanese', 'utf-16']
    
    for enc in encodings:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc)
        except:
            continue # エラーが出たら次の文字コードを試す
            
    # 全てダメだった場合の最終手段（エラー文字を「?」に置き換えて強制読み込み）
    file.seek(0)
    return pd.read_csv(file, encoding='cp932', encoding_errors='replace')
# --------------------------------------------------------

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
               "※「メールアドレス」を照合し自動で差し引きます。")

# --- メイン画面 ---
if uploaded_file_investors is not None:
    
    # 💡 自分で作った関数を使って安全に読み込む
    df_inv = load_csv_safe(uploaded_file_investors)
        
    required_columns_inv = ['ID', 'fundID', 'メールアドレス']
    missing_columns_inv = [col for col in required_columns_inv if col not in df_inv.columns]
    
    if missing_columns_inv:
        st.error(f"エラー: 出資者一覧CSVに以下の必須項目が見つかりません: {', '.join(missing_columns_inv)}")
        st.info("※もし「ID」や「メールアドレス」の列があるはずなのにこのエラーが出る場合、ファイルが『Excelファイル(.xlsx)』のままになっていないか（正しい手順でCSV保存されているか）ご確認ください。")
    else:
        # 2. 配布済みリストの読み込みと集計
        gift_summary = pd.DataFrame(columns=['メールアドレス', '配布済金額'])
        
        if uploaded_file_gifts is not None:
            # 💡 ここも関数を使って安全に読み込む
            df_gift = load_csv_safe(uploaded_file_gifts)
            
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
            st.toast("出資者一覧を読み込みました。（配布済みリスト未アップロード）", icon="✅")

        # --- 3. データの前処理と集約 ---
        st.write("### 📊 計算結果レポート")
        df_inv['fundID'] = pd.to_numeric(df_inv['fundID'], errors='coerce')
        
        grouped = df_inv.groupby('ID').agg(
            fund_list=('fundID', lambda x: list(x.dropna())),
            メールアドレス=('メールアドレス', 'first')
        ).reset_index()

        # --- 4. 2つのデータを結合 ---
        merged_df = pd.merge(grouped, gift_summary, on='メールアドレス', how='left')
        merged_df['配布済金額'] = merged_df['配布済金額'].fillna(0)

        # --- 5. ギフト対象金額の判定ロジック ---
        def calculate_gift(funds):
            has_1_to_4 = any(f in [1, 2, 3, 4] for f in funds)
            has_5_or_6 = any(f in [5, 6] for f in funds)
            has_5_or_more = any(f >= 5 for f in funds)
            
            if has_1_to_4 and not has_5_or_more:
                return 0
            elif has_1_to_4 and has_5_or_6:
                return 4000
            elif not has_1_to_4 and has_5_or_more:
                return 2000
            else:
                return 0 

        merged_df['対象金額'] = merged_df['fund_list'].apply(calculate_gift)
        merged_df['今回配布金額'] = merged_df['対象金額'] - merged_df['配布済金額']
        merged_df['今回配布金額'] = merged_df['今回配布金額'].apply(lambda x: max(0, x))

        # --- 6. 結果の表示 ---
        target_df = merged_df[merged_df['対象金額'] > 0].copy()
        target_df = target_df[['ID', 'メールアドレス', 'fund_list', '対象金額', '配布済金額', '今回配布金額']]
        target_df = target_df.rename(columns={'fund_list': '保有fundID一覧'})

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="🎯 今回の新規配布対象者数", value=f"{len(target_df[target_df['今回配布金額'] > 0])} 名")
        with col2:
            st.metric(label="💰 今回の配布予定総額", value=f"¥ {int(target_df['今回配布金額'].sum()):,}")
        with col3:
            st.metric(label="（参考）本来の対象総額", value=f"¥ {int(target_df['対象金額'].sum()):,}")

        st.write("")
        
        tab1, tab2 = st.tabs(["🎁 今回配布するリスト", "📋 全員の計算結果（確認用）"])
        
        with tab1:
            distribute_df = target_df[target_df['今回配布金額'] > 0]
            if len(distribute_df) > 0:
                st.write("今回、新たにギフトを配布する必要がある対象者の一覧です。")
                st.dataframe(distribute_df, use_container_width=True)
                
                csv_data = distribute_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 今回配布リストをダウンロード", data=csv_data, file_name="ギフト今回配布リスト.csv", mime="text/csv")
            else:
                st.info("全員に配布済みか、新たに対象となる人がいません。")
                
        with tab2:
            st.write("対象外の人も含めた、全IDの判定結果です。")
            st.dataframe(merged_df[['ID', 'メールアドレス', 'fund_list', '対象金額', '配布済金額', '今回配布金額']], use_container_width=True)

else:
    st.info("左のパネルからCSVファイルをアップロードすると、自動計算がスタートします。")
