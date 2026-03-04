import streamlit as st
import pandas as pd

st.set_page_config(page_title="GiftCalc Engine", layout="wide", initial_sidebar_state="expanded")

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

st.title(":orange[🎁 GiftCalc Engine]")
st.markdown("##### Amazonギフト配布対象者・金額の自動計算ツール（連携版）")

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
               "※「6r」は5以降の別ファンドとして判定し、正しく表示します。\n"
               "※「1~4」と「6r」のみを持つ場合は0円と判定します。")

if uploaded_file_investors is not None:
    df_inv = load_csv_safe(uploaded_file_investors)
    required_columns_inv = ['ID', 'fundID', 'メールアドレス']
    missing_columns_inv = [col for col in required_columns_inv if col not in df_inv.columns]
    
    if missing_columns_inv:
        st.error(f"エラー: 出資者一覧CSVに以下の必須項目が見つかりません: {', '.join(missing_columns_inv)}")
    else:
        gift_summary = pd.DataFrame(columns=['メールアドレス', '配布済金額'])
        if uploaded_file_gifts is not None:
            df_gift = load_csv_safe(uploaded_file_gifts)
            required_columns_gift = ['受取人様Eメール', '金額']
            missing_columns_gift = [col for col in required_columns_gift if col not in df_gift.columns]
            if not missing_columns_gift:
                df_gift['金額'] = df_gift['金額'].astype(str).str.replace(',', '', regex=False).str.replace('¥', '', regex=False).str.replace('円', '', regex=False)
                df_gift['金額'] = pd.to_numeric(df_gift['金額'], errors='coerce').fillna(0)
                gift_summary = df_gift.groupby('受取人様Eメール')['金額'].sum().reset_index()
                gift_summary = gift_summary.rename(columns={'受取人様Eメール': 'メールアドレス', '金額': '配布済金額'})
                st.toast("2つのファイルの読み込み・照合に成功しました！", icon="✅")
        else:
            st.toast("出資者一覧を読み込みました。", icon="✅")

        st.write("### 📊 計算結果レポート")
        
        # 💡 【見た目のクリーンアップ＆「6r」保護処理】
        # 1. 本当の空欄を除外
        df_inv = df_inv.dropna(subset=['fundID']).copy() 
        
        # 2. 文字列に変換し、末尾の「.0」だけを安全に消去（6rなどの文字はそのまま残る）
        df_inv['fundID'] = df_inv['fundID'].astype(str).str.strip()
        df_inv['fundID'] = df_inv['fundID'].str.replace(r'\.0$', '', regex=True)
        
        # 3. nanという文字になってしまったものを除外
        df_inv = df_inv[df_inv['fundID'].str.lower() != 'nan'] 
        
        grouped = df_inv.groupby('ID').agg(
            fund_list=('fundID', lambda x: list(x)),
            メールアドレス=('メールアドレス', 'first')
        ).reset_index()

        merged_df = pd.merge(grouped, gift_summary, on='メールアドレス', how='left')
        merged_df['配布済金額'] = merged_df['配布済金額'].fillna(0)

        def calculate_gift(funds):
            has_1_to_4 = False
            has_5_or_6 = False
            has_5_or_more = False
            
            for f in funds:
                f_lower = f.lower() # 大文字の「6R」でも正しく判定できるように小文字化してチェック
                
                if f_lower in ['1', '2', '3', '4']:
                    has_1_to_4 = True
                if f_lower in ['5', '6']:
                    has_5_or_6 = True
                
                # 5以降の判定（6rを含む）
                if f_lower == '6r':
                    has_5_or_more = True
                else:
                    try:
                        # 6r以外の数字（10など）はここで判定
                        if float(f) >= 5:
                            has_5_or_more = True
                    except:
                        pass
            
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

        target_df = merged_df[merged_df['対象金額'] > 0].copy()
        
        # 💡 リストをカンマ区切りで綺麗に結合（例: ['1', '6r'] → "1, 6r" ）
        target_df['保有fundID一覧'] = target_df['fund_list'].apply(lambda x: ', '.join(x))
        target_df = target_df[['ID', 'メールアドレス', '保有fundID一覧', '対象金額', '配布済金額', '今回配布金額']]

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
                st.dataframe(distribute_df, use_container_width=True)
                csv_data = distribute_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 今回配布リストをダウンロード", data=csv_data, file_name="ギフト今回配布リスト.csv", mime="text/csv")
            else:
                st.info("全員に配布済みか、新たに対象となる人がいません。")
                
        with tab2:
            merged_display = merged_df.copy()
            merged_display['保有fundID一覧'] = merged_display['fund_list'].apply(lambda x: ', '.join(x))
            st.dataframe(merged_display[['ID', 'メールアドレス', '保有fundID一覧', '対象金額', '配布済金額', '今回配布金額']], use_container_width=True)

else:
    st.info("左のパネルからCSVファイルをアップロードすると、自動計算がスタートします。")
