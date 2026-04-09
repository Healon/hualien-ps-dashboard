# ============================================================
#  醫療病人安全互動式視覺化儀表板  v3.1
#  修正：所有圖表 X/Y 軸標題顏色統一為深色高對比
#  SAC 定義：1=死亡、2=重大傷害、3=輕中度、4=無傷害
# ============================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="病人安全事件儀表板",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 全域樣式 ─────────────────────────────────────────────────
st.markdown("""
<style>
    * { font-family: Arial, 'Helvetica Neue', sans-serif !important; }
    .stApp { background-color: #F8F9FA; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2e3d 0%, #2C3E50 100%);
    }
    [data-testid="stSidebar"] * { color: #D6EAF8 !important; }
    [data-testid="stSidebar"] label { color: #AED6F1 !important; font-weight: 600; }

    .kpi-card {
        background: #FFFFFF; border-radius: 10px; padding: 18px 22px;
        box-shadow: 0 1px 8px rgba(0,0,0,0.09);
        border-left: 5px solid #3498DB; margin-bottom: 10px; min-height: 108px;
    }
    .kpi-card.danger  { border-left-color: #E74C3C; }
    .kpi-card.warning { border-left-color: #F39C12; }
    .kpi-card.death   { border-left-color: #C0392B; }

    .kpi-label {
        font-size: 11px; color: #2C3E50; font-weight: 700;
        letter-spacing: 0.6px; margin-bottom: 5px; text-transform: uppercase;
    }
    .kpi-value { font-size: 36px; font-weight: 900; color: #1C2833; line-height: 1.1; }
    .kpi-card.danger  .kpi-value { color: #922B21; }
    .kpi-card.warning .kpi-value { color: #7D6608; }
    .kpi-card.death   .kpi-value { color: #7B241C; }
    .kpi-sub { font-size: 11px; color: #4D5656; margin-top: 4px; font-weight: 500; }

    .chart-container {
        background: #FFFFFF; border-radius: 10px; padding: 20px;
        box-shadow: 0 1px 8px rgba(0,0,0,0.07); margin-bottom: 16px;
    }
    .section-title {
        font-size: 15px; font-weight: 700; color: #2C3E50; margin-bottom: 4px;
    }
    hr { border-color: #EAECEE; }

    /* ── Tab 標籤文字高對比（覆蓋 Streamlit 所有版本的 selector）── */
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span,
    .stTabs [data-baseweb="tab"] {
        color: #1C2833 !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        opacity: 1 !important;
    }
    /* 選中 tab：深藍色 + 底線加粗 */
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] span,
    .stTabs [aria-selected="true"] {
        color: #154360 !important;
        font-weight: 800 !important;
        opacity: 1 !important;
    }
    /* 未選中 tab 保持深灰可讀 */
    .stTabs [aria-selected="false"] p,
    .stTabs [aria-selected="false"] span,
    .stTabs [aria-selected="false"] {
        color: #2C3E50 !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }
    /* Tab 底線顏色加深 */
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #1A5276 !important;
        height: 3px !important;
    }
    .stTabs [data-baseweb="tab-border"] {
        background-color: #AEB6BF !important;
    }
</style>
""", unsafe_allow_html=True)


# ── 軸標題統一樣式（深色，確保可讀）────────────────────────
# 所有圖表軸標題使用此字典，確保顏色一致
AXIS_TITLE_FONT  = dict(size=13, color="#1C2833", family="Arial")   # 深黑，最高對比
AXIS_TICK_FONT   = dict(size=10, color="#2C3E50", family="Arial")   # 深藍灰
TITLE_FONT       = dict(size=16, color="#2C3E50", family="Arial")
GRID_COLOR       = "#EAECEE"
ZERO_LINE_COLOR  = "#BDC3C7"
PLOT_BG          = "#FFFFFF"
PAPER_BG         = "#FFFFFF"

# ── 常數 ─────────────────────────────────────────────────────
TIMESLOT_MAP = {
    "00:01-02:00":"00-02時","00:00-02:00":"00-02時",
    "02:01-04:00":"02-04時","02:00-04:00":"02-04時",
    "04:01-06:00":"04-06時","04:00-06:00":"04-06時",
    "06:01-08:00":"06-08時","06:00-08:00":"06-08時",
    "08:01-10:00":"08-10時","08:00-10:00":"08-10時",
    "10:01-12:00":"10-12時","10:00-12:00":"10-12時",
    "12:01-14:00":"12-14時","12:00-14:00":"12-14時",
    "14:01-16:00":"14-16時","14:00-16:00":"14-16時",
    "16:01-18:00":"16-18時","16:00-18:00":"16-18時",
    "18:01-20:00":"18-20時","18:00-20:00":"18-20時",
    "20:01-22:00":"20-22時","20:00-22:00":"20-22時",
    "22:01-24:00":"22-24時","22:00-24:00":"22-24時",
}
TIMESLOT_ORDER = [
    "00-02時","02-04時","04-06時","06-08時","08-10時","10-12時",
    "12-14時","14-16時","16-18時","18-20時","20-22時","22-24時",
]
CATEGORY_COLORS = {
    "跌倒":"#003f5c","藥物":"#444e86","管路":"#955196",
    "傷害":"#dd5182","醫療":"#ff6e54","治安":"#ffa600","其他":"#7F8C8D",
}
SAC_DESC   = {1:"死亡", 2:"重大傷害", 3:"輕中度", 4:"無傷害"}
SAC_COLORS = {1:"#7B241C", 2:"#C0392B", 3:"#F39C12", 4:"#1E8449"}
HIGH_SAC   = [1, 2]

CTRL_CL_COLOR   = "#5D6D7E"
CTRL_UCL_COLOR  = "#E74C3C"
CTRL_BAND_FILL  = "rgba(44,62,80,0.06)"
OUTLIER_COLOR   = "#C0392B"


# ── 資料載入 ─────────────────────────────────────────────────
@st.cache_data(show_spinner="📂 載入資料中...")
def load_data(path):
    xl  = pd.ExcelFile(path)
    df  = pd.read_excel(xl, sheet_name="109-113全部")
    df["發生日期"] = pd.to_datetime(df["發生日期"], errors="coerce")
    df  = df[df["發生日期"].notna()].copy()
    df["年月"]    = df["發生日期"].dt.to_period("M").astype(str)
    df["SAC_num"] = pd.to_numeric(df["SAC"], errors="coerce")
    df["單位"]    = (df["通報者資料-通報者服務單位"]
                     .astype(str).str.strip().str.upper()
                     .replace({"NAN":"未知","":"未知"}))
    df["時段標準"] = df["發生時段"].map(TIMESLOT_MAP)
    cat_map = {
        "跌倒事件":"跌倒","藥物事件":"藥物","管路事件":"管路",
        "傷害行為":"傷害","醫療事件":"醫療","治安事件":"治安",
        "手術事件":"醫療","麻醉事件":"醫療","輸血事件":"醫療",
        "不預期心跳停止":"醫療","檢查檢驗":"其他","檢驗檢查":"其他",
        "公共意外":"其他","其他事件":"其他",
    }
    df["事件大類"] = df["事件類別"].map(cat_map).fillna("其他")

    # ── 診斷分類函數 (classify_dx) ──────────────────────────
    def classify_dx(text):
        if pd.isna(text): return "其他"
        t = str(text).lower()
        if any(k in t for k in ["思覺失調","精神病","psycho","schizo"]):
            return "思覺失調/精神病"
        if any(k in t for k in ["雙相","躁症","bipolar","manic"]):
            return "雙相/躁症"
        if any(k in t for k in ["憂鬱","depression","depressive"]):
            return "憂鬱症"
        if any(k in t for k in ["失智","dementia"]):
            return "失智症"
        if any(k in t for k in ["帕金森","parkinson"]):
            return "帕金森氏症"
        if any(k in t for k in ["腦梗","中風","stroke","i63","i64",
                                  "腦血管","腦出血","ich"]):
            return "腦血管病"
        if any(k in t for k in ["骨折","fr.","fracture"," # "]):
            return "骨折相關"
        if any(k in t for k in ["糖尿病","diabetes"," dm","dm ","dm,","dm."]):
            return "糖尿病"
        if any(k in t for k in ["腎病","ckd","腎衰","腎功能"]):
            return "腎病"
        if any(k in t for k in ["肝病","肝炎","肝硬化","肝衰"]):
            return "肝病"
        if any(k in t for k in ["心臟","心衰","心肌","冠狀動脈","心房","心室"]):
            return "心臟病"
        if any(k in t for k in ["肺炎","呼吸","copd","氣喘","支氣管"]):
            return "呼吸系統"
        if any(k in t for k in ["癌","腫瘤","惡性","malignant","carcinoma","lymphoma"]):
            return "腫瘤/癌症"
        return "其他"

    df["診斷分類"] = df["發生者資料-診斷"].apply(classify_dx)

    # ── 跌倒深度分析資料（跌倒工作表 merge 全部工作表科別與影響程度）
    df_fall = pd.read_excel(xl, sheet_name="109-113跌倒")
    df_fall["發生日期"] = pd.to_datetime(df_fall["發生日期"], errors="coerce")
    df_fall = df_fall[df_fall["發生日期"].notna()].copy()
    df_fall["年月"] = df_fall["發生日期"].dt.to_period("M").astype(str)
    cols_from_all = [
        "通報案號",
        "病人/住民-所在科別",
        "病人/住民-事件發生後對病人健康的影響程度",
        "病人/住民-事件發生後對病人健康的影響程度(彙總)",
        "單位",   # 供精神科下鑽篩選使用
    ]
    # 去除空白避免比對失敗
    for col in cols_from_all[1:]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df_fall = df_fall.merge(df[cols_from_all], on="通報案號", how="left")

    # ── 事件說明特徵萃取 (extract_fall_features) ─────────────
    FALL_FEATURES = {
        "地點_床邊下床":     ["下床","床邊","起床","離床","坐起"],
        "地點_浴廁":        ["廁所","洗手間","浴室","如廁","洗澡"],
        "地點_走廊行走":     ["走廊","走路","行走","散步"],
        "地點_椅子輪椅":     ["椅子","輪椅","便盆椅"],
        "機轉_滑倒":        ["滑","打滑","濕"],
        "機轉_頭暈血壓低":   ["頭暈","暈","血壓低","姿位性"],
        "機轉_自行起身未告知":["自行","未按鈴","未通知","未叫護"],
        "機轉_站不穩腳軟":   ["站不穩","腳軟","無力","腿軟"],
        "發現_護理人員巡視":  ["巡房","巡視","護士發現","護理師發現"],
        "發現_聲響":        ["聲音","聲響","跌倒聲"],
        "傷害_頭部":        ["頭","額頭","頭皮"],
        "傷害_下肢":        ["腳","膝蓋","足部","下肢","腳踝"],
        "傷害_臀髖":        ["臀","髖"],
        "病況_精神症狀":     ["幻覺","妄想","躁動","激動","衝動"],
        "病況_約束相關":     ["約束","保護帶","掙脫","解開"],
    }
    def extract_fall_features(text):
        t = str(text) if not pd.isna(text) else ""
        return {feat: any(k in t for k in kws)
                for feat, kws in FALL_FEATURES.items()}

    feat_df = df_fall["事件說明"].apply(
        lambda x: pd.Series(extract_fall_features(x)))
    df_fall = pd.concat([df_fall.reset_index(drop=True),
                         feat_df.reset_index(drop=True)], axis=1)

    db  = pd.read_excel(xl, sheet_name="住院人日數")
    db["年月"] = pd.to_datetime(db["年月"]).dt.to_period("M").astype(str)
    db["單位"] = db["單位"].astype(str).str.strip().str.upper()
    tot = db.groupby("年月", as_index=False)["住院人日數"].sum()
    tot["單位"] = "全院"
    db  = pd.concat([db, tot], ignore_index=True)
    return df, db, df_fall

EXCEL_PATH = "109-113全部_藥物跌倒管路傷害醫療治安__115_02_01.xlsx"
try:
    df_all, df_bed, df_fall_base = load_data(EXCEL_PATH)
except FileNotFoundError:
    st.error(f"❌ 找不到資料檔：{EXCEL_PATH}，請確認與 app.py 在同一資料夾。")
    st.stop()
except Exception as e:
    st.error(f"❌ 載入失敗：{e}")
    st.stop()


# ════════════════════════════════════════════════════════════
#  資料清理：讀檔後、任何 groupby 之前套用
#  1) normalize_category：統一 NaN/空白/undefined/None
#  2) label_map：代碼 → 顯示名稱
#  3) 固定排序常數
# ════════════════════════════════════════════════════════════

def normalize_category(df, col, missing_label="未填/其他"):
    """把 NaN、空字串、'undefined'、'nan'、None 統一成 missing_label"""
    if col not in df.columns:
        return df
    df = df.copy()
    df[col] = (df[col].astype(str)
               .str.strip()
               .replace({"nan": missing_label,
                         "none": missing_label,
                         "None": missing_label,
                         "undefined": missing_label,
                         "Undefined": missing_label,
                         "": missing_label,
                         "NaN": missing_label}))
    df[col] = df[col].where(df[col].notna(), missing_label)
    return df

# ── 顯示名稱映射（代碼 → 中文顯示名稱）─────────────────────
LABEL_MAP = {
    # 傷害程度
    "無傷害":               "無傷害",
    "輕度":                 "輕度",
    "中度":                 "中度",
    "重度":                 "重度",
    "極重度":               "極重度",
    "死亡":                 "死亡",
    "無法判定傷害嚴重程度":   "無法判定",
    # 科別常見縮寫
    "PSYCH":  "精神科",
    "SURG":   "外科",
    "MED":    "內科",
    "REHAB":  "復健科",
    "LTC":    "護理之家",
    "ICU":    "加護病房",
    "NICU":   "新生兒加護",
    "ER":     "急診",
    "OR":     "手術室",
    # 單位代碼（W = Ward）
    "W11":  "W11病房", "W12":  "W12病房", "W13":  "W13病房",
    "W21":  "W21病房", "W22":  "W22病房", "W23":  "W23病房",
    "W31":  "W31病房", "W32":  "W32病房", "W33":  "W33病房",
    "W41":  "W41病房", "W42":  "W42病房",
}

def display_label(val, fallback=None):
    """取代碼的顯示名稱，找不到就回傳原值（或 fallback）"""
    return LABEL_MAP.get(str(val), fallback if fallback is not None else val)

# ── 固定排序常數 ─────────────────────────────────────────────
INJ_ORDER    = ["無傷害", "輕度", "中度", "重度", "極重度", "死亡", "無法判定"]
SAC_ORDER    = [1, 2, 3, 4]
INJ_LABEL_MAP = {
    "無傷害": "無傷害", "輕度": "輕度", "中度": "中度",
    "重度": "重度", "極重度": "極重度", "死亡": "死亡",
    "無法判定傷害嚴重程度": "無法判定",
}

# ── 套用 normalize_category 到關鍵欄位 ──────────────────────
_NORM_COLS_ALL = [
    "事件大類", "事件類別", "單位",
    "病人/住民-所在科別",
    "病人/住民-事件發生後對病人健康的影響程度",
    "病人/住民-事件發生後對病人健康的影響程度(彙總)",
    "通報者資料-工作年資", "SAC",
]
for _col in _NORM_COLS_ALL:
    df_all = normalize_category(df_all, _col)

_NORM_COLS_FALL = [
    "病人/住民-所在科別",
    "病人/住民-事件發生後對病人健康的影響程度",
    "病人/住民-事件發生後對病人健康的影響程度(彙總)",
    "跌倒事件發生對象-事件發生時有無陪伴者",
    "跌倒事件發生對象-事件發生前是否為跌倒高危險群",
    "跌倒事件發生對象-最近一年是否曾經跌倒",
    "跌倒事件發生對象-當事人當時意識狀況",
]
for _col in _NORM_COLS_FALL:
    df_fall_base = normalize_category(df_fall_base, _col)

# 傷害程度簡短標籤（顯示用）
_inj_col = "病人/住民-事件發生後對病人健康的影響程度"
if _inj_col in df_fall_base.columns:
    df_fall_base["傷害程度顯示"] = df_fall_base[_inj_col].map(
        INJ_LABEL_MAP).fillna(df_fall_base[_inj_col])
if _inj_col in df_all.columns:
    df_all["傷害程度顯示"] = df_all[_inj_col].map(
        INJ_LABEL_MAP).fillna(df_all[_inj_col])

# ════════════════════════════════════════════════════════════
#  session_state 全域篩選器初始化
# ════════════════════════════════════════════════════════════
_all_months = sorted(df_all["年月"].dropna().unique())
_data_start  = _all_months[0]
_data_end    = _all_months[-1]   # 永遠從資料動態取最新月份

def _ss_init(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

_ss_init("date_range",    (_data_start, _data_end))
_ss_init("event_type",    "全部")
_ss_init("dept",          "全部科別")
_ss_init("unit",          "全院")
_ss_init("feature_tag",   [])
_ss_init("loc_filter",    "全部地點")
_ss_init("inj_filter",    "全部傷害程度")

# ── 每次執行都強制把結束端點同步到資料最新月份 ────────────────
# 避免舊 session_state 記住過期的結束月份（資料更新後不會自動反映）
_cur_s, _cur_e = st.session_state["date_range"]
if _cur_e not in _all_months or _cur_e < _data_end:
    st.session_state["date_range"] = (_cur_s if _cur_s in _all_months else _data_start, _data_end)


def filter_df(base_df=None, use_fall=False):
    """
    統一篩選函數 — 所有圖表都呼叫此函數，避免各圖重複過濾不一致。
    base_df=None → 使用 df_all；use_fall=True → 使用 df_fall_base
    """
    src = (df_fall_base if use_fall else
           (base_df if base_df is not None else df_all))
    s, e = st.session_state["date_range"]
    df   = src[(src["年月"] >= s) & (src["年月"] <= e)].copy()

    if not use_fall:
        u = st.session_state["unit"]
        if u == "W11+W12（精神科）" and "單位" in df.columns:
            df = df[df["單位"].isin(["W11","W12"])]
        elif u != "全院" and "單位" in df.columns:
            df = df[df["單位"] == u]
        cat = st.session_state["event_type"]
        if cat != "全部" and "事件大類" in df.columns:
            df = df[df["事件大類"] == cat]
        # SAC 篩選固定全選（側邊欄已移除 SAC 篩選器）

    dept = st.session_state["dept"]
    dept_col = "病人/住民-所在科別"
    if dept != "全部科別" and dept_col in df.columns:
        df = df[df[dept_col] == dept]

    return df


def render_breadcrumb():
    """麵包屑導航：全院 > 科別 > 單位 > 個案"""
    parts = ["🏥 全院"]
    dept = st.session_state.get("dept", "全部科別")
    unit = st.session_state.get("unit", "全院")
    feat = st.session_state.get("feature_tag", [])
    if dept != "全部科別":
        parts.append(f"🏬 {dept}")
    if unit != "全院":
        parts.append(f"🛏 {unit}")
    if feat:
        parts.append(f"🔍 {' + '.join(feat[:2])}{'…' if len(feat)>2 else ''}")
    crumb_html = " <span style='color:#AEB6BF'>›</span> ".join(
        [f"<span style='color:#2E86C1;font-weight:600'>{p}</span>" for p in parts]
    )
    st.markdown(
        f"<div style='font-size:13px;padding:6px 0 10px 0'>{crumb_html}</div>",
        unsafe_allow_html=True,
    )


# ── 側邊欄 ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏥 病人安全儀表板")
    st.markdown("**國軍花蓮總醫院**")
    st.markdown("---")

    all_months = sorted(df_all["年月"].dropna().unique())
    st.markdown("### 📅 時間區間")
    _cur_range = st.session_state["date_range"]
    # 確保兩端點都在合法月份清單內
    _s = _cur_range[0] if _cur_range[0] in all_months else all_months[0]
    _e = _cur_range[1] if _cur_range[1] in all_months else all_months[-1]
    month_range = st.select_slider("月份", options=all_months,
        value=(_s, _e), label_visibility="collapsed", key="_slider_month")
    st.session_state["date_range"] = month_range
    start_m, end_m = month_range

    st.markdown("---")
    st.markdown("### 🏬 發生單位")
    unit_opts = ["全院", "W11+W12（精神科）"] + sorted(
        [u for u in df_all["單位"].dropna().unique()
         if u not in ["未知","未填/其他",""]])
    _u = st.session_state["unit"]
    sel_unit = st.selectbox("單位", unit_opts,
        index=unit_opts.index(_u) if _u in unit_opts else 0,
        label_visibility="collapsed", key="_sb_unit")
    st.session_state["unit"] = sel_unit

    st.markdown("---")
    st.markdown("### 📋 事件類別")
    cat_opts = ["全部"] + sorted(df_all["事件大類"].unique())
    _c = st.session_state["event_type"]
    sel_cat = st.selectbox("類別", cat_opts,
        index=cat_opts.index(_c) if _c in cat_opts else 0,
        label_visibility="collapsed", key="_sb_cat")
    st.session_state["event_type"] = sel_cat

    st.markdown("---")
    st.markdown("### 🏥 診斷科別篩選")
    dept_all_opts = ["全部科別"] + sorted(
        [d for d in df_all["病人/住民-所在科別"].dropna().unique()
         if str(d).strip() not in ["", "nan", "未填/其他"]])
    _d = st.session_state["dept"]
    sel_dept = st.selectbox("診斷科別", dept_all_opts,
        index=dept_all_opts.index(_d) if _d in dept_all_opts else 0,
        label_visibility="collapsed",
        help="用於診斷特徵分析與跌倒深度分析",
        key="_sb_dept")
    st.session_state["dept"] = sel_dept

    # ── 特徵標籤篩選器 ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 特徵標籤篩選")
    _feat_opts = [
        "地點_床邊下床","地點_浴廁","地點_走廊行走","地點_椅子輪椅",
        "機轉_滑倒","機轉_頭暈血壓低","機轉_自行起身未告知","機轉_站不穩腳軟",
        "發現_護理人員巡視","發現_聲響","病況_精神症狀","病況_約束相關",
    ]
    sel_feats = st.multiselect(
        "選取特徵（留空=全部）", options=_feat_opts,
        default=st.session_state["feature_tag"],
        label_visibility="collapsed",
        help="選擇後，事件明細表只顯示含該特徵的案例",
        key="_ms_feat")
    st.session_state["feature_tag"] = sel_feats

    # ── 地點 × 傷害程度 下鑽篩選器 ───────────────────────────
    st.markdown("---")
    st.markdown("### 📍 地點 × 傷害程度 下鑽")
    _loc_opts  = ["全部地點", "床邊下床", "浴廁", "走廊行走", "椅子輪椅"]
    _inj_disp  = ["全部傷害程度", "無傷害", "輕度", "中度",
                  "重度", "極重度", "死亡", "無法判定"]
    _lv = st.session_state["loc_filter"]
    _iv = st.session_state["inj_filter"]
    sel_loc = st.selectbox("發生地點", _loc_opts,
        index=_loc_opts.index(_lv) if _lv in _loc_opts else 0,
        label_visibility="collapsed", key="_sb_loc")
    sel_inj_drill = st.selectbox("傷害程度", _inj_disp,
        index=_inj_disp.index(_iv) if _iv in _inj_disp else 0,
        label_visibility="collapsed", key="_sb_inj")
    st.session_state["loc_filter"] = sel_loc
    st.session_state["inj_filter"] = sel_inj_drill
    if st.button("🔄 清除地點/傷害篩選", key="_btn_clear_loc"):
        st.session_state["loc_filter"]  = "全部地點"
        st.session_state["inj_filter"]  = "全部傷害程度"
        st.rerun()

    st.markdown("---")
    st.markdown("""<div style='font-size:11px;color:#85C1E9;line-height:2.0'>
    📌 資料來源：病人安全通報系統<br>
    📆 資料期間：109–113 年<br>
    🔄 最後更新：115/02/01<br>
    🔖 版本：v3.5</div>""", unsafe_allow_html=True)
    st.markdown("---")


# ── 過濾（使用 filter_df() 統一介面，同時保留舊變數名稱相容）────
dff      = filter_df()
dff_fall = filter_df(use_fall=True)
dff_dx   = filter_df()   # 已含 sel_dept 篩選（filter_df 內處理）

bed_key  = ("全院" if sel_unit in ["全院","W11+W12（精神科）"]
             else sel_unit)
df_bed_f = df_bed[df_bed["單位"] == bed_key].copy()
mc = dff.groupby("年月").size().reset_index(name="件數").sort_values("年月")
mc = mc.merge(df_bed_f[["年月","住院人日數"]], on="年月", how="left")
mc["發生率"] = (mc["件數"] / mc["住院人日數"] * 1000).round(2).fillna(0)
mc["年月顯示"] = mc["年月"].str.replace("-", "/", regex=False)
dff["年月顯示"] = dff["年月"].str.replace("-", "/", regex=False)

# ════════════════════════════════════════════════════════════
#  📅 年度比較分析（2024 vs 2025）— 固定全院層級
#  不受科別篩選器影響；使用 df_fall_base（全量跌倒資料）
# ════════════════════════════════════════════════════════════

# ── 住院 / 含護理之家 切換 ────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📅 年度比較範圍")
    inc_ltc = st.radio("跌倒統計範圍", ["只看住院", "含護理之家"],
                       index=0, horizontal=True,
                       label_visibility="collapsed")

EXCLUDE_DEPT = [] if inc_ltc == "含護理之家" else ["護理之家"]

# 全量跌倒資料（含年份欄位）—— 年度比較專用
_fb = df_fall_base.copy()
_fb["年"]  = pd.to_datetime(_fb["年月"], format="%Y-%m").dt.year
_fb["月"]  = pd.to_datetime(_fb["年月"], format="%Y-%m").dt.month
if EXCLUDE_DEPT:
    _fb = _fb[~_fb["病人/住民-所在科別"].isin(EXCLUDE_DEPT)]

_fb24 = _fb[_fb["年"] == 2024]
_fb25 = _fb[_fb["年"] == 2025]

INJ_COL_SUM  = "病人/住民-事件發生後對病人健康的影響程度(彙總)"
INJ_COL_DET  = "病人/住民-事件發生後對病人健康的影響程度"
DEPT_COL_YR  = "病人/住民-所在科別"

# 全院事件（傷害行為）
_all_yr = df_all.copy()
_all_yr["年"] = pd.to_datetime(
    _all_yr["年月"], format="%Y-%m", errors="coerce").dt.year
_all_yr["月"] = pd.to_datetime(
    _all_yr["年月"], format="%Y-%m", errors="coerce").dt.month
_harm24 = _all_yr[(_all_yr["年"]==2024) & (_all_yr["事件大類"]=="傷害")]
_harm25 = _all_yr[(_all_yr["年"]==2025) & (_all_yr["事件大類"]=="傷害")]
_harm25_last_m = int(_harm25["月"].max()) if not _harm25.empty else 1

def _safe_pct(num, den):
    return round(num / den * 100, 1) if den > 0 else 0.0

def _inj_rate(df):
    if INJ_COL_SUM not in df.columns: return 0.0
    n = len(df)
    return _safe_pct((df[INJ_COL_SUM] == "有傷害").sum(), n)

def _psych_pct(df):
    if DEPT_COL_YR not in df.columns: return 0.0
    return _safe_pct((df[DEPT_COL_YR] == "精神科").sum(), len(df))

def _mid_above_rate(df):
    if INJ_COL_DET not in df.columns: return 0.0
    sub = df[df[DEPT_COL_YR].isin(["外科","內科"])]
    return _safe_pct(
        sub[INJ_COL_DET].isin(["中度","重度","極重度","死亡"]).sum(),
        len(sub))

# 指標計算
v24_inj    = _inj_rate(_fb24)
v25_inj    = _inj_rate(_fb25)
v24_psych  = _psych_pct(_fb24)
v25_psych  = _psych_pct(_fb25)
v24_mid    = _mid_above_rate(_fb24)
v25_mid    = _mid_above_rate(_fb25)
n24_harm   = len(_harm24)
n25_harm   = len(_harm25)
harm25_est = round(n25_harm / _harm25_last_m * 12) if _harm25_last_m > 0 else n25_harm

# ── 頁首 ─────────────────────────────────────────────────────
st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
            padding:20px 28px;border-radius:10px;margin-bottom:12px'>
  <h2 style='color:#FFFFFF;margin:0;font-size:21px;font-weight:700'>
    🏥 醫療病人安全事件互動式儀表板
  </h2>
  <p style='color:#AED6F1;margin:5px 0 0;font-size:12px'>
    國軍花蓮總醫院｜{start_m} ～ {end_m}｜單位：{sel_unit}｜類別：{sel_cat}
  </p>
</div>""", unsafe_allow_html=True)

render_breadcrumb()

if dff.empty:
    st.markdown('<div style="background:#FFF3CD;border-left:4px solid #F39C12;padding:10px 14px;border-radius:4px;color:#7D4700;font-size:13px">⚠️ 目前篩選條件下無資料，請調整側邊欄設定。</div>', unsafe_allow_html=True)
    st.stop()


_tab1, _tab2, _tab3, _tab4 = st.tabs([
    "🎯 即時監控戰情室",
    "📈 跌倒事件分析",
    "💊 藥物安全分析",
    "⚠️ 傷害行為分析",
])

with _tab1:


    # ════════════════════════════════════════════════════════════
    #  PAGE 1 · Level 1：近一個月即時警示（Executive Summary）
    # ════════════════════════════════════════════════════════════
    _all_m_sorted = sorted(dff["年月"].dropna().unique())
    _last_m = _all_m_sorted[-1] if _all_m_sorted else None
    _prev_m = _all_m_sorted[-2] if len(_all_m_sorted) >= 2 else None

    def _safe_count(df, month):
        if month is None: return 0
        sub = df[df["年月"] == month]
        return int(sub["編號"].count()) if "編號" in sub.columns else len(sub)

    _n_last = _safe_count(dff, _last_m)
    _n_prev = _safe_count(dff, _prev_m)
    _mom_delta = _n_last - _n_prev

    _rate_last = float(mc[mc["年月"]==_last_m]["發生率"].values[0]) if _last_m and _last_m in mc["年月"].values else 0.0
    _rate_prev = float(mc[mc["年月"]==_prev_m]["發生率"].values[0]) if _prev_m and _prev_m in mc["年月"].values else 0.0
    _rate_delta = round(_rate_last - _rate_prev, 2)

    _rates_clean = mc["發生率"].replace(0, np.nan).dropna()
    _ucl_val = float(_rates_clean.mean() + 3*_rates_clean.std()) if len(_rates_clean) >= 3 else 9999.0
    _breach_ucl = bool(_rate_last > _ucl_val)

    _sac12_last = int(dff[(dff["年月"]==_last_m) & (dff["SAC_num"].isin([1,2]))]["SAC_num"].count()) if _last_m else 0
    _sac12_prev = int(dff[(dff["年月"]==_prev_m) & (dff["SAC_num"].isin([1,2]))]["SAC_num"].count()) if _prev_m else 0

    def _led(delta, up_is_bad=True):
        if delta > 0: return ("#C0392B","#FADBD8","▲") if up_is_bad else ("#1E8449","#D5F5E3","▲")
        if delta < 0: return ("#1E8449","#D5F5E3","▼") if up_is_bad else ("#C0392B","#FADBD8","▼")
        return "#7F8C8D","#F4F6F6","─"

    _nc,_nb,_na = _led(_mom_delta)
    _rc,_rb,_ra = _led(_rate_delta)
    _sc,_sb,_sa = _led(_sac12_last)
    _ucl_led  = "#E74C3C" if _breach_ucl else "#27AE60"
    _ucl_bg   = "#FADBD8" if _breach_ucl else "#D5F5E3"
    _ucl_txt  = "⚠️ 突破 UCL！異常訊號" if _breach_ucl else "✅ 在管制界限內"

    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
                padding:14px 22px;border-radius:10px;margin-bottom:14px'>
      <h2 style='color:#FFFFFF;margin:0;font-size:19px;font-weight:700'>
        🎯 即時監控戰情室
      </h2>
      <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
        Level 1 · Executive Summary · 篩選期間：{start_m} ～ {end_m}（區間末月：{_last_m}）
      </p>
    </div>""", unsafe_allow_html=True)

    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        st.markdown(f"""<div style='background:#FFFFFF;border-left:5px solid {_nc};border-radius:10px;
            padding:16px 18px;box-shadow:0 2px 8px rgba(0,0,0,0.09)'>
      <div style='font-size:11px;color:#5D6D7E;font-weight:700'>📅 本月總件數</div>
      <div style='font-size:34px;font-weight:900;color:#1C2833;margin:6px 0'>{_n_last}</div>
      <div style='font-size:11px;font-weight:700;color:{_nc};background:{_nb};
                  border-radius:4px;padding:3px 8px;display:inline-block'>
        {_na} {_mom_delta:+d} 件 MoM（上月 {_n_prev} 件）
      </div></div>""", unsafe_allow_html=True)

    with _c2:
        st.markdown(f"""<div style='background:#FFFFFF;border-left:5px solid {_ucl_led};border-radius:10px;
            padding:16px 18px;box-shadow:0 2px 8px rgba(0,0,0,0.09)'>
      <div style='font-size:11px;color:#5D6D7E;font-weight:700'>📈 本月發生率（‰）</div>
      <div style='font-size:34px;font-weight:900;color:#1C2833;margin:6px 0'>{_rate_last:.2f}‰</div>
      <div style='font-size:11px;font-weight:700;color:{_ucl_led};background:{_ucl_bg};
                  border-radius:4px;padding:3px 8px;display:inline-block'>
        {_ucl_txt}（UCL={_ucl_val:.2f}‰）
      </div></div>""", unsafe_allow_html=True)

    with _c3:
        _sac_led = "#E74C3C" if _sac12_last>0 else "#27AE60"
        _sac_bg  = "#FADBD8" if _sac12_last>0 else "#D5F5E3"
        _sac_lbl = "⛔ 需立即關注！" if _sac12_last>0 else "✅ 本月無重大傷亡"
        st.markdown(f"""<div style='background:#FFFFFF;border-left:5px solid {_sac_led};border-radius:10px;
            padding:16px 18px;box-shadow:0 2px 8px rgba(0,0,0,0.09)'>
      <div style='font-size:11px;color:#5D6D7E;font-weight:700'>🚨 SAC 1+2 本月件數</div>
      <div style='font-size:34px;font-weight:900;color:#1C2833;margin:6px 0'>{_sac12_last}</div>
      <div style='font-size:11px;font-weight:700;color:{_sac_led};background:{_sac_bg};
                  border-radius:4px;padding:3px 8px;display:inline-block'>
        {_sac_lbl}（上月 {_sac12_prev} 件）
      </div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    #  PAGE 1 · Level 2：系統安全與通報品質
    # ════════════════════════════════════════════════════════════
    st.markdown("""<div style='background:#F0F3F4;border-radius:8px;
        padding:10px 16px;margin-bottom:12px'>
      <span style='font-size:14px;font-weight:700;color:#2C3E50'>
        🏗 Level 2 — 系統安全與通報品質檢驗
      </span>
      <span style='font-size:11px;color:#5D6D7E;margin-left:8px'>
        事件類別件數排行 · 事件類別佔比分布
      </span>
    </div>""", unsafe_allow_html=True)

    # ── 計算事件類別統計（隨時間區間連動）───────────────────
    _cc = (dff["事件大類"].value_counts()
           .reset_index()
           .rename(columns={"事件大類":"類別","count":"件數"}))
    if "件數" not in _cc.columns:
        _cc.columns = ["類別","件數"]
    _cc = _cc.sort_values("件數", ascending=False).reset_index(drop=True)

    # 前三名亮色，其他淡色
    _TOP3_BRIGHT = ["#E74C3C","#E67E22","#2471A3"]
    _DIM_COLOR   = "#BDC3C7"
    # 統一顏色陣列：前三名用 _TOP3_BRIGHT，其餘淡色
    # 長條圖與甜甜圈都用此陣列，確保顏色完全一致
    _unified_colors = [_TOP3_BRIGHT[i] if i < 3 else _DIM_COLOR
                       for i in range(len(_cc))]
    _bar_colors  = _unified_colors

    _l2a, _l2b = st.columns([1.4, 1])

    with _l2a:
        # ── 事件類別長條圖（X=類別，Y=件數，依件數降冪，隨篩選動態排列）
        st.markdown('<p class="section-title">📊 各事件類別發生件數（依件數排列）</p>',
                    unsafe_allow_html=True)
        st.caption("件數排序隨篩選時間區間即時更新；🔴🟠🔵 = 前三高發類別")

        _cc_bar = _cc.sort_values("件數", ascending=False).reset_index(drop=True)
        fig_cat_bar = go.Figure(go.Bar(
            x=_cc_bar["類別"],
            y=_cc_bar["件數"],
            marker_color=_bar_colors[:len(_cc_bar)],
            marker_opacity=0.88,
            text=_cc_bar["件數"],
            textposition="outside",
            textfont=dict(size=11, color="#1C2833", family="Arial Bold"),
            hovertemplate="<b>%{x}</b>：%{y} 件<extra></extra>",
        ))
        fig_cat_bar.update_layout(
            height=320,
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="事件類別", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                categoryorder="total descending",
                showgrid=False,
            ),
            yaxis=dict(
                title=dict(text="發生件數", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                gridcolor=GRID_COLOR, griddash="dot",
                zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
                range=[0, _cc_bar["件數"].max() * 1.25],
            ),
            margin=dict(t=20, b=50, l=60, r=30),
            bargap=0.3,
        )
        st.plotly_chart(fig_cat_bar, use_container_width=True)

    with _l2b:
        # ── 事件類別甜甜圈（前三名亮色，其他淡色）────────────
        st.markdown('<p class="section-title">🍩 事件類別佔比分布</p>',
                    unsafe_allow_html=True)
        st.caption("前三名事件以亮色凸顯，其餘淡色；檢視資源配置優先順序")

        _top3_labels = _cc["類別"].tolist()[:3]
        fig_donut = go.Figure(go.Pie(
            labels=_cc["類別"],
            values=_cc["件數"],
            hole=0.52,
            marker=dict(
                colors=_unified_colors,
                line=dict(color="#FFFFFF", width=2),
            ),
            textinfo="label+percent",
            textfont=dict(size=10, color="#1C2833"),
            pull=[0.06 if i < 3 else 0 for i in range(len(_cc))],  # 前三名外凸
            hovertemplate="<b>%{label}</b><br>%{value} 件（%{percent}）<extra></extra>",
            sort=False,
        ))
        fig_donut.update_layout(
            height=300, paper_bgcolor=PAPER_BG, showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            annotations=[dict(
                text=f"TOP 3<br><span style='font-size:9px'>{' / '.join(_top3_labels[:3])}</span>",
                x=0.5, y=0.5,
                font=dict(size=10, color="#2C3E50"),
                showarrow=False,
            )],
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        # 前三名圖例說明
        for i, lbl in enumerate(_top3_labels[:3]):
            _cnt = int(_cc[_cc["類別"]==lbl]["件數"].values[0])
            _pct = _cnt / _cc["件數"].sum() * 100 if _cc["件數"].sum() > 0 else 0
            _icon = ["🥇","🥈","🥉"][i]
            st.markdown(
                f"<div style='font-size:12px;color:#2C3E50;padding:2px 0'>"
                f"{_icon} <b>{lbl}</b>：{_cnt} 件（{_pct:.1f}%）</div>",
                unsafe_allow_html=True
            )


    # ════════════════════════════════════════════════════════════
    #  PAGE 1 · 每月發生件數與發生率趨勢（Level 2 下方）
    # ════════════════════════════════════════════════════════════
    st.markdown("""<div style='background:#F0F3F4;border-radius:8px;
        padding:10px 16px;margin-bottom:12px'>
      <span style='font-size:14px;font-weight:700;color:#2C3E50'>
        📊 每月發生件數與發生率趨勢
      </span>
      <span style='font-size:11px;color:#5D6D7E;margin-left:8px'>
        隨時間區間與單位篩選連動
      </span>
    </div>""", unsafe_allow_html=True)

    fig_a1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig_a1.add_trace(go.Bar(
        x=mc["年月顯示"], y=mc["件數"], name="發生件數",
        marker_color="#2C3E50", marker_opacity=0.75,
        text=mc["件數"],
        textposition="outside",
        textfont=dict(size=8, color="#2C3E50", family="Arial"),
        hovertemplate="<b>%{x}</b><br>件數：%{y} 件<extra></extra>",
    ), secondary_y=False)
    fig_a1.add_trace(go.Scatter(
        x=mc["年月顯示"], y=mc["發生率"], name="發生率(‰)",
        mode="lines+markers", line=dict(color="#E74C3C", width=2.5),
        marker=dict(size=5, color="#E74C3C"),
        hovertemplate="<b>%{x}</b><br>發生率：%{y:.2f}‰<extra></extra>",
    ), secondary_y=True)
    fig_a1.update_layout(
        height=380, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right",
                    font=dict(size=11, color="#2C3E50")),
        xaxis=dict(
            title=dict(text="年月", font=AXIS_TITLE_FONT),
            tickangle=-45, showgrid=False, tickfont=AXIS_TICK_FONT,
        ),
        margin=dict(t=30, b=50),
        uniformtext=dict(mode="hide", minsize=7),
    )
    fig_a1.update_yaxes(
        title_text="發生件數", title_font=AXIS_TITLE_FONT,
        tickfont=AXIS_TICK_FONT, secondary_y=False,
        gridcolor=GRID_COLOR, griddash="dot",
        zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
    )
    fig_a1.update_yaxes(
        title_text="發生率 (‰)",
        title_font=dict(size=13, color="#C0392B", family="Arial"),
        tickfont=dict(size=10, color="#C0392B", family="Arial"),
        secondary_y=True,
    )

    # ── 政策介入標注：2025/05 住院看護費用補助辦法 ────────────
    _POLICY_X  = "2025/05"
    _POLICY_LBL = "住院看護費用補助辦法"
    # 確認此月份存在於 X 軸資料中才加標注
    if _POLICY_X in mc["年月顯示"].values:
        fig_a1.add_vline(
        x=_POLICY_X,
        line_dash="dash", line_color="#1E8449", line_width=1.8,
        )
        fig_a1.add_annotation(
        x=_POLICY_X, y=1.02, xref="x", yref="paper",
        text=f"▼ {_POLICY_LBL}",
        showarrow=False,
        font=dict(size=11, color="#1E8449", family="Arial"),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#1E8449", borderwidth=1,
        borderpad=4,
        xanchor="left",
        )

    st.plotly_chart(fig_a1, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 各單位發生件數長條圖（隨篩選連動）──────────────────────
    st.markdown('<p class="section-title">🏢 各單位發生件數</p>',
                unsafe_allow_html=True)
    st.caption("隨左側時間區間與事件類別篩選連動；依件數降冪排列")

    _unit_cnt = (dff["單位"].value_counts()
                 .reset_index()
                 .rename(columns={"單位":"單位","count":"件數"}))
    if "件數" not in _unit_cnt.columns:
        _unit_cnt.columns = ["單位","件數"]
    _unit_cnt = _unit_cnt[
        ~_unit_cnt["單位"].isin(["未知","未填/其他","NAN",""])
    ].sort_values("件數", ascending=False).reset_index(drop=True)

    if not _unit_cnt.empty:
        _u_max = _unit_cnt["件數"].max()
        _u_q75 = _unit_cnt["件數"].quantile(0.75)
        _u_colors = [
            "#E74C3C" if v == _u_max else
            "#E67E22" if v >= _u_q75 else
            "#2471A3"
            for v in _unit_cnt["件數"]
        ]
        fig_unit = go.Figure(go.Bar(
            x=_unit_cnt["單位"],
            y=_unit_cnt["件數"],
            marker=dict(color=_u_colors, opacity=0.88, line=dict(width=0)),
            text=_unit_cnt["件數"],
            textposition="outside",
            textfont=dict(size=10, color="#1C2833", family="Arial"),
            hovertemplate="<b>%{x}</b>：%{y} 件<extra></extra>",
        ))
        fig_unit.update_layout(
            height=320,
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="單位", font=AXIS_TITLE_FONT),
                tickfont=dict(size=10, color="#2C3E50", family="Arial"),
                showgrid=False,
                categoryorder="total descending",
            ),
            yaxis=dict(
                title=dict(text="件數", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                gridcolor=GRID_COLOR, griddash="dot",
                zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
                range=[0, _u_max * 1.25],
            ),
            margin=dict(t=20, b=60, l=60, r=20),
            bargap=0.25,
        )
        st.plotly_chart(fig_unit, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    #  PAGE 1 · Level 3：人因脈絡與行動指引
    # ════════════════════════════════════════════════════════════
    st.markdown("""<div style='background:#F0F3F4;border-radius:8px;
        padding:10px 16px;margin-bottom:12px'>
      <span style='font-size:14px;font-weight:700;color:#2C3E50'>
        🔬 Level 3 — 人因脈絡與行動指引
      </span>
      <span style='font-size:11px;color:#5D6D7E;margin-left:8px'>
        尖峰時段識別 · 時段×類別情境熱區（ROI 行動依據）
      </span>
    </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    #  圖C：時段 + 圖D：SAC 環圈（並排）
    #  軸標題深色，刻度深色
    # ════════════════════════════════════════════════════════════
    col_c, col_d = st.columns([1.2, 1])

    with col_c:
        st.markdown('<p class="section-title">🕐 事件發生時段分佈（每2小時）</p>',
                    unsafe_allow_html=True)
        ts_raw = dff["時段標準"].dropna()
        if ts_raw.empty:
            st.info("無時段資料")
        else:
            ts_cnt = ts_raw.value_counts().reindex(TIMESLOT_ORDER, fill_value=0)
            max_v  = max(int(ts_cnt.max()), 1)
            clrs = []
            for v in ts_cnt.values:
                r = v / max_v
                if r < 0.4:
                    clrs.append(f"rgba(192,57,43,{0.25 + 0.30*(r/0.4)})")
                else:
                    clrs.append(f"rgba(192,57,43,{0.55 + 0.43*((r-0.4)/0.6)})")

            peak   = ts_cnt.idxmax()
            peak_v = int(ts_cnt.max())

            # 次高峰：排除最高峰後的最大值
            ts_no_peak = ts_cnt.drop(index=peak)
            sec_peak   = ts_no_peak.idxmax()
            sec_peak_v = int(ts_no_peak.max())

            fig_c = go.Figure(go.Bar(
                x=TIMESLOT_ORDER, y=ts_cnt.values,
                marker_color=clrs, marker_line=dict(width=0),
                text=ts_cnt.values, textposition="outside",
                textfont=dict(size=11, color="#1C2833"),
                hovertemplate="<b>%{x}</b><br>%{y} 件<extra></extra>",
            ))
            # 最高峰標註
            fig_c.add_annotation(
                x=peak, y=peak_v, text=f"▲ 高峰<br>{peak}",
                showarrow=True, arrowhead=2, arrowcolor="#E74C3C",
                font=dict(size=11, color="#7B241C", family="Arial Bold"),
                yshift=25, ax=0, ay=-45)
            # 次高峰標註
            fig_c.add_annotation(
                x=sec_peak, y=sec_peak_v, text=f"△ 次高峰<br>{sec_peak}",
                showarrow=True, arrowhead=2, arrowcolor="#F39C12",
                font=dict(size=10, color="#7D6608", family="Arial Bold"),
                yshift=25, ax=0, ay=-45)
            fig_c.update_layout(
                height=460, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                xaxis=dict(
                    title=dict(text="發生時段", font=AXIS_TITLE_FONT),
                    tickangle=-30, tickfont=AXIS_TICK_FONT, showgrid=False,
                ),
                yaxis=dict(
                    title=dict(text="事件件數", font=AXIS_TITLE_FONT),
                    tickfont=AXIS_TICK_FONT,
                    gridcolor=GRID_COLOR, griddash="dot",
                    range=[0, peak_v * 1.45],   # 加大上界，讓兩個標註都有空間
                    zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
                ),
                margin=dict(t=30, b=60, l=60, r=20), bargap=0.18)
            st.plotly_chart(fig_c, use_container_width=True)

    with col_d:
        st.markdown('<p class="section-title">⚠️ SAC 嚴重度分佈</p>',
                    unsafe_allow_html=True)
        sac_d = dff["SAC_num"].dropna()
        sac_d = sac_d[sac_d.isin([1,2,3,4])]
        if sac_d.empty:
            st.info("無 SAC 資料")
        else:
            sc   = sac_d.value_counts().sort_index()
            lbls = [f"SAC {int(k)}<br>{SAC_DESC.get(int(k),'')} ({v}件)"
                    for k, v in zip(sc.index, sc.values)]
            clrs = [SAC_COLORS.get(int(k), "#aaa") for k in sc.index]
            hp   = sac_d.isin(HIGH_SAC).sum() / len(sac_d) * 100

            # pull：讓 SAC 1（死亡）扇形稍微突出，強調最高嚴重度
            pull_vals = [0.06 if int(k)==1 else 0 for k in sc.index]

            fig_d = go.Figure(go.Pie(
                labels=lbls, values=sc.values, hole=0.52,
                pull=pull_vals,
                marker=dict(colors=clrs, line=dict(color="white", width=3)),
                textinfo="percent+label",
                textfont=dict(size=10, color="#1C2833", family="Arial"),
                hovertemplate="<b>%{label}</b><br>%{value} 件 (%{percent})<extra></extra>",
                direction="clockwise", sort=False,
                insidetextorientation="horizontal",
                textposition="outside",          # 所有標籤統一放外側，不被截斷
            ))
            fig_d.add_annotation(
                text=f"<b>SAC 1+2</b><br>死亡+重大<br>{hp:.2f}%",
                x=0.5, y=0.5,
                font=dict(size=12, color="#7B241C", family="Arial Bold"),
                showarrow=False)
            fig_d.update_layout(
                height=480, paper_bgcolor=PAPER_BG,
                legend=dict(orientation="h", y=-0.12, xanchor="center", x=0.5,
                            font=dict(size=10, color="#2C3E50")),
                margin=dict(t=40, b=80, l=80, r=80))   # 四周充足空間
            st.plotly_chart(fig_d, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)



    # ── 時段 × 事件大類 交叉熱力圖 ──────────────────────────────
    st.markdown('<p class="section-title">🌡 時段 × 事件類別 情境熱力圖（ROI 行動熱區）</p>',
                unsafe_allow_html=True)
    st.caption("顏色越深 = 在該時段、該類別的事件越密集 → 管理介入投資報酬率最高的情境")

    _hm_df = dff[dff["時段標準"].notna() & dff["事件大類"].notna()].copy()
    if not _hm_df.empty:
        _hm_piv = (_hm_df.groupby(["時段標準","事件大類"])
                   .size().reset_index(name="件數")
                   .pivot(index="時段標準", columns="事件大類", values="件數")
                   .reindex(index=TIMESLOT_ORDER)
                   .fillna(0).astype(int))
        _cat_order = sorted(_hm_piv.columns.tolist(),
                            key=lambda c: _hm_piv[c].sum(), reverse=True)
        _hm_piv = _hm_piv[_cat_order]

        _hm_text = [[str(v) if v>0 else "" for v in row]
                    for row in _hm_piv.values]

        fig_hm_slot = go.Figure(go.Heatmap(
            z=_hm_piv.values,
            x=_hm_piv.columns.tolist(),
            y=_hm_piv.index.tolist(),
            text=_hm_text,
            texttemplate="%{text}",
            textfont=dict(size=11, color="white", family="Arial Bold"),
            colorscale=[
                [0.0, "#F4F6F6"],
                [0.2, "#AED6F1"],
                [0.5, "#2471A3"],
                [1.0, "#1A5276"],
            ],
            hovertemplate=(
                "<b>%{y} · %{x}</b><br>件數：%{z}<extra></extra>"
            ),
            colorbar=dict(
                title=dict(text="件數", font=dict(size=11, color="#1C2833")),
                tickfont=dict(size=10, color="#2C3E50"),
                thickness=14, len=0.7,
            ),
            xgap=3, ygap=2,
        ))
        fig_hm_slot.update_layout(
            height=400, paper_bgcolor=PAPER_BG, plot_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="事件類別", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                side="bottom",
            ),
            yaxis=dict(
                title=dict(text="發生時段", font=AXIS_TITLE_FONT),
                tickfont=dict(size=10, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=20, b=60, l=90, r=80),
        )
        st.plotly_chart(fig_hm_slot, use_container_width=True)
    else:
        st.info("目前篩選條件下無時段資料。")

    # ════════════════════════════════════════════════════════════
    #  PAGE 1 · Level 3b：單位 × 事件類別 情境熱力圖
    # ════════════════════════════════════════════════════════════
    st.markdown('<p class="section-title">🏢 單位 × 事件類別 情境熱力圖</p>',
                unsafe_allow_html=True)
    st.caption("各單位在各事件類別的集中度 — 顏色越深代表該單位該類別件數越多，可識別高風險單位與事件組合")

    _uc_df = dff[dff["單位"].notna() & dff["事件大類"].notna()].copy()
    if not _uc_df.empty:
        # 取 Top 15 發生單位（避免 Y 軸過長）
        _top_units = _uc_df["單位"].value_counts().head(15).index.tolist()
        _uc_df = _uc_df[_uc_df["單位"].isin(_top_units)]

        _uc_piv = (_uc_df.groupby(["單位","事件大類"])
                   .size().reset_index(name="件數")
                   .pivot(index="單位", columns="事件大類", values="件數")
                   .fillna(0).astype(int))

        # 欄位依總件數降冪排列
        _uc_col_order = _uc_piv.sum().sort_values(ascending=False).index.tolist()
        _uc_piv = _uc_piv[_uc_col_order]

        # 列依總件數降冪排列（高發單位在上）
        _uc_row_order = _uc_piv.sum(axis=1).sort_values(ascending=False).index.tolist()
        _uc_piv = _uc_piv.loc[_uc_row_order]

        _uc_text = [[str(v) if v > 0 else "" for v in row]
                    for row in _uc_piv.values]

        fig_uc_hm = go.Figure(go.Heatmap(
            z=_uc_piv.values,
            x=_uc_piv.columns.tolist(),
            y=_uc_piv.index.tolist(),
            text=_uc_text,
            texttemplate="%{text}",
            textfont=dict(size=11, color="white", family="Arial Bold"),
            colorscale=[
                [0.0, "#F4F6F6"],
                [0.15, "#AED6F1"],
                [0.5,  "#2471A3"],
                [1.0,  "#1A5276"],
            ],
            hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>件數：%{z}<extra></extra>",
            colorbar=dict(
                title=dict(text="件數", font=dict(size=11, color="#1C2833")),
                tickfont=dict(size=10, color="#2C3E50"),
                thickness=14, len=0.7,
            ),
            xgap=3, ygap=2,
        ))
        fig_uc_hm.update_layout(
            height=max(360, len(_uc_piv) * 30 + 100),
            paper_bgcolor=PAPER_BG, plot_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="事件類別", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                side="bottom",
            ),
            yaxis=dict(
                title=dict(text="發生單位", font=AXIS_TITLE_FONT),
                tickfont=dict(size=10, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=20, b=60, l=110, r=80),
        )
        st.plotly_chart(fig_uc_hm, use_container_width=True)
    else:
        st.info("目前篩選條件下無資料。")

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    #  PAGE 1 · 精神科跌倒深度分析（W11 / W12，側邊欄連動）
    # ════════════════════════════════════════════════════════════
    _PSYCH_WARDS = ["W11", "W12", "W11+W12（精神科）"]
    if sel_unit in _PSYCH_WARDS:

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
<div style='background:linear-gradient(135deg,#1B2631,#4A235A);
            padding:14px 22px;border-radius:10px;margin-bottom:14px;
            border-left:5px solid #7D3C98'>
  <h2 style='color:#FFFFFF;margin:0;font-size:18px;font-weight:700'>
    🧠 精神科跌倒深度分析（{"W11 ＋ W12" if sel_unit == "W11+W12（精神科）" else sel_unit} 專屬）
  </h2>
  <p style='color:#D7BDE2;margin:4px 0 0;font-size:11px'>
    W11・W12 急性精神科病房 · 認知行為風險 · 藥物影響 · 月趨勢追蹤
    ｜篩選期間：{start_m} ～ {end_m}
  </p>
</div>""", unsafe_allow_html=True)

        # ── 資料準備 ──────────────────────────────────────────
        # df_fall_base 已在 load_data 中 merge「單位」欄位
        _pf_all = df_fall_base[
            df_fall_base["單位"].isin(_PSYCH_WARDS)
        ].copy()

        _ps, _pe = st.session_state["date_range"]
        _pf_t = _pf_all[(_pf_all["年月"] >= _ps) & (_pf_all["年月"] <= _pe)].copy()
        _pf_h = _pf_all[~((_pf_all["年月"] >= _ps) & (_pf_all["年月"] <= _pe))].copy()

        _nt = len(_pf_t)
        _nh = len(_pf_h)
        _h_months = max(_pf_h["年月"].nunique(), 1)
        _h_avg    = round(_nh / _h_months, 1)

        # ── KPI 三卡（紫色系）────────────────────────────────
        _kp1, _kp2, _kp3 = st.columns(3)
        _ks = ("background:#FFFFFF;border-radius:12px;padding:16px 18px;"
               "box-shadow:0 2px 10px rgba(0,0,0,0.09);"
               "border-left:5px solid {c};min-height:96px")

        def _pk(col, title, val, sub, c):
            col.markdown(
                f"<div style='{_ks.format(c=c)}'>"
                f"<div style='font-size:11px;color:#5D6D7E;font-weight:700;"
                f"letter-spacing:0.5px;margin-bottom:6px'>{title}</div>"
                f"<div style='font-size:28px;font-weight:900;color:#1C2833;"
                f"line-height:1.1'>{val}</div>"
                f"<div style='font-size:11px;color:#85929E;margin-top:4px'>{sub}</div>"
                f"</div>", unsafe_allow_html=True)

        _cog_t = int(_pf_t["可能原因-意識或認知障礙"].fillna(0).sum()) if "可能原因-意識或認知障礙" in _pf_t.columns else 0
        _cog_h = int(_pf_h["可能原因-意識或認知障礙"].fillna(0).sum()) if "可能原因-意識或認知障礙" in _pf_h.columns else 0
        _cog_tp = round(_cog_t / max(_nt, 1) * 100, 0)
        _cog_hp = round(_cog_h / max(_nh, 1) * 100, 0)
        _cog_flag = "⚠️ " if _cog_tp > _cog_hp + 15 else ""

        _drug_t  = int(_pf_t["可能原因-與使用藥物相關"].fillna(0).sum()) if "可能原因-與使用藥物相關" in _pf_t.columns else 0
        _drug_tp = round(_drug_t / max(_nt, 1) * 100, 0)
        _sed_t   = int(_pf_t["可能原因-鎮靜安眠藥"].fillna(0).sum()) if "可能原因-鎮靜安眠藥" in _pf_t.columns else 0
        _sed_tp  = round(_sed_t / max(_nt, 1) * 100, 0)

        _pk(_kp1, f"🧠 {_cog_flag}意識/認知障礙佔比",
            f"{_cog_tp:.0f}%",
            f"本期 {_cog_t} 件 ｜ 精神科歷史均 {_cog_hp:.0f}%", "#7D3C98")
        _pk(_kp2, "💊 藥物相關佔比",
            f"{_drug_tp:.0f}%",
            f"本期 {_drug_t} 件（含鎮靜 {_sed_tp:.0f}%）", "#C0392B")
        _pk(_kp3, "📋 本期跌倒件數",
            f"{_nt} 件",
            f"精神科歷史月均 {_h_avg} 件／月", "#1A5276")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── 子區塊 1：風險因子雙條對比圖 ─────────────────────
        st.markdown('<p class="section-title">📊 風險因子比較：本期 vs 精神科歷史均值</p>',
                    unsafe_allow_html=True)
        st.caption("紅色 = 本篩選期間，藍色 = 精神科歷史均值；百分比以各期跌倒件數為分母")

        _rf_def = [
            ("意識/認知障礙",  "可能原因-意識或認知障礙"),
            ("步態不穩",       "可能原因-步態不穩"),
            ("身體虛弱",       "可能原因-身體虛弱"),
            ("鎮靜安眠藥",     "可能原因-鎮靜安眠藥"),
            ("降壓藥",         "可能原因-降壓藥"),
            ("抗癲癇藥",       "可能原因-抗癲癇藥"),
            ("抗憂鬱劑",       "可能原因-抗憂鬱劑"),
            ("執意自行下床",   "可能原因-高危險群病人執意自行下床或活動"),
            ("躁動",           "可能原因-躁動"),
            ("其他行為因素",   "可能原因-其他與病人生理及行為因素相關"),
        ]

        _rf_lbls, _rf_tp, _rf_hp = [], [], []
        for _lbl, _col in _rf_def:
            _n_t = int(_pf_t[_col].fillna(0).sum()) if _col in _pf_t.columns else 0
            _n_h = int(_pf_h[_col].fillna(0).sum()) if _col in _pf_h.columns else 0
            _rf_lbls.append(_lbl)
            _rf_tp.append(round(_n_t / max(_nt, 1) * 100, 1))
            _rf_hp.append(round(_n_h / max(_nh, 1) * 100, 1))

        fig_rf = go.Figure()
        fig_rf.add_trace(go.Bar(
            name=f"本期（{start_m}～{end_m}）",
            x=_rf_lbls, y=_rf_tp,
            marker=dict(color="#C0392B", opacity=0.88, line=dict(width=0)),
            text=[f"{v:.0f}%" for v in _rf_tp],
            textposition="outside",
            textfont=dict(size=10, color="#1C2833", family="Arial"),
        ))
        fig_rf.add_trace(go.Bar(
            name="精神科歷史均值",
            x=_rf_lbls, y=_rf_hp,
            marker=dict(color="#2471A3", opacity=0.55, line=dict(width=0)),
            text=[f"{v:.0f}%" for v in _rf_hp],
            textposition="outside",
            textfont=dict(size=10, color="#1C2833", family="Arial"),
        ))
        fig_rf.update_layout(
            barmode="group", height=360,
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(title=dict(text="風險因子", font=AXIS_TITLE_FONT),
                       tickfont=dict(size=10, color="#2C3E50", family="Arial"),
                       showgrid=False),
            yaxis=dict(title=dict(text="佔比（%）", font=AXIS_TITLE_FONT),
                       tickfont=AXIS_TICK_FONT,
                       gridcolor=GRID_COLOR, griddash="dot",
                       range=[0, max(max(_rf_tp, default=0),
                                     max(_rf_hp, default=0)) * 1.3 + 5]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                        font=dict(size=11, color="#2C3E50")),
            margin=dict(t=40, b=60, l=60, r=30),
            bargap=0.2, bargroupgap=0.05,
        )
        st.plotly_chart(fig_rf, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── 子區塊 2：精神科跌倒月趨勢 ──────────────────────
        st.markdown('<p class="section-title">📈 精神科跌倒月趨勢（歷史全覽）</p>',
                    unsafe_allow_html=True)
        st.caption("灰色折線 = 歷史全期；紅色圓點 = 本篩選期間；虛線 = 精神科歷史月均")

        _pf_mly = (_pf_all.groupby("年月").size()
                   .reset_index(name="件數").sort_values("年月"))
        _pf_mly["年月顯示"] = _pf_mly["年月"].str.replace("-", "/", regex=False)
        _pf_mly["目標期"] = (_pf_mly["年月"] >= _ps) & (_pf_mly["年月"] <= _pe)

        fig_pt = go.Figure()
        fig_pt.add_trace(go.Scatter(
            x=_pf_mly["年月顯示"], y=_pf_mly["件數"],
            mode="lines+markers",
            line=dict(color="#AEB6BF", width=2),
            marker=dict(size=5, color="#AEB6BF"),
            name="歷史全期",
        ))
        _tgt_mly = _pf_mly[_pf_mly["目標期"]]
        if not _tgt_mly.empty:
            fig_pt.add_trace(go.Scatter(
                x=_tgt_mly["年月顯示"], y=_tgt_mly["件數"],
                mode="markers",
                marker=dict(size=11, color="#C0392B", symbol="circle",
                            line=dict(color="#FFFFFF", width=1.5)),
                name=f"本期（{start_m}～{end_m}）",
            ))
        fig_pt.add_hline(
            y=_h_avg, line_dash="dot", line_color="#7D3C98", line_width=1.5,
            annotation_text=f"月均 {_h_avg} 件",
            annotation_position="top right",
            annotation_font=dict(size=10, color="#7D3C98"),
        )
        fig_pt.update_layout(
            height=280, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(title=dict(text="年月", font=AXIS_TITLE_FONT),
                       tickfont=dict(size=9, color="#2C3E50", family="Arial"),
                       tickangle=45, showgrid=False),
            yaxis=dict(title=dict(text="跌倒件數", font=AXIS_TITLE_FONT),
                       tickfont=AXIS_TICK_FONT,
                       gridcolor=GRID_COLOR, griddash="dot",
                       rangemode="tozero"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                        font=dict(size=11, color="#2C3E50")),
            margin=dict(t=40, b=70, l=60, r=30),
        )
        st.plotly_chart(fig_pt, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── 子區塊 3：近期事件逐件摘要表 ────────────────────
        if _nt > 0:
            st.markdown('<p class="section-title">📋 本期精神科跌倒事件逐件摘要</p>',
                        unsafe_allow_html=True)
            st.caption("依年月排列；標籤自動從通報欄位萃取（🧠認知 💊藥物 ⚡行為 🦵肌力）")

            # 標籤定義
            _tag_def = [
                ("🧠認知障礙", "可能原因-意識或認知障礙",           "#E8DAEF", "#6C3483"),
                ("💊鎮靜藥",   "可能原因-鎮靜安眠藥",               "#FADBD8", "#922B21"),
                ("💊降壓藥",   "可能原因-降壓藥",                   "#FADBD8", "#922B21"),
                ("💊抗癲癇",   "可能原因-抗癲癇藥",                 "#FADBD8", "#922B21"),
                ("🦵步態不穩", "可能原因-步態不穩",                 "#D6EAF8", "#1A5276"),
                ("⚡執意下床", "可能原因-高危險群病人執意自行下床或活動","#FEF9E7","#7D6608"),
                ("🔴躁動",     "可能原因-躁動",                     "#FADBD8", "#922B21"),
            ]

            _rows_html = ""
            for _, row in _pf_t.sort_values("年月", ascending=False).iterrows():
                _cid  = str(row.get("通報案號", ""))
                _ym   = str(row.get("年月", ""))
                _hd   = str(row.get("跌倒事件發生對象-事件發生前是否為跌倒高危險群","")) == "是"
                _desc = str(row.get("事件說明",""))
                _desc_s = (_desc[:90] + "…") if len(_desc) > 90 else _desc

                # 產生標籤
                _tags_html = ""
                for _tlbl, _tcol, _tbg, _tclr in _tag_def:
                    if row.get(_tcol, 0):
                        _tags_html += (f"<span style='display:inline-block;font-size:10px;"
                                       f"background:{_tbg};color:{_tclr};"
                                       f"border-radius:4px;padding:1px 6px;margin:1px 2px'>"
                                       f"{_tlbl}</span>")

                _hd_badge = (
                    "<span style='display:inline-block;font-size:10px;"
                    "background:#FADBD8;color:#922B21;"
                    "border-radius:4px;padding:1px 6px;margin:1px 2px'>⚠️高危群</span>"
                ) if _hd else ""

                _rows_html += (
                    f"<tr style='border-bottom:0.5px solid #EAECEE'>"
                    f"<td style='padding:8px 10px;font-size:11px;color:#5D6D7E;"
                    f"white-space:nowrap'>{_ym}</td>"
                    f"<td style='padding:8px 10px;font-size:11px;color:#2C3E50'>{_cid}</td>"
                    f"<td style='padding:8px 10px;font-size:11px'>{_hd_badge}{_tags_html}</td>"
                    f"<td style='padding:8px 10px;font-size:11px;color:#2C3E50;"
                    f"line-height:1.5'>{_desc_s}</td>"
                    f"</tr>"
                )

            st.markdown(f"""
<div style='overflow-x:auto'>
<table style='width:100%;border-collapse:collapse;font-family:Arial,sans-serif'>
  <thead>
    <tr style='background:#4A235A;color:white'>
      <th style='padding:8px 10px;text-align:left;font-size:11px;white-space:nowrap'>年月</th>
      <th style='padding:8px 10px;text-align:left;font-size:11px;white-space:nowrap'>案號</th>
      <th style='padding:8px 10px;text-align:left;font-size:11px;min-width:160px'>風險標籤</th>
      <th style='padding:8px 10px;text-align:left;font-size:11px'>事件摘要</th>
    </tr>
  </thead>
  <tbody>{_rows_html}</tbody>
</table>
</div>""", unsafe_allow_html=True)
            st.caption(f"共 {_nt} 件；顯示全部本期事件")

        st.markdown("<br>", unsafe_allow_html=True)


with _tab2:


    # ════════════════════════════════════════════════════════════
    #  PAGE 2：跌倒事件分析
    # ════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
                padding:14px 22px;border-radius:10px;margin-bottom:14px'>
      <h2 style='color:#FFFFFF;margin:0;font-size:19px;font-weight:700'>
        📈 跌倒事件分析
      </h2>
      <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
        跌倒事件深度分析 · 月趨勢 · 管制圖 · 診斷特徵 · 風險因子
        ｜篩選期間 {start_m} ～ {end_m}
      </p>
    </div>""", unsafe_allow_html=True)


    # ── 年度比較區塊 ─────────────────────────────────────────
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
                padding:12px 20px;border-radius:8px;margin-bottom:14px'>
      <h3 style='color:#FFFFFF;margin:0;font-size:17px;font-weight:700'>
        📅 年度比較分析（2024 vs 2025）
      </h3>
      <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
        全院層級・不受科別篩選影響・範圍：{inc_ltc}
      </p>
    </div>""", unsafe_allow_html=True)

    # ── 4個指標卡（含紅綠燈警示 + Tooltip 定義）────────────────
    def _kpi_card(label, value, delta_val, delta_txt, up_is_bad=True, tooltip=""):
        """
        醫療專業 KPI 卡片
        - 越低越好 (up_is_bad=True)：上升→紅燈、下降→綠燈
        - 越高越好 (up_is_bad=False)：上升→綠燈、下降→紅燈
        - tooltip: 右上角懸停說明（分子分母定義）
        """
        if delta_val > 0:
            arrow  = "▲"
            d_color = "#C0392B" if up_is_bad else "#1E8449"
            d_bg    = "#FADBD8" if up_is_bad else "#D5F5E3"
            led     = "#E74C3C" if up_is_bad else "#27AE60"   # 左邊指示條顏色
            status  = "⛔" if up_is_bad else "✅"
        elif delta_val < 0:
            arrow  = "▼"
            d_color = "#1E8449" if up_is_bad else "#C0392B"
            d_bg    = "#D5F5E3" if up_is_bad else "#FADBD8"
            led     = "#27AE60" if up_is_bad else "#E74C3C"
            status  = "✅" if up_is_bad else "⛔"
        else:
            arrow, d_color, d_bg = "─", "#7F8C8D", "#F2F3F4"
            led    = "#AEB6BF"
            status = "➖"

        # 數值字體在指標惡化時加粗強調
        val_weight = "900" if (up_is_bad and delta_val > 0) or (not up_is_bad and delta_val < 0) else "800"
        val_color  = "#C0392B" if (up_is_bad and delta_val > 0) else "#1C2833"

        if tooltip:
            # 清理 tooltip 文字：移除換行、單引號、雙引號，避免破壞 HTML 屬性
            _tip_clean = (tooltip
                          .replace("\n", " ")
                          .replace("'", "")
                          .replace('"', "")
                          .replace("=", "＝")
                          .replace("<", "＜")
                          .replace(">", "＞"))
            tooltip_html = (
                f'<div title="{_tip_clean}" '
                f'style="position:absolute;top:10px;right:12px;'
                f'width:18px;height:18px;background:#EBF5FB;border-radius:50%;'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-size:11px;color:#2E86C1;cursor:help;'
                f'border:1px solid #AED6F1;font-weight:700;">ℹ</div>'
            )
        else:
            tooltip_html = ""

        return f"""
    <div style='background:#FFFFFF;border-left:5px solid {led};border-radius:10px;
                padding:16px 18px 14px;box-shadow:0 2px 8px rgba(0,0,0,0.09);
                position:relative;min-height:110px'>
      {tooltip_html}
      <div style='font-size:11px;color:#5D6D7E;font-weight:700;
                  letter-spacing:0.4px;margin-bottom:8px;padding-right:24px'>
        {status} {label}
      </div>
      <div style='font-size:32px;font-weight:{val_weight};color:{val_color};
                  line-height:1.1;letter-spacing:-0.5px'>{value}</div>
      <div style='font-size:11px;font-weight:700;color:{d_color};
                  background:{d_bg};border-radius:4px;
                  padding:3px 8px;display:inline-block;margin-top:8px'>
        {arrow} {delta_txt}
      </div>
    </div>"""

    # 指標定義 Tooltip
    TOOLTIP_INJ   = "跌倒有傷害率 = 有傷害件數 ÷ 跌倒總件數\n傷害判斷：病人健康影響程度(彙總) = 有傷害"
    TOOLTIP_PSYCH = "精神科跌倒占比 = 精神科跌倒件數 ÷ 全院跌倒總件數"
    TOOLTIP_MID   = "中度以上傷害率 = 外科+內科中，中度/重度/極重度/死亡件數 ÷ 外科+內科跌倒總件數"
    TOOLTIP_HARM  = "傷害行為件數 = 事件大類為「傷害」的通報件數（全院）"

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        delta_inj = round(v25_inj - v24_inj, 2)
        st.markdown(_kpi_card(
            "跌倒有傷害率",
            f"{v25_inj:.2f}%",
            delta_inj,
            f"{delta_inj:+.2f}% vs 2024（{v24_inj:.2f}%）",
            up_is_bad=True, tooltip=TOOLTIP_INJ,
        ), unsafe_allow_html=True)
    with mk2:
        delta_psych = round(v25_psych - v24_psych, 2)
        st.markdown(_kpi_card(
            "精神科跌倒占比",
            f"{v25_psych:.2f}%",
            delta_psych,
            f"{delta_psych:+.2f}% vs 2024（{v24_psych:.2f}%）",
            up_is_bad=True, tooltip=TOOLTIP_PSYCH,
        ), unsafe_allow_html=True)
    with mk3:
        delta_mid = round(v25_mid - v24_mid, 2)
        st.markdown(_kpi_card(
            "中度以上傷害率（外科+內科）",
            f"{v25_mid:.2f}%",
            delta_mid,
            f"{delta_mid:+.2f}% vs 2024（{v24_mid:.2f}%）",
            up_is_bad=True, tooltip=TOOLTIP_MID,
        ), unsafe_allow_html=True)
    with mk4:
        delta_harm = n25_harm - n24_harm
        st.markdown(_kpi_card(
            "傷害行為年件數",
            f"{n25_harm} 件",
            delta_harm,
            f"{delta_harm:+d} 件 vs 2024（{n24_harm}件）",
            up_is_bad=True, tooltip=TOOLTIP_HARM,
        ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 圖①：跌倒月份趨勢比較折線圖 ─────────────────────────
    st.markdown('<p class="section-title">① 跌倒事件月份趨勢比較（2024 vs 2025 vs 歷年均值）</p>',
                unsafe_allow_html=True)

    # 各年月份件數
    def _monthly_counts(df, yr):
        sub = df[df["年"] == yr]
        return sub.groupby("月").size().reindex(range(1,13), fill_value=0)

    cnt24  = _monthly_counts(_fb, 2024)
    cnt25  = _monthly_counts(_fb, 2025)
    # 2020-2023 歷年平均
    hist_mean = pd.Series(0.0, index=range(1,13))
    hist_yrs  = [y for y in [2020,2021,2022,2023] if y in _fb["年"].values]
    if hist_yrs:
        hist_mean = pd.concat(
            [_monthly_counts(_fb, y) for y in hist_yrs], axis=1
        ).mean(axis=1)

    MONTHS_ZH = ["1月","2月","3月","4月","5月","6月",
                 "7月","8月","9月","10月","11月","12月"]

    fig_yr1 = go.Figure()
    # 歷年均值（灰色虛線）
    fig_yr1.add_trace(go.Scatter(
        x=MONTHS_ZH, y=hist_mean.values, name="2020–2023 均值",
        mode="lines", line=dict(color="#AEB6BF", dash="dash", width=2),
        hovertemplate="<b>%{x}</b><br>歷年均值：%{y:.1f} 件<extra></extra>",
    ))
    # 2024（藍色實線）
    fig_yr1.add_trace(go.Scatter(
        x=MONTHS_ZH, y=cnt24.values, name="2024 實際",
        mode="lines+markers",
        line=dict(color="#2471A3", width=2.5),
        marker=dict(size=7, color="#2471A3"),
        hovertemplate="<b>%{x}</b><br>2024：%{y} 件<extra></extra>",
    ))
    # 2025（紅色實線，只畫有資料的月份）
    last_m25 = int(_fb25["月"].max()) if not _fb25.empty else 0
    cnt25_plot = cnt25.copy().astype(float)
    if last_m25 < 12:
        cnt25_plot.iloc[last_m25:] = None   # 截斷之後月份
    fig_yr1.add_trace(go.Scatter(
        x=MONTHS_ZH, y=cnt25_plot.values, name="2025 實際",
        mode="lines+markers",
        line=dict(color="#C0392B", width=2.5),
        marker=dict(size=7, color="#C0392B"),
        hovertemplate="<b>%{x}</b><br>2025：%{y:.0f} 件<extra></extra>",
        connectgaps=False,
    ))
    fig_yr1.update_layout(
        title=None,
        height=380,
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right",
                    font=dict(size=11, color="#2C3E50")),
        xaxis=dict(
            title=dict(text="月份", font=AXIS_TITLE_FONT),
            tickfont=AXIS_TICK_FONT, showgrid=False,
        ),
        yaxis=dict(
            title=dict(text="跌倒件數", font=AXIS_TITLE_FONT),
            tickfont=AXIS_TICK_FONT,
            gridcolor=GRID_COLOR, griddash="dot",
            zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
            rangemode="tozero",
        ),
        hovermode="x unified",
        margin=dict(t=70, b=60, l=60, r=20),
    )
    st.plotly_chart(fig_yr1, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── 圖②：各科別 2024 vs 2025 分組橫條圖 ────────────
    st.markdown('<p class="section-title">② 各科別跌倒件數：2024 vs 2025</p>',
                unsafe_allow_html=True)

    CMP_DEPTS   = ["精神科","外科","內科","復健科"]
    last_m25_fb = int(_fb25["月"].max()) if not _fb25.empty else 1

    cmp_data = []
    for dept in CMP_DEPTS:
        n24 = (_fb24[DEPT_COL_YR] == dept).sum()
        n25 = (_fb25[DEPT_COL_YR] == dept).sum()
        cmp_data.append({"科別": dept, "2024": n24, "2025": n25})
    df_cmp = pd.DataFrame(cmp_data).sort_values("2024", ascending=True)

    fig_yr2 = go.Figure()
    # 2024（藍色）
    fig_yr2.add_trace(go.Bar(
        name="2024",
        y=df_cmp["科別"],
        x=df_cmp["2024"],
        orientation="h",
        marker_color="#2471A3",
        marker_opacity=0.85,
        text=df_cmp["2024"].astype(str) + " 件",
        textposition="outside",
        textfont=dict(size=10, color="#1C2833", family="Arial"),
        hovertemplate="<b>%{y}</b><br>2024：%{x} 件<extra></extra>",
    ))
    # 2025（紅色）
    fig_yr2.add_trace(go.Bar(
        name="2025",
        y=df_cmp["科別"],
        x=df_cmp["2025"],
        orientation="h",
        marker_color="#C0392B",
        marker_opacity=0.80,
        text=df_cmp["2025"].astype(str) + " 件",
        textposition="outside",
        textfont=dict(size=10, color="#C0392B", family="Arial Bold"),
        hovertemplate="<b>%{y}</b><br>2025：%{x} 件<extra></extra>",
    ))
    max_val = max(df_cmp["2024"].max(), df_cmp["2025"].max())
    fig_yr2.update_layout(
        title=None,
        barmode="group",
        height=380,
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right",
                    font=dict(size=11, color="#2C3E50")),
        xaxis=dict(
            title=dict(text="跌倒件數", font=AXIS_TITLE_FONT),
            tickfont=AXIS_TICK_FONT,
            range=[0, max_val * 1.4],
            gridcolor=GRID_COLOR, griddash="dot",
            zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
        ),
        yaxis=dict(
            title=dict(text="科別", font=AXIS_TITLE_FONT),
            tickfont=dict(size=12, color="#2C3E50", family="Arial"),
            automargin=True,
        ),
        margin=dict(t=70, b=60, l=80, r=120),
        hovermode="y unified",
    )
    st.plotly_chart(fig_yr2, use_container_width=True)






    # ════════════════════════════════════════════════════════════
    #  月趨勢 / 類別趨勢 / 年資分布
    # ════════════════════════════════════════════════════════════
    st.markdown("""<div style='background:#F0F3F4;border-radius:8px;
        padding:10px 16px;margin-bottom:12px'>
      <span style='font-size:14px;font-weight:700;color:#2C3E50'>
        📊 月趨勢 · 事件類別趨勢 · 通報者年資分布
      </span>
      <span style='font-size:11px;color:#5D6D7E;margin-left:8px'>
        每月件數與發生率 · 各類別堆疊趨勢 · 工作年資與 SAC 分布
      </span>
    </div>""", unsafe_allow_html=True)


    # ════════════════════════════════════════════════════════════
    #  圖A：每月件數 + 發生率（雙軸）
    #  軸標題：深色 #1C2833，字體 13px Bold
    # ════════════════════════════════════════════════════════════
    fig_a = make_subplots(specs=[[{"secondary_y": True}]])
    fig_a.add_trace(go.Bar(
        x=mc["年月顯示"], y=mc["件數"], name="發生件數",
        marker_color="#2C3E50", marker_opacity=0.75,
        text=mc["件數"],
        textposition="outside",
        textfont=dict(size=8, color="#2C3E50", family="Arial"),
        hovertemplate="<b>%{x}</b><br>件數：%{y} 件<extra></extra>",
    ), secondary_y=False)
    fig_a.add_trace(go.Scatter(
        x=mc["年月顯示"], y=mc["發生率"], name="發生率(‰)",
        mode="lines+markers", line=dict(color="#E74C3C", width=2.5),
        marker=dict(size=5, color="#E74C3C"),
        hovertemplate="<b>%{x}</b><br>發生率：%{y:.2f}‰<extra></extra>",
    ), secondary_y=True)
    fig_a.update_layout(
        title=dict(text="📊 每月發生件數與發生率趨勢", font=TITLE_FONT),
        height=420, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right",
                    font=dict(size=11, color="#2C3E50")),
        xaxis=dict(
            title=dict(text="年月", font=AXIS_TITLE_FONT),
            tickangle=-45, showgrid=False, tickfont=AXIS_TICK_FONT,
            linecolor="#BDC3C7", linewidth=1,
        ),
        margin=dict(t=60, b=50),
        uniformtext=dict(mode="hide", minsize=7),  # 月份過密時自動隱藏標籤
    )
    fig_a.update_yaxes(
        title_text="發生件數",
        title_font=AXIS_TITLE_FONT,
        tickfont=AXIS_TICK_FONT,
        secondary_y=False,
        gridcolor=GRID_COLOR, gridwidth=1, griddash="dot",
        zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
    )
    fig_a.update_yaxes(
        title_text="發生率 (‰)",
        title_font=dict(size=13, color="#C0392B", family="Arial"),  # 右軸與折線同色
        tickfont=dict(size=10, color="#C0392B", family="Arial"),
        secondary_y=True,
    )

    # ── 政策介入標注：2025/05 住院看護費用補助辦法 ────────────
    _POLICY_X  = "2025/05"
    _POLICY_LBL = "住院看護費用補助辦法"
    # 確認此月份存在於 X 軸資料中才加標注
    if _POLICY_X in mc["年月顯示"].values:
        fig_a.add_vline(
        x=_POLICY_X,
        line_dash="dash", line_color="#1E8449", line_width=1.8,
        )
        fig_a.add_annotation(
        x=_POLICY_X, y=1.02, xref="x", yref="paper",
        text=f"▼ {_POLICY_LBL}",
        showarrow=False,
        font=dict(size=11, color="#1E8449", family="Arial"),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#1E8449", borderwidth=1,
        borderpad=4,
        xanchor="left",
        )

    st.plotly_chart(fig_a, use_container_width=True)


    # ════════════════════════════════════════════════════════════
    #  圖B：管制圖
    #  軸標題：深色，控制線標籤各自使用線條顏色
    # ════════════════════════════════════════════════════════════
    rates = mc["發生率"].replace(0, np.nan).dropna()
    if len(rates) >= 3:
        cl  = float(rates.mean())
        std = float(rates.std())
        ucl = cl + 3 * std
        lcl = max(0.0, cl - 3 * std)
        mc["異常點"] = mc["發生率"].apply(lambda x: (x > ucl) or (0 < x < lcl))

        fig_b = go.Figure()
        fig_b.add_trace(go.Scatter(
            x=list(mc["年月顯示"]) + list(mc["年月顯示"])[::-1],
            y=[ucl]*len(mc) + [lcl]*len(mc),
            fill="toself", fillcolor=CTRL_BAND_FILL,
            line=dict(color="rgba(0,0,0,0)"),
            name="管制區間", hoverinfo="skip"))
        fig_b.add_trace(go.Scatter(
            x=mc["年月顯示"], y=mc["發生率"],
            mode="lines+markers", name="月發生率",
            line=dict(color="#3498DB", width=2),
            marker=dict(size=7,
                color=mc["異常點"].map({True: OUTLIER_COLOR, False: "#3498DB"}),
                symbol=mc["異常點"].map({True: "diamond", False: "circle"}),
                line=dict(width=1.5, color="white")),
            hovertemplate="<b>%{x}</b><br>%{y:.2f}‰<extra></extra>"))
        outliers = mc[mc["異常點"]]
        if not outliers.empty:
            fig_b.add_trace(go.Scatter(
                x=outliers["年月顯示"], y=outliers["發生率"],
                mode="markers+text", name="⚠️ 超出管制",
                marker=dict(size=13, color=OUTLIER_COLOR, symbol="diamond",
                            line=dict(width=2, color="white")),
                text=outliers["發生率"].round(2).astype(str) + "‰",
                textposition="top center",
                textfont=dict(size=10, color="#7B241C", family="Arial Bold"),
                hovertemplate="⚠️ <b>%{x}</b>：%{y:.2f}‰<extra></extra>"))
        for y_val, lbl, clr, ds in [
            (ucl, f"UCL = {ucl:.2f}‰", "#E74C3C", "dash"),
            (cl,  f"CL  = {cl:.2f}‰",  "#5D6D7E", "solid"),
            (lcl, f"LCL = {lcl:.2f}‰", "#E74C3C", "dash"),
        ]:
            fig_b.add_hline(y=y_val, line_dash=ds, line_color=clr, line_width=2,
                annotation_text=f"  {lbl}", annotation_position="right",
                annotation_font=dict(size=11, color=clr, family="Arial Bold"))
        fig_b.update_layout(
            title=dict(text="📉 病安發生率統計管制圖（X̄ ± 3σ）", font=TITLE_FONT),
            height=380, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1, x=1, xanchor="right",
                        font=dict(size=11, color="#2C3E50")),
            xaxis=dict(
                title=dict(text="年月", font=AXIS_TITLE_FONT),
                tickangle=-45, showgrid=False, tickfont=AXIS_TICK_FONT,
            ),
            yaxis=dict(
                title=dict(text="發生率 (‰)", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                gridcolor=GRID_COLOR, griddash="dot",
                zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
            ),
            margin=dict(t=60, b=50, r=140))
        st.plotly_chart(fig_b, use_container_width=True)

        r1, r2, r3 = st.columns(3)
        r1.markdown(f"""
    <div style='background:#FFFFFF;border:1px solid #D5D8DC;border-radius:10px;
                padding:14px 18px;box-shadow:0 2px 6px rgba(0,0,0,0.08);text-align:center'>
      <div style='font-size:12px;color:#5D6D7E;font-weight:600;margin-bottom:6px'>📏 中心線 CL</div>
      <div style='font-size:28px;font-weight:900;color:#1C2833'>{cl:.2f}‰</div>
    </div>""", unsafe_allow_html=True)
        r2.markdown(f"""
    <div style='background:#FFFFFF;border:2px solid #E74C3C;border-radius:10px;
                padding:14px 18px;box-shadow:0 2px 6px rgba(0,0,0,0.08);text-align:center'>
      <div style='font-size:12px;color:#922B21;font-weight:600;margin-bottom:6px'>🔴 上管制線 UCL</div>
      <div style='font-size:28px;font-weight:900;color:#C0392B'>{ucl:.2f}‰</div>
    </div>""", unsafe_allow_html=True)
        r3.markdown(f"""
    <div style='background:#FFFFFF;border:2px solid #1E8449;border-radius:10px;
                padding:14px 18px;box-shadow:0 2px 6px rgba(0,0,0,0.08);text-align:center'>
      <div style='font-size:12px;color:#1A5276;font-weight:600;margin-bottom:6px'>🟢 下管制線 LCL</div>
      <div style='font-size:28px;font-weight:900;color:#1E8449'>{lcl:.2f}‰</div>
    </div>""", unsafe_allow_html=True)
        if not outliers.empty:
            st.markdown(f'<div style="background:#FFF3CD;border-left:4px solid #F39C12;padding:10px 14px;border-radius:4px;color:#7D4700;font-size:13px">⚠️ 共 <b>{len(outliers)}</b> 個月份超出管制界限，請重點追蹤！</div>', unsafe_allow_html=True)
    else:
        st.info("📌 管制圖需要至少 3 個月資料，請擴大時間區間。")


    # ════════════════════════════════════════════════════════════
    #  圖E：各類別堆疊趨勢
    # ════════════════════════════════════════════════════════════
    cat_m = dff.groupby(["年月顯示","事件大類"]).size().reset_index(name="件數")
    if not cat_m.empty:
        piv = cat_m.pivot(index="年月顯示", columns="事件大類", values="件數").fillna(0)
        fig_e = go.Figure()
        for cat in piv.columns:
            fig_e.add_trace(go.Bar(
                x=piv.index, y=piv[cat], name=cat,
                marker_color=CATEGORY_COLORS.get(cat, "#7F8C8D"),
                hovertemplate=f"<b>%{{x}}</b><br>{cat}：%{{y}} 件<extra></extra>"))
        fig_e.update_layout(
            title=dict(text="📊 各類別事件每月趨勢（堆疊）", font=TITLE_FONT),
            barmode="stack", height=380,
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            legend=dict(orientation="h", y=1.1, x=1, xanchor="right",
                        font=dict(size=11, color="#2C3E50")),
            xaxis=dict(
                title=dict(text="年月", font=AXIS_TITLE_FONT),
                tickangle=-45, showgrid=False, tickfont=AXIS_TICK_FONT,
            ),
            yaxis=dict(
                title=dict(text="事件件數", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                gridcolor=GRID_COLOR, griddash="dot",
                zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
            ),
            hovermode="x unified", margin=dict(t=60, b=60))
        st.plotly_chart(fig_e, use_container_width=True)


    # ════════════════════════════════════════════════════════════
    #  圖H：通報者工作年資分析
    # ════════════════════════════════════════════════════════════
    SENIORITY_ORDER = ["未滿1年","1-5年","6-10年","11-15年","16-20年","21-25年","26年以上"]
    SENIORITY_COLORS = ["#003f5c","#2f6a8f","#3498DB","#5dade2","#85c1e9","#aed6f1","#d6eaf8"]

    seniority_col = "通報者資料-工作年資"

    if seniority_col in dff.columns:
        sen_raw = dff[seniority_col].dropna().astype(str).str.strip()
        # 只保留有效的年資標籤
        sen_raw = sen_raw[sen_raw.isin(SENIORITY_ORDER)]

        if not sen_raw.empty:
            col_h1, col_h2 = st.columns([1.3, 1])

            # ── 左：各年資層事件件數（橫向長條，按年資順序排列）
            with col_h1:
                st.markdown('<p class="section-title">👷 通報者工作年資 — 事件件數分佈</p>',
                            unsafe_allow_html=True)
                sen_cnt = (sen_raw.value_counts()
                           .reindex(SENIORITY_ORDER, fill_value=0)
                           .reset_index())
                sen_cnt.columns = ["年資", "件數"]
                sen_cnt["佔比"] = (sen_cnt["件數"] / sen_cnt["件數"].sum() * 100).round(1)

                fig_h1 = go.Figure(go.Bar(
                    x=sen_cnt["件數"],
                    y=sen_cnt["年資"],
                    orientation="h",
                    marker=dict(
                        color=SENIORITY_COLORS,
                        line=dict(width=0),
                    ),
                    text=[f"{v} 件 ({p:.2f}%)"
                          for v, p in zip(sen_cnt["件數"], sen_cnt["佔比"])],
                    textposition="outside",
                    textfont=dict(size=11, color="#1C2833", family="Arial"),
                    hovertemplate="<b>%{y}</b><br>件數：%{x} 件<br>佔比：%{customdata:.2f}%<extra></extra>",
                    customdata=sen_cnt["佔比"],
                ))
                fig_h1.update_layout(
                    height=340,
                    plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                    xaxis=dict(
                        title=dict(text="事件件數", font=AXIS_TITLE_FONT),
                        tickfont=AXIS_TICK_FONT,
                        gridcolor=GRID_COLOR, griddash="dot",
                        zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
                    ),
                    yaxis=dict(
                        title=dict(text="工作年資", font=AXIS_TITLE_FONT),
                        tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                        categoryorder="array",
                        categoryarray=SENIORITY_ORDER,
                        automargin=True,
                    ),
                    margin=dict(t=20, b=50, l=80, r=120),
                )
                st.plotly_chart(fig_h1, use_container_width=True)

            # ── 右：各年資層 SAC 嚴重度堆疊（比較不同年資的嚴重度分布）
            with col_h2:
                st.markdown('<p class="section-title">⚠️ 各年資層 SAC 嚴重度比較</p>',
                            unsafe_allow_html=True)
                sen_sac = (dff[[seniority_col, "SAC_num"]]
                           .dropna()
                           .copy())
                sen_sac[seniority_col] = sen_sac[seniority_col].astype(str).str.strip()
                sen_sac = sen_sac[
                    sen_sac[seniority_col].isin(SENIORITY_ORDER) &
                    sen_sac["SAC_num"].isin([1,2,3,4])
                ]

                if not sen_sac.empty:
                    sac_cross = (sen_sac.groupby([seniority_col, "SAC_num"])
                                 .size().reset_index(name="件數"))
                    sac_piv   = (sac_cross.pivot(
                                    index=seniority_col,
                                    columns="SAC_num",
                                    values="件數")
                                 .reindex(SENIORITY_ORDER)
                                 .fillna(0))

                    fig_h2 = go.Figure()
                    for sac_lv in [1, 2, 3, 4]:
                        if sac_lv in sac_piv.columns:
                            fig_h2.add_trace(go.Bar(
                                name=f"SAC {sac_lv} {SAC_DESC[sac_lv]}",
                                y=sac_piv.index,
                                x=sac_piv[sac_lv],
                                orientation="h",
                                marker_color=SAC_COLORS[sac_lv],
                                marker_opacity=0.85,
                                hovertemplate=(
                                    f"<b>%{{y}}</b><br>"
                                    f"SAC {sac_lv} {SAC_DESC[sac_lv]}：%{{x}} 件"
                                    f"<extra></extra>"
                                ),
                            ))
                    fig_h2.update_layout(
                        barmode="stack",
                        height=340,
                        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                        legend=dict(orientation="h", y=-0.22, x=0.5,
                                    xanchor="center",
                                    font=dict(size=10, color="#2C3E50")),
                        xaxis=dict(
                            title=dict(text="事件件數", font=AXIS_TITLE_FONT),
                            tickfont=AXIS_TICK_FONT,
                            gridcolor=GRID_COLOR, griddash="dot",
                        ),
                        yaxis=dict(
                            title=dict(text="工作年資", font=AXIS_TITLE_FONT),
                            tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                            categoryorder="array",
                            categoryarray=SENIORITY_ORDER,
                            automargin=True,
                        ),
                        margin=dict(t=20, b=80, l=80, r=20),
                    )
                    st.plotly_chart(fig_h2, use_container_width=True)

        else:
            st.info("目前篩選條件下無工作年資資料。")
    else:
        st.markdown(f'<div style="background:#FFF3CD;border-left:4px solid #F39C12;padding:10px 14px;border-radius:4px;color:#7D4700;font-size:13px">⚠️ 找不到欄位：{seniority_col}</div>', unsafe_allow_html=True)


    # ════════════════════════════════════════════════════════════
    #  陪伴者分析：有無陪伴 × 傷害程度 × 活動情境
    # ════════════════════════════════════════════════════════════
    st.markdown("""<div style='background:linear-gradient(135deg,#7E5109,#CA6F1E);
        border-radius:8px;padding:10px 16px;margin-bottom:12px'>
      <span style='font-size:14px;font-weight:700;color:#FFFFFF'>
        👥 陪伴者分析
      </span>
      <span style='font-size:11px;color:#FAD7A0;margin-left:8px'>
        事發時有無陪伴 · 傷害嚴重度差異 · 不在場落差 · 活動情境風險
      </span>
    </div>""", unsafe_allow_html=True)

    # ── 資料準備 ─────────────────────────────────────────────
    _COMP_EVENT = "跌倒事件發生對象-事件發生時有無陪伴者"
    _COMP_DAILY = "跌倒事件發生對象-平日有無陪伴者"
    _INJ_DETAIL = "病人/住民-事件發生後對病人健康的影響程度"
    _INJ_SUM    = "病人/住民-事件發生後對病人健康的影響程度(彙總)"
    _ACT_COL    = "跌倒事件發生對象-事件發生於何項活動過程"

    # df_fall_base 在 load_data 中已 merge 傷害程度欄位，直接篩選時間區間
    # 不可再 join df_all，否則欄位名稱產生 _x/_y 衝突導致計算失敗
    # 同時依側邊欄「發生單位」篩選（全院 = 不篩單位）
    _cf_base = (df_fall_base if sel_unit == "全院"
                else df_fall_base[df_fall_base["單位"].isin(["W11","W12"])]
                if sel_unit == "W11+W12（精神科）"
                else df_fall_base[df_fall_base["單位"] == sel_unit])
    _cf = _cf_base[
        (_cf_base["年月"] >= start_m) & (_cf_base["年月"] <= end_m)
    ].copy()
    _cn_total = len(_cf)

    # 事發時有無陪伴
    _no_comp  = int((_cf[_COMP_EVENT] == "無").sum()) if _COMP_EVENT in _cf.columns else 0
    _yes_comp = int((_cf[_COMP_EVENT] == "有").sum()) if _COMP_EVENT in _cf.columns else 0
    _no_pct   = round(_no_comp / max(_cn_total,1) * 100, 1)

    # 不在場落差：平日有陪伴但事發時無陪伴
    _gap_n = 0
    if _COMP_DAILY in _cf.columns and _COMP_EVENT in _cf.columns:
        _gap_n = int(((_cf[_COMP_DAILY]=="有") & (_cf[_COMP_EVENT]=="無")).sum())

    # 無陪伴且有傷害
    _no_comp_inj = 0
    if _COMP_EVENT in _cf.columns and _INJ_SUM in _cf.columns:
        _no_comp_inj = int(((_cf[_COMP_EVENT]=="無") & (_cf[_INJ_SUM]=="有傷害")).sum())
    _no_comp_inj_pct = round(_no_comp_inj / max(_no_comp,1)*100, 1)

    # ── KPI 三卡（橘色系）────────────────────────────────────
    _ca1, _ca2, _ca3 = st.columns(3)
    _cs = ("background:#FFFFFF;border-radius:12px;padding:16px 18px;"
           "box-shadow:0 2px 10px rgba(0,0,0,0.09);"
           "border-left:5px solid {c};min-height:96px")

    def _ck(col, title, val, sub, c):
        col.markdown(
            f"<div style='{_cs.format(c=c)}'>"
            f"<div style='font-size:11px;color:#5D6D7E;font-weight:700;"
            f"letter-spacing:0.5px;margin-bottom:6px'>{title}</div>"
            f"<div style='font-size:28px;font-weight:900;color:#1C2833;"
            f"line-height:1.1'>{val}</div>"
            f"<div style='font-size:11px;color:#85929E;margin-top:4px'>{sub}</div>"
            f"</div>", unsafe_allow_html=True)

    _ck(_ca1, "🚷 事發時無陪伴佔比",
        f"{_no_pct:.1f}%",
        f"共 {_no_comp} 件 ／ 總 {_cn_total} 件", "#E67E22")
    _ck(_ca2, "⚠️ 陪伴者不在場件數",
        f"{_gap_n} 件",
        "平日有陪伴、事發時卻無陪伴者", "#C0392B")
    _ck(_ca3, "🩹 無陪伴且有傷害",
        f"{_no_comp_inj_pct:.1f}%",
        f"無陪伴中 {_no_comp_inj}/{_no_comp} 件有傷害", "#7D3C98")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 無陪伴跌倒件數月趨勢圖（長條 + 移動平均）
    st.markdown('<p class="section-title">📊 無陪伴跌倒件數月趨勢</p>',
                unsafe_allow_html=True)
    st.caption(
        "橘色長條 = 每月無陪伴跌倒件數（淡色=歷史，深色=本篩選期間）；"
        "紫色折線 = 3 個月移動平均，反映中期趨勢方向"
    )

    if _COMP_EVENT in df_fall_base.columns:
        _tr_base = (df_fall_base if sel_unit == "全院"
                    else df_fall_base[df_fall_base["單位"].isin(["W11","W12"])]
                    if sel_unit == "W11+W12（精神科）"
                    else df_fall_base[df_fall_base["單位"] == sel_unit])
        _tr_no = (_tr_base[_tr_base[_COMP_EVENT] == "無"]
                  .groupby("年月").size()
                  .reset_index(name="件數")
                  .sort_values("年月"))
        _tr_no["年月顯示"] = _tr_no["年月"].str.replace("-", "/", regex=False)
        _tr_no["3月均"]   = _tr_no["件數"].rolling(3, min_periods=1).mean().round(1)

        _tr_target = _tr_no[
            (_tr_no["年月"] >= start_m) & (_tr_no["年月"] <= end_m)
        ]

        fig_trend = go.Figure()

        # 全期長條（淡橘）
        fig_trend.add_trace(go.Bar(
            x=_tr_no["年月顯示"], y=_tr_no["件數"],
            name="無陪伴跌倒件數",
            marker=dict(color="#E67E22", opacity=0.45, line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>無陪伴：%{y} 件<extra></extra>",
        ))

        # 篩選期間長條加深
        if not _tr_target.empty:
            fig_trend.add_trace(go.Bar(
                x=_tr_target["年月顯示"], y=_tr_target["件數"],
                name=f"本期（{start_m}～{end_m}）",
                marker=dict(color="#E67E22", opacity=0.92, line=dict(width=0)),
                hovertemplate="<b>%{x}</b>（本期）<br>無陪伴：%{y} 件<extra></extra>",
            ))

        # 3個月移動平均
        fig_trend.add_trace(go.Scatter(
            x=_tr_no["年月顯示"], y=_tr_no["3月均"],
            mode="lines", name="3 個月移動平均",
            line=dict(color="#7D3C98", width=2),
            hovertemplate="<b>%{x}</b><br>3月均：%{y:.1f} 件<extra></extra>",
        ))

        fig_trend.update_layout(
            height=320,
            barmode="overlay",
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="年月", font=AXIS_TITLE_FONT),
                tickfont=dict(size=9, color="#2C3E50", family="Arial"),
                tickangle=45, showgrid=False,
            ),
            yaxis=dict(
                title=dict(text="無陪伴跌倒件數", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                gridcolor=GRID_COLOR, griddash="dot",
                rangemode="tozero",
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                        font=dict(size=11, color="#2C3E50")),
            margin=dict(t=50, b=70, l=60, r=30),
            bargap=0.15,
        )

        # ── 政策標注：2025/05 住院看護費用補助辦法 ─────────────
        _POLICY_M = "2025/05"
        if _POLICY_M in _tr_no["年月顯示"].values:
            fig_trend.add_vline(
                x=_POLICY_M,
                line_dash="dash", line_color="#1E8449", line_width=1.8,
            )
            fig_trend.add_annotation(
                x=_POLICY_M, y=1.02, xref="x", yref="paper",
                text="▼ 住院看護費用補助辦法",
                showarrow=False,
                font=dict(size=11, color="#1E8449", family="Arial"),
                bgcolor="rgba(255,255,255,0.88)",
                bordercolor="#1E8449", borderwidth=1, borderpad=4,
                xanchor="left",
            )

        st.plotly_chart(fig_trend, use_container_width=True)

        # ── 政策說明 Expander（點擊展開顯示 PDF 第一頁）──────────
        _NURSING_PDF_B64 = "/9j/4AAQSkZJRgABAQEAlgCWAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAbaBNkDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAorjfiD4/TwDaWFzLpVxfx3crQ5hcLsYDIHPUnn8jXJax8Y/EWj6X/ad18OdQtrLcEM13deVtY9Mr5eQPc454oA9forwzUPi741dvKstG0G0uDa/bVguLzzpJIShdSm1lDEqM4GT7V3fws8dXXj7wxLqN5Yx2s9vcG3cxMSkhCq2VB5H3hwSfr6AHcUVW1C+t9L0261C7fZbWsTTStjOFUEk/kK8Q8N/ET4i+INHudWgm8MWmnLdSokuquYiP4toIIBChgoOO3POTQB7xRXzVo/xY8VeIklN1400zQXXIjhXTfNeXAz8uVYc9MZBJxiu4+FGv8AxIvtQlg8V6Vdvp0gLJeXUC27xMOg2/KWU+wOCeuKAPXaKgvb2206xnvbyVYba3jaSWRuiqBkn8q8U8SfG2PTvHumNo2qwal4dljRbu3itiZEbcQSCQCTgjAzjjp6gHuVFeG/F34lWd54Vt9J0ebVbPWriaGXyHt5reVE5IzkDOSFxgmut+GvjbUNbtbTSNS0HXYb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f8NaWNV0e6l8hoBDvkshI3zAY6DBO1+gBIb1b3aiigDlfFfgqLxhqmkNqV2TpWnyGd7AR8XEvAUuxP3QNwxjncea1fEuhQeJvDd/oty7RxXcRjLr1Q9Q3vggHHtWrRQB5R8T/hMPEWjwzeHP9G1C1t0tfIDlY7mBMbUbnGVxkH2wexHoPhjRE8N+F9N0ZHWT7HbrEzqu0OwHzNjtk5P41rUUAFeaeDPh3e6XceO01abMOv3DpG8bjc0JDnfx0b96Rj1U9sE+l0UAeZXfwsdvBHhPw1BcxSR6TqMV1dPJkCRcu0gUY6kvwD261l6b4G8V/wDC77bWtav21DTdPt3NreSIqMyMHCxkIANymQknuB+A9hooAw/FHhDRPGOnLZa1ZieNG3RurFXjPqrDkfToar2nhfTvCWh3KeE9Dsor0QkQhuDI/YPIcsRn1NdJRQB534X+Ftra6bq8nil4tX1jWwRqE5HyhSc7I+AQAQDkY5VcAbRWX4B+DMfg/wAY3Ot3Wo/bUg3R6cpB3IjLjc/bcAWXA4xzx0HrFFAFe/luYdPuJbK3FzdJGzQws4QSPjhSx6ZPeuM8F+A5dNk1TWPEz22o65rEiy3P7vdFCFOUjTdnhSBz/sr/AHcnu6KAKNxoum3WrWmqz2UMl/aKyW87Llow3XH+e59TXC/ELQLvWfiF8PZoYHe2tL2aWaUD5YyojkXPpnyj+VekUUAIyq6MjqGVhgg9CK4zwB8ObDwDZ6lDa3Elw99NuMrfKyxjOxOO4BPPGSe1dpRQB4ppv7O+npq93darr17d20khMccX7t3UnJ81zncT0OAM4znnA6TXPgp4R1DwvJpOmWEWm3AYPDeqpkkVh/eZjllOTlc479hXo9FAGfoWmHRfD+m6UZzObK1jt/NK4L7FC7sZOM46ZrQoooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKA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H1yeyu4ZxZwJGr3kcMkg+0O2FhAVCN2CD1GNyjvXTQTC4t45gkiCRQwWRSrDPYg8g+1AD1VUUKoCqBgADAArlZPhx4ZbXW1mGzntLtzuk+x3UtusjepCMOf5981uvq1rHrUekuzrdSwNcR5U7XVWCthumQWXj/aFXWdUUs7BVHUk4AoAFAVQBnAGOTmloooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAK4vxn/yNngf/ALCcn/oiSu0rnPEHhy91nWNIv4NSgthpkxnjje1Mm9ypQ5IkXjDdAOvegCx4z/5EXxB/2Dbn/wBFNVTSdTg0X4a6ZqNz/qrfS4HIBwWPlrhRnuTgD61qeINMn1nQb3TILmO2N3C8DyvEZNqspU4G5eeeOfwNLoemzaVoVnptxcR3JtYUhWRIjHuVVAGQWbnjnn8KAPPdDmsrX4sWTyalZT3l1osz3Msc6sr3D3EXyA55wAFUddqivUJporeF5ppEjijUs7uwCqBySSegrnpPDN03jiLxGt/bKsdobMW32QnMZdXJ3b/vZUYOMexrpKAPJvEfim0mvNei0bWtNa0udJeWW7itXvHeQb18sOj7VAXBC4PVj3JN/wAIeIY9H8OaT9ou/EGox/YII1gh0CXy48IvKssXPH+0a7zWLaS60HULWBMyS20kaKOMkqQBTtJtWsdGsbR/vwW8cTY9VUD+lAFqNxJGrqGAYAjcpU/iDyPoa8fvC/8AwozxYz58/wC33xb13/aj+ucV7FXJ3XgoXMl3ai/C6Pe3q31zZeTlmkDKxUSbuEZlDEbSeW5ANADbyx1LT/iCNfg0+W+tbnTFspEgeMPFIkjODh2UFSHI4PBHTmq/wxaVtD1YyoI863fbUDbgo845APcZzzWzqvh6S71211uxu47bULe3ktlaeEzJscgkhQ64bKjnPrweMXNC0a30DR4NOtmd0j3M0j43SOzFmc47liT+NAE2pzx2uk3lxKQI4oHdiewCkmvF5YbmP4VWiSp4ncRadbBvOEUNrEcJxt+VmA6A4Y+9eu+INKm1yyGmGVYrGc4vCCd8kfeNewDdCfTIAycjI+IGl63rHhw6VosFrJHdPHFOZH2NEm9SXXscAHjg+melAHW1meJP+RW1f/rym/8AQDWnVDWbGfU9Hu7G3uI7d7iJojI8RkChgQeAy88+tAHK2TOvwHt2jzvHhlSuPX7NxWfpuoaloGheBLlrqO6sr/7LYNbeQqiISQ/I6N97I2gHJIIJwBXY6FojaV4XtdDvJ4ryK3tltQwhMe+NUCgMNzc4HJz+FZOn+CZLX+xra61Q3WmaK/mWNuYNr7gpWPzH3HdsViBhV7E5xQB11cXfNfQ/Ei6m03S7a9uRpFupaa48nYDNNj5tjHBwegrtKwb7wpa6hrs2qyXuowyy20dsyWt08IKozsDlCDnMh79vrQBheE3vH+JHixtSgtobw2lhuS2maVMYm6MyqfTtXW6zLBbaPdXdxFFJHaxtcbZm2plBuBJwcYIBzg469qx/Dvgu28Oa9rGqQ317ctqIiUJdTPMYljBGN7ks2SSeTx0rc1GG4uLGSC2NuHlBQtcIXQKeuU43fTI+tAHicus/2zrlithq9pa/2nZXF1dQWdxNd7HcRAb1gWM7xyOc52nOcCvU/BN3pMnh+PT9KuXn/s3FtcmSCSF/OABZmVwGyxO4k9d3Ws2x8HHSvGGnX0IkuN1ldR31/I4EjuzQeWoC42qAjbVUALg9zzveHfD0Hhywntobi4uXnuZLmae5bdJI7HqT7AKPwoAqXup+KRqM1tp/hyzkgU/Jd3OpeWjj/dWNm/DFV5v+E/kQ+SfDVu/o/nzD8/krqqKAMy9uxZaF5uq6lbaZL5YWS6Dqscb+qmTjGema4PxJNa3fhQ31vrt1rcelTC4j2vtkuLlyEiUNCqfKNzYCZOSPTn05kV12uoZfQjIrIm0R73Wob/ULwzQWrb7S0SPZGj4xvfkl2AJweAM5xnmgCn4a0CHT7291W11e7u7TUAjQQvdPNFGgUYYFySWbqTnuB2ycHxzJqOnarBrX2qNRZ2d89pBt3KjLbs3mtnq+QAOwUsOdxrXg8MarpPiCS60TWo7fSLhzJPplxbGVFcnLNEwZSmeuORkk45xWnqOjSX/iDS78yIbaziuEkgZc+YZAoHtgAN+dAHn/AInjuF8R6ddw3EEM9tdL5cTBhp6TNkAy8ZlmZm4CAFMliTjJ77SpdX1XTZode0tdOkYbCLW+L7h3KuoVl/nWJqHhe/8AEOrtc3LNYW2GTzDN5l1sPBSPHyQAjgsu5yO4rsbeBLW2it4t3lxIEXcxY4AwMk8k+55oA84isfDtn4zSF5rWWMzG1jZphPMk5XIXf5byI465MqHjODVtvCOiTfEM2t5aG/tv7JEgh1CV7oB/NI3/AL0tzjAzXTDwvp41xtWLXLTG5+1CMzHyll8kQ7gnTOwY5zySaqWWk6x/wnt7q99JaGxFktraeSGDnLlzvBJ5HAyDz1wOlAHRQwxW0EcEESRQxqESNFCqqgYAAHQAU+iigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiuf8N+Jz4lsdSu7awdIrW8mtbd2kGy6EZxvU44BPHTj3qHw9440rXdHlv5WOmPb3DWtzBfMsbQzLjcpJOD1HPvQB01FIrBlDKQQRkEd65z+3NRX4jvoTRW50z+yhe+dyJFfzShU84II56DpQB0lFefeMfGf9neIfD0Oka5p/wC9lnS7tmkVww8ospYKGcYZRjbjJOO9bnhvxlpeu3Mmlreo+sW0Ye5g+zSwHBx8yrIA23kfmPUUAdLRRWLq3izRtD1jTNK1C78q81OTy7WPYzb2yByQMDkgc+tAG1RRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQBDdT/ZbSa48mWby0L+XCu52x2Udz7Vx8PxBub8H+zPBXiW45wGnt0tkP4yOP5V21FAHFy+IfHTofs3gSJD2+06xEMfgqn+dbfhu9129sHbxBpEOnXavgLDciZXX1BHT0wa2aKACuG1rxxf+FvGNjpmtacj6TqkwhstQts5jcnASVTnnkcg8jnHUDuaZJFHKFEkavtYMu4ZwR0I96AH1zXjC51SXTJtK0TMV7cRNvvGU7LSLBy/u55CqOc89Aa6WszxHcmy8MatdBWcw2U0gVRknCE4H5UAedXbaVY/C7wxcytewXVzYW8FhpdjfywJdTyICqkKwz8zZLE9+SeKraboXhfw94f0y1m0C28WeJJZ/JulNurzb92ZGfzB8qoCAC2M/LyM5o1ewstJ8A+CdUk065vtQE+lqAiGWUKiq/lxg8KDt6DGTjOTXR69H4g02JfGWmaWg1JEC3+lRybzdWw5ALAcypkkEA9SvzcZAO4W2jisxa2wFtGsflxiFVAiGMDaMYGOwxj2ry4WluPi+0UmtazrM9vpqGcCeNI4h5rEiYRKi7QOdhBJ3dCOR1en6rYfEfwrcRQ/2zpayqEkOx7aaM9flfGG6diRjr1rhoX0jTdb8Q6N4VgMbQ6LDp6q0bq/2qSaRQX3AEn51Yk9hnoKAMSK1tNN0LwWsN9qv9ptZmW20y3hkgSXzYwzlJoYwxPIJy569RXrvgqdL3QheSWUNtfu7JeKhVn8xDtw7B3JYAAfMxb1x0ryf4g2syW8d7oZMDaW0EFvqFs7bkJYRhVlPLkhiPKj+QZYsxOBXofhW5bw3ejwrceG57VgS8eoWNqzWtyD/G7clHPcMTz3IxQB3FVLqz064vLSa7trWW5hYm2eVFLo2OdhPIOPSrdc9rngzSvEOvaNrN6bgXWkSmW3Ecm1Scg/MMc8qOmPfIoA6GiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigApCAQQQCD1BpaKAEACgAAADgAUtFFABVf7DafanuvssH2h8bpfLG5sAgZPU4DMB9T61YooAy9W8OaTrlxp9xqVlHcS6fOLi2Zs/I4+nUdDg8ZA9K1KKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKTcu/buG7GcZ5xQAtFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFICCSARkdaAFooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKw/GOrXmg+DtV1bT0ge6s7dpkWdSUO3k5AIPTPetyuX+JDBPhr4jJ/wCgfKPzUigDF8R+I/Evhvw+NV1DVdAiAaLdBHavv2swUlWeYAkZzjbzg1heJ/FPiWx0q41bR9eluYrWW3KSGxhNleJI4QhZFJbIY4IyCPxzU2oaZe3fjOWx1OGGDS7iWe3ubmS0to1mt2gHlhZG/eM4ZtuV6ba5ybXZtU+GXiOXU9XNxeyXNoY7Us21IoZLZfNVW5USbhJ6HcMd6APfBnAz1rh9W/4Se78Y35hvdS0vQrGzjCtaW0Uz3czMSSgdG+6ODgda7iuL+JelT6jomnzWttJPNZ6lby7Y4mlJQtsfKKyllw2SMjgc0AcVoniC/wBQ1jWLTWdT8QR2kF+baC5ubu3sPLG0ECQAqxJJH3V6EfSvQ/BOia5oWkyW+teIDrLO++GRozujU9V3liXHoTz/AE8Rj8PapqGneLLWx0q5E0+pfZzIum2sMUeRHneXdpUADFsLnrkkEnHv+gLpVnplvpGl3dvNHYQpDsjlVioAwM4PGcUAM8Rapc6ZZIbbSNR1JpiYsWBQPGSOGO9hge/OO9cr4a17xZYfD++utb0oXWp6WZU2PdYludpJ52ptB2lQNpbd9eK6fxV4ji8NaNJdCFrq9cFLSzT79xJjIUegHUnsATXDLqGqaD8MfDOoprN3Pc3+oWs887RtKTHO2541TBYqFbAA544oA1/hvonizw9ollp+r/2cbUK8kgSaR51dyWxyNoAzjA44zk9+9rn9P8UNqeppbQaBrUduwJ+2XNsIIx/wF2D/APjtblw0yW8jW8aSTBSUR32Kx9CcHH1waAOESHxRd+KbLWv7U0ZLCDzrS7+xyvLGEHzBnDOqhwy7e5Xe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WLbV31y8MUWqtdtcQnTZoLhltY4gE3iRQwU/MJC25SSCNvYDuKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACuX+Iunahq3gHVrDS4PPvJ41VIt2Nw3ruGf8AdzXUUUAedSeHtUmmvJY/BGiRS3z7rqSXWHJmHdGIhJ2HuoIB7ggnPNfEnwp4n1bSmvG8N6S18witFk0u7maVYzKhAZDGqugI7/dznoDXtVFACEBlIOcHjg4rml8A6BvZpo7+53HO251K4lUewDORXTUUAeceFPAXhl7zxJ9q8PadOq6vIsPn26ybU8qI4G4HjcWP4muw03wr4f0a6N1peiadZXBUoZbe2SNtp6jIHTgVrBVXO1QMnJwOppaAMbXreK30nVtThtPOvksZQhA3OQEJCLnpkgcDqa5i40rU5/hh4WfTrTz7/TEsLsWjsEMvlqu5MngHGcZ7ivQKKAPNtY+I2q3Gk3VnpXgfxWuqyxNHEZrHZFG5GAxkDEYB598dq7CAa9L4UtNptbTWzbxeaLlDNGkmBvB2sue/IP51s0UAcFceFfEUUd+zXVlqK3t0LuaC1luNMcOI0jIWRJHyCEB2kYJJOfTiJrrwZ4a1TUn8W+DNXgkvZoyhu4PtUYVY1XaJd7bzuDHPX5hXulFAHN+DdR0e70lYdC0m70/T48tGs1m1uhyc/KGxn8KpQeELq9trpPEt42qcTW8UayFEuLZirR+coAHmKQcMuCM5zXY0UAeaXOla+fDFq/iLTrrWPtMIOoWlnOBPaSh2dJIPmAJAfYdrZ+VcZGari9u/GXjjT1m8G61badZlJYtSu0+yT28ikkrnJ8yNsKCvXJJ9Mep0UAFeK6dGbCzlW20O4mu5Fu7SWKTSroJFG87swVo49rlhtyd4wFUDuT7VRQB5P4dtrhviVocr2+vYh0u4R21OLCJzGB5Z645PU56V6H4mtru98Kaxa2ChryaymjgBOAXKELz9SK1aKAOeitNYsPB2m6ZpiQpfpaRW5mmOUtyEALkDliMcKOp6kDmsXVPDcvh3SPDsmkWVxqY0a+a6uIlZfPud8civIMkBn3SbsZGeg7V3dFAHEaX4h8Q694xsXg8O6lpmhw28y3b6kFiZ3baU2oGOcFevox/HW8ewyXHw+8QwwwtNK+nTqkaLuLEocYHc10NFAHkMxxJNb6do+oPbT3iXkl1Dpd1DPvUALsBjRFChQoBLDHXJJrc+HVvMniTxfcSQ6mqTXFrtk1JAszkQDOccHGe3bFehUUAZPiE6lJpj2ekgre3X7pLgj5bcH70h9wOg7nHbJGBNp5Bg8Nw6fNH4Z0u1RprkeYszSxlXiEJT5mI25YgHJOBzkV2tFAHlHhC2vLPwgPF+jWUms6rLJcRyC8uJTPcWq3D7VRnJw2Ap5HOAPSvVIZDLBHI0bRl1DFH6rkdD704AKMAAD0FLQBwOmWXi86Hc6veKf7Z/tV72HTjOAnkbRGINwOOUBYdtxUnvXPt400HwuNcudOs/ENlq1+PNXTLqwkaKOcA8qoG0BifmIbntivXqKAOD8D6emqXx8af2bqOg3l9C0V5pkvyxzOCMTbSAc8EZIBP6lvjfQ7rWbh9OsNY1sXN+ojaCCYJbW0R4eRyFz93OFLfMe2Mkd9RQB5Vqfg/U7DQPFWnafpcs7tY+Rp119vmkM0cgKtGySOwDKB1HByMAdK6J/hzaXFyt1d+IPEM9wIBb+Yt95P7vOduIlUYzXZ0UAU4NMtodLj0+QPdW6KEP2tzMzgf3i2Sx+tctp9hr8fxK1nWdSt4Tp0WmpbWjW3JmAkZ/ukkhhkg9jxjrXa0UAee2Hhi38LaM3ia68PLqXiENLd3IhIaRTJI0jCMH5Sy7tuRgkDgngVq/DCzurD4a6Hb3sTRXAgLsjjBXcxYZHY4IrraKAOEHgLVrrxJc6rqfjDUHRo/s8MdlEls/k7iwV3UZPJPK7T/KoNJ8BWUPigXlnpkdhYaaWNr5oMkl3cnIM0hY7mVdzBQTyWZuBgn0KigDg/DOjeJLrx7qXiTxNb2tu0FqNOsUtn3LJHv3tLySRk44PPUduei8SaXe6xZRWljc/YnaVfMvEOJYYwct5fozYC56AEnnGDtUUAcBa6DqIv8AxDeRW91FdrrcdzZlZhEJ0EESkO3eJsMG4J64GRU934JvofDqy6ZfonieG5kv1vSuElnf/WIw/wCebABMdgqnqK7iigDI8PXetXulhtf0uGwvR8rxwziVH9x6D2Ofqa5rUvDQ0jWvB1n4d0iOHTbW9uLiYRAhEYwOFLHk8liMnPYegrvKKAOC1nwLq+v351y51v7HrVohGki0B8mzJ+9u3cybh8rEgDHapvCeueO7i5Fl4m8KQ26odrahb3kexvcR5Lfr+Art6KAM7UtQu7MhLPSLm/kYZHlvGiL/ALzOw/QE+1cF4o+Hmu+MZo9Zvr6xstVsQG061t4/MiDBg4E7sMyDI6bQBycHJz6dRQB5Rovxa1iC8OleKfBmrwX8Z2PLp9s0yOfUL1x9C2a9Qs7pL20iuY0mjWRchJomjcfVWAIP1qeigDgPHP2g+M/CywpqxRYr1nbTEUuOIgASwwAcn0pnhrS/EDeP7jUZJNes9CSzVEtdRulm+0TEnLbd7bABjpjP5g+hUUANdd6Mu4rkEZXqPpXGW3w4sI7htR1O5uvEOpxbzavrEvmRwk9AqAbV6DJ254yK7WigDz7XPDvjDxLaxw3UXhqyMc8UyyIJrh/3bhwMkJwSoyPQmtm0svG66pBNea3or2YYedbw6fIpZe+GMpIPp29q6iigCOeVIIWmkVmWMbvkjLt+AAJP4V5nrFh4j1zVrtvBsuq6Mt6R9uv9RjVImATaBHHIhlB4HI2gcnqa9QooA4D4e6hqWlbPBesaB/Z8+n2263ubbc9tdRggFgx6MSckHnknjpXT+K31dPDF/wD2Dbpcao6CO3SQgKCxCljnghQS2D1xitiigDjZ/B19dXlzANRSz0k3CPFb2cfl7oWhKSxMFwMFvmVuSpqK30DxJoeuTzaM1lewTafaW8lzqdw4laSHzBuIRDuJVlySRXb0UAcr4K8NX2gtrd3qk1rNfapftdu9sGCqpUBU+bnAwfzrqqKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAoorH1zW7rSBH9m0HUtUMgP/HmIsKfRt7qR+ANAGxRXHWXiHxnfanAjeCVsrBmAlmutTj3hfUIgbkemefauxoAKKKggvbS6lmit7qGaSFtkqxyBjG3owHQ/WgCeiiigAorzG08Qh77xFH4i8djTI7TVZba3gV7aFjCFRl5ZCx+8RkelN8E6nDcfEzU7XSfEd/q2jnS0nIurhpQs5kKkqWHA2joOOfpgA9Qoorze/8AGOnXHxAt7iLxVa22iaTayfbAl0rJdTP0TaCd2wDcSBwSB60AejM6oV3MF3HAycZPpTq838ZajaeIde8Mada/aL3T4Zl1e4lsIXnBVQRCuUBADtu5JAwh5rp9A8YWHiHVNT0uG2vbW+00oLiC7h2MAwypGCRgj3z7UAdDRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAQ3V3bWNu1xd3EVvAuN0kzhFGeBknisC6+IXg6zz53ifScjqEu0c/kpNb91a299ayWt3BFPbyrtkilQ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jNaFFAEMtpbzzwTyxK8luS0TMM7CRgke+CRn0J9TUjxRyMjOis0bbkJGSpwRkehwSPxNOooAw7Xwjotl4ru/EtvZiPU7qEQyyKeGGQScf3jhcn2HvncoooAzYdDsoPEF5rSK32y7gjt5cn5dqFiMD1+bn6D3yDQNMCWEa2iLHp8bR2yLwI1KbCAP93itKigDD8MeFbLwpa3kFnNczfa7p7qWS5lMjlmwANx5IAAHPNbYRQzMFAZupA5NLRQBRt9ItLbVLrUwrPe3KqjSyHJVF6Iv91QcnA6k5OTVbTPC+i6Nquoanp+nxQXmoMGuZVzlz9Og55OMZPJrXooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigArM1/XLXw5pEmqXyyG1hK+a0YBKKTgtjPIGcnHOM8GtOvMPH2q6TZ6xaa3c+Gby+j0p3jv5ZNKDI0DKQCjyYDESbCCp6FvU0Adg/jPQcWTW1/Fepd3409HtHEqrMVZgGIPAwvX3FUtT+IOh6N4ij0vULy1iilt2ljuRcK3zqwBjZByD8wI6559K8zvNN1Ox0zT4Ga60ltKsNR1ySKOSFwspB2MpAO0bpWUL6LnrzU92NZJg8N3Hh+R28QmCcvcSwwLI0CI9zgx79iuUUjIH32OM9QD2+ORZY0kQ7kcBlPqDWRo/ifTta1HUtOtzNHfadIEubeeMoyZztYdipxkEE0+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gAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACvOPjJZ6rdeDJRbX1tDZ+fbK8bWpeUuZ0AIfeAACQcbTnHXmvR65LVvANpr+sS3Osapqd7pz7WXSXn22wYc5KrgtyAcEnn1oAzPEtoEtLK7bxZpn2zTY7iGa51JIzvEigkbUaMKw2rj9c1zPwqsYNYj8MXUvie2v30WykaPTY7cK1u0oC/M4b5sDjpnJ967W80rxJ5cmmaZpfhe30pMrbeZ5jFR2/dqgUH6NVHSfDXjnRtBsNJs9f0OKGyiWJG/s6RmYL/eJlxk+wFAHfNjaQTgH3xXmd/onh8Xstvo+lS+KNZ3kZ1G8kuba0b/pq7syrj+6AXP613Go6BYeINLgs/EFla34QrIytGdnmAfeUEkgcnjJ4OOazZvAHh4DdptodGuAMC40lvsr/iF+VvowIoAg8K+BLXQrp9W1B01DXphiS7MYVYV/55wp0jQdOOT39K66vMtVsPizo0o/sXWNN122JwBfW6wzKPfbtVvrkH2rrPDC+LzEZPFE2jBivyw6fDJlT6l2fB+gX8aAOhrh9IttXXXbNpYtVW7WeY6lNPcM1rJFtfYI1LFR8xjK7VBADbuc57iigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooqOeeG2haaeVIokGWeRgqr9SaAJKKrrf2b3zWKXULXaxCYwBxvEZJAbHXGQRmrFABRRVaXUbGC/gsZryCO7nUtDA8gDyAdSq9Tj2oAs0UUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFYOsan4itLrytJ8OxahGQCJpL9YAD6EbSa3qytZj19xH/AGHc6bCefM+227yfQja6/rQBiW5+It1ewvOvhvT7MODJGpmuJSvcZ+QCuwrmNO0bxampxXWpeLIZrdTl7O20xIkf23MzN+RFdPQAUUVweu+Edat/GOn+IPCl8LVZLhRq1lJIRDcR5+ZwvI34z7ng9c5AO8qpqepW2kabPf3blYYV3HAyWPZQO5JwAO5IFW65L4h2UN14bWZtJvdUubW4SW0t7SR0bzuVVmKEHaCck54xQBl6L4luNH0rV7fX9U26vbxf2lcvPEZILFZmOyDKYJ2gDjr83GR0huNf1eyutQu9R8URPFo7QNd6fpekYMvm48tA8jtktkcLg8j1rKstMv7XRNU0iO1tI1tfK1CeW6mWaWe5Vlcx3UcbMQGwCu0nCgDnkFLLVbTWtSv7GyutSkMk0d6zWmnStLp163992QLJGB0DA8AY4AwAeuKdyhsEZGcHqK8i+KviyJrTxBoq3awi1sQjp9vhj855VOF8tkLsRwcKRw3brXqthHdxafbx388c92saiaWNNiu+OSFycZPauC+JltBpkmjazBJFbTNqkSSkrAiyHY+GZpBgsu1dpYkDAwM4oA89ns7u88S3Gn2sgEo0KOFJYrzUbwp87AEGNF6ddpXbwMZ5r2PwbrGnXento9re39zd6SkcN01/BJHNkrlWbzFBORz9K8o8Ra9qsLf2zYapOl8z29u10twJCY/NwFKx2qxkfO3V+/fgV7B4a8NReHI7/beXF5Pe3TXMs9y25zwFVc9wqqo/M96ANLU7o2WlXd2HjQwQvLulztG0E5OOccV5FqEniHxZ4r8B6nFqGlW6XC3k1nPHYyM0Y8oZLJIw3Z4x0x154r1DX9F/t62jsbi4Mems267iUYa4UciMt2Q/xdyOOATXjd3JOfGWiW3hdL250W1/tAWpNz81wPLUTRW7EcIgwEP97IBxzQB6f4E1a+1Oz1OO9up777HfSW0d/JFHGlwF4JRUA4DAjPP1Pbp7ieG2hMk8yQx5A3uwUAk4HJ9yK47wRZeG5pP7X8J30sNg0HkTaWj4iikBHzNGeUkGCD65yc9T1Or2mn3+j3lrqqRPp8kTC4EpwuzHJJ7Y657YzQBxPiW68X6L4PuXuNato7wanBDaXltAmZIJJET94rqVDfMx+Xjge9Yd5qGknxRPa6h42vbnRLe0V55V1TZI8zEnaq24XKhMEnHG4c1oi7ttQ07wjp0KiHShd/bbfzmJZbC0T5JHJ/vP5bAnsw9K5Ke21uysP+Ebsy7W11YXs1jcpq6RWhgVmCttji+b5HRvnfBzyRQB7bo1zp93o9rNpd0t1YmMCGYTGXcBxy5JJPGDk5z1q9WL4R06z0jwjpWn2E0M9vb2yIs0LBkkIHzMCOuTk/jW1QBzmnXHit/GuqQahZWcfhxIlNjcRvmV34yCM/73UDoMZ5ro65zTvGNtqXjXVPDEdjex3GnRLK9xJHiJwccA5/2uPXB9K6OgAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigCpqdrc3uny29pqE1hOw+S5hRHZD9HBB/L8q5qLwXqsq/8THxxr87f9O5ht1/JUz+tdhRQBx8vw6sbhStxrviWYHqH1eYD8gQKueGvBOl+FLiebTp9Qbz1w8dxdvKhOc7tpOM+9dJRQAUUUUAFYmtaNd6lqWnzQ3pSyUSw39nJkx3ULoRjHZgcYPHBP0rbooA5c6BqGjm2Xw5HpuVt1t5bnUfMkmKITtG5eXAyeCRVC08I+JbbWdV1VPE1jDc6n5XnCHSjhfLUquN0p7etdvRQBlaHYatYW8kera0NVkZ8pL9lWAqPTCnB/z1rnviFp19r1pa6bo8F6NUhmFxBeRyGCG2bYyb3kx82A5+Rck8ZwK7aigDy/xF4CuYPDdrcMt74hvbUxyXkMmo3Km42MGzErSMgOR90qc9sHFelWdx9rsoLnyZYfOjWTypV2umRnDDsR0IqaigDK1nQ49dRba8upxYY/e2sLbBP7Ow+Yr/ALIIzznI4rnNT0W+/wCFn+EprKyEejadZXalo1wkRZVULgcD+HA9j6V3FFAHC6t8K9J1DxQfEVjqOqaNqEn+ufTZljEp9SCp5Pfse4zW14l8Kx+J/CMvh+7v7kJKED3PHmNtYNzgAHOMHjHNdBRQBy1x4Lgv5Lw3cxSO4jSzEUHyhLNOfJB7bzyxHb5R0Bqgmla23xQ0+ZtPtoNC03T5o7aeBsBvMKARlP4Suztxj06V3FFAHO6B4OsfDWs6re6ZLNFbaiyyPY5/cxSDO5kHbdkZHt9AOioooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiuV+JkKT/DPxGkgyosZHH1Ubh+oFAHUPIkalpHVVHUscCs1/Eugx3UdrJrenLcSttjia6QO59AM5NeXeL9P0Kz0maw0Tw/pS6tAizxTyXNuJZDFh3VVJaRsgMpUgf1qn4ytbLVvBuuSC409jby6ez2FrACto0kiYKTbEZleNwcEHBzz2oA9xrL1LxLoWjXK22qazYWMzp5ipdXCRFlzjI3EZ5rUAAAAGAK4PxHa2nh7xJJ4jne7uL7VfJ0yy2WqzLakZbAUsOGIJz2NAGz/AMJ7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KaL41tr/AMVa1oF7LZW11Y3Sw2yfaR5lwrJvyEPOQOuM9/Srmg+IZtX1jX9Pms1g/sq7WBXWTd5oZA4OMDHBHrQBv0UVja94ltNAuNLt54pp7jUroW0EMChn6El8Z+6vc9s0AbNFZmp+I9E0UMdU1exs9oyRPOqH8icmrGmapZazp0OoadcJcWkwzHKnRucUAW6KRmCqWYgKBkk9BXIy+PrOT4b3XjG0t5hBHC7wxXK7DI4Yqo4zwzYAI9aAOvoqvp8891p1rcXNsbaeWJXkgLbjExAJXPfB4zVigAorP03XNM1eS6isL2KeW0kMVxGpw8TAkYZTyOh6+lUvDfiaPxFLq8S2klu+mX8ljJvYMHZcfMpHYgjrQBu0UUUAFFUodY0251S40yC/tpL+2UPNbLIDJGD0JXqOo/MetXaACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAIbuKWaznit52t5njZY5lUMY2I4YAgg4PPIxXkNtf+LL7wBoOqv4sv21TUtQjszClvbpGCZmR/ux7uFRjnPY17JXmvhiz1fSYWt28JXNy9hqF79juJbqOOPZJM5DKpbPIbG7bnBOOCaAHeGtBOt3fiOPVdc1u5itdUe1gj/tOWLCBEPPllc5LHr2Aqx8Hjdv4Nnlub65uom1C4W28+QuY4lbaFDHkjKk8nvWX4rt9StTN4pk+G+kXN9aAS+cl9vuMr91woiwxXg9ScDiuq+G2jT6B8O9F066jMdykHmSo3VXdi5B9wWwaAOqrkL3x9baN4wt/D2t2M1ib1sWF4GDw3GTjaTgFGyQMEHqOcEE9fVLUNI07Vvs/9oWUFybaZZ4TKgby5B0YehoAu1h+I5NZ+ymDTNG0/UopY2Eq3l0Yx0+7t8tt2enUVuVg+Jhqk9stlY6LBqMM4xKZb9rYR4PGSqliPpQB5r4Ws7218Sx3Hh2bQIE1a2bUriOKw8r7IiqqRx5JyA7B8/KCCHPPSqsupeMNNl1/VrHUtPhurnxFb2Jt4LbzY5XaOJR87HO3BA4AOQeR2u+EbUeF9e8UalNbaDZW1jdpE8NpaPPO7NAmIoZCyn5iRxtOWLetOn8Kr4S0LTtevZJrb7TrttqOpWgcfZrQtKxyq4+XbvRSQcEIKAPY685vb6S3+J1va6VHDq2sCFptSknOPsVpkbY4QCArsT0OSeCxxgjsItSTW49StdMvVhmtZxbvMqiQqSiPlQeM4fgnIyOh6Vylhpel6R8V7DTrGPEsWiXNzPI7FpJWkniG92PLMdrcmgBviHxU2m6Zd+I2+H11ILVAz3F6beJyMgcYZ3wM+lbWkXPja51GGbUbHQbfSpFyyQ3Mz3C5HHJQKfpxUXxOmiX4beIkZ13/AGBztJ554Bx9a6i0bfZQN6xqf0oA4b4manqFz4b1fR9CbbPHZSzX93/DbRKhbZn/AJ6OBgDqFJbjjMd5o0/jGx0jSbLzNI0fT4Ybh3hVWzOFBiiQOCGVOrEggnaOoONn4izx6b8NfEkqRgB7GZCEX+KQFc8e7ZJrdsCLbRLUvwI7ZN34KKAPKPBMugeLdD0aXxBqes6nrVzksi3F35UbhiAf3WEToOTivVNZn1Cz0a4n0q0S9vIk3R20khTzcdV3c4JGcE98Zrz/AOGOneJJ/h/4elg1+1tbERbhbpp252XeSQztIRz6hRXZeMfEyeEfC93rL2k115O1UhiHLOxCqCewyRz/ADoAgt0t5NNl122gttC1jUIIjcyXcQZo2AyFkG5ckBiOo7fSvM/CF3p9pquv3Op+OrkOmuzS/ZtOVQt0dqfOURXcqeVwDj5fXNdF4kvNJ8H+DLS98UWOn6l4iupGkiW6iVlN0+N2Gb7kaDaucj5UHfFVdE1abwX4JE+j2934hKzSX2qSC3khjIfmRoGYBcKedqg55PFAHf6D4o07xGZxYLejySNxuLOWEMD0ILqM/wA62qpaPqtrrmj2eqWTM1tdxLNGWGDgjPI9au0AZNp4Z0ax8Q3mvW1hHHql6gjuLgM2XUY4xnA6DOAM4Ga1q5zTvDFzY+NdU8QSa5e3FvexLGmnyH91ARjkc+3HA+8eua6OgAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAz7LRbDT7u+ureALLe3AuZmPOZNgTI9OF/U+tWrq1t761ltbqGOe3lUpJFIoZXU9QQetTUUAYfh3wfoHhMXI0PTksxdMGm2uzbiM4+8TjGT09a0/7PtP7T/tL7On23yfI87HzeXndt+meas0UAYHivwbovjOwitNZtjIkUgkjdG2uvPIDehAwR/UAjeVQqhVAAAwAO1LRQAyaGK5geCeJJYZFKvG6hlYHqCD1FOdFdGRwGVhgg9xS0UAUdG0i00HR7XSrBWW1tU2RhmyQPc1ckjSVCkiK6nBwwyOOadRQBBcWdrdmI3NtDMYXEkfmoG2MONwz0PJ596nIyMGiigBkMMVvCkMEaRRIAqIihVUDsAOlPoooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACszXNbh0SzjkdGmubiVbe1t0OGmlboo9B1JPYAntWnXnWszvdfHfw3YScw2elz3kanp5jloyfrgfrQB39qLkW0f2tomuMZcxAhc+gzzx0z39ulTVS1a6vLLTJrmw09tQuEGVtllWMv64ZuM/WuYi1rx/foDB4R03Ts9Df6pvP4rGhx+dAHaVHOJmgkFu6JMVOxnUsoPbIBGR+IrjZ4PidPGRHe+FrUnukM8hH4kgfpXS6IurppUSa7JZyX4yHezVljYdjhuQcdaAGaLrKaqlzFIggv7OXybu33Z8t8Agg91YEMpwMg9jkA8QLrB0eZtBmtYtRT54xdoWifHVWwQQD6jpXHid7D9oF7aI4h1LQVlmUd5I5WCsfooI/Gsz4oLpeh6ZeOft+qapdo8sVpcXUk0NrEPvzGEts2r2DA5OAKAO7utXvrLwTLrMlvbS30FgbmSCKXMTOqbmVXweMggGpvDGtnxH4Y07WTata/bIRL5LPuKg+/f1/GuFtDBp3wquLDwXZRX2nQ2lxDcS3dw9vLHKFPmbo2jJ3ZJO3j04HNa3w1XxIPCuhG/bSV0r+zIPISBZDOR5a7SzEhRx1AB570Ad0SAMk4ArCvPGvhawBN14j0qIj+FrtN35ZzW7XmXxi0DS1+HV5NBptpFMlzbsJI4VVgTKqk5AznDEfjQB1mieOfDviS/ez0i/a7lRdxZLeQR49nKhT+ddDQBgYFFAGDeeMdFsdYm0mWe4e+hRHeKC0lmID52/cU88HisvQ/FGuSrfpqWg305iuWW0ltrUw+fD1VisxXa3Y+4qv4nm0PwHpurau+qXNhe6rcCUyoY3lmkChVjQSKVCgDuMDJ5ArlNH8WRWGl6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oeM+nNAHAeArXxTZ3Ourpmk+H7a3TWZkkSWd98aYRvKQpHjYN3GemTwMV61XF/DYahLp2t6hqGnXGnvqGsT3MVvcrtkWMhFGR/wE119ybgWsptVia42nyxKSE3dskAnFAHiXiCPztS1/Vrfwj4ot7WF3nvrj7YbfzxGPmK7pMBMA/dViR0K9K6fwyuuaJLox0bw9pMHhu/SLzbW0mZ7i3VgSs7OyKWBH3g245HWp9S8O33hn4deIYbaK713VNVjuHu3jOGaWVCu5I+m0cfKOcDv0q/q/gibVvD+jfZL59K17TIYlgvYeSuFAaNgD8yHHT/64IB2teM6vpVtb+J9W1S38O/ZodOujdJNqs2y1nu3OPOYs+Qv8KbVxnkkYAr2R0WSNkcZVgQR6iuRsPBCWNh/pMiaxqEMU9tbz6gW5t5GyIpevmBR6j6YzQBw2u6h4r0zWPFeope2KyrpEd5kW/nG1jyQlsSW25P7w52nOMnjAr0PwZoOo+HNPktL/AFm4v4pGVrdLpg8kHy/NHv43DOccDA7VXn8EK3g3WNJW78zUdUjZp72RMb5cYX5R91FwoCjoo9ck5U5+IGu6tokc+i2Oj29hepc3V0L4TidQpVlRAAQGDN19vTkA67Xte0nQbVX1iUxwTkxj9w8it7Hap656HrXjniHR7e6tXvvD8E1vFYytfWi2PhExAyIrbAzyY3gE+mOOnAr3iuI1rR5/Cum+JNV8P6fcajLqf72ewFxtVG2sGeJdpyzE5YZ5xxzwQDC8F+MvEa+GtOuLvw/4j1h7pFle4MdrHGoI/wCWQUqSvcbua9TU7lBwRkZweorn/Allc6d4C0GzvI2iuYbGJZI2GCh2jg+46V0NAGP4m06fVNFa2t0jlIljke3lbalwiuC0bHB4YAjpg9DwTUHhbSptMjv2ayh0+C5uPNgsIGBWBdiqegCgsQWIXjnuSa36KACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAoqOCeG5iEsEqSxnIDowIODg8j3FSUAFFFRzTxW0DzTyJFEg3O7thVHqSegoAkopAQQCCCD0IpJJEhiaWV1SNAWZmOAoHUk0AOornL3x/4RsDifxHpu//AJ5xTrK//fK5P6VuWV7b6jZQ3lq5eCZdyMVK5H0IBH40AT0UUUAFFFFABRRVKx1fT9SuLu3s7yKaezk8q4iU/NE3ow6jODg9D2oAu0UVHNPDbpvmlSJc4y7BR+tAElFZ9nr2kaity1jqlndC1/1/kTq/lcZ+bB47/lWafHfhrzbJF1RJFvZlgt5oo3eJ5G6L5gBUE+hNAHRUUVHHPDLJJHHKjvEdsiqwJQ4zg+hwQfxoAkoqBL21kvZLNLmFrqJQ8kKuC6KehI6gGq+oa5pOkNGupapZWTSAlBc3CRlgOuNxGaAL9FZdl4m0HUbpbWx1vTbq4fO2KC7jdzgZOADnpU1/rWl6W6pf6ja2rspZVmlVSVHU4J6Due1AF6imQzRXEKTQyJJE6hkdGBVgehBHUVRXxBoz3wsl1Wya6LmMQidd28dVxn73t1oA0aKKKACiisjSfEVrrGq6vp0MM8c+lTLDMZVAViy7gVIJyMeuDQBr0UUUAFFQS3lrBNHDNcwxyynEaO4DOfQA9anoAKKRmCqWYgADJJ7UKwZQykFSMgjvQAtFNDqzMoYFl6gHkU6gAooooAKKKKACis611/R727Fra6rZT3B3bY451Zm2/ewAecd8dKs3l9aadb+fe3UNtDkL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OTXbzRR3EMkMyK8UilHRhkMCMEGn0UAYMXhy20Kwki8KaZpWn3MoVGlMGBgZwW24LkZ4BI6nmodB8H2+lajLrF/dS6rrky7XvrgAFF/uRIOI09h+JNdJRQAVi2vh2JX1K5vZWnvdSTyp5h8uyIAhY0/uqMk+pJJPttUUAU9O02DTNIttNt9wht4FhVs4YhVCgkjvgdawvCXhK68PajrWoX+ryanealMn76SMIVijBWNTjgkAnJAGfSupooAp3WlWN9d211dW6zS2zbofMJZUb+8F6bvRsZHrVyiigDE1/wAH+H/FPlHW9KgvGhyI3cEMoPYMCDj2q5o+i6foGnrYaXbC2tUJKxKxIH0yTV+igAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACqd3qthYXlnaXV1HDcXrsltG5wZGAyQPwq5Xkd9r15r/AIoWXTdPvIdeLPaaOt5ZssdpCrDz7pywwd33RjP8I6k4APWJ7iG1iaW4mjijXq8jBQPxNR2V/Z6lbC5sLuC6gJIEsEgdSR1GQcV5trS2msaxLczaFoE0s2rx6dY3d9CH8xY1/fswJwSCjooHJIHpmun8IXgnvdct0ntIre3uzFb6ZFEsb2sajbl1AB+cguMjoRg9gAbOta1aaBYC8vRMY2lSFRDEZGLuwVRgepIH41jW3jiG60+91JNG1IafaW8s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vDkfhTw1a6Qly900W95LiQYaV3YszEduSa26ACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACivPdH8S6vD4i8Y2Vze2l41reRppdncTJbs5ZN5jD454YAZB5HX07HQ9RuNV0iG8u9NuNNnfcHtbgguhBI6jgg4yD6EUAaNFFcT4u8XDw94t8MWz6rZ2lhdyXC3y3DIAFWPcpyeV+bj33fSgDtqK52z8caBqOvWmj2N6Lq4u7VruF4RvjKBiDlh0OQevp9K6KgAooooAKKK5uTx54dS+msVu55ryFtkkFvZTyup9NqITQB0lFcpqfjy10rTLjUZ9F102lum+ST7Fs2r64cqf0qGx8aatqVxZPbeC9V/s26CsLx57cYRsENtEhyMHPXNAHY0UVyPxE8Tan4T0C21LS7e2uZGvYoJIpw2GR8jgg8HO3nnvxQB11FFFABRWD4u8SL4b0V54reS71Gb91ZWUK7pJ5T0AHoOpPYA1znhLxvrt/rNp4c1bw9dDUIbRZdRvd0apExB25RWbG7HTIJ67QOgB6DRRWP4n8QJ4X0KXV5rSe5trdlM4gALpGTguAeoGQT7ZPagDYorm/GPiRtB8H3OqWHlz3bbYrKMjd5szsFRcAgnk9PY1f8AD+tR65paTkeVdx4jvLY8NbzADcjDtg9OxGCMgg0AatFFczYeNbW9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qnDo+nQatcarFZQpqFwixzXCp87qvQE/56D0FXaKACmCGITNMI0ErKEL7RuKgkgZ9Bk/mafRQAUUUUAFFFFABRRRQAVWisLaHUbi/SPFzcRxxyvn7yoWKj8N7fnVmigAooooAKKKKACo4YIbaPy4IkiTJO1FCjJOScD1JJqSigAooooAonRtLby92m2h8p2ePMCnYzMWYjjgkkk+5p2qaTp+t2D2OqWcN3avjdFMu4ZHQ+x96uUUAZGieFtC8NrING0u2svM4cxJgt9T1Na9FFADZI0ljaORFdGGGVhkEehFUdP0LSNJeR9N0qxs3k5dra3SMt9doGa0KKAAgEEEZBpscaQxJFEipGgCqijAUDoAOwp1FAGfZaHpenalfajZ2MMN5fsrXMqDBlKjAz/n3rQoooAglsraaR5JII2kePymfHzFM52564yTxTLXTbGxtmtrSzt4IGzuiiiCqc9cgDnNWqKAMDSvBHhjQ9QN/pmh2VrdHP72OPBGeuPT8K36KKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAjnnhtoHnnlSKJBueSRgqqPUk9K4S9+JVjbeMbOztL6y1LR54XE72Ae5mtpVyQSI92VbgYxkEHmu+dFkRkdQyMMMrDII9K4G9uk0nxXZxi++w6WZVWOF9RtbW3Y9wkaoZJDnsxHNAD/ABt4x8QeH9Km1PStO0u4sInij8yW5kMu52VcGEIMEFhwXrV8M63cXGqanomqarY3urWOx5Us7V4liVxkAlmYE/j9a8++Iuna62mavqUehWmmyXs9lDNO2pGQSsk6iNxGseM5IBJIO0dK7fRtG8VaVeQpHJ4fh04yF7mKKCYzSkn5mMjP8z+5HPegDsaKK4rx/oF9rdzoEmmX+oW17a3yuotyREU3KZGlPThQcepOMHPAB2tITgE+npS1V1Ca7t7CWWwtEu7lRlIHm8oP7bsHH5UAcJL8QLiXxxpVvplnqV3pN4kttJG2nNAUuUBcYkl2AkqGyuf4KPE+qeIbn4g6NaaJpGoSJpqTXF2pu44IrhHULHzuORuB4K544HBxV8Xa74vvLGDQ4tB0qz1LVt9vbK+oNNLCChDzYWMBQqk/NuPUcHODatW8Q6bFZaNH4o8KR6iIUtlM6PLczbBxnMoLHknoepoA72xluZ7GGW8tRa3LLmSFZBIEPpuAGfyrO8Ux37+H7htL1eHSryPEkdzOFMWR/C+4H5T0JHI60/w/b67bWTx6/f2d7cb/AJJba3MQ2+hBJ5+mK8v+I8egpcSWtrodxqAe6RNVvIVNxJB5h4hh3tgSPkAhfuqc4yRQBveIvEurWviPQ1iv9Nt4re3Zrv7RfC2gvZmRfkj3KzOqZ3HaCfnUZBJrovB+uXeux3s1xqOkXSxS+X5enxyKYW7hy5ye2DtFcFrOoi08NeC9YE+mWdiPNs0+yX0trGgkwIwH8tnAAQhiQMEZ4rofhUkAh8QTR6pZXzz6iZGFrdyXHljy1UBnkAYk7T7ehoA6nXvEWlaLbSpea3p2n3TREw/a5lHOCFO0kFhn09KwvCvjqfxD4YE5tIk1tFPmQSebDbM3mbF2zFCp3DBAG48j61veIrdG097iOM/bkXFvNEIRMhzk7GmBUd857Z71yFvLca74Ov8ASktofELSytDdwya5FJJECBgl0jCqQQTgDgjjPYApzeOPFEWqeII9Sk0PR7Pw+LeS7k8qW68xZV3KqnKHPb7vU16fb3EV3bRXMDb4pUEiNgjKkZB59q8c0PQ/EV7478TZh0ZZ7Q2OIrySW6jR1gwr8BN7AdyBgk49a9U0OPW4rEpr1xYz3Qc4ks4mjUr2yGJ560AZk/ibV/tUtvZ+DdWmMbFTLLNbxRt7gmQkj8KwNJ8a+L/FE2pw6P4c0u1OnXTWksl9qDspdeuPLiwfwNa3iLXL/UbuTw34XYHUW+W8v8Zi05D1JPeUj7qde5wOvI+Fr298A6T4gjtNLutW0Ow1eWJjDNuuYVCRlm2EYcEkk4YYJPGOgB6RoJ182Lf8JEmmrdhztOnPIYyvvvAIP51W1/V9Y0m8042OhvqdlcTCG5aGXEtvkgB9pGGXrnkYqTwx4r0fxhpQ1HRroTwhtjqQVeNv7rKeh/T0rnPH2n6o93pM8PijUtLsZL+KKY2+xY4gcgZIXcdz7VG47QW5HagDZ8V3WpaZaSalHqRttMt49062+n+fOOeXBL4wB1Gw4wTWF8O9Vu724upNQ8XW2o/bVFxZ6a0kLXFvEeQzmMLyQRlQuB61y/xNt438R+JZY7aGaRPDke930xrooc3HIcMBCcAfMc9OBxUvg+C9Txf4N/tK3u0KaXciA3NtbwjASEZVYmY9Cfv4PP1oA9euzcCzmNoI2uQh8oSkhC2OAcc4zXNT+INbX4c6jrk+kjTNXtbWeX7JO3mqGjDHqMZDbcj61reIbbU7rSJk0m/ezugrFWjjR3bg4Vd/yqScckGuBhfVdQ8H+EtJk8TXF0+rzzWeoXCwp5jJ5MpeP50JBQptyRng59KAK/ibxfrdrpkSadrd1JrIntIpFh0oLaK02whWZw2cq3G18163XiljFpuq+I7HRJJpruWS/eOeP+2QtxbvaBkSVo4olA/1YxzzuU+9dt8Lri9ufCk73t/cXoXULmOCS4fe4iSQqoLHlvunk5PNAEWpeMry213WdNkv9A0qGxaIR3WoTMS++MN/q8rnByPvfhUvhnxoZfCUOqa9PAS2ovp63FpGxjlIlMaPjJwGIHcjmuUutWt4viR4kVtSv7K7e4ijgjstGN1PIEt4yxVzG4GN3THQg96foqS6v8IxJarcXRk8QLNE7R4eRf7RVi5AAxxkngAYPAoA6Tw9LqbfFbxfbyajcS6bBDaPFayNuWN5EOSufuj5DwOPmq58QvEWpeGNEs77TTbBnv4beX7RA8oEbkqSFRgSQcHA64xTPD2D8SPGZ7hbFT/36Y/1pPiLELnTdFtTM8Hna1aASxkBkw+/IJBGRt7igDCsPFWvT/ELS9Pi1CW50+e2nuLuK40iS08tExtaMP8AOcsQOSRW4/xP8OHQW1u2/tK705Bl7iHT5gijO0ksygHB64JrM8PX3h23+IbQxXup39/d2ht7XULiUzQTKjF5I43wBuB5YDIwByDkVyWnQ6xqvwb8L+FtP0eaa21ZVSe+jb5LdBOXk3jtkDg98kdcZAPalvYG09b5fMaBohKNsTFipGfugbs47YzXB3Xj3UP+E1t7fSNL1LVNKNsTdwLp0kM0D/NsdTLsBViCvPHykg16EcrGdigkD5V6D6V4beaj4lhu9cF/bwaZrF+guNQ1CC+8xtJso+UQBV2hiAwUB8szE4AxQB67a6g2q2BtbuGTStQuIXItJLiMzqnTeNjH1HI6Gsb4W3OoXvw20a71S8lvLuaJnaaU5Yje20E9+McnmqltcRap458Matbi4aCXQrqQSTx7HI3wY3DAwfm/Xjir/wAMxt+GXh3A/wCXFD+lAEfj7UL77JYaBo109trOr3KRwyxn5oIkIeWX6BRj33AVieOL7W7+YaBaXNtpl/EVura6hvZ3uGQEru8mKE7lPIK5xz9Kk1zShp3i7w9r+qTGXUZb6Xe0OSsFulrO3lRjqRkZJxlj2HAGLf8AiEalFbat4ku9M0W4S3P7qK9u1njhkYMqyxwlSDgLwW6k+uKAO28F67e+IFvbifU7C6jt5mtnht9Pmt3hlU/MGMrkn6bR/Surry7SG8T2EOn2/hG2trjS0uXN1Dd6dPYgKx3Fg88jSMWLEggEcc+leo0AYHje9vtN8D61f6bcG3vLW0eeKQIrYKDd0YEHIBHTvVrwxeXmoeFNIvdQKG8ubOKabYu0bmQE4H41wU9/qN34d+Klle3klxFZrcpbK4H7tGty+0HGcc963PCWg6v/AGdod/deKb2SCOzhK2UMEUcRHljhvlLN+dAHbVzHiS5v7XWtGay8R6dYRvOsdxY32wfaUJ58s/e8zGQADg/hz0k0Uc8MkMqho5FKup6EEYIrwPxANKTxJaPonhaGfRbQTy286Q71urqIoGlkx+8khjDn7udxBxkdADt/iB4806wj0uHSfEcKXi6vbxXMdownfyySJEZVDds8Yzkcc1t+HdXutU8T6i8d7qEukmINDBe6TJbeW+edkrIu5fY88+grzjxlr2uag3lzy3xgtfEtvDEbKyiRPlKsMSSHG/J4yMZA3cZrsfAl9qU/i/W7W5v9RmtY7S3mWC/mgmdHdpASGhyoGE6A96AOn1zxPDoep6Vp72F7d3GptIkC2qocFF3ENuZccZ/I5xUGgeLBreu6vo8ul3dhd6Z5TSrO0bArIpZeUZhnAPGfxrE+Iccja/4QeIXxcXdyo+wlBMc20n3S/wAoPHftmsPw7aw22p+Pp9TbVtOhhjs5JXlvy1yipAzEmVXOeD0BoA63wlrWoarrnilbu5R7C01P7HZgoFKlUBdcj73J789a62vA7/wTY2/w58My3Nqy67res2zyXTSM0ytO5Y/MTkEIACfVcnnmvfBwMUAFFUNbtUvtCv7WSe4t0mt3RpbbPmoCpyUwCd3pgVkfD7StQ0XwVY2OpzzzXKGQg3DZkVC7FFbk8hSuRnjp2oA6asbxTHfv4fuG0vV4dKvI8SR3M4UxZH8L7gflPQkcjrWzXjPxHj0FLiS1tdDuNQD3SJqt5CpuJIPMPEMO9sCR8gEL91TnGSKAN7xF4l1a18R6GsV/ptvFb27Nd/aL4W0F7MyL8ke5WZ1TO47QT86jIJNdF4P1y712O9muNR0i6WKXy/L0+ORTC3cOXOT2wdorgtZ1EWnhrwXrAn0yzsR5tmn2S+ltY0EmBGA/ls4ACEMSBgjPFdD8KkgEPiCaPVLK+efUTIwtbuS48seWqgM8gDEnafb0NAHTeIvEul6LZ3Ec+t6ZYXxiYwLeTKPmwdpKZDEZ9Kx/DXjifxD4XjuY7KNNaCDzLafzYIC5YqAsxQg5xkAbjyB71s+JLdTYPcwRsuoIuIZoRAJl5ydrTAqB61yStP4h8E3OlRWkHiDzpWiu1OuRySQHgqxkWPAIIzgDggYz2AKjeO/EkN/rjavPomj2GgzQJdsIZbkyiQAgI25DnBH8PUivUIpUmhSWM7kdQyn1B6V474f0XxLf+NfFE/laItxa3VuVS7ea5SOUQKA4wE3Nt2/MRkEtjrz6jpUOtjSHh1m7tGvzuCz2URVQMcHa5PI/KgCro2r6xeavqenanojWS2pBt7xJPMhuUOcEcAhhgZXnHr0rjPGOq6/YTw6K/ic2ep32Ta3EdpHa2ioMl2eRzISVUfdBBJI7HNafhqxvrbxj4mj1bxHqF8iQxhLK7K7fKZcmYBVCgFg6gL02ndkkY8s0S1vUu/Ah06xkEx0+dwbPRY0kkzHHkmSeQLL1+/wBngHdQB774dukvNBtJF1i31hgmyS+t9oSZhwThSQPoKh17UdZ02405tN0ldRtZrgQ3YWXZJCrEASDPDAc5HHb3xhfC2MR+HdSBRkkOs3vmBwobd5pHO3K5wB0OPTimeLYddh8TaDcR+JZrDSpb5Y5Y0gTZyPlRjgkl2+UE4UZ9cZALXivXtR0rX9Otory3tNOls7u6upntWmkUQhCdoDDs57Hp0rN8I+IdV1Xx/qVl9uvbjR4dOinVb6yWCQSuxwVAVTsKg/eBP5VkeIWlu73X9U1PVrn7FpeorpkMaPBBHFFcxwLIXdomOAZRk9QBmsOfLaNc67o9/dWt+NYs9MjvbXVnuI7pAVUcFVVgA7DBXGQfxAPda4P4r6tFbeBdasvsuoSTPaFlkgtJGjjIOQxkA2rgjPXIxXW6vb6lc2Jj0m/hsrrcCJZrfzlx3G3cv55ry3x1qlwlrL4Wl8TahrOs38bQtp+mWcSIikfM0uI5HVQDnAO7HtzQBsyePdXtbDSNPsfDF42rXfkrb297NGGliAHmytsdigA7t3YcHkV6R2rxrwx4d03+3hpmqX3jAa9fWpke+mla2WdExlE2ncqLkfK2Ov0FemeHvDVp4agmhs7q/mjlYMRd3TzbT/s7jxnPNAE82v6XB4gt9Clugmp3EJnhgKN86DOSGxtyMHjOaoeGvFSeIZtTs5LGex1HTJhDdW82CASCVZWH3lIGQcD6Vz/AIiaC1+MPhm8uZY4YY9NvC8kjBVUDbySeB96tHxV40stL8E3Ws6e7TTXCmDTwkZ3XMxGE2DGWGecjggEigCz4D8X/wDCbeHP7WOnSWJE7wmNpA4YrjJVsDI5x0HINdDdc2kw+0G3yhAmG3MfH3vmBHHXkYrnfh1YWOl+ANHstPu7e7iigG+a3cOjSH5nwR/tE1n/ABBt9K2QSf2Nbar4inUw6bbzpvXd1Lup42JncSenTOSKALGgeJItN8PmbxN4s0K8YXLxRXtvMkayAYwpGceZ1yF6cfWuO0vxteahpPiGC013VZL6LWp1sJ7bSHu1WAbdqNtjIK8nuG6Ee+T4T1nUdH8KafFpNi1i93eWbTO1kZri6M8UjvKOQhBK4UA/KF+YAnFZcWr6za6F4uurXUNdtbqDWLiVZA9pDGJAU/1kefMY46hcr096APoW3aQ2cTyfPIYwWwhTccc/KeR9D0rhpfinbp4Ti8Tx+HdYbSmcK8r+SpXMnl8L5hZju9Bj3rvkBVFDNuYDBbGM+9fPhsbh/hfaobbW3hF5HEJXuo1tE/04DAjDBm+rKcGgD1jx5rGpaTZ6KukziG7vtXt7QbkDgoxO4EHtgE5HPHWurVlcZVgwzjIOea821nw3YeIfitY2dw93d2tlayahd28107wq7nZEqpnCniRvw9OKk+E+m21kfFs1knlWr67PDBChPlqkeANo6DJLdPQelAHoxOBk15Ta6z4i8bapdz+GfH2lWFt5rpBp4tYp5lRDt3tn5vmwW9gRXqrosiMjqGVhgqRkEV5j49+Fvh+TQrzWdEtI9G1jT4mure4sf3I3IC2Cq4HOOoAI/SgD0bT4J7XTreC6umurlIwJbhlCmR8ctgcDJzwOlWax/Ceo3Gr+D9G1G7GLm6sYZpeMZZkBJx7k5rTuVuGtpRayRx3BU+W8qF1DdiVBBI9sigDivGfjrWfCcXnjws09o1wlul096qqSxwrFVDNj8K3tAPil2nfxEmkRqceRHp5kYr672fAP4AV5z8QtM8Y6mNF0F/EVjLf6heiRLa2sPLSNIgXMhZnYkKQnpknFdB4U0hdcW31oeLvE0l1bSlLmymu41WKZTh4pI1QA4PHuOR1FAHoVct421qXTLCGPTtZtLLVjIssFvOu/7SgOGTYAXwQeqjIIFdTXE/EbxG+maYmkWDT/ANpaiChe3geZ7W3yBJOVQE8A4H+0R6GgDj9L8draeIdc8XPpuuXOkalew6fY+VGFjZUATeqOwZmZs4AXIwQcHIr2avDdZ0OW88K2On6FF4rlmtJIk06e9MWnxW5BA3Kp8os+3cBkEkk88mu98MeLdTvPFFz4X1XQ5rS4s7NLgXJukn8xSdoLlQAGJycDPQ9KAO1rivFfiHWdI8deEtOsDA9lqss0VzHLHkgIFbcrA8HBPtxXa15748tJb/x/4Etob2eyd5b4i4twhdMQZ43qy+3IPX15oA9CpH3bG2Y3Y4z0zWLofhsaJcTztrOsajJMAG+33fmKv+6oAVfwFbZOBk0AeZaD4w8ZeJb/AE+W0tdIt7Oawe7uI2EkjQ5Zki+bIyWZG4A4CnnpXNN8TvEep+ENL1ax1O3TVrq5jhWxg0iXyCzSlNrzOWGcDPBU10PgKx1k23g7U7WK3XSV0uaO9l8075Ax3Rrsx2YZBz0ZunfndDs1s/CPhKKRtVu9QaGO90W1aZfss1xtYhG+UBNm7fyckDgkgigD3Jc7RuILY5xS1T0r+0f7Ktf7WFsNQ8sfaPsxJj399uecfWrlABRXD29tq48Qxs0Wqi+GoSNNcNcMbM2eW2KE3bc7NgwF3BgSeMk9xQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAVwT/DppNcuZhc6fHpc2rx6q1sLHdLI6quVMm8AKXUtjaevXnFd7RQByvxCs5b7wvHbRIWZ9RsRgDOB9pjyfpXVUUUAFFFFABVPUrq6tbXNlZNd3LHbHHvCKD6ux6KO+AT6A1cooA8t1zwNOmr6N4hv9ObxNqxvGF7EFQRiEwyBURZGCrGjFTycknJ5NSXnhm+1/xP4aMng+DSdI026a6mImgLMwX92NqHpuxnmvTqKAEZQ6MpzgjBwSD+Y6VyXijS5Y7fw7ZaRp4+zprVvLOIlwI41LOzn/gQGT6muuooA808R6DLqXiQ6xokNxP4kgYJZ3Jt/JtLZOQRIzD97kEgldzdMBetVvBHii38Lq3hnXdF1Wy1kzPNc3S2z3EV5K5y0oeNSSCfbgYGeK9UooAwfF3h/wD4SbQRZxtAlxHcQ3MElxF5iI8cityuRkEAqRkcMab4X8NvoB1Oe5ube5vNRuvtEssFt5CgBFVUClm4ULxz3NdBRQByvh2zli8b+MbtkIjmuLVEYjhttumcf99V08sazRPG5YK4KnaxU49iOR+FPooAr2dja6dbLbWdvFbwLkhI1CjJ6njufWuW+HlpqFtaeIJNStnt5rnXbuZFYdUJAUj1Hy8HvXY0UAZ2m6DpWj3F5PpthBaSXjiS4MK7RIw7kDjPJrJ1fwpe61NcC48T6jHZPIksVpFBbbY2RgwyWiLMNyg4J9ua6eigDzrW9E8UWkerSrp+n+IU1KzFndGKU2Vy8QDgdd0ZIEjcjbnjjiuc0fXL648eJqo8B+K0u4LU2iW0sg+zQ5K5ZTJtVSQoHBAPXrzXtFFAGRqFlqeq2VqbbVLrRZgd0ywxwysRj7pLqwB9x+tYH/CHaxpXky6Rq8F69vcS3UUer2qnEsu/zGEkIQrnzH6qw56cDHbUUAeS+JvE3iv7BPouo/D3Ux5+Ql7od6X2uTnzFKplDnn5sZ79a634eWdzpfhS102TRLnTILZPkW6uEllkLEszNs4BJJP49K62igDkrPwzJqviSTxJrkQSdI2g0+1V+bSNhhnLKf8AWsMZIPygAAnrVzwrZ65pmmXlhqjw3LW1w62M4whngwChk2jhskgnHOM4PU9DRQB578PrjUtR8Y+NtRv9Ml08SXVtAsUh3fNHFtbDdx90g+jCuh8W+DNL8aWtla6t57W9rci48uOTaJCARtb257YPvXQ0UAV4rG0git4obWGOO2GIFWMARDGPl9OCRx2rm/hjbPa/DPw9FIpVvsaPg+jfMP0NdZQAAAAMAdBQBXvYZ7i1eK2uTbSNx5yoGZR3wDxn0yCPY1ws/wAPZNXtZLSaZ9OsFk+0RxBhPLdXA5E10zZEmCB+75X1PQD0KigDlrzUfEWk+BWvL7TYb/VYIn+0RWLkBgMgPGCOTjadvHU4zgAu+HME9r8OfD8NzE0Uq2Me5GGCOMjI+mK6eigDmNf0/ULvxr4SubeHfY2c11JdPn7hMDIn5ljWT8XtUisvAGoWclrczPfx/Z4DFEXXzSRtVsdMnp9PWu9oIB6jNACDgDjHtWXrmoatp8ET6Voh1V2bDxrdJCUHY5fgjr/9etWigDzIeGvGN5/wlZNno9jD4iXayS3kkrwfuREfuxgHpnr7VqxaR8QLbSLXT7XWdAtxbwpCJBZSux2qBnl8dvSu4ooAy7KxvbjQls/EEttdXDqVna2RokkGfTJPI6jODz24rJvLC7HxC8Ptb2ezTLTTrtTIi4RGYwhUwOBwvA+vpXVUUAeZX3w3jvIUnu9Ms7i/m8Rm+nkKK3+jeeTtOeoMYUEe+Kv+DrOaPx94nuE0FtIskhtrWNfKVEmZfMYsm3gjDjn3GcHiu+ooA4zX/Busa74ltb4+Krm0061Yyw21vbRiWOQoUbbKQeCrN1B6/TGVqHw40291yG2hsJHidln1XVb2Rpp7kLwsCu5J+bA3FcAKNvfA9IooA4DUNE8Ta38RdKOoQWaeHdIka9hnhOGnkKlURlJJDLknPQj0zgd/RRQAUUUUAIyh0ZTnBGDgkH8x0rkvFGlyx2/h2y0jTx9nTWreWcRLgRxqWdnP/AgMn1NddRQB5p4j0GXUvEh1jRIbifxJAwSzuTb+TaWycgiRmH73IJBK7m6YC9areCPFFv4XVvDOu6LqtlrJmea5ultnuIryVzlpQ8akkE+3AwM8V6pRQBz/AIu8O/8ACTaTbwRm2S5tryC7t3uYfMRWRwTlcgkFdwxkdeop3hbw43h6C/M9xBc3d9dvdTSw2/krkgAKF3NgKAAOa3qKAOV8L2csPijxjcuhVZtRiCEjG4C2i5HtzXRX0E1zYzQ2929pM6EJcRorNGexAYEH6EVYooA5A+ENWiuJb+HxTcXOoSwLbym/s4HhkQFiF2xrGwGWbo3fvgVyeqS6/wCGYdOS88DzX9rptlJZW1zod+5KROEB+Qr5isBGvzZ4557163RQB5z8MLu8t9Gi02PwxrtrbeZJNLfaq6K8juxYsQSGJOeu2t/VvCd9rM832jxRqUdmZo54bWKC22xMjK68tEWYBlB5Psc109FAHDT2fjDw+t1LYWOka/HPL9oljObOeSQBQGJO6MnCLzhenSuNur7WPFvjDS7y8+H3iO2m02ZZTD9rCWsrqcozF1CkqckEcnpzXtdFAGbeWE2rWMUdxc3djuGZo7SYKWz/AA7wNw+qlT71x3iTw0bLUPDdpoGi3Ys4ZbmWZtOnEDKxj2gtISCS248k5OK9DooA8t0HS9St/itaM+h39nbQaZMZLm61GS8Ehd0A+ZidrZXoD056V6lRRQBxE3wy0u+8Vy6/qt5eapIrM9na38nm29qTydqdxnoOn4gGtix8KwR6yNa1K5l1LU0UrDJKAsdsp6iKMcLnuTlj61v0UAcfpPgZdB8eXuvaXeGDT9QhP2vTgPkM+QRIvYfxZ+p9eN2/sUhg1G/srVZNSltmVWJ+ZyFO1AT0XPYcZJPU1p0UAef2fhKfVfCPgPT9StI2ttOSGW+tp15DLauijB7h2GRXL+IvBp0fwVrtrYeFI7i81TVJUtZLeBC1tG0iiMnuEwD06ZHTOR7RRQBn61a6jeaVNDpWpf2denBiuDCsoBHYq3UH864u3+G9rp3ho22t32q+Io4syCwD+VDJIXL4ESYBy5z85IHXgCvRKKAPP7Dw9r3hLwreXmh2Gmz69dSefPZ42RBQMJDEQQAEXgZ6nPTNbfgHw9ceGPBtlp164kvjvnunBzmV2LNz3xnGfaulooAq6lb3F3plzb2l41ncyxssVyqBzExHDbTwcelc1B4d8SX+itpHiPX7W7tpB5c8lraGGa4jPVWbcVXI4O1ckHgjrXX0UAMiijghSGJFjjjUKiKMBQOAAPSoNQlvIbUmwtUuLknCLJL5aD3ZsEgfQE+1WqKAOe0Hwy2n6jc61ql39v1q6URvPs2pDGDkRRLk7UB565J5Ncz4u8JeJbHxMvirwLNAl9OAmo2M7YhugPusR03Dp1B9D1z6PRQBmaFdatd6YkmtabFp97nDRRTiZT7ggD8qx38KXq61ZX8WpfO9wZtTmKkSXCqpEcKdliBOdv45JJJ6uigDg9c8K6dpnhy7uNVbVdZtUs3t7qISbnkh8zejkE/NJEOA2Q2Mnk4FV/hetzqkut+K7i1ntotUliiso7j/AFn2aFNqMfdskn1PPTFeiUUAc7rep+KLS/SDRvDdrqFu65NzLqQh2H0KbCfyJ/Cua1HRPH+r+ING1lk8N2cmlmYxRmaeYN5qbDu+Veg9DXo9FAHEz2HxKnX5dd8PW5/6ZWEh/wDQnNb88OsP4TuIZXt5NYa0kUPACkbS7SFIBJIGcd616KAOb8N6XfaR8ONO0wxKNQt9NSMxluBL5f3Sf97jNc54f8Fanq/w2ttF8WOtvIltFHaw2wAayMagJJv5Jl4ycHHbHXPo9FAHJ+DtK8YaRGbXxFrllqtugxFKsLLOfTc2cH8ifc11lFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUVynivWp01fRvDFhK0V7q8jmSdPvQW8a7pGHox4VT2Jz2oA6vrRUNrawWVtHbW0axwxjCqvb/ABPv3rB1OPxpJeSLpdzoUFoT8j3EMskgHuAwGaAOkoziuV0vQPFMWqxXuq+MWuoUzmzt9Pihjb2JO5v1Brpp4IrmB4J40likUq6OMhgexFAElFcp4e1d7fxPqnhK7keSWyjS6s5ZGJaW2fjBJ6lGyuTyRtzk5NUfHl/aajGfDp1NbKFAl3qt0suxra2Q7gAezuVAHsGPpkA7mivPrzxTJqelafIbvV/D80umzalNFHDDKY4I8ffaRTtJByOPXODVnwnNLbavBaq2vXpvbBb66l1W6DGzJOEjMYAVWb5+Bj7vSgDuKKxtd1mbTBHDDoWqamZwVH2JUwvszM67frXI+GL7xDpXhfUodaeU2lkJnF8l6l1ewpnKqyBWVmVckksc46GgD0eivELm4km8R6ksviHXdctF062utMghu2ge6nl3FQBCEGPlyePlGSehr2XTZbmbS7WW8tTa3TxKZYDIJPLbHK7h97B796ALJZVxuIGTgZPU02SaKIoJJEQu2xNzAbm9B6ng1554untfFPjnSvCou0jttKZdX1NxLsK7eIoweoyWyfQY9RWX8X9d8Oalpeh6a2s2MhfW7YziG4V3hiG7c+FJIwDjPvQB61RXO6R450DXdT/s/TrqeaYqWBNpMiHHXDsoX9an8US6m2lNYaKjf2jegwxzkfJbA8NKx/2QcgdScDpkgA1LO9tdQtI7qyuYrm3kGUlhcOrduCOKi0vVrDWrFb3TbqO5tmZlEkZ4yDgj2INebaD4a1TStNvNM0G81IraE2lhM15C1mwfcHlKxop3IdxKtk7sDJzmjwX4csNL8YS6FbPfXlnosYeG5GpvshlbqkkC7QGbLMDggj8cAHqtV76+ttNsJ768mWG2t4zJLI3RVAyTVivPvGtzL4u1NfAelSMEk2y61dJ0trfORHn+++MAemTjFAHeW1zBeW0VzbSpNBKgeOSNsq6kZBB7ipa4a21iLwDeWfh7WJBHosgEWlai/CoAOIJT0DAD5WP3h15BJ7hWDKGUggjII70ALTJZY4YzJLIsaDqznAH415x4/wDEnhDUdBuItSi1e4jsplJuLC1kje1kztBWVgqhucYyc56U74japd3Hw51i2h8PajLaPp4f7XcSRIqjaGyVZ/M3L3BUHIoA9IBB6GivOfDtlc3/AIl0a/u9L0ezubGxEf8Ao2rO9z5ZTADxiMKy5PQngnIPY9D451zUfD+hQXmmC1M73sFuftSsyBZHCE/KQRjIOaAOlorz2y8YX4+IaaRca5ot7pv9nyXVw9snli2ZHC4LeY3qM5x9BWMPGvh63+Kuva7JqRlsLDSoLMyWiPPGzM7SEkxgj5emT0yR60Aet0VXsL611OwgvrKZZrW4QSRSL0ZSMg1yvinxppdvaXenaZ4jtIddTIiiijN04kB+48aBm56HjIzQB2VFeW2fxX1WO40XSdQ8H6jJrV5HuuIYSiFADguIyxYL/v7e/PFepUAFFYur+JLXTvt1rAY7jVraya9SweTymmQZ+6xGOoxnnB64rhNUvtY8beEtN1K6n0bwxBI0V9aXE2oO00eOQT8qDBUkYyeDQB6rRXH+FL/UNYvZbxfGOj6xZR5jlt9PstoRu3z+ax/PII/OuwoAKK4n4t6udF+GmrXEc7w3DqkMDxuUYOzgcEdMDJ/Cun0S2urLQrC1vrh7m7it40nmc5MjhRuJP1zQBfooooAKKzrLXtJ1HU7zTbPUIJr2yIFxAj5aMn1FaNABVafUbG1u7e0uLy3hubnPkQySqry4xnaCctjI6etQ6rrWl6HbpcarqFrYwu2xXuJQgZsE4BPfANeY+PPEfhzVfFPgiWG7+1i21Myk29vJLwFyMbVOTuC8DJ79qAPXaK5KT4jaHb6rZWF1Dqtob6UQ2893p00Ebuei5dQcnPpXRanqdpo9hJe3rulvHjcyRNIRn2UE/pQBYWWN5HjWRWdMB1ByVzzyO1PrzO913w8fiFoOqReHdabVL3faw3SwmASJjlnjch2VQc7iuAO/AFaHig3qfFXwSlrfXMFvcreLcxJKQkqxxhlBXoeT1xmgDvKKKoatdajaWqyabpg1CUtgxG4EOB65IIoAv0V5rH408bap4rvfDdloGkadfWlutw73t5JMhRsYI8tBk89OOhrvtKXUl02EavJayXwH71rVGWMn2DEn9aALlFFcp8SoUufhn4hDchbGSVSD/Eo3KfzANAHV0Vl+HIHtvDGlQSzSTSpZxK8krFmchBkknqc1qUAFFeXeLPFGj3WspqLXyT2nhyYmG0gnAlvtQI2rGgHJCgkHA5LEdFaujXxjf3mv6loumeH5Zrqwjhkke4ukhjAlTcoJAZs8MDgHpQB11Fcv4E8V3Hi/Rrm7utOFjNbXklo6LL5iuyYyynAOMnHI7V1FAGdc6/o1lF5t1q1hBHz88tyij8yasWGo2Wq2cd5p93Bd20mdk0EgdWxwcEcda8R8Lvb2Vvqvlx6FHP8A2td4kl0aa9nAEhAGI8enAzXs2gzSXGh2kssnmOyct9je0zz/AM8nyyfQ/XvQBo0hIUEkgAckmlrjPD+sanr3j/XZba6B8O6ci2Cx7QRLdA7nZT1G3O09jx6UAdXZX1nqVql1Y3UF1bv92WCQOjfQjirFeL2kml6B4X8QaVJ4p/4Rq6s9fuTayRtlip2soMXWRSrDjHb2r17TrmO8022uYrgXCSRKwmC7RJx1x2z6UAWqpPq+nx6zHpD3ca6hJCZ0tycMyA4JHrzWd4utW1HQZtM/si51GO8BjYQTRxGLuHLOwxggEEAnIHFePya1ren2+o+ODd6VC1rbx6NpZvXNxLcLG+13VsoDvfJL46BuMDJAPfqKp6TdPfaPZ3UkltLJLCju9q++JmIGdjd1znFcr8R7vU7C00WXT9SvrWOfU4bW5is4kd5Y3znblSQ3HBB7nI9ADtqo6brFhq5vBYz+abO5e0nGxl2SrjcvIGeo5HBzxXk9pNq2keHvFmtWura4s1jq0SFb+cSyLbbYWdNshaNSBIxDY4wMnFcvpur6xeXOo2Wj6tLFfah4jCxTRamjv8wQs5jij8t12KSTuxxjHHIB9HUVV1C7ksNPluY7O5vnjGfIt9nmP9NzKPfrXAWtz4mbx82pW2nxWMN9aiOTTNT1ZVLupGJlSMSYbYCpH0z0oA9An1Gytry2s57uCK5ut3kQvIFeXbgttB5OARnFWa8Y+IP9tN8QPDiS3V+IknuTbtCtvagfuifkldm5wMEso46c4r0TwvremXFpBpi6xb3OpRoWkgOoR3Mw5P3ivX8qAOjrO1rXdM8O6bJqGrXsVrbRjl5D1Poo6k+w5qe+uooLWbdLEr7DgPN5eTjj5u317V4IbuK5+Kc2opceG7U6dZrERq+sterJI5LBkZhncoxwuNvrzigD3rS9TtNZ0u21KwlMtrcoJInKlcg+x5FW647SfiJoE0tpp15rtjNqk7bP9EilELMTwAxBA7dTW7req3WlQxNa6Lfao8jbdloYxsPYsXdcD3GfegDTJCgkkADkk1QOuaWJLBBfQMdQLC0KNuWYhdx2kcHgE15nbX2t+HtF8RSX94tlpUE0l2FTVUmvLRSBtgVfLdcF+B8wxu46c8/pupaSmoaP4f1TT74iys3ntYm1NLR45LiU70ZzLH5m0YRcDkE5XnNAHvlFQ2dtFZ2cNtCrrFGgVVdy5AHYkkk/nU1ABRWda69pN7q93pNtqFvLqFoAZ7dXy8YPqPxH0zWjQAUVh674g0fT3/szUEuLiW6iIFrDZyTmVDwRhVIx2OfxrlvAusafbeFpl8LaN4gvrVL6WMQ3MkQMJGMhWkkA8sY4wWIOc80AehRzRTLujkRxkrlWB5HUU+vDtItrvUtL8UabPoWjxW114juHJ1DVTA8c3yYCbEb5h2IPcjBHX2u3iaKzii6MkYXli+CB6nBb68ZoAmorxy5+I3iNfh9aeIDqvh6LUpJF26YsDb5R5/l95cgY5OF/Gtf4oa9pM39gaONTha6Ot27XEVvJvlijTcznamWB4A6d6APTKKxfD/ivRvFC3Z0m6aVrSXyriOSJ4njbnGVcAjOD+VaGoQ3lxZPHY3a2lwcbZmh80L/wHIz+dAFqivIrOPXNV8X+JdG8SeOL23stINuY5rForHeJUL4JCkjGP71enaRfadfWCf2bqUOoQwgRGaO4WYkgfxMCfm9aAL9U7bVrC81C8sLe7iku7IqLmEH5otwyuR6EdDVLxReapZ6Fcto9lc3N+0T+QYRGQjgZUsHZcjPpk14RpviPxJrHinUbjQL511bUJtO5LqYsGHcfMCQsCqjeD84xzwxGKAPpCivLP+Ehs4viXPqniDVLKwGkWC2JhiuCwnuZDvfYuAzhV2cbeCfavTrW5hvbWK5t33wyqHRsEZB+tAEtFc5ceKWh8f23hVrFsXNi12l2so+XDFSpQj2HOT16Uzw/ceJIbPVoPEogU2kjC21CEAC4h25DlMnaw7jge3cgHTUVxvws1jW9f8AWGqa9Kkt3cFyrrGELRhioLAcZOCeAOCK7KgApAykkAglTg4PQ14V4w1nwtqHje8Xx7pGv21rFKLXT7ny5Irfy1+83BBYsxY5APyha9e8LaVo2j+HbW10AJ/ZpUyxOshk3hju3biSTnNAGxRRXGfEE+JbDw9qer6Lr0VitnatOIWskkLFRk/Mx4yB6UAdnRXnvhd7HTodO1vXfG91Jf3trG7Wl9qMSQqzqDhYwFGQTgHGa9C6jIoAKpS6vp8Gr2+ky3caX9xG0sMDHDSKvUj1x6VS8UwG90KfTzpFxqcd2pheOGWOMoCPvlnYYwcYIyQccV44+p61YQah4xN1psA0WzGjac185uZLhkba7q3yAsznaXwRw3BAyQD32is7Qb2XUtAsL2eW0lmmgR5Hs5N8JYjnY3cZzWjQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABXnGqo8f7QOgyyD91Lo00cRPTerMWx+BFej1heI9CbVG0/ULTYuqaXN59o7nAbI2vGx7K6kjPY4POMUAbtYmsaPquozhrLxJeaZDtw0UEEL5PqGdCRT9R0yLxNo8cVxJqenEnd/o1y9vLGwyCCUOCOvqD1GeDWQnw08NFf9Liv75+73mozyE/gXx+lAFjTfDsPh+9OoXvijWLtipUrqN6vk/XYAqj64roLS8tb+Dz7O5huIiceZDIHXP1Fcz/wrDwR38NWDH1ZCx/MmtTS/D2ieFLW6fRtJjtlkAaSO1T5pCM4GPXk/nQByMyPL+0TbtCDiLw4fOI6YM7YH5kVH400Fb3xhby/2JpItzD9olvJ3XzrqWMfKgQKzyBAA2wDDHaCcDB6rw9oUtpqOpa5qCr/AGpqbLvVTkQRIMRxA98DJJHViewFFn4QsLW/vJ5S1zFNfDULeCblbWbHzNH6ZOT9SaAOLupbt9DtfEF/JNrdpeWMkepnSoPlmhjLtFJGWZWicZyVHGS3GQK0/B1rea2ula5NHqlqywrIt/JPEG1GFslFmiQkZCsMMeeO2cVuXPhrWL0XNvN4puYrGYMogtbKBGVD1Usytnr1AFVIvh8kGm2thF4o8SR29rGkUSxXiR7VUAKPlQZ4AoA1vFt9Zad4ZvJtQ2/ZSojcvaNcqNxCjdGvLDJH51yfhmO4uF1bw/pd1eaPeWMkTyS/2TaxRbXUkKqLnqOfm5HH0rt7/R7bVNBl0i+eWeCaHyZHLYduMbsjGG75Hem6RoOn6H9qNkk++6kEs8k9zJO8jBQoJaRiegA/CgDzjR/Bob4l65bTa5qxNvptoolt5UtjtYv8oESKFUbBgDH4132leHRoWnXNrp+pX0jzHcsl/O1yY29RuP44z1pun6PNbeM9a1d9vk3ltaxRYPP7vzN3/oYrdoA89h8PaXp/xG0vT0hE4bSb2e5e4Ad7h3lgDPIT94nn27AADFZyxXWveItNn8P+FbW0tfD2oXEdyk08duskwj2Lt8tWOBv3ZK+ldsfDufHi+JvtLHGmHTxb44GZRJuz+GKonwR/xNNUvIfEGr2cWoXAuHtrORI0VvLRCclS2Tsz1H07kAh8DeM73xXc63b3ekLZnS7xrQzwz+bFK6kghSVU8YHboR06Vc8X69f6dplxb6Ham61doWdM/wCqt1AJ8yRugAxwvViMAdSNDw74esfDGkrptgZTCJHlLTPvdmY5Ys3UnJ6mp9aspdS0LULCCbyJrm2khSXGdjMpAb8Cc0AeYaL9s8L+G/CsFjqD2FjroieW5/s4XEpvJlU5kcyYG4nA+Q424JpdG8GtqPxB8YRXXibXVmheyaSW0uFtjMTDkbhGoHHQY/HJ5r0jSNLn03wrYaV9pAuLWyjt/PVdw3KgXcAevIzXOeBtC8Q6frvibVvEbWhudRnhWM2uQjxxJtD7SSVyCOCc5B9qAOovLO8k0xbSyv2t5MBGuXQSSBcYJGeN/uQR7HpXC3Fhoumas/hiwtfFAukhF3M2n3BT7VvYgySS7xliwIJJHTjgcek1zOr+HtWufFUOs6Vq0FiRZNaTCW184uN4ZSBuXGPm59+noAcc39kf2vH4A1HwlqcdrrcbT+Zc6h9pcFc/O3zvsxjqG644Ndd4T8E2Hgi2kjstU1SW1Cn91e3QeOMdcqMALTNJ8HXVp4vfxLqeuSaleGzNkiNbJEkabw3yhe+Qevr9K6ygDyjxodd8Rajo97ZNFZ6bBqUUNgl5CWF1Mwb9+yZBCLj5B1Jy3TGeQ8ZwXUFhrlpqW6a7t9GtRJ9qa4uykmZSzKyAICQF+ZwAMD3r2nxHodxrVzockNysUen6kl5KrD/WKqOMD3yw/Wq+reD4dSsvE0S3LpLrsKxO5GRFtj2DA9Op/GgDz7wlZRR+PPC0jafBav8AYLsr5OjNp+75YRzuYmTG5ueOvvXafFKAT+B5FIiOL2z4mXcnNzGPmHcc8j0qY+HdWl+ItprE13bNo9jZSxWsKoRKryFAwbsVwgIPB7Y71c1/wR4d8UXttd6xpy3UtuNq5dgGXOQGAIDAHnBz+poA4Gx1TTtJ+KCvfanpl1bw6JLE40mxYRW5aZCVcIz4G1SSWwAOTgVHfD7D8EPE2tyQeRNr7POkO3BWOVlihQD/AK57OPc16BqvhW31CwttGt47ey0MOHura3jCGdRgiPAACoT97uQMdyao+I/Aa+Itd0y7l1a7i021lSafTAS0M7p9wgE/JjuAMH2PNAG2klp4X8Lw/aN6Wun20cbeVE0hVVAXhUBJH0HSuQ1Px7byz+TpUbaQLkDdrerWEsEAB4+Teo3uOwcqPc9K9EprokiMjqrIwwysMgj0NAGD4W8OaTottLdWMxvrq8PmXOpSyCSW5PqWHGPQDgV0Fefa98INB1KR7nR57vw/escmTTZDGjH3jHH5YrS8K+A/+EbdZrnxHr2q3C/8/d/J5Q+kYOD/AMCzQBi+MtVmuV1eeLQHglsLeXT7a+u48PcTzgRokAB5UsyksfTAHUjnPFCXN34Rl0K38Oab5tncw6NbXnnNLcOsWxyyIsW7ARSxAbjBxnv6jd6NLqviC0vL51Fjp7eba2ynPmTEY81/90EhR6kk84Ado/h230q5vLlmE9xcXU1wsrp80YkIJQH0+UD3wPSgDkNP8Y6vN4l8MQ291o9/o+t/aUBtbaSFoTCu4klmOTnIwVFekVxh8Na1cfEq01e6uLM6Lp0M7WaRx7ZfNmwHD9iBgnPXnvya6jUtPXVLJ7SS4uIYpOJDbvsZl7ru6gH1GD7igDhb+KH4i+NYbPy1uPDWgyM9yzDMd1eY2iMdiEBJJ9Tik0nxaPBuvjwd4ouDHEedI1OZvlnh7RyMejr93J68Z5Iz3thYWml2MNjYW8dvawrtjijXCqKy/Ffg/RvGelrYazbGWNG3xyI21429VP8ATpQBuggjIOQaK57wr4Ps/CFq1rYX+pT2xGFhu7jzFj/3Rj5fwroaAOb0zwpbWPjTVPEa29vbzXcKwBYAcuAdzSP0+YnA47L1JPHSUUUAcV8WEC/Dy9vBGHlsJYLyIE4wySoevbjI/GsDxfeeKrnxN4Rzoum2si6i5tzLqDSB28l8htsY2jGTkZ5xXoWv6PD4h8P3+kXDtHFeQNCzqOVyOo+nWudufhzb38lpLf8AiPxFcyWjb4HN4sZjbGMgxovOCR+JoA57Xk128+IfgWx10aYSbu4uo1svMO3yos/MX9yMdK9J1TU7fSbJrmcO/wDDHFEu6SV+yIo5LH/6/SuU0n4dppXjpfEB1jUb2CK0MNvb31y87RSMfnYMxJAIA49Sfau3oA8mtbbxivxLGqMdOa/urBZJLC4BZbW284L5Uci9HxlmOCC3GMAUni/w1oC/EbwpFql7dTW063xlS91OVlXEakBdz/KPXGM9812d54Qh1TxXfalqflXVhc6dFZi1dfulZGcnP4rg9c59qmtvAfhG0C+T4Z0kMvR2tEZv++iCf1oAk8PXvheCJdF8PX2mMtupItbS4RygzycAk9as3PiXQbMuLrW9NgKEhhLdIu0++TUtroekWNwJ7TSrG3mAIEkNuiMAfcDNRHw3oRvnvjounG8kOXnNqnmMfUtjJoA85tPGfhe2+L+sag2uWTW0ulQRpNFJ5is4dsgFc5IGPzrp1+Kvg17+KzTVZDJKwRW+yTBAT0yxTA+tdiiJGoVFVVHQKMCnUAZfiC51G30mVNItzNqMw8q3yPkjYj77nsq9T64wOSK5HXtBg8I/A7VdHhmkmW30yVWlkJJd2BLH2BYnjtXoVcd8R/CereLvDr6fpOrmxkkISaNwDFNGSCQeCQRjIIxnoevABP4k8OTa/wCFLddOunstYtYllsLuNtrRybR8pI/hbGCORjscCtHwnd6ve+F7CfXrX7LqpjK3MWAMOCVzxxzjPHrWrbwi3tooQSRGgQE9TgYp5AIIIyD1FAHkGv219B4l1bUhZaVoy6aDcWbhVnkOW+e7aCNSz7uV3MRsG4gE5Imk02bUviNrDNo8OrSS6fYSuDevbQA4kBYjksOOAVOPbNdnpfgq30+1WOe9ubu5t2nFleyH9/axSf8ALNXOc4HAJ/Kq0Xw8s0vpb6XXfEE13NGsck39oNEzqpJUHywvAyfzNAFP4QReX4GaTYqedqF2+1TkD98y8f8AfNdFrFh4gu5wdK1y20+HZgrJYeexb13FwMe2KzdJ+HWg6JdW9xYNqUTW7FkT+0pymScnKlsEEkkjHOa6icyrbymBVaYITGrHALY4BPpmgDx3wvBqth8P7HWdR17W4bC4ee5vTpqW+LYtKxMhBiLlDyTgkrnpgcb3hPw9d6zM+s3Wq+Io7ITLJprSauzG4ix9941AUA9cehwQMc3/AId+F9c0fQLBPEd9vnt4vLhsoDiKEHOSxH+sc55JyB2Hc0pPA/ibw/rzXPgnW7S00idzJNpV/GzwxuTkmMDlQeuAV/LgAHa61b6jeWBtNOuFtJJvkkuurQp3KDu/YZ4HXnGDw/hPwpYpP4p0iwu7+wsbfU40VbO5MbNi2h3Zbrkkkkggk969FtxOLeMXJjM+0eYYwQpbvgHJxWH4Y8Pz6Fca9LPcrOdS1OS9QgcojKgCn3G0j6YoA5fStI0jwX8UWtUs40g1y1V7S4lJkcXEWRIm9iWyylW5PJBr0fcpYrkbgMkZ5A/yDWL4q8MWfizRjYXTyQyI4mtrmI4kt5V+66n1H8qwPBWleNLHxHqk/iq6tbyJraG3trm3O3zAjOclOzHec0ATePtXvWspPD+iSxR6ldxZmuJZfLjs4CdpdnwdrMflTgnJJ/hNcbLpccGhXOmW1n4U0Zp7aeHNhA17dsI12yhWxGGlUZJGSe+K9M1HwrpWqQ+VPC4RryO9l2OQZpEOVDk8sowOOgAAGAKmn0S2SO4n0+2tIdQeVrqOaSHeFnKbN5HXlRtOCCRnnmgDznwhPqmn+K/DmjaP4hg1Hw5PpL3ZhFisIjiUhVZcfNuLnncf72ea1fiLrFhc3+keHoodQvtTTUIbqSzsFdZRCA2XEgKhRyBncP51P4D8O6/DreqeJPFENpbahdRpaW1nakGO3gQk4BBP3mOcZ/ngd9gZzjmgDybw9Y3smieLLi1udY0/7Nq0+bCxkjuZZtsEICb5Uclsrjg45I54NQaeJ4YvD+l+M7bxS97qrGEz/wBqNGhlxuwYoZuFA7kdskDt6bo+h2uifb/spc/bryS9l3nOJHxnHtxXOw+HvEF/8RItX1mezbStJWUaYsKkSSNKAC0g6ZVcrx164GaAOm0fR7TQdOWxsfP+zoSVWa4eYjPYFyTj2zivOrPUdKl8T2t3FY3Mtnrd3NZ4g0i3gV3w4cSs375tu1skYHB+leqVz1j4J0Ww1n+1oku2uluJrmPzLyVo4nlz5hWPdsGdx7UAeZTWFnaeItcsYtGto4rG6WG3ubXTbZ5QGjV/mnun25G/GMfzrufhh/xMfAuj6xe21kdSmjcvPDbJGSN7AfdGOgGccUx/CMltp2qauuj6RqHiO6uHuwLuFWGOAkIkxkYRVGem7J4zWl8PdGvPD/gHR9Mv1CXcEH71AQdjMxbbxxxnHHpQBU8YW/h60nivZvD2n6p4huv3NjC9ujyzOBxkkcIvUsfuj8AeH8Kt4g0i21nSoBfyXEOpzLNcaPpsI82QhXLGSZ9gxu2gY4CivW7bSLO1v579Yy95Pw88h3PtzkICfuqP7owO/XJrzr/hXWry6jrc1xa+HbtLzUprqFr9ZpcI2NoaMMFyAMfhQB0fw41LVNS8PXZ1e4lnuLbUbm1VplRZAkb7QH2fKWGDkjj69a6DXr2207QL+8veLWKBmmPkmUKmOSUH3gByR6A1zXww0HVfD3hi5ttZt7a2uZtQnuBb2uPLiVm4C46LwSB2BFdfd2sN9ZT2lwu+CeNopF9VYYI/I0AeSiG2m0jxH4dttPuZLl9GkvbUHSobeBQyPGpRIgZNxy2AwJODgevMW7x2utafrmmXNwUvxHp0DW1ldiIyB2bja1uXHBBXaRx0r2TTvDEHhpZJNEgae7mjjhlm1DUJnJSMHYPm39NzcAKOa5nVvAfiCDWB4p0PVLJtdV2Y2k9vts2DABiq5LLIQAC+ct04FAHodqtwtrEt3JFJcBR5jxRlEZu5CkkgfiamrI0CbxBNaE+ILPT7a4GMfYrh5AfXIZRt/M1r0Ac3Y+FLa18dX/iZbe3gmnthajyQd0oJDM8nQbsqoAHZc5OcDpKKKAOU8W3Go6rDL4e0R3glmQi91AcLZxEchT3lYcADpncccZ8tt7TVrPwL4Zl1CUGzu7jT/saQPMIvL+zysyNDEN2cjcxBO8nOBjA901C3ku9NuraKXyZJoXjSTGdhIIB/CsLS/Ca2ukeFLa6nLT6DGgHl/ckcQNETz2+YkUAeDfZEk8KeMXfTLUR/2hcYmXQpSyjKEYuHYGIA/wAJUkc5619PIioioowqjAHoK4DxJ4F1W98L6lpGkahbRjVdRkuLzz4z/q5HBO0joyhR7Hnpwa7DWtFsPEGlTabqUHnW0uMgMVII5BBHII9RQB4ZMkNj8NII5NQ0WHzb9QbSK0zeThb3JJYPubAUnAQ8CvRtNltfFHxM/tO0hYWmi2ZQyPA0TtdT4yCGAbKxKOoyN9bmneEtL8NaXLB4Y0yxsbkptSZo9xz6u33mx1wTz0yOtU7jwQU8ItpGlaze6ffM7TNqMbHzJZmOXeQAgNu547cYxgUAUPhcqXFn4k1ZACuo67dSxv8A3o1YIv8A6Cfzrd8TaNpF7bm/1m8vbe0tYy0vlahNbxFRzlwjAH69as+GfD9r4W8N2Oi2ZZobWPbvbq7Eksx9yST+NRaj4at9avkm1aeS7tIXDw2JAWAMOjOvWQ5/vHaP7ueaAPItO8K6dpFhL4+vfD0d5plzdPJLYXcPnvBYHAjlAfJ3jG8jurn0Fex+H4NBGmpd+HrewjsrlQ6vZRKiyDsflA/+tWm8aSRtG6KyMCrKwyCPQivPdE+F0nhfXJrzw94mv7HT5pfMbTTGssXPUDd09M4zjvQBv+M9V0q30S80y68RW+j313buttI115UqMQQrqAQxAb09MV45YvDqPiuW4eTU7qO81GIQ3Gn2V3I8wt0XeUlklwqlgykgM2Aegxj6Au452QNarB544V5gSEz1OByfpkfWuHg+HupaRqlvqmj6/ItwD5U1pKg+ypAxXesCHcYT8oI5IJAzxQBQhS0k+MGkabHYQWd3p9veX7yRNzcRy7VQsT8xfLOWVs8rnkGvT65HWPh7peo6TLBayz2OpGYXMWqI7PcJOBgOXJyRjjbnGOBjjGt4c07WdM0/yNa1xdXnGNs/2RYCB6EAkH60AcDr3inSLP4z6XNDMdQnTS5rb7Np48+TzTICEIXhTgMfmIAA5xWl4z13VtU0STwtpNmg8SanCyy26ThxZQEctK4GFJXge54Jxk9hbeHNGsr29vbTTbe3u77P2ieFNkkmevzDkevHfnrU+m6Rp+kRPHp9pFbrI2+QovzSN/eZurH3OTQBgeA/EOhalpK6PpQmtp9JjW1nsLpdk0G0bfmHQ9OoyK6ysiPwzpUPimXxJDbeXqc1t9mlkViBImVI3DoSNoGeuOPStfrQBUv7Ox1bTZrS+hhubOZCsiSAMrDv/ntXIfCG0lsvh3aQsztb+fO1qX6mAyNsP0I5HsRV7TPhx4c0hJ4bKG8js52LSWX22byGJ65Tdgg9wcg11SIkcaxxqqooAVVGAAOwoAcRkYryX4geD9Guorfw/avqF3rmrzqIvtOozz/ZoQwaSUqzkBVAIGRySBzXqtwk0lu6QSiKUjCyFN233xkZrN0jw5ZaPPcXaGW51C5x9ovblt0suOgzgBVHZVAA9KAOE0DRvCXh7xE/hDV9A0lbk/vNLvJ7SMm8hJ+6WI5kT7p7kAHua9RVVRFRFCqowABgAVzfjbwTpvjnRlsb9nhlifzLe6ix5kL+o9j3H9QDUvhTQNU8P2RtdQ8RXWsoABE1zEodB/vDlvxJoAz/AB5rV7Bp8mi6JLFHq13CzNcSybI7KHo0ztg7f7q8ct64NcXHpIs9Hl0y1svCmkzSQT2qvaRNfXjNEmJAGxGDKBzgkknnB5r0rVPCulavazW9zC4S4uI7m42OQZmQgqrnqV4A29MdMVPPoln/AKRPa21rFfSy/aFmeEPicJsEhHrt4OCDjPNAHmXhGbUtL1/whpOg+I4NR8PXdjNM8H2BYRHGmBuH8e5nYg5PXOc17BXn/gjw74iHibUvE3imGztbySEWNpaWZzHFCG3MRyfvNhuueucdB6BQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUVn6Trul67BJNpd/BdpE5jkMTZKMOzDqD9a0KACiobi7trRN9zcRQpgndI4UYHXrWQvjbwq1vHcf8JJpIhkdo0dryMBmXG4DJ5I3L+Y9aAN2isbSfFmha5f3FhpuoxT3cCh5IcMrbTj5gCBuXkcjI5FbNABRVe0vra+EptZPNWJzGzqDt3DqAehweDjoQR1BqxQAUUUUAFFV72/tNNt/tF9cxW0O5U8yVwq7mOAMn1JAqrp2uWWp3l/aW7uJrG4+zTK67fn2huD3+U54oA0qKxbXxRp934sv/DSrOmoWUKTvvj+R42A5Vh6FgOcHOcZxW1QAUVheMPFFp4Q8N3Oq3IDug2W8GcNPKfuoOp5PscDJ7Vn+HviHpHiHWBo0UV5Dqa2y3E0Mlu4WPIBK7yADjPXgHsTQB1tFFZWoeJ9B0oyC/1ixt2iIEiSTqGXp1Gcjgg/SgDVorJvPE+hWFxFbXGq2guZVDRW6yB5ZARkFUXLMMegpNE8S6Z4glvYrCSYy2UgiuIp7eSF42IyMq4B5HNAGvRTJZY4InlldUjRSzMxwFA5JNZPhnXj4i0WPU2sLiwSUsY0uMBnjz8sgHUAjkZAP4YJANmisW/8X+G9LO2/1/TLds42yXSBvyzmtCfUrO2jt5ZZ1ENwypHKOUJb7vzDgZ4AJ6kgdSKALVFFFABRRRQAUVVvtTsNLjjk1C+trRJZBFG1xKsYdz0UEkZJwePas6bxj4ZgYpJr+mb/APnmt0jOf+Ag5NAG3RXLW3xE8NXWt22kx3ky3N0SsBltZY0kYfwqzKAT9K6mgAooooAKKKKACiqNzrOnWeqWmmXN3HFeXgY28T5Hm7fvBT0JGRx1q9QAUUVUvtTsNMEBv7yC1E8ohiMzhQ8hBIUE9zg8UAW6KKKACikZlRSzMFVRkknAAoBDKCCCDyCO9AC0UVS1fVLfRNGvdUu932ezgeeQLjcQoJIGccnHFAF2iqmn6hBqWlW2oxB44LiFZlEy7GCsMjcD0PNUx4q8PtqkWmLrenNfSnCW63KF2PpgHr7UAa9FFY994r8P6ZqDWGoazY2l2ED+TPOsbEHOCATz0PSgDYorn7Pxv4fv9dj0W3vmN9KhkiR4JEEoHXYzKA2AM8E10FABRSOwRGY5woycAk/kOtQWV9a6jaJdWc6TQOSA6HuDgg+hBBBHUEUAWKKKKACiubtPHOi3uhafrULz/Yb+7WzikMJ4kZigz7bhjPI5FOuvF9nZeN4/DNzH5byWIvVuWlUIB5hTaQSDnIGMZzn2oA6KiiqCazYSa7Loq3AOoRW63Lw4PEbMVBz06jp15HrQBforP03WbLVp7+G0kZpLC4NtcBkK7ZAAcAkc8EHI9a0KACiszXPEGmeG7Fb3V7n7NatII/NMbMqsem4qDtHucDp60/UtZstK0OfWZ5C1jDD57SRDflMZ3DHUY5oA0KKxU8V6K99pll9rKT6nALizWSF1EyEbuGIxuxyVzkccVtUAFFFUG1rTl15dDa5A1Jrf7UsBU5aPcV3A4x1HTOaAL9FFFABRVO01bTb+4mt7PULS4ng/1scMyu0f+8Acj8auUAFFFZOueIrHw+2mi+83/iYXiWUPlpu/eOCVyOuPl6jPagDWooooAKKKKACiiszV9f07QnsEv5mRr+6W0gCoWLSMCQMDnHHXtxQBp0Vi6v4hj0vWNI0tLSa6udRlZQkOP3MajLStn+EEqPx4yeDrxSxzRLLE6yRuMq6HII9QaAH0UVi2XizRtQ0Bdct7otp7OyCXym6qxU8Yz1B5oA2qK4bwp8Qv+Ehuru2bTL1zFqU1pHcW9nJ5PlqflZ2YAKfUckegruaACiqV3q+n2F/ZWN1dJFc3zMtsjZ/eFRkgHpnB6VU8Q+Irbw5DYy3MM8ovL2KyjWFQW3yZAOCRxx25oA2KKKr317Bp2n3N9cttt7aJppWxnCqCSfyFAFiiqml6naa1pdtqVhL5tpcxiSJ9pGVPseRVugAoorH8VeIYPCnhq81u5heaG1Cs0aEBmBYLxnvzQBsUVHby+fbRTeW8fmIG2SDDLkZwR61JQAUVlah4n0HSjIL/AFixt2iIEiSTqGXp1Gcjgg/SkvPE+hWFxFbXGq2guZVDRW6yB5ZARkFUXLMMegoA1qKyNE8S6Z4glvYrCSYy2UgiuIp7eSF42IyMq4B5HNaksscETyyuqRopZmY4CgckmgB9FY3hnXj4i0WPU2sLiwSUsY0uMBnjz8sgHUAjkZAP4YJS/wDF/hvSztv9f0y3bONsl0gb8s5oA2qKbHIksayRuro4DKynIIPQg1T1PVYNJhWWeG8lDHAW1s5bhs+4jVsfU4FAF6iuc8PeMrXxO0cmm6dqZspFYpfSwBITtJBAy27OQR93tXRAgjIOQe4oAWiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiobi8tbRc3NzDCPWRwv8AOgDyfwLrlr4cl8Xxx6RrF/cS+I7zC2Fg8o2qwABfAQd+C3evV7K5N5ZQ3LW89sZUDGGcAOmezAEjP415v4B8VeHNMtvEn27XtLtml8Q30qrNdxqWUvwQCeQfWuu07x34V1fUl07T9fsLm7cHZFHKCWx6ep9hQBl+PrK2vdT8IJcxQyD+1/8AlsgZRi3mbkH3VT+FcFd2lnB4e8E/2Sslve22tSxXklvbCeX7UqOJm2/xEsmfQLg8AYrv/F00cvjTwTprhWM95czlSMgrHbSA/wDoYrO8R2XhvwtqfhW1MVlpulC8u55UbCRndbSA9fUuBj6AdhQBX8DRNB4413UtYubsXl+YrPT/AO1Io4LidIow0pVFVQV3MOgPC9etbHxL1q503QrLTrGZob3Wr+HTYpVPzRCQ4Zh77cgHsSDXLLq+k+DvF9vL4ujuJ4Zox/YmtXaM3kQ4/wBS6kZRxnl8bmBG4itP4mPBfad4V8SWNxFc2Gna3bXE00Lh08ottLZHHB2j8aAPQre3tdL0+O3hVLe0togiLnCoij+QArIu/HHhSxB+0+JNJjI/hN2hb8gc1vMqupVlDKwwQRkEVlWHhbw/pTs9homnWzsSxaG2RST9QKAMKT4reDFUmLVnuMf8+1pNLn8VQitbwz4u0nxZBPLpbz5gYLKk8DRMuc44Ycg4PSt2igDyv4n3WpTW92YrLVobKBY45nnaFbJyJUaOQncXGGHJC9OuAKr6RHdR+L9Y1LWNLgENjqom3Qi4uysssEf+rEafMyqFBJXjdgdcnuPGsEN7oE1rL9ldHysiXGqSWKbSCDueMEkc/dIwa4D4W2P9o+DylvqUFtq97biQ6jYWMjTI4bP76dyUdskZTjv9QAaNj4lC/E/X7218Pa7ebrKzhxHZ+UyjMhLESlCAeMeu0+leoq25FYqVyM4PUVxnhppB8R/FMM04mmhsdNSSTaF3ttmJOB0znOPeu0oA858XJdTeJbO98M3Pna3Zuy3El0N9nawMvzhycCNhgH5fnPfjpU8A+K/BGm6UZ212IalqN0/2m6v3RJruQEjfgE7Y/wC6OABx1zWl8TINSg8Oy6grWk2j2LCa60piYhdxD7waTPrghMYOCDuyBWbo/hiy8b6naaxcaFBp3hiy+bTdONusZunx/rpFA4QDhVPXqeDggHqNeS+Jm1KOX4nCw06ykt5LFftNxLcmNlAtDnChG3EA8ZIHvXrQGBgdK8z1fwzpfiZPGt1ZeJNYhEkht7yK0IMayRwIGXbjMny4BGRnkcdaAHXk1hceINLub/UtMsxpNkH0y0uZ18y4mdMCVkB3eWoyq8ZJLHsM3vhdcLe2GtX1xdWsmq3mpST3kFuxP2Y4CpGc4PCp19zVaebTYm8N69pHiSGztbuzGlQXE1m0yz5KtGCcrsbKOPm7kjrWn4TGmaDrWqaBJetJrlzO+oztNCIjcK/8SYJBUY24ByMHI7kApfFQySWOiW0cqIr6gZLhZZnije3jgleQOU5K4Ucd+K5vw+dGu/EM2s3jaQt4dHIh0j7Mbc3CyZcF2dm8w4RlPBx1x0zq/EnSxr+m69qF2JE0/RtLnW2wxUTXJG4n3VdiD0JLg8Ag8X4bu4ovHOtR2V7pzG4s4oI/IuYdsrskgAxBBsJyRnLLjjJOcKAWNN8TR+F/Dd9rOjR+HpLi7nS9fT7cSTLEkjKBEGRVSIqpGc5ywP0Hul1aw31nNaXUSyQTIY5I25DKRgivnya6vtZ+HccMMWosgaLTVe81gRw+dGyAqsaqI3HynBLc44yeK+iaAON+G2t3Oq6DeWF/KZr7Rr6bTZpWPMvlnCufcrjJ7kE12VeefCe3d4PE+s/8sNU126ntj2eINgMPqd35V6HQBzHhXxpB4o1LWrBdOvLG40qcRSLcptLq27aw+uw8fSunqjYaVBYXN5cq0ktzeSeZNLIQScDCqMAAKo4A+pOSSTeoA4/4h2sF5p2iRXEKSodcsso6hgf3oB4PsSPxrP1bXBYy3aWHjHwzpdjauRLHDZ+dPEV+8rKJcAjv8vFX/Hlwq3XhS0z89xrsBA9kDOT+g/Oqep+B9cvovEljaa7Z6fpusztI6rYGWXDxRo+WMigZ2sMbTwc57AAbr9xbal4x+Hd5BPFdQST3LpNFyj/6MxBHXuK7q4uYLSBp7maOGFfvSSOFUduSa4DxFDBpXjL4baXAFVIZbhI1UYG1LfbwPxFd9d2ltf2ktreW8VxbyrtkilQMrD0IPBoAwrz4geD7HIuPE2lAjqq3SO35KSazJ/iz4PijLRX9zc47W9jO+fx2Y/Wuk07w/o2kIqabpVlaKvTyIFT9QK0qAMzQdesPEmlJqOmySPAxK/vI2jZWHUFWANcf458Waxa6H4kt9MjudL1PS/s8lvdGNJYrlJXCjbuUjOcgjGQQOTXoZzjjrXmt/Y65qWraZo+u30E99eXi3k9vZhhb21nbuHHB5LPIIwS3qQOAcgFTxLa6ba31hDrkvi7Wr5blYrSSMrbIbhkPEbr5SjIDdDXY+ENCs9MtHu4dK1DTbm5/18F5ftctkHg58x1/Ec156ln4o8VadoOoLqN/qxs0bUZYmaKzR3IKxJHIkYPmbWY5yQBjONwNb3heO6tfijcW6XWqJZy6FDdzWV9dvOY53kI5LE4IAI4OKAPSK8s+Kt1Z3/ifwj4evGAs1vRqN8xBKxxIdib/AEVmcrk8CvQdc1yy8P6a17es2M7Ioo13STOeiIo5Zj2H9K5zw14XnvRq+s+KLaNtR1tPJktCdy21rjCwZ7nBJYjqT7UAdrTJZBDC8pV2CKW2ou5jjsAOp9q8ls/HNx8MtbHhTxi00ul9dM1faWJh7LJjklehI56cYINep6dqdhq9ml5p15Bd2z/dlgkDqfxHegDlP+E/tdTilgs/C3iS/jYGNx/Z3loexBMrKPrXO+B4vGvhPRbrS4/Cl1d2gu5JLEXmpwRtDAQNsZwX6HP51t+I9X1vWvFVl4d8J3ZtjZzCfVtQEYdIUxxDg8M7ZzjqMA+tavje/wBe0XR/7a0NEuvsOZLqwdf+PiL+Iqw5V1AyOx54PFAE/h3U/Et9PcJr3h2LTEUAwyRXyzh/YgAEH36VynxI1WXUGtdHtrU3Okw6harrDhtocPKirbqe7EsGYdlABPzV2nhjxFZeK/DtnrVhuFvcqSFf7yMCQyn3BBFYXxAa3sdF0e1jSOJbnXbGNEUAAsbhXPHr8pNAHK67p+nWcnxE1H/hHkv5onykoWLFsRZRvv8AnIxyxOVBPt0p93p98NC8CrrWkWtnexa3YhmR0d5GEbli21QFO4dAT9aparqWjXms64t1faMLiDxHvez1K4KCaFbNITlAGLDd2xglay4tR0Ky1LRbCzvreXVL/wAVQX0kFrbSxQxxEMg2B1AwOMkdSfyAPfK831g6hB8aFudJ0q3v7tfDwXE9z5IQG4POdreh7etekV5xYaJa+NvGXiDW7ma9Gnw+Xplo1rdywCYR7jLkow3L5jEDt8poAjiGuSfFzw/Jr9vpsUw067MQspXkAGY+pZV557V6XXmaaHpfh34ueHLTS7doUk0+8dw0zyEnKc5ck9q9MoA4qW51y6+IWq6bHrv2PS7awguQoto2ZC5dTh2HA/dk8g9e1cf4QumvvGGp6Ve6tq0OnauW1DSHWdYDdKCUlbMaqQW2hwBj5TnqST0On21t4o+InjO3uGlNnbJY2kkanas+FldkbuVy4yARnGDkEg7XjHwXofiW2sZdRuJ9Pk06QPa3lrMsLwk4GAxBAGQvbqBigDN+HUVza6p4tspNQvLq1tNT8m2S6naYxr5ascMxJ5Levb61J8UfEF1pPhG+tNJUvqtzazOgX/ljCikyyn0wvA/2mWqnwxONV8ZRfbZb4R6vs+0y7d0hESAk7QFzx2ArW8fQWlj4E8V3wjVZ7jTJo5JSckjyyqrk9Blug4ySepNAHKeK/D3hiXQ9O0O1F3BqT2kE1hbyJdzxGOJ0Lbo4soTjhjjPzZ75rnvBs/hq5aLXfEXha0P9uXEdhawQ6MGggkRpAcFiSxbHJCjG3B6ceheMrVv7K0m7WIBrbhZklukkTcmMD7Mpcg9xkDIFcH8GtJkuI9JvZbSNDbeeySyaVOeruDsuGk2g4PZOnB5yaAPZdSkurHRbl9Ls457qGEm3ti4jV2A+Vc9AP88V5Dp+rahBpF1e/wDCSeG7TXtUuFka9guDeeZKDiOFio2RR4GwZLYyTya9rJCqWYgADJJ7V4Jpsd4ng3Sm+y6lBpT6jZOEu3jEDs92sgeBQC2Crc5IHPTOcAHSy20FhqWuJrMXiZjdX5uUj0RbgwzZijUjdCOoZWBDEHivSNFuxfaPa3C2l7aKyYEF8CJlA4+fJJzxnkk1wnh628Rxaj4sXQRpESy65M0k14ZHZSY4zgRqAO+c7uc12Ok6uZ7y70m4nhuNS06GFrpoE2KWkDEYUkkcL3PegDlfG/iXxHp+lzwr4e0p1uJ1tLWG7uDcG+djgKIlUDGMk7mGADxWX408Qyy+ENSsv+Eh0WBpNFkd9Ps7Rp2P7tlYLKHwE3AqG2DHfpUvjXw9Nqdzpmq67PJHNLqlraWVtbzFfssTyjed6kEysByw6AYHTJwPE2hXdjF4lsNPklnt9K8NxwTSLci1+X/SXG5EQh8KRx8oPfrwAbvg7UY/7S8N2V9rniKW5ls82sVzpiQWspSIbgpMQbgHOc9O5zz0XxTnuLXwFdXNrd3drLHcW372zkZJArTorAbeTkMeK5Lw7pN9pPizwQL9YwZrW5KYv7i5ORAmciXhfouB27Ct74t65pdn4Ul0i7uJUvL1oWt4o4pC0u2ZCQrKMbgB0znpQBlWszxfFTSns7XxDBCdOupJYb65dmu9u0LhXkOMFuAdvOKqS+I9Wbxr4n8W2fhyRo9F0pLRo764WFkAzO/C78nG3jPpnHSpGll0fxEvjCz0XVE0mzsJY7m41u9kR3LuhBjRy75wuAu1ckgcUzW7kaD8INagvpoR4k1tmluLJZAZRLcsAE29flQgf8BNAHp3h7Vjr3h3TtWNq9r9st0nELsGKhhkcjrx/kVyXxBsdGiMdxc2d3q2q3zC3sNKa9l8maXHUxBtoUDljjGOvJrtdNs10/S7SyXG23hSIY9FUD+lcJaatpcXxe19tcvYLW7tba3g0xbqQRgwsu6RkzwSX4OOcLigC54B+G2n+DxJqMyQza5cg/aJ4kCRxgnJjiQYCqMDtk4/AdzWLeeL/DenwNNd69psUajOWukyfoM5P4Vznw78fR+NtU8SC3WY2dtdqbSRkIUxFAuM9juRmwefnoA6XWtR1mzZI9I0I6i7jJke7SCND7k5b8lNcX4zudQn8RaPfv8AYrOy0MrJcTXSySw/a5wI0RdgBbZuzngfOucdut1Oy8U3WoMLDWtPsdPwMf6A0s4PcZMm38dv4VzOrR3Hia8tvB0Orz3r2kwu9U1JYo18gp80UeFG3eX2nbjhVOetAGjoN540fxle2eo/YLrRIYwGvI7drc+cRnZGC77wMgEk9c85GK7SuQ0HxxbzanJ4d15otP8AEVudrQudqXQ7SQk/eVuu3qOR2zXX0AUdV1SLSrVZnilnkkkWKGCEAvK7dFGSB6nJIAAJJpuk6smqxT/6NPa3FtL5M9vPt3xvtVhypKkFWUggnr65FSanplvqtp9nuPMADrIkkTlHjdTkMrDoR/8AWPBpul6Vb6TBLHC0sjzSGWaaZy7yuQBuY/RVHoAAB0oAvV554ha6s/GekzxLb6n4guJfLs7N8iGwtP8AltNxyGIwN565CgcHPoThijBCA+PlJGQD9O9cE+k22k/E7Rrozz3F/cWF9LdzsSXkVTAFXaOiDJ2qB155JJIByc+pNf8Ai3VrG28bJN9pkZLqawsPNuY4BwLeEJvPGeXCgAsT8zZx3Xw91Owl0ibRLPSbnSn0ZxbvaThsgH5ldS2CQwyeQD14rz3Xrq+8N+Ih4m8Qu2lq0M0WjxabaxqZnZst5obeElf5STgjGeQ3FeqeD7HV7Hw1aJr9+L7VGXfPMFUYzyEBA+YLnGe9AFL4hanf6b4Zf7FazvHO3lXVzC6KbWDBLyDeQN20EDnqR9DyFleeIoPDyvZCKy0y4ultP7LhtZbm40q38ohCfIdXDkqGYdRv6gg56Xx0La/vtI0W7g1Am5kea0a3uTDDNcRKXWKVl+ZQcbgR3XPauZ8WeG7i18CeILs6LaW7Xn9nzeXArS3CFJVMgmOHEmzLfOFbK5yDjkA5Sws9XsLiY6Na3ll4huY4zCxihQtcOSZ2c3JMhTGMY+YnOfWvoCzjuIrKCO7nWe4WNVllVNgdgOWC9snnFeA21pLqmq+FZ7C3lvbNtXtrhJILQrGsasdz58uMbR3OwCvoCeCK6t5LeeNZIZVKOjDIZSMEGgDhvFHg2S/mi1DUvF97Hb2V9HewRytFBHAit8670VX+4XAO4YyM5xWA174K8cWuh65rOrpZafCrudOv9XZSZEOyN9u/rjed33jkepzkeMdI8Pm4h0rw34Wsri0/tGC01PUXbGxnkVRCkrBmByRvK52jjqeOm8VXOr+ENEtLqx8PeGUD3UNpHZRozly52hVbagH/AHyaAOo8Haj4SnspbHwneWUkFu254beTdsJ74POD69K5v4ra4WsYvDduk0kd1Nbrq00HW2tZJVT/AL6cnAHXG49Oa9Ct7WC3G6K2hhdgN3lKB+uBmuP8fQWem+Go4oYlje+1my3nq0jm4jYkk8k4X8AAOgoAq+N7S/srvwxY6Pq15aW91fQ2J0+3ZY0EAVmdgygSAhVHRsdOKwfCM3hzTviRrmqHVfssLzjSLKGe7kczSqB5jOXJySwwu484OOortLSM6/41bWCP+JbpET2tm56SzuR50g9lChAfXfWX4vEGsfEDwfoCBXNvcSavcKOfLWNSI2P1dsfhQB21/FdzWMsdhcx21yw/dzSQ+aqn3XIz+Yrx/wAbrcXPiLRvCOv+M5547pvtd5FbWaRARpygUKrOWZxwMnAUkjpXruptqK2ZXS44GunO1WuGIjj/ANogcnHoMZ9R1ry7xF4YbT/Enhm2smu9R1q5nur29u451gnl2w7M7+kaAuqhRwBwOeaALsel+Etc16PQ9Qv/ABXc3U0TSxJqM95Akqr97aDsHH0r0bTdPt9K06CwtBILeBdqCSVpGA9NzEk/ia800TTrzTvinpA1C1kglk027KiXV5b9j88XJMigJ34XivVaAPJfEzalHL8ThYadZSW8liv2m4luTGygWhzhQjbiAeMkD3rQvJrC48QaXc3+paZZjSbIPplpczr5lxM6YErIDu8tRlV4ySWPYZbq/hnS/EyeNbqy8SaxCJJDb3kVoQY1kjgQMu3GZPlwCMjPI461PPNpsTeG9e0jxJDZ2t3ZjSoLiazaZZ8lWjBOV2NlHHzdyR1oAs/C64W9sNavri6tZNVvNSknvILdifsxwFSM5weFTr7mmfFQySWOiW0cqIr6gZLhZZnije3jgleQOU5K4Ucd+Ku+Expmg61qmgSXrSa5czvqM7TQiI3Cv/EmCQVGNuAcjByO5w/iTpY1/Tde1C7Eiafo2lzrbYYqJrkjcT7quxB6ElweAQQDK8PnRrvxDNrN42kLeHRyIdI+zG3NwsmXBdnZvMOEZTwcdcdM5Gm+Jo/C/hu+1nRo/D0lxdzpevp9uJJliSRlAiDIqpEVUjOc5YH6Cv4bu4ovHOtR2V7pzG4s4oI/IuYdsrskgAxBBsJyRnLLjjJOcLBNdX2s/DuOGGLUWQNFpqveawI4fOjZAVWNVEbj5TgluccZPFAH0SM45615VptlqcWsW1prGu3Mur3t1Lc3mlW99cAW8DsdhRoyAiqAPvYBzgHPX1WvMvGviC8vNP8AEENrot8J9KlW1W5h1V7VS0qoUYiNgzAeYrbSCPfk0AZHhjQIpNI8O6fdWbxRXMV0WF3YPdI8heQqGLNiPAG7kfNnFeh+DvCNr4L0X+y7O9vbmHeZB9qkDbCeoUAAKvfHvXEaDY6np8momz0HSjq2hqLeXUb/AFGaeSZjCshYHyxjKuMjjk13vhDXJfEvhLTdZntRayXkPmGEPuC8kcH0OM/jQBt0UUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAyWKOeF4Zo1kikUq6MMhgeCCO4rlrX4ZeCbNy0XhnTmJOT50Xm/wDoea6yigDLh8M6BbDEGh6bEP8ApnaRr/IVZj0rTopVljsLVJFOVdYVBH0OKt0UAUbnSLG71Wx1OeAPeWIkFvJk5QSABvzAFQap4c0nWr/Tb3UbNLifTZGltS+cIxABOOh6A89wDWrRQBBdWdrfReVd20NxGDu2SoHGfXBpk+nWVzpsunTWsTWUsZieDaAhUjBGKtUUAUdKtLmwtBaXFz9pSL5YZW/1jJ2D+rDpnv1wKvUUUAFFFFAGPeeFPD+o6wmr3uj2VxfogRZ5YgxAHTrxkdj1FaxRTGYyo2EbduOMelOooA5fwt4ItfCur63qEF7dXTapJG2Lly5iRAQqBiSWA3HBPbA7ZPSzeb5L+Rs83B2b87c++KfRQBzQ8IR6hfRX3iK8bVpoW3wwMnl2sLeqxZOT7uWI7YrpaKKACszQtA07w5YNZaZCYoXmed9zFizuckknr/gBWnRQBljw5ow0ePSRp1v/AGfFIJEt9vyqwfeCB2+bmpbnRtPu9XstVntla+sQ4t5skFA4ww9wR61fooApavpVprmkXWl38ZktbqMxyKDgkH0PY0ajpseo6c9g000EEg2v9nbYxTuueoBHGRg+hFXaKAMm88NaRe+GpPD0llEulvD5PkINoVe230IPIPrzUb6JNH4ctdDtL6aOGOBLaS6dt05jVdpIPQOQPvduoFbVFAEFlZW2m2MFlZwrDbQII4o0HCqBgCp6KKACiiigCtdafaXs1rNc26SyWkvnQMw5jfaVyPwYirNFFAHIw/DrRbfx4vi2Pz1ukjYJb7/3KOwIZwvYkE8DjknrXXUUUAFFFFABWfY6Rb2V3d3pzNeXZHnTydSo+6g9EGTge5JySSdCigCtp+n2uladb6fZRCK1t4xHFGCTtUcAc1ieHfBdh4b1jVdStri6nm1Bl4uJS4hjXJEaZ5CgsePoO1dJRQBE1tA9xHcPDG08YISQqCyg9QD1GaloooArXmn2WoxCK+s7e6jByEniVwD64IpbSxtLCEw2drDbRk52QxhBn6CrFFAFax0+0022FvZW8cEW4sVQYyxOSx9STySeTVmiigCnpmlWGjWf2TTbWO1t97SCKMYUMxLHA7ck03U9HsdYFoL6AS/ZLqO7gycbJUOVb9TV6igCKG1t7d5XggjjaZ/MkKKBvbAGT6nAHPtVe80jT9QvLK7u7SKa4sXMltI65MTEYJH4fyHoKu0UAV720W+s5LWSSWNJBtYxOUbHcBhyMjjIwfQiltLO2sLOKztII4LaFQkcUa4VQOwFT0UAchpvw/s9M8cy+Jk1C+mJt2ghtLiVpEt9xyxQsSQDj7vQZPsB19FFAEENla29xcXENvFHNcsGmkVQGkIAUFj3wABTri3hu7aW2uYkmglUpJG65VlPBBHcVLRQBieF/CekeD9Mk0/Rrcw28kzTMGYsSx9z2AAA9hVnX9EtPEehXmj34f7LdJsfY2GHOQQfXIFaVFAGDdeErC8u5J5rzWNr/wDLCLVbiKMfRUcYHt0rPi+GHhCGyWzTS5Psy52xG9nKjJyeC/qSa66igCh/ZFoNFOkKsi2Zi8naJWLbOhXcTu6cdc+lZ+reDdF1m70m5urXbJpcqS2/lHYPk5VWA6qDggdse5zv0UAcvq/gTTdV1SXU4r3VdMvJgonl029eDzsDA3gcEgcZxmpfDPgjR/Clxd3VgLqW8vMfaLq6uGlklx0ySff0ro6KAM7V9EstbNgbxXP2G8jvYdrYxImcE+o5NOu9F0+9g1GGa2UrqMJguivBkTaVwSPZiKv0UAc//wAIhp3/AAmEHiQPcC5gt2gjg80mFd2AXC9mKgA44P15rfKKxUsoJU5UkdDS0UAUb/SLTU57SS8VpUtZPOjiJ+QyD7rMO5XnGeATnGQCK2p+F9F1jVtP1TUNPinvdPbfbStnKH+uDyM5weRWvRQAVmax4c0XxBGser6XaXwT7hniDFfoeo/CtOigDkYvhd4HhkDr4Z08kf303D8iSK6ezsrXT7ZbaytobaBPuxQxhFX6AcVPRQAyWJJ4XikGUcFWGSMg/SobHT7PTLVbWwtILW3XkRwxhFB9cCrNFAGNrnhLQPErQtrOlW168ORG8q/MoPbI5x7VqWttDZWsVtbxiOGJQiIOigdBUtFABRRRQAVk3Ph+1ufEEWtiWaK+is5LNHQjAR2Vs4IIyCvH1PBrWooA5tPAuhPLcz6hbvqtzcxmKSfUH85th6qoPCD2UCsfw/8ADe58MXxOl+LtYj0wNlNPk2Soi/3QXBwPoAfeu8ooAMA4yOnSsjXdCXxBCtnd3Mq6a3/HxbRfKbgf3Wfrs9QMZ7nGQdeigDnPE3g2x8Q6JBYRO2mzWZD2F1aDa9qw4GzGOMcEdx+BrburNLyza1mkl2OAHMbmNmHflcEZ9sVYooAyL/w1pWoaANEe28jT1aNlitmMOzY4ddpXBXlRyMGqCfD7wyt3b3bWEs1xbSrNDJPeTSlHXkMN7nkV01FABWdrGiWOuRWsd/EXW1uoruLBxtkjOVP9Poa0aKAGpGkcaxoiqijaqqMAD0xXOeGvAmh+FNR1C+0yGQXF82WaV93lpnIjTj5UHp9OeBXS0UAFUYdJtYdXuNVIaS8mjWLzHOdkY5CL6DOSe5J5PAxeooA5Sy8Fm28fT+J5tXu7pTbGC2tJzuFvuYM+1upHAwO2TyeMdXRRQBmaFoGneHLBrLTITFC8zzvuYsWdzkkk9f8AACkHhzRho8ekjTrf+z4pBIlvt+VWD7wQO3zc1qUUAULnRtPu9XstVntla+sQ4t5skFA4ww9wR607V9KtNc0i60u/jMlrdRmORQcEg+h7GrtFAFLUdNj1HTnsGmmggkG1/s7bGKd1z1AI4yMH0IqteeGtIvfDUnh6SyiXS3h8nyEG0Kvbb6EHkH15rWooAqaXYJpWk2enxyyypawJCskzbncKoALHuTjmqcvhrTZzqfnRu41KeK4uFLnBaNUVcY6D92v61r0UAczr3hD+1NJ1e20/VbrTLrU5xPJcxHdhhGkRG3jKlEHGepz6VsaNpcGh6JY6VbFjBZwJAhbqQoAyfc4zV6igAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAoormvGMNxPbWcQ0NdVsWmAugL027wr08wdAwAzkZH49gDC0fxLq8PiLxjZXN7aXjWt5Gml2dxMluzlk3mMPjnhgBkHkdfTsdD1G41XSIby702402d9we1uCC6EEjqOCDjIPoRXkuk2OmWnibxJpnhrQdMk1eS9DabeXaKYYU8iJmZXOWYgtu2rnO4HpzXreh22pWejWtvq9+l/fomJrlIREJD67R+Xv1wOlAGhRRXHrqviWH4qf2TMlnJoFxZNPCY/9bEU2Al/TLMQOxH0NAHYVjar4ls9I1O106W3vZru7jeSCO2t2k3hMbuRwMbl5OByOa2a898bR3F7460G1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6PF5I1GC1ZsS5KCZyXIbHJAZscdhXQXGnW91e291cBpGtzuhRj8iN/fx3bHAJ6c4xk5t0AeV6R4J8S/aNV1rxI6XM+ozrK2iadN5Vu7KoUGV2O5lwBleR7NnFbLfD+bWXuNT1/UCustF5Vi+ns0aaYo6eSeCWz95jjcOMAcV3dFAHK+A5fFA0m5svFkaG+s7gwx3aY23UWAVk4+pHQdPXNUfEuh36tr+swhY4I9KuY4LK1X5ruVkJLy4HJ4CqOT1OecV3FFAHDWng65mu9GllvLgadClvdT2cr5UXESYTYp+6MkM3bMa8ckixp0ZPxc16XHyrpVmpP1eb/CuxqFLWCO7lukiVZ5VVJJAOWVc7Qfpub86AJqKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooqlq1xc2mmzXFr5HmRjd++DFcd+FBYn0AHNAF2ivDvD/i3XIfFWqQ3uuW+nW99fB4TdQZQDA4QTToyAnsEJz6V7jQAUVz/AIn12XR302G2Ns9xd3Gz7NKH3zRj/WeXtB+ZQd2MHIBrhvBvie//ALO8Oo9/evGtjdSG3ntpGk1CRSTt82QALtAXBzzkg4AoA9ZorzfwZrfiGO+i8Pz2cd1c+UNRvry41HeqrNI3yRBFYcYIVSw4FekUAFFYPivWrrSNOhTTI7ebVr2ZbeyiuGKxs5yxLEc7Qqse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k4xgeg+CofGNvZ3KeLbiyuHMm62eEjzQhz8sm1VTI45X3ryC2upNI03V9R1PX9Q1XZqLiaaxlmtSSUjUuJEUopJAXaxToMntXrngrxTpWtWr6ZaS6it9YKBPbaopFygPQsT976gntQBY8fyND8P9fmjuXtpYrGWSKWOQoyuqllwRznIFUH8Z6TbeE7eZr281DNmRLd6ZA9yFZU+djIgKKw68kVzPxpttPvNDvLa20yym1dbRrme9kt1Z7W3TkfMRkF2Gxfqx7Vq6rZ+JX8KR6TcaZpcdklw8d/IlyLaKSzQZDDhtgccMOSAGx1BABX8HeL/Fl1oFitxoE+qzuvmi9Nzb2/nW7Mdknl7yclcdgM8V6XXkmi6us/jPSfEuoaQ6SaoP7L0W1tG3CK1TLNcEEKdhJH8IwuODmvW6ACkBDAEEEHoRWR4m06fVNFa2t0jlIljke3lbalwiuC0bHB4YAjpg9DwTUHhbSptMjv2ayh0+C5uPNgsIGBWBdiqegCgsQWIXjnuSaAN+iiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigBrokiMjqrIwwVYZBFct410S9v9K0waNCRcWN/FOiQyrAQmGR9rEEL8rntXV0UAeIS/D/AMTRxz2c1hLNBq+spNcSjW5ZfIiLozGSLYsb8Rkbjk8gdhXtojQSGQIvmEBS2OSPTP406igDk/HXhufV/BGuadosMS6hqIXczHHmHcudzH/ZBA9OBV7X9B/tkD7SPttujBo9PeTyoHYcgykAlwDzjp0+U9a3qKAODv8AwZrqTHxBp2sxt4oUbFM0eLQwZBNuE5KLxncDuz35wO8oooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAoori/F2pvd+J9C8HwOyLqRknvmU4Itoxkp7b2wpx2z60AdhBPDcxCWCVJYzkB0YEHBweR7ipKyPEWpyeHPC19qVlYJdGwtzKLUSeUCijLAEKcYUEgY7YrlZPGvic/8I9t8P6ZCNcYLBnUXlaPMZkywESjAAPQmgD0Go5p4raB5p5EiiQbnd2wqj1JPQV59p2u+NNd8I3GuRXeiaesf2jags5ZiwiZlJDGRQASh/hrofAet3/iXwRpmr6pBDDdXUZZkiztI3EA4PTIAOOetAHRgggEEEHoRVTU9W0/RrT7XqV5DaW24IZpm2oCemSeB+Ncx4f1I6X451Twc/FulumoacP7kLHa8f0V/ujsDjoBR4m8SOul6rDc+Fp5dPgjcXM2pSRQ2roB65ZmB7YQ/nQB16TwyQLOk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igAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKK4Tx/fyXdk+npeTabpVu6T6rqybl8mNWBEcRHJkY4zjO0deSBQB3Es0UEe+aRI0yF3OwAyTgDn1JA/Gn15f4y8Q2GpajBpuoaXq1zotrJDKi29qzjVJyN0caNwGUZDEZyT6BTnsfCF/q2oaRLNrTWQvvtMga3tZA/2Zc8RORwXUcHH/wBegDfoqve3L2lq80dtNcuv3YYQNzn0G4gD6kgV57oWs+J9b8Xavf38s+n2Wiy/ZjotrCs5uCyBgTJn73K9AAOOcZNAHpVFeLx+IvElzeXd7outWz67qt4tuuhS2sj/AGARYDByXAUKpy77DkkBSeDXr73BstONxeks0UW6YwRM+SBztQZY+w5NAFmkJAIBIBPT3rzuTxTrN74tsr/QNM1y+0ZoHiu7aSzFujMOUkjaYpzkkHtgDvWH8VdT1V9R8O26RRxGLWbWeDy7SaeZDhuuAEbHdFbJx1oA9horG8MzX02kI+ozXElyzMc3Fqtu+P8AcBOB+NX9R1Kz0mye8vphDbpjc5BOM/TmgC1RXkeofEqOz+I2nHS7+/1PStRidJ9NSwlLrIqna8O5VyDgAgHA5Pfj0LQteuNaaXzdA1XTEQAq9+ka7/YBXY5+ooA2qKz9Y1vT9Bsxd6lO0MBYJuETvyegwoJrk9N8aapP4h1BU0XVtQ0WQRvYzx6e0DKSCHVvN2BgCAQR645oA7yiuH8TxA/E/wACzBmU5vlbDEBh5OQD64PNdpDPDcKWhlSRQdpKMCAfTigCSiuW1bxVe2/i638O6RpceoXRtGu7kyXPkrAm4KmTtbJJ3cdeKylGuaR4lvtSvNa0bT7e/SNRYXV+80cco43puWPGRgbR1PNAHfUVyOg6p4vl8V6hp+r6ZbPpEKjyNShjMAZ8DK+WzszDkjcMDj3rQ8VaxPpW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gAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiikDKWKgjI6jPSgBaKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigCOeNpreWNJXhZ0KiRMbkJHUZyMj3rzzwVpMGi/E7xdaQS3Ew+y2TvLcymSSRyJCWZj3P5egFeiTGUQSGAI020+WHJClscZIyQM1wejaJ41s/G9/rl5BoHk6itvFcJDdzFo0j3DK5iAJIY8EjpQB39FFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQB//2Q=="
        with st.expander("📄 住院看護費用補助辦法（點擊查看）", expanded=False):
            st.markdown(
                "<p style='font-size:12px;color:#1E8449;font-weight:700;"
                "margin-bottom:8px'>國軍花蓮總醫院 住院看護費用補助辦法"
                "（114年03月31日訂定 ／ 114年09月16日第一次修訂）</p>",
                unsafe_allow_html=True,
            )
            import base64 as _b64
            _img_html = (
                f"<img src='data:image/jpeg;base64,{_NURSING_PDF_B64}' "
                f"style='width:100%;border-radius:6px;"
                f"box-shadow:0 2px 10px rgba(0,0,0,0.12);' />"
            )
            st.markdown(_img_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)



    # ── 第一層：有無陪伴 × 傷害嚴重度堆疊橫條圖 ─────────────
    if _COMP_EVENT in _cf.columns and _INJ_DETAIL in _cf.columns:
        _INJ_ORDER  = ["無傷害","輕度","中度","重度","極重度","死亡"]
        _INJ_COLORS = ["#1E8449","#AED6F1","#F39C12","#E67E22","#C0392B","#7B241C"]

        _ct = (_cf.groupby([_COMP_EVENT, _INJ_DETAIL])
                  .size().reset_index(name="件數"))
        _ct = _ct[_ct[_INJ_DETAIL].isin(_INJ_ORDER)]

        st.markdown('<p class="section-title">🥧 事發時陪伴狀態 × 傷害嚴重度佔比</p>',
                    unsafe_allow_html=True)
        st.caption("左：無陪伴的傷害嚴重度分布　右：有陪伴的傷害嚴重度分布；比較兩者差異可評估陪伴介入效益")

        _cp1, _cp2 = st.columns(2)
        for _col, _label, _comp_val in [(_cp1, "🚷 無陪伴", "無"), (_cp2, "👥 有陪伴", "有")]:
            _pie_df = _ct[_ct[_COMP_EVENT] == _comp_val].copy()
            # 補齊所有傷害等級（避免某等級為0時消失）
            _pie_df = (_pie_df.set_index(_INJ_DETAIL)["件數"]
                       .reindex(_INJ_ORDER, fill_value=0)
                       .reset_index())
            _pie_df.columns = ["傷害等級","件數"]
            _pie_df = _pie_df[_pie_df["件數"] > 0]
            _total = _pie_df["件數"].sum()

            fig_pie = go.Figure(go.Pie(
                labels=_pie_df["傷害等級"],
                values=_pie_df["件數"],
                hole=0.45,
                marker=dict(
                    colors=[_INJ_COLORS[_INJ_ORDER.index(l)]
                            for l in _pie_df["傷害等級"]],
                    line=dict(color="#FFFFFF", width=2),
                ),
                textinfo="label+percent",
                textfont=dict(size=11, color="#1C2833", family="Arial"),
                hovertemplate="<b>%{label}</b><br>%{value} 件（%{percent}）<extra></extra>",
                sort=False,
            ))
            fig_pie.update_layout(
                height=280, paper_bgcolor=PAPER_BG, showlegend=False,
                margin=dict(t=30, b=10, l=10, r=10),
                annotations=[dict(
                    text=f"<b>{_total}</b><br>件",
                    x=0.5, y=0.5,
                    font=dict(size=16, color="#1C2833", family="Arial"),
                    showarrow=False,
                )],
                title=dict(
                    text=_label,
                    font=dict(size=13, color="#2C3E50", family="Arial"),
                    x=0.5, xanchor="center",
                ),
            )
            _col.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 第二層：陪伴者類型 + 不在場落差 ─────────────────────
    _da1, _da2 = st.columns([1, 1.2])

    with _da1:
        # 陪伴者類型分布（事發時有陪伴的件數）
        _type_map = {
            "家屬":     "有無陪伴者-有-家屬",
            "看護":     "有無陪伴者-有-看護",
            "工作人員": "有無陪伴者-有-工作人員",
            "其他":     "有無陪伴者-有-其他",
        }
        _type_df = pd.DataFrame([
            {"類型": lbl, "件數": int(_cf[col].fillna(0).sum())}
            for lbl, col in _type_map.items()
            if col in _cf.columns
        ]).query("件數 > 0").sort_values("件數", ascending=True)

        st.markdown('<p class="section-title">👤 事發時陪伴者類型分布</p>',
                    unsafe_allow_html=True)
        st.caption("了解哪類陪伴者最常在場，強化相應的教育訓練")

        if not _type_df.empty:
            _type_colors = ["#F39C12" if v==_type_df["件數"].max()
                            else "#FAD7A0" for v in _type_df["件數"]]
            fig_type = go.Figure(go.Bar(
                x=_type_df["件數"], y=_type_df["類型"],
                orientation="h",
                marker=dict(color=_type_colors, line=dict(width=0)),
                text=[f"{v} 件" for v in _type_df["件數"]],
                textposition="outside",
                textfont=dict(size=11, color="#1C2833", family="Arial"),
                hovertemplate="<b>%{y}</b>：%{x} 件<extra></extra>",
            ))
            fig_type.update_layout(
                height=220, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                xaxis=dict(title=dict(text="件數", font=AXIS_TITLE_FONT),
                           tickfont=AXIS_TICK_FONT,
                           gridcolor=GRID_COLOR, griddash="dot",
                           range=[0, _type_df["件數"].max()*1.35]),
                yaxis=dict(tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                           automargin=True),
                margin=dict(t=10, b=40, l=80, r=70),
            )
            st.plotly_chart(fig_type, use_container_width=True)

    with _da2:
        # 不在場落差：平日有陪伴但事發時無陪伴 → 顯示其傷害分布
        st.markdown('<p class="section-title">⚠️ 陪伴者不在場事件之傷害分布</p>',
                    unsafe_allow_html=True)
        st.caption(f"平日有陪伴、事發時卻無人在場的 {_gap_n} 件——這些最可預防")

        if _gap_n > 0 and _INJ_SUM in _cf.columns:
            _gap_df = _cf[(_cf[_COMP_DAILY]=="有") & (_cf[_COMP_EVENT]=="無")]
            _gap_inj = _gap_df[_INJ_SUM].value_counts().reset_index()
            _gap_inj.columns = ["傷害","件數"]
            _gap_inj_colors = {
                "有傷害":"#C0392B","無傷害":"#1E8449",
                "無法判定傷害嚴重程度":"#AEB6BF","跡近錯失":"#F39C12",
            }
            fig_gap = go.Figure(go.Pie(
                labels=_gap_inj["傷害"],
                values=_gap_inj["件數"],
                hole=0.50,
                marker=dict(
                    colors=[_gap_inj_colors.get(v,"#AEB6BF")
                            for v in _gap_inj["傷害"]],
                    line=dict(color="#FFFFFF", width=2),
                ),
                textinfo="label+percent",
                textfont=dict(size=10, color="#1C2833"),
                hovertemplate="<b>%{label}</b>：%{value} 件（%{percent}）<extra></extra>",
            ))
            fig_gap.update_layout(
                height=220, paper_bgcolor=PAPER_BG, showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10),
                annotations=[dict(
                    text=f"<b>{_gap_n}</b><br>件",
                    x=0.5, y=0.5,
                    font=dict(size=16, color="#1C2833"),
                    showarrow=False,
                )],
            )
            st.plotly_chart(fig_gap, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 第三層：活動情境 × 陪伴狀態熱力圖 ───────────────────
    if _COMP_EVENT in _cf.columns and _ACT_COL in _cf.columns:
        st.markdown('<p class="section-title">🗺 活動情境 × 陪伴狀態（件數熱力圖）</p>',
                    unsafe_allow_html=True)
        st.caption("顏色越深 = 該情境無陪伴跌倒越集中 → 優先建立「該情境主動陪伴」介入規範")

        _act_ct = (_cf.groupby([_ACT_COL, _COMP_EVENT])
                      .size().reset_index(name="件數"))
        _act_piv = (_act_ct.pivot(index=_ACT_COL, columns=_COMP_EVENT, values="件數")
                            .fillna(0).astype(int))
        # 依「無陪伴」件數降冪排列
        if "無" in _act_piv.columns:
            _act_piv = _act_piv.sort_values("無", ascending=False)

        _act_text = [[str(v) if v > 0 else "" for v in row]
                     for row in _act_piv.values]

        fig_act = go.Figure(go.Heatmap(
            z=_act_piv.values,
            x=_act_piv.columns.tolist(),
            y=_act_piv.index.tolist(),
            text=_act_text,
            texttemplate="%{text}",
            textfont=dict(size=11, color="white", family="Arial Bold"),
            colorscale=[
                [0.0, "#FEF9E7"],
                [0.2, "#FAD7A0"],
                [0.5, "#E67E22"],
                [1.0, "#7E5109"],
            ],
            hovertemplate="<b>%{y}</b> × <b>%{x}</b>：%{z} 件<extra></extra>",
            colorbar=dict(
                title=dict(text="件數", font=dict(size=11)),
                tickfont=dict(size=10),
                thickness=14, len=0.7,
            ),
            xgap=3, ygap=2,
        ))
        fig_act.update_layout(
            height=max(340, len(_act_piv)*30 + 80),
            paper_bgcolor=PAPER_BG, plot_bgcolor=PAPER_BG,
            xaxis=dict(title=dict(text="事發時陪伴狀態", font=AXIS_TITLE_FONT),
                       tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                       side="bottom"),
            yaxis=dict(title=dict(text="活動情境", font=AXIS_TITLE_FONT),
                       tickfont=dict(size=10, color="#2C3E50", family="Arial"),
                       automargin=True),
            margin=dict(t=20, b=60, l=140, r=80),
        )
        st.plotly_chart(fig_act, use_container_width=True)


    # ════════════════════════════════════════════════════════════
    #  🔬 診斷特徵分析
    #  資料：df_all["診斷分類"]  + 傷害程度
    #  篩選器：時間區間 + 側邊欄科別篩選器
    # ════════════════════════════════════════════════════════════

    # 診斷分類顯示順序與配色
    DX_ORDER = ["思覺失調/精神病","雙相/躁症","憂鬱症","失智症","帕金森氏症",
                "腦血管病","骨折相關","糖尿病","腎病","肝病",
                "心臟病","呼吸系統","腫瘤/癌症","其他"]
    DX_COLORS = {
        "思覺失調/精神病": "#7B241C",
        "雙相/躁症":      "#C0392B",
        "憂鬱症":         "#E74C3C",
        "失智症":         "#E59866",
        "帕金森氏症":      "#F39C12",
        "腦血管病":        "#2471A3",
        "骨折相關":        "#1ABC9C",
        "糖尿病":          "#27AE60",
        "腎病":            "#117A65",
        "肝病":            "#7D6608",
        "心臟病":          "#6C3483",
        "呼吸系統":        "#2C3E50",
        "腫瘤/癌症":       "#5D6D7E",
        "其他":            "#AEB6BF",
    }
    # 傷害程度顏色（與科別分析共用）
    DX_INJ_ORDER  = ["無傷害","輕度","中度","重度","極重度","無法判定傷害嚴重程度"]
    DX_INJ_COLORS = {
        "無傷害":              "#1E8449",
        "輕度":               "#F39C12",
        "中度":               "#E67E22",
        "重度":               "#C0392B",
        "極重度":              "#7B241C",
        "無法判定傷害嚴重程度":  "#7F8C8D",
    }
    INURY_COL_DX = "病人/住民-事件發生後對病人健康的影響程度"
    # 中度以上傷害：中度、重度、極重度、死亡
    HIGH_INJURY   = ["中度","重度","極重度","死亡"]

    dept_label = sel_dept if sel_dept != "全部科別" else "全院"
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
                padding:14px 20px;border-radius:8px;margin-bottom:16px'>
      <h3 style='color:#FFFFFF;margin:0;font-size:17px;font-weight:700'>
        🔬 診斷特徵分析
      </h3>
      <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
        資料期間：{start_m} ～ {end_m}　科別：{dept_label}　共 {len(dff_dx)} 筆
      </p>
    </div>""", unsafe_allow_html=True)

    if dff_dx.empty or "診斷分類" not in dff_dx.columns:
        st.info("目前篩選條件下無診斷資料。")
    else:
        dx_inj = dff_dx[["診斷分類", INURY_COL_DX]].copy()

        # ── 圖1：Treemap（方塊大小=件數，顏色=中度以上傷害率）──
        st.markdown('<p class="section-title">① 診斷分類 Treemap（方塊大小=件數，顏色深=傷害率高）</p>',
                    unsafe_allow_html=True)

        dx_summary = []
        for dx in DX_ORDER:
            sub  = dx_inj[dx_inj["診斷分類"] == dx]
            n    = len(sub)
            if n == 0:
                continue
            hi   = sub[INURY_COL_DX].isin(HIGH_INJURY).sum()
            rate = round(hi / n * 100, 1)
            dx_summary.append({"診斷分類": dx, "件數": n,
                                "中度以上傷害件數": hi, "傷害率": rate})
        df_dx_sum = pd.DataFrame(dx_summary)

        if not df_dx_sum.empty:
            fig_dx1 = go.Figure(go.Treemap(
                labels=df_dx_sum["診斷分類"],
                parents=["診斷分類"] * len(df_dx_sum),
                values=df_dx_sum["件數"],
                customdata=df_dx_sum[["件數","中度以上傷害件數","傷害率"]].values,
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "件數：%{customdata[0]}<br>"
                    "中度以上傷害：%{customdata[1]} 件<br>"
                    "傷害率：%{customdata[2]:.2f}%<extra></extra>"
                ),
                marker=dict(
                    colors=df_dx_sum["傷害率"],
                    colorscale=[
                        [0.0, "#D5E8D4"],   # 低傷害率→淺綠
                        [0.3, "#FFE6CC"],   # 中低→淺橙
                        [0.6, "#F39C12"],   # 中→橙
                        [1.0, "#7B241C"],   # 高→深紅
                    ],
                    showscale=True,
                    colorbar=dict(
                        title=dict(text="中度以上<br>傷害率(%)",
                                   font=dict(size=11, color="#1C2833")),
                        tickfont=dict(size=10, color="#2C3E50"),
                        thickness=14, len=0.7,
                    ),
                    line=dict(width=2, color="white"),
                ),
                textfont=dict(size=13, color="white", family="Arial Bold"),
                textinfo="label+value",
            ))
            fig_dx1.update_layout(
                height=420, paper_bgcolor=PAPER_BG,
                margin=dict(t=10, b=10, l=10, r=120),
            )
            st.plotly_chart(fig_dx1, use_container_width=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── 圖2：100% 堆疊橫條圖（傷害程度分布，件數>=3）────────
        st.markdown('<p class="section-title">② 各診斷分類傷害程度分布（100% 堆疊，件數 ≥ 3）</p>',
                    unsafe_allow_html=True)

        dx_valid = dx_inj.groupby("診斷分類").filter(
            lambda x: len(x) >= 3)
        if not dx_valid.empty:
            inj2 = (dx_valid.groupby(["診斷分類", INURY_COL_DX])
                    .size().reset_index(name="件數"))
            inj2_piv = (inj2.pivot(index="診斷分類",
                                    columns=INURY_COL_DX, values="件數")
                        .fillna(0))
            # 排序：依總件數升序
            inj2_piv["_tot"] = inj2_piv.sum(axis=1)
            inj2_piv = inj2_piv.sort_values("_tot", ascending=True)
            tot2     = inj2_piv["_tot"].astype(int)
            inj2_piv = inj2_piv.drop(columns="_tot")
            # 轉百分比
            inj2_pct = inj2_piv.div(inj2_piv.sum(axis=1), axis=0) * 100

            fig_dx2 = go.Figure()
            for inj_lv in DX_INJ_ORDER:
                if inj_lv in inj2_pct.columns:
                    fig_dx2.add_trace(go.Bar(
                        name=inj_lv,
                        y=inj2_pct.index,
                        x=inj2_pct[inj_lv].round(1),
                        orientation="h",
                        marker_color=DX_INJ_COLORS[inj_lv],
                        marker_opacity=0.85,
                        hovertemplate=(
                            f"<b>%{{y}}</b><br>{inj_lv}：%{{x:.1f}}%<extra></extra>"
                        ),
                    ))
            # 右側 n= 標籤
            fig_dx2.add_trace(go.Scatter(
                y=inj2_pct.index,
                x=[102] * len(inj2_pct),
                mode="text",
                text=["n=" + str(t) for t in tot2],
                textfont=dict(size=10, color="#2C3E50", family="Arial"),
                showlegend=False, hoverinfo="skip",
            ))
            fig_dx2.update_layout(
                barmode="stack",
                height=max(320, len(inj2_pct) * 38 + 80),
                plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center",
                            font=dict(size=11, color="#2C3E50")),
                xaxis=dict(
                    title=dict(text="百分比 (%)", font=AXIS_TITLE_FONT),
                    tickfont=AXIS_TICK_FONT, range=[0, 115],
                    gridcolor=GRID_COLOR, griddash="dot", ticksuffix="%",
                ),
                yaxis=dict(
                    title=dict(text="診斷分類", font=AXIS_TITLE_FONT),
                    tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                    automargin=True,
                ),
                margin=dict(t=40, b=60, l=100, r=60),
                hovermode="y unified",
            )
            st.plotly_chart(fig_dx2, use_container_width=True)




    # ════════════════════════════════════════════════════════════
    #  圖F：各單位熱力圖
    # ════════════════════════════════════════════════════════════
    top_u = dff["單位"].value_counts().head(15).index.tolist()
    um = (dff[dff["單位"].isin(top_u)]
          .groupby(["年月顯示","單位"]).size().reset_index(name="件數"))
    if not um.empty:
        hp_piv = um.pivot(index="單位", columns="年月顯示", values="件數").fillna(0)
        fig_f = go.Figure(go.Heatmap(
            z=hp_piv.values, x=hp_piv.columns.tolist(), y=hp_piv.index.tolist(),
            colorscale=[
                [0.0,"#F4F6F6"],[0.35,"#E6B0AA"],
                [0.70,"#C0392B"],[1.0,"#78281F"],
            ],
            hovertemplate="<b>%{y}</b><br>%{x}<br>件數：%{z:.0f}<extra></extra>",
            colorbar=dict(
                title=dict(text="件數", font=dict(size=12, color="#1C2833")),
                tickfont=dict(size=10, color="#2C3E50"),
                thickness=15, len=0.8),
            xgap=1, ygap=1))
        fig_f.update_layout(
            title=dict(text="🗺️ 各單位每月事件熱力圖（Top 15）", font=TITLE_FONT),
            height=460, paper_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="年月", font=AXIS_TITLE_FONT),
                tickangle=-45, tickfont=dict(size=9, color="#2C3E50"),
                showgrid=False,
            ),
            yaxis=dict(
                title=dict(text="病房 / 單位", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50"),
            ),
            margin=dict(t=60, b=80, l=90, r=90))
        st.plotly_chart(fig_f, use_container_width=True)


    # ── 明細表 ───────────────────────────────────────────────────
    with st.expander("📋 查看事件明細資料表", expanded=False):
        cols = [c for c in [
            "編號","事件大類","事件類別","發生日期","年月","單位","SAC_num",
            "發生時段","時段標準","發生者資料-年齡","發生者資料-性別",
            "病人/住民-事件發生後對病人健康的影響程度(彙總)",
        ] if c in dff.columns]
        df_show = dff[cols].copy().rename(columns={
            "SAC_num":"SAC","事件大類":"類別",
            "發生者資料-年齡":"年齡","發生者資料-性別":"性別",
            "病人/住民-事件發生後對病人健康的影響程度(彙總)":"影響程度"})

        def _hl(val):
            if val in [1, 1.0]:
                return "background-color:#FADBD8;color:#7B241C;font-weight:bold"
            elif val in [2, 2.0]:
                return "background-color:#FDEBD0;color:#784212;font-weight:bold"
            elif val in [3, 3.0]:
                return "background-color:#FEF9E7;color:#6D4C00"
            return "color:#1C2833"

        st.dataframe(df_show.style.map(_hl, subset=["SAC"]),
                     use_container_width=True, height=400)
        st.caption("🔴 SAC 1 死亡　🟠 SAC 2 重大傷害　🟡 SAC 3 輕中度　⬜ SAC 4 無傷害")




    # ════════════════════════════════════════════════════════════
    #  📋 科別深度分析（跌倒事件）
    #  資料來源：109-113跌倒工作表 merge 全部工作表
    #  時間區間與主篩選器連動
    # ════════════════════════════════════════════════════════════
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
                padding:14px 20px;border-radius:8px;margin-bottom:16px'>
      <h3 style='color:#FFFFFF;margin:0;font-size:17px;font-weight:700'>
        📋 跌倒事件 — 科別深度分析
      </h3>
      <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
        資料期間：{start_m} ～ {end_m}　共 {n_fall} 件跌倒事件
      </p>
    </div>
    """.format(start_m=start_m, end_m=end_m, n_fall=len(dff_fall)),
    unsafe_allow_html=True)

    DEPT_COL    = "病人/住民-所在科別"
    INJURY_COL  = "病人/住民-事件發生後對病人健康的影響程度"
    HIGHRISK_COL= "跌倒事件發生對象-事件發生前是否為跌倒高危險群"
    MOBILITY_COL= "跌倒事件發生對象-事件發生前的獨立活動能力"
    CONSCI_COL  = "跌倒事件發生對象-當事人當時意識狀況"
    GETUP_COL   = "可能原因-高危險群病人執意自行下床或活動"

    # 傷害程度顏色對應（由輕到重）
    INJURY_ORDER  = ["無傷害", "輕度", "中度", "重度", "極重度", "無法判定傷害嚴重程度"]
    INJURY_COLORS_MAP = {
        "無傷害":              "#1E8449",
        "輕度":               "#F39C12",
        "中度":               "#E67E22",
        "重度":               "#C0392B",
        "極重度":              "#7B241C",
        "無法判定傷害嚴重程度":  "#7F8C8D",
    }

    if not dff_fall.empty and DEPT_COL in dff_fall.columns:

        # 只取件數 >= 5 的科別
        dept_counts = dff_fall[DEPT_COL].value_counts()
        valid_depts = dept_counts[dept_counts >= 5].index.tolist()
        df_dept = dff_fall[dff_fall[DEPT_COL].isin(valid_depts)].copy()

        if df_dept.empty:
            st.info("目前期間內無足夠資料進行科別分析（各科需至少 5 件）。")
        else:
            # ── 圖1：堆疊百分比橫條圖（傷害程度）─────────────────
            st.markdown('<p class="section-title">① 各科別傷害程度分布（堆疊百分比）</p>',
                        unsafe_allow_html=True)

            inj_cross = (df_dept.groupby([DEPT_COL, INJURY_COL])
                         .size().reset_index(name="件數"))
            inj_piv   = (inj_cross.pivot(index=DEPT_COL, columns=INJURY_COL, values="件數")
                         .fillna(0))
            # 計算各科總件數並排序
            inj_piv["_total"] = inj_piv.sum(axis=1)
            inj_piv = inj_piv.sort_values("_total", ascending=True)
            totals   = inj_piv["_total"].astype(int)
            inj_piv  = inj_piv.drop(columns="_total")
            # 轉換為百分比
            inj_pct  = inj_piv.div(inj_piv.sum(axis=1), axis=0) * 100

            fig_dept1 = go.Figure()
            for injury in INJURY_ORDER:
                if injury in inj_pct.columns:
                    fig_dept1.add_trace(go.Bar(
                        name=injury,
                        y=inj_pct.index,
                        x=inj_pct[injury].round(1),
                        orientation="h",
                        marker_color=INJURY_COLORS_MAP[injury],
                        marker_opacity=0.85,
                        hovertemplate=(
                            f"<b>%{{y}}</b><br>{injury}：%{{x:.1f}}%"
                            f"<extra></extra>"
                        ),
                    ))
            # 右側總件數標籤
            fig_dept1.add_trace(go.Scatter(
                y=inj_pct.index,
                x=[102] * len(inj_pct),
                mode="text",
                text=["n=" + str(t) for t in totals],
                textfont=dict(size=10, color="#2C3E50", family="Arial"),
                showlegend=False, hoverinfo="skip",
            ))
            fig_dept1.update_layout(
                barmode="stack",
                height=max(320, len(inj_pct) * 38 + 80),
                plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center",
                            font=dict(size=11, color="#2C3E50")),
                xaxis=dict(
                    title=dict(text="百分比 (%)", font=AXIS_TITLE_FONT),
                    tickfont=AXIS_TICK_FONT,
                    range=[0, 115],
                    gridcolor=GRID_COLOR, griddash="dot",
                    ticksuffix="%",
                ),
                yaxis=dict(
                    title=dict(text="科別", font=AXIS_TITLE_FONT),
                    tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                    automargin=True,
                ),
                margin=dict(t=40, b=60, l=90, r=60),
                hovermode="y unified",
            )
            st.plotly_chart(fig_dept1, use_container_width=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── 圖2：分組橫條圖（三項特徵比率比較）────────────────
            st.markdown('<p class="section-title">② 各科別風險特徵比率比較</p>',
                        unsafe_allow_html=True)

            # 排序依總件數降序（讓大科在上方）
            dept_order = dept_counts[dept_counts >= 5].sort_values(ascending=True).index.tolist()

            feat_data = []
            for dept in dept_order:
                sub = dff_fall[dff_fall[DEPT_COL] == dept]
                n   = len(sub)
                if n == 0:
                    continue
                # ① 跌倒高危險群佔比（「是」）
                r1 = (sub[HIGHRISK_COL] == "是").sum() / n * 100
                # ② 需協助或完全依賴活動者佔比
                r2 = (sub[MOBILITY_COL].isin(["需協助","完全依賴"])).sum() / n * 100
                # ③ 意識混亂或嗜睡佔比
                r3 = (sub[CONSCI_COL].isin(["意識混亂","嗜睡"])).sum() / n * 100
                feat_data.append({"科別": dept, "跌倒高危險群": r1,
                                   "需協助/完全依賴": r2, "意識混亂/嗜睡": r3})

            df_feat = pd.DataFrame(feat_data)

            FEAT_COLORS = {
                "跌倒高危險群":    "#C0392B",
                "需協助/完全依賴": "#3498DB",
                "意識混亂/嗜睡":  "#F39C12",
            }
            fig_dept2 = go.Figure()
            for feat, clr in FEAT_COLORS.items():
                fig_dept2.add_trace(go.Bar(
                    name=feat,
                    y=df_feat["科別"],
                    x=df_feat[feat].round(1),
                    orientation="h",
                    marker_color=clr,
                    marker_opacity=0.80,
                    hovertemplate=f"<b>%{{y}}</b><br>{feat}：%{{x:.1f}}%<extra></extra>",
                ))
            fig_dept2.update_layout(
                barmode="group",
                height=max(340, len(df_feat) * 55 + 80),
                plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center",
                            font=dict(size=11, color="#2C3E50")),
                xaxis=dict(
                    title=dict(text="佔比 (%)", font=AXIS_TITLE_FONT),
                    tickfont=AXIS_TICK_FONT,
                    range=[0, 110],
                    gridcolor=GRID_COLOR, griddash="dot",
                    ticksuffix="%",
                ),
                yaxis=dict(
                    title=dict(text="科別", font=AXIS_TITLE_FONT),
                    tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                    automargin=True,
                    categoryorder="array",
                    categoryarray=dept_order,
                ),
                margin=dict(t=40, b=60, l=90, r=30),
                hovermode="y unified",
            )
            st.plotly_chart(fig_dept2, use_container_width=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── 圖3：執意自行下床比率（由高到低，超過40%紅色）────
            st.markdown('<p class="section-title">③ 各科別「執意自行下床」比率（由高到低）</p>',
                        unsafe_allow_html=True)

            getup_data = []
            for dept in valid_depts:
                sub = dff_fall[dff_fall[DEPT_COL] == dept]
                n   = len(sub)
                if n == 0:
                    continue
                rate = sub[GETUP_COL].eq(1).sum() / n * 100
                getup_data.append({"科別": dept, "比率": round(rate, 1), "總件數": n})

            df_getup = (pd.DataFrame(getup_data)
                        .sort_values("比率", ascending=True))   # 水平圖低→高由下而上

            bar_colors = [
                "#C0392B" if r >= 40 else "#3498DB"
                for r in df_getup["比率"]
            ]
            fig_dept3 = go.Figure(go.Bar(
                y=df_getup["科別"],
                x=df_getup["比率"],
                orientation="h",
                marker_color=bar_colors,
                marker_opacity=0.85,
                text=[f"{r:.2f}%" for r in df_getup["比率"]],
                textposition="outside",
                textfont=dict(size=11, color="#1C2833", family="Arial"),
                customdata=df_getup["總件數"],
                hovertemplate=(
                    "<b>%{y}</b><br>執意自行下床：%{x:.2f}%<br>"
                    "科別總件數：%{customdata} 件<extra></extra>"
                ),
            ))
            # 40% 警戒線
            fig_dept3.add_vline(
                x=40, line_dash="dash", line_color="#E74C3C", line_width=2,
                annotation_text="  40% 警戒線",
                annotation_position="top right",
                annotation_font=dict(size=11, color="#E74C3C", family="Arial Bold"),
            )
            fig_dept3.update_layout(
                height=max(300, len(df_getup) * 40 + 80),
                plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                xaxis=dict(
                    title=dict(text="執意自行下床比率 (%)", font=AXIS_TITLE_FONT),
                    tickfont=AXIS_TICK_FONT,
                    range=[0, max(df_getup["比率"].max() * 1.25, 55)],
                    gridcolor=GRID_COLOR, griddash="dot",
                    ticksuffix="%",
                ),
                yaxis=dict(
                    title=dict(text="科別", font=AXIS_TITLE_FONT),
                    tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                    automargin=True,
                ),
                margin=dict(t=40, b=60, l=90, r=60),
            )
            st.plotly_chart(fig_dept3, use_container_width=True)

            # 超過40%提示
            high_depts = df_getup[df_getup["比率"] >= 40]["科別"].tolist()
            if high_depts:
                st.markdown(
                    f'<div style="background:#FFF3CD;border-left:4px solid #F39C12;'
                    f'padding:10px 14px;border-radius:4px;color:#7D4700;font-size:13px">'
                    f'⚠️ 以下科別執意自行下床比率超過 40%，建議加強衛教與防跌措施：'
                    f'<b>{"、".join(high_depts)}</b></div>',
                    unsafe_allow_html=True)

    else:
        st.info("目前期間內無跌倒事件資料，或科別欄位缺失。")

    st.markdown('<p class="section-title">🏆 各病房 / 單位事件件數排名（Top 20）</p>',
                unsafe_allow_html=True)

    unit_stats = (dff.groupby("單位")
                  .agg(總件數=("編號","count"),
                       高嚴重度=("SAC_num", lambda x: x.isin(HIGH_SAC).sum()))
                  .reset_index()
                  .sort_values("總件數", ascending=True)
                  .tail(20))

    if not unit_stats.empty:
        unit_stats["高嚴重度佔比"] = (
            unit_stats["高嚴重度"] / unit_stats["總件數"] * 100).round(1)
        fig_g = go.Figure()
        fig_g.add_trace(go.Bar(
            y=unit_stats["單位"], x=unit_stats["總件數"],
            orientation="h", name="總件數",
            marker_color="#3498DB", marker_opacity=0.45,
            hovertemplate="<b>%{y}</b><br>總件數：%{x} 件<extra></extra>"))
        fig_g.add_trace(go.Bar(
            y=unit_stats["單位"], x=unit_stats["高嚴重度"],
            orientation="h", name="SAC 1+2（死亡+重大傷害）",
            marker_color="#E74C3C", marker_opacity=0.85,
            customdata=unit_stats["高嚴重度佔比"],
            hovertemplate=(
                "<b>%{y}</b><br>死亡+重大傷害：%{x} 件<br>"
                "佔比：%{customdata:.2f}%<extra></extra>")))
        fig_g.add_trace(go.Scatter(
            y=unit_stats["單位"], x=unit_stats["總件數"],
            mode="text", text=unit_stats["總件數"].astype(str) + " 件",
            textposition="middle right",
            textfont=dict(size=10, color="#1C2833", family="Arial"),
            showlegend=False, hoverinfo="skip"))
        fig_g.update_layout(
            barmode="overlay",
            height=max(420, len(unit_stats) * 28 + 120),
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            legend=dict(orientation="h", y=1.06, x=1, xanchor="right",
                        font=dict(size=11, color="#2C3E50")),
            xaxis=dict(
                title=dict(text="件數", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                gridcolor=GRID_COLOR, griddash="dot",
                zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
            ),
            yaxis=dict(
                title=dict(text="病房 / 單位", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=50, b=60, l=90, r=90),
            hovermode="y unified")
        st.plotly_chart(fig_g, use_container_width=True)

        top10 = (unit_stats.sort_values("總件數", ascending=False)
                 .head(10).reset_index(drop=True))
        top10.index += 1
        top10 = top10.rename(columns={
            "單位":"病房/單位","高嚴重度":"SAC 1+2 件數",
            "高嚴重度佔比":"死亡+重大佔比(%)"})
        st.caption("📋 Top 10 單位詳細數據")
        st.dataframe(top10, use_container_width=True, height=310)

    # ════════════════════════════════════════════════════════════
    #  📝 事件說明特徵萃取分析
    #  資料：dff_fall（已含 extract_fall_features 布林欄位）
    #  篩選器：時間區間 + 科別篩選器連動
    # ════════════════════════════════════════════════════════════
    FALL_FEAT_NAMES = [
        "地點_床邊下床","地點_浴廁","地點_走廊行走","地點_椅子輪椅",
        "機轉_滑倒","機轉_頭暈血壓低","機轉_自行起身未告知","機轉_站不穩腳軟",
        "發現_護理人員巡視","發現_聲響",
        "病況_精神症狀","病況_約束相關",
    ]
    # 依科別篩選 dff_fall（繼承時間篩選）
    if sel_dept != "全部科別":
        dff_fall_feat = dff_fall[
            dff_fall["病人/住民-所在科別"] == sel_dept].copy()
    else:
        dff_fall_feat = dff_fall.copy()

    dept_label_feat = sel_dept if sel_dept != "全部科別" else "全院"
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
                padding:14px 20px;border-radius:8px;margin-bottom:16px'>
      <h3 style='color:#FFFFFF;margin:0;font-size:17px;font-weight:700'>
        📝 事件說明特徵萃取分析
      </h3>
      <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
        資料期間：{start_m} ～ {end_m}　科別：{dept_label_feat}
        　共 {len(dff_fall_feat)} 件跌倒事件
      </p>
    </div>""", unsafe_allow_html=True)

    feat_cols_exist = [f for f in FALL_FEAT_NAMES if f in dff_fall_feat.columns]

    if dff_fall_feat.empty or not feat_cols_exist:
        st.info("目前篩選條件下無跌倒事件說明資料。")
    else:
        n_total = len(dff_fall_feat)

        # ── 圖1：各特徵出現件數橫條圖（由高到低，>30% 紅色警示）──
        st.markdown('<p class="section-title">① 各特徵出現件數與佔比（由高到低）</p>',
                    unsafe_allow_html=True)
        st.caption("💡 點擊任一長條，下方將顯示該特徵在各病房的分佈（RCA 根本原因分析）")

        feat_counts = []
        for feat in feat_cols_exist:
            cnt = int(dff_fall_feat[feat].sum())
            pct = round(cnt / n_total * 100, 2)
            feat_counts.append({"特徵": feat, "件數": cnt, "佔比": pct})
        df_feat_cnt = (pd.DataFrame(feat_counts)
                       .sort_values("佔比", ascending=True)   # 水平圖：低→高（視覺上高在上）
                       .reset_index(drop=True))

        bar_clrs1 = ["#C0392B" if r >= 30 else "#3498DB"
                     for r in df_feat_cnt["佔比"]]

        fig_feat1 = go.Figure(go.Bar(
            y=df_feat_cnt["特徵"],
            x=df_feat_cnt["佔比"],
            orientation="h",
            marker_color=bar_clrs1,
            marker_opacity=0.85,
            text=[f"{r:.2f}%  (n={c})"
                  for r, c in zip(df_feat_cnt["佔比"], df_feat_cnt["件數"])],
            textposition="outside",
            textfont=dict(size=10, color="#1C2833", family="Arial"),
            customdata=df_feat_cnt["件數"],
            hovertemplate=(
                "<b>%{y}</b><br>件數：%{customdata}<br>"
                "佔比：%{x:.2f}%<extra></extra>"
            ),
        ))
        # 30% 參考線
        fig_feat1.add_vline(
            x=30, line_dash="dash", line_color="#E74C3C", line_width=1.5,
            annotation_text="  30%",
            annotation_position="top right",
            annotation_font=dict(size=10, color="#E74C3C", family="Arial Bold"),
        )
        fig_feat1.update_layout(
            height=520,
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="佔比 (%)", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                range=[0, max(df_feat_cnt["佔比"].max() * 1.35, 45)],
                gridcolor=GRID_COLOR, griddash="dot", ticksuffix="%",
                zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
            ),
            yaxis=dict(
                title=dict(text="特徵項目", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=30, b=60, l=130, r=140),
        )

        # 點擊事件（on_select 原生，不需第三方套件）
        pareto_event = st.plotly_chart(
            fig_feat1, use_container_width=True,
            on_select="rerun", key="pareto_select"
        )

        # ── 下鑽：選中特徵後顯示各單位分佈 ────────────────────────
        selected_feat = None
        if pareto_event and pareto_event.get("selection"):
            pts = pareto_event["selection"].get("points", [])
            if pts:
                selected_feat = pts[0].get("y")   # 水平圖用 y 取類別

        if selected_feat and selected_feat in dff_fall_feat.columns:
            st.markdown(f"""
    <div style='background:#EBF5FB;border-left:4px solid #2E86C1;
                padding:10px 14px;border-radius:4px;margin:8px 0 12px 0;
                font-size:13px;color:#1A5276'>
      🔍 <b>下鑽分析：「{selected_feat}」各病房 / 單位件數排名 Top 20</b>
      　｜ RCA 根本原因分析
    </div>""", unsafe_allow_html=True)

            drill_df = dff_fall_feat[dff_fall_feat[selected_feat] == True].copy()
            if "單位" not in drill_df.columns and "病人/住民-所在科別" in drill_df.columns:
                drill_df = drill_df.rename(columns={"病人/住民-所在科別": "單位"})

            unit_col = "單位" if "單位" in drill_df.columns else drill_df.columns[0]
            unit_cnt = (drill_df[unit_col].value_counts()
                        .head(20).reset_index()
                        .rename(columns={"index": unit_col, unit_col: "件數",
                                         "count": "件數"}))
            if "件數" not in unit_cnt.columns:
                unit_cnt.columns = [unit_col, "件數"]
            unit_cnt = unit_cnt.sort_values("件數", ascending=True)
            total_feat = int(dff_fall_feat[selected_feat].sum())

            fig_drill = go.Figure(go.Bar(
                x=unit_cnt["件數"],
                y=unit_cnt[unit_col],
                orientation="h",
                marker_color="#1A5276",
                marker_opacity=0.82,
                text=[f"{v} 件 ({v/total_feat*100:.1f}%)" for v in unit_cnt["件數"]],
                textposition="outside",
                textfont=dict(size=10, color="#1C2833", family="Arial"),
                hovertemplate="<b>%{y}</b>：%{x} 件<extra></extra>",
            ))
            fig_drill.update_layout(
                height=max(280, len(unit_cnt) * 32 + 80),
                plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                xaxis=dict(title=dict(text="件數", font=AXIS_TITLE_FONT),
                           tickfont=AXIS_TICK_FONT,
                           gridcolor=GRID_COLOR, griddash="dot",
                           range=[0, unit_cnt["件數"].max() * 1.35]),
                yaxis=dict(title=dict(text=unit_col, font=AXIS_TITLE_FONT),
                           tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                           automargin=True),
                margin=dict(t=20, b=40, l=90, r=120),
            )
            st.plotly_chart(fig_drill, use_container_width=True)
            st.caption(f"共 {total_feat} 件具備「{selected_feat}」特徵，顯示 Top {len(unit_cnt)} 個單位")
        elif not selected_feat:
            st.caption("👆 點擊任一橫條，即可下鑽查看該特徵的單位分佈")

        # ── feature_tag 互動事件明細表 ────────────────────────────
        st.markdown("<hr>", unsafe_allow_html=True)
        _active_feats = st.session_state.get("feature_tag", [])
        _feat_label   = "、".join(_active_feats) if _active_feats else "全部特徵"
        st.markdown(f'<p class="section-title">📋 跌倒事件明細表（篩選條件：{_feat_label}）</p>',
                    unsafe_allow_html=True)

        # 套用 feature_tag 篩選
        detail_df = dff_fall_feat.copy()
        if _active_feats:
            _mask_feat = pd.Series([True] * len(detail_df), index=detail_df.index)
            for _f in _active_feats:
                if _f in detail_df.columns:
                    _mask_feat = _mask_feat & (detail_df[_f] == True)
            detail_df = detail_df[_mask_feat]

        # 選取顯示欄位
        _disp_cols_map = {
            "發生日期":                    "事件日期",
            "病人/住民-所在科別":            "科別",
            "通報者資料-通報者服務單位":      "單位",
            "病人/住民-事件發生後對病人健康的影響程度": "傷害程度",
            "跌倒事件發生對象-發生地點":      "發生地點",
            "事件說明":                     "事件敘述",
        }
        _avail = {k: v for k, v in _disp_cols_map.items() if k in detail_df.columns}
        if _avail:
            detail_show = (detail_df[list(_avail.keys())]
                           .rename(columns=_avail)
                           .copy())
            # 去識別：截斷事件敘述至前50字
            if "事件敘述" in detail_show.columns:
                detail_show["事件敘述"] = (detail_show["事件敘述"]
                                           .astype(str)
                                           .str.slice(0, 50)
                                           .str.replace(r'\d{3,}', '***', regex=True)  # 遮蔽數字
                                           + "...")
            # 傷害程度標準化顯示
            if "傷害程度" in detail_show.columns:
                detail_show["傷害程度"] = detail_show["傷害程度"].map(
                    INJ_LABEL_MAP).fillna(detail_show["傷害程度"])

            n_detail = len(detail_show)
            n_total_fall = len(dff_fall_feat)
            pct_detail = n_detail / n_total_fall * 100 if n_total_fall > 0 else 0
            st.caption(f"共 {n_detail} 件（佔全部跌倒事件 {pct_detail:.1f}%）｜資料已去識別處理")
            st.dataframe(
                detail_show.reset_index(drop=True),
                use_container_width=True,
                height=min(400, 35 * min(n_detail + 1, 12)),
            )
            if _active_feats and st.button("🔄 清除特徵篩選", key="_btn_clear_feat"):
                st.session_state["feature_tag"] = []
                st.rerun()
        else:
            st.info("無法顯示明細表（缺少必要欄位）。")

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── 圖2：「自行起身未告知」各科別比率（分組橫條）─────────
        st.markdown('<p class="section-title">② 「自行起身未告知」各科別比率比較</p>',
                    unsafe_allow_html=True)

        FOCUS_DEPTS = ["精神科","外科","內科","復健科","護理之家","骨科","其他"]
        DEPT_COLORS_MAP = {
            "精神科":  "#C0392B",
            "外科":    "#3498DB",
            "內科":    "#27AE60",
            "復健科":  "#F39C12",
            "護理之家": "#8E44AD",
            "骨科":    "#2C3E50",
            "其他":    "#7F8C8D",
        }

        getup_feat = "機轉_自行起身未告知"
        dept_col_f = "病人/住民-所在科別"
        dept_rate  = []
        for dept in FOCUS_DEPTS:
            sub = dff_fall[  # 用全院跌倒資料（只套時間篩選）
                dff_fall[dept_col_f] == dept]
            n = len(sub)
            if n < 3:
                continue
            rate = round(sub[getup_feat].sum() / n * 100, 1) if getup_feat in sub else 0
            dept_rate.append({"科別": dept, "比率": rate, "總件數": n})

        df_dept_rate = pd.DataFrame(dept_rate).sort_values("比率", ascending=True)

        if not df_dept_rate.empty:
            bar_clrs2 = [DEPT_COLORS_MAP.get(d, "#7F8C8D")
                         for d in df_dept_rate["科別"]]
            warn_text = ["⚠️" if r >= 40 else "" for r in df_dept_rate["比率"]]

            fig_fe2 = go.Figure()
            fig_fe2.add_trace(go.Bar(
                y=df_dept_rate["科別"],
                x=df_dept_rate["比率"],
                orientation="h",
                marker_color=bar_clrs2,
                marker_opacity=0.85,
                text=[f"{r:.2f}% {w}"
                      for r, w in zip(df_dept_rate["比率"], warn_text)],
                textposition="outside",
                textfont=dict(size=11, color="#1C2833", family="Arial"),
                customdata=df_dept_rate["總件數"],
                hovertemplate=(
                    "<b>%{y}</b><br>自行起身未告知：%{x:.2f}%<br>"
                    "科別總件數：%{customdata} 件<extra></extra>"
                ),
            ))
            fig_fe2.add_vline(
                x=40, line_dash="dash", line_color="#E74C3C", line_width=2,
                annotation_text="  40% 警戒線",
                annotation_position="top right",
                annotation_font=dict(size=11, color="#E74C3C", family="Arial Bold"),
            )
            fig_fe2.update_layout(
                height=max(300, len(df_dept_rate) * 52 + 80),
                plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                xaxis=dict(
                    title=dict(text="自行起身未告知 比率 (%)", font=AXIS_TITLE_FONT),
                    tickfont=AXIS_TICK_FONT,
                    range=[0, max(df_dept_rate["比率"].max() * 1.35, 55)],
                    gridcolor=GRID_COLOR, griddash="dot", ticksuffix="%",
                ),
                yaxis=dict(
                    title=dict(text="科別", font=AXIS_TITLE_FONT),
                    tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                    automargin=True,
                ),
                margin=dict(t=40, b=60, l=80, r=120),
            )
            st.plotly_chart(fig_fe2, use_container_width=True)

            warn_depts = df_dept_rate[df_dept_rate["比率"] >= 40]["科別"].tolist()
            if warn_depts:
                st.markdown(
                    f'<div style="background:#FFF3CD;border-left:4px solid #F39C12;'
                    f'padding:10px 14px;border-radius:4px;color:#7D4700;font-size:13px">'
                    f'⚠️ <b>{"、".join(warn_depts)}</b> 的「自行起身未告知」比率超過 40%，'
                    f'建議加強病人安全教育與護理巡視頻率。</div>',
                    unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── 圖3：地點 × 傷害程度 交叉熱力圖（可下鑽）───────────
        st.markdown('<p class="section-title">③ 發生地點 × 傷害程度 交叉熱力圖（點擊格子下鑽）</p>',
                    unsafe_allow_html=True)

        LOC_FEATS = {
            "床邊下床": "地點_床邊下床",
            "浴廁":    "地點_浴廁",
            "走廊行走": "地點_走廊行走",
            "椅子輪椅": "地點_椅子輪椅",
        }
        INJ_ORDER_HM = ["無傷害","輕度","中度","重度","極重度","無法判定傷害嚴重程度"]
        INJ_LABEL_HM = {"無法判定傷害嚴重程度": "無法判定"}   # 簡短顯示
        inj_col_f    = "病人/住民-事件發生後對病人健康的影響程度"

        def get_location(row):
            for lbl, feat in LOC_FEATS.items():
                if feat in row and row[feat]:
                    return lbl
            return None

        dff_fall_feat2 = dff_fall_feat.copy()
        dff_fall_feat2["地點"] = dff_fall_feat2.apply(get_location, axis=1)
        # 傷害程度簡短標籤
        dff_fall_feat2["傷害程度顯示"] = (dff_fall_feat2[inj_col_f]
                                           .map(INJ_LABEL_MAP)
                                           .fillna(dff_fall_feat2[inj_col_f]))
        hm_data = dff_fall_feat2[
            dff_fall_feat2["地點"].notna() &
            dff_fall_feat2[inj_col_f].notna()
        ].copy()

        if not hm_data.empty:
            # 顯示用傷害程度排序
            INJ_ORDER_DISP = [INJ_LABEL_MAP.get(i, i) for i in INJ_ORDER_HM
                              if INJ_LABEL_MAP.get(i, i) in hm_data["傷害程度顯示"].unique()]
            loc_order = list(LOC_FEATS.keys())

            hm_cross = (hm_data.groupby(["地點","傷害程度顯示"])
                        .size().reset_index(name="件數"))
            hm_piv   = (hm_cross.pivot(index="傷害程度顯示", columns="地點", values="件數")
                        .reindex(index=INJ_ORDER_DISP, columns=loc_order)
                        .fillna(0).astype(int))

            text_matrix = [[str(v) if v > 0 else "" for v in row]
                           for row in hm_piv.values]

            fig_fe3 = go.Figure(go.Heatmap(
                z=hm_piv.values,
                x=hm_piv.columns.tolist(),
                y=hm_piv.index.tolist(),
                text=text_matrix,
                texttemplate="%{text}",
                textfont=dict(size=14, color="white", family="Arial Bold"),
                colorscale=[
                    [0.0, "#F4F6F6"],
                    [0.3, "#AED6F1"],
                    [0.6, "#3498DB"],
                    [1.0, "#1A5276"],
                ],
                hovertemplate=(
                    "<b>地點：%{x}</b><br>"
                    "傷害程度：%{y}<br>"
                    "件數：%{z} 件<extra></extra>"
                ),
                colorbar=dict(
                    title=dict(text="件數", font=dict(size=12, color="#1C2833")),
                    tickfont=dict(size=10, color="#2C3E50"),
                    thickness=14, len=0.7,
                ),
                xgap=3, ygap=3,
            ))
            fig_fe3.update_layout(
                height=320,
                paper_bgcolor=PAPER_BG, plot_bgcolor=PAPER_BG,
                xaxis=dict(title=dict(text="發生地點", font=AXIS_TITLE_FONT),
                           tickfont=dict(size=12, color="#2C3E50", family="Arial"),
                           side="bottom"),
                yaxis=dict(title=dict(text="傷害程度", font=AXIS_TITLE_FONT),
                           tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                           automargin=True),
                margin=dict(t=20, b=60, l=100, r=80),
            )

            # 點擊事件（不需第三方套件）
            hm_event = st.plotly_chart(
                fig_fe3, use_container_width=True,
                on_select="rerun", key="hm_loc_inj_select"
            )

            # 同步點擊結果到 session_state
            _clicked_loc = None
            _clicked_inj = None
            if hm_event and hm_event.get("selection"):
                pts = hm_event["selection"].get("points", [])
                if pts:
                    _clicked_loc = pts[0].get("x")
                    _clicked_inj = pts[0].get("y")
                    if _clicked_loc:
                        st.session_state["loc_filter"] = _clicked_loc
                    if _clicked_inj:
                        st.session_state["inj_filter"] = _clicked_inj

            # 讀取 session_state 的地點/傷害篩選
            _cur_loc = st.session_state.get("loc_filter", "全部地點")
            _cur_inj = st.session_state.get("inj_filter", "全部傷害程度")

            # 目前篩選狀態提示
            if _cur_loc != "全部地點" or _cur_inj != "全部傷害程度":
                _tag_parts = []
                if _cur_loc != "全部地點":
                    _tag_parts.append(f"📍 地點：{_cur_loc}")
                if _cur_inj != "全部傷害程度":
                    _tag_parts.append(f"🩹 傷害：{_cur_inj}")
                st.markdown(
                    f"<div style='background:#EBF5FB;border-left:4px solid #2E86C1;"
                    f"padding:8px 14px;border-radius:4px;font-size:13px;color:#1A5276'>"
                    f"🔍 <b>下鑽篩選中：</b> {'　'.join(_tag_parts)} "
                    f"（可在側邊欄「地點 × 傷害程度 下鑽」清除）</div>",
                    unsafe_allow_html=True
                )

            # ── 下鑽：個案清單 ─────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p class="section-title">📋 下鑽個案清單</p>',
                        unsafe_allow_html=True)

            drill3 = hm_data.copy()
            _loc_map_back = {v: k for k, v in
                             {"全部地點":"全部地點","床邊下床":"床邊下床",
                              "浴廁":"浴廁","走廊行走":"走廊行走","椅子輪椅":"椅子輪椅"}.items()}
            if _cur_loc != "全部地點":
                drill3 = drill3[drill3["地點"] == _cur_loc]
            if _cur_inj != "全部傷害程度":
                drill3 = drill3[drill3["傷害程度顯示"] == _cur_inj]

            n_drill = len(drill3)
            n_all   = len(hm_data)
            pct_all = n_drill / len(dff_fall_feat) * 100 if len(dff_fall_feat) > 0 else 0

            st.caption(
                f"符合條件：**{n_drill}** 件"
                f"（佔熱力圖資料 {n_drill/n_all*100:.1f}%，"
                f"佔全部跌倒事件 {pct_all:.1f}%）"
            )

            # 個案清單顯示欄位
            _case_col_map = {
                "發生日期":                    "事件日期",
                "病人/住民-所在科別":            "科別",
                "通報者資料-通報者服務單位":      "單位",
                "傷害程度顯示":                  "傷害程度",
                "地點":                          "發生地點",
                "事件說明":                      "事件敘述",
            }
            _case_avail = {k: v for k, v in _case_col_map.items()
                           if k in drill3.columns}
            if _case_avail and not drill3.empty:
                case_show = drill3[list(_case_avail.keys())].rename(columns=_case_avail).copy()
                if "事件敘述" in case_show.columns:
                    case_show["事件敘述"] = (case_show["事件敘述"].astype(str)
                                             .str.slice(0, 50)
                                             .str.replace(r'\d{3,}', '***', regex=True)
                                             + "...")
                st.dataframe(
                    case_show.reset_index(drop=True),
                    use_container_width=True,
                    height=min(380, 35 * min(n_drill + 1, 11)),
                )

            # ── 下鑽：該格在各科別的分布橫條圖 ───────────────────
            if not drill3.empty:
                dept_col_f = "病人/住民-所在科別"
                if dept_col_f in drill3.columns:
                    dept_cnt = (drill3[dept_col_f].value_counts()
                                .reset_index()
                                .rename(columns={"index": "科別",
                                                 dept_col_f: "科別",
                                                 "count": "件數"}))
                    if "件數" not in dept_cnt.columns:
                        dept_cnt.columns = ["科別", "件數"]
                    dept_cnt = dept_cnt.sort_values("件數", ascending=True)

                    _loc_txt = _cur_loc if _cur_loc != "全部地點" else "全部地點"
                    _inj_txt = _cur_inj if _cur_inj != "全部傷害程度" else "全部傷害"
                    st.markdown(
                        f'<p class="section-title">'
                        f'各科別分布：{_loc_txt} × {_inj_txt}</p>',
                        unsafe_allow_html=True)

                    fig_drill3 = go.Figure(go.Bar(
                        x=dept_cnt["件數"],
                        y=dept_cnt["科別"],
                        orientation="h",
                        marker_color="#3498DB",
                        marker_opacity=0.82,
                        text=[f"{v} 件 ({v/n_drill*100:.1f}%)"
                              for v in dept_cnt["件數"]],
                        textposition="outside",
                        textfont=dict(size=11, color="#1C2833", family="Arial"),
                        hovertemplate="<b>%{y}</b>：%{x} 件<extra></extra>",
                    ))
                    fig_drill3.update_layout(
                        height=max(200, len(dept_cnt) * 38 + 70),
                        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                        xaxis=dict(
                            title=dict(text="件數", font=AXIS_TITLE_FONT),
                            tickfont=AXIS_TICK_FONT,
                            gridcolor=GRID_COLOR, griddash="dot",
                            range=[0, dept_cnt["件數"].max() * 1.35],
                        ),
                        yaxis=dict(
                            title=dict(text="科別", font=AXIS_TITLE_FONT),
                            tickfont=dict(size=12, color="#2C3E50", family="Arial"),
                            automargin=True,
                        ),
                        margin=dict(t=20, b=40, l=80, r=120),
                    )
                    st.plotly_chart(fig_drill3, use_container_width=True)
        else:
            st.info("目前資料不足以產生交叉熱力圖。")



    # ════════════════════════════════════════════════════════════
    #  ⚠️ 高風險因子綜合分析
    #  資料：dff_fall（時間篩選連動）
    # ════════════════════════════════════════════════════════════
    RISK_DEPTS       = ["精神科","外科","內科","復健科"]
    RISK_FACTOR_DEFS = {
        "鎮靜安眠藥":   lambda s: s["可能原因-鎮靜安眠藥"].eq(1),
        "執意自行下床": lambda s: s["可能原因-高危險群病人執意自行下床或活動"].eq(1),
        "步態不穩":    lambda s: s["可能原因-步態不穩"].eq(1),
        "意識混亂":    lambda s: s["跌倒事件發生對象-當事人當時意識狀況"].isin(["意識混亂","嗜睡"]),
        "無陪伴者":    lambda s: s["跌倒事件發生對象-事件發生時有無陪伴者"].eq("無"),
        "跌倒高危群":  lambda s: s["跌倒事件發生對象-事件發生前是否為跌倒高危險群"].eq("是"),
        "曾跌倒史":    lambda s: s["跌倒事件發生對象-最近一年是否曾經跌倒"].eq("有"),
    }
    DRUG_FACTOR_DEFS = {
        "鎮靜安眠藥": "可能原因-鎮靜安眠藥",
        "降壓藥":    "可能原因-降壓藥",
        "止痛麻醉劑": "可能原因-止痛麻醉劑",
        "降血糖藥":  "可能原因-降血糖藥",
        "抗癲癇藥":  "可能原因-抗癲癇藥",
        "肌肉鬆弛劑": "可能原因-肌肉鬆弛劑",
    }

    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
                padding:14px 20px;border-radius:8px;margin-bottom:16px'>
      <h3 style='color:#FFFFFF;margin:0;font-size:17px;font-weight:700'>
        ⚠️ 高風險因子綜合分析
      </h3>
      <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
        資料期間：{start_m} ～ {end_m}　共 {len(dff_fall)} 件跌倒事件（全院）
      </p>
    </div>""", unsafe_allow_html=True)

    if dff_fall.empty:
        st.info("目前期間內無跌倒事件資料。")
    else:
        # ── 圖1：科別 × 高風險因子 熱力矩陣 ────────────────────
        st.markdown('<p class="section-title">① 各科別高風險因子比率熱力矩陣 (%)</p>',
                    unsafe_allow_html=True)
        st.markdown(
            '<p style="font-size:12px;color:#5D6D7E;margin:-4px 0 10px 0">'
            '顏色越深代表該科別病人具有此風險因子的比率越高</p>',
            unsafe_allow_html=True)

        hm_rows, hm_text = [], []
        valid_depts_risk = []
        for dept in RISK_DEPTS:
            sub = dff_fall[dff_fall["病人/住民-所在科別"] == dept]
            n   = len(sub)
            if n < 3:
                continue
            valid_depts_risk.append(dept)
            row, txt = [], []
            for fname, func in RISK_FACTOR_DEFS.items():
                try:
                    rate = round(func(sub).sum() / n * 100, 1)
                except Exception:
                    rate = 0.0
                row.append(rate)
                txt.append(f"{rate:.2f}%<br>(n={n})")
            hm_rows.append(row)
            hm_text.append(txt)

        if valid_depts_risk:
            factor_names = list(RISK_FACTOR_DEFS.keys())

            fig_risk1 = go.Figure(go.Heatmap(
                z=hm_rows,
                x=factor_names,
                y=valid_depts_risk,
                text=hm_text,
                texttemplate="%{text}",
                textfont=dict(size=12, color="white", family="Arial Bold"),
                colorscale=[
                    [0.0,  "#FEF9E7"],   # 極低 → 淡黃
                    [0.25, "#F9E4B7"],
                    [0.5,  "#E59866"],   # 中   → 橙
                    [0.75, "#C0392B"],   # 中高 → 紅
                    [1.0,  "#641E16"],   # 極高 → 深紅
                ],
                zmin=0, zmax=100,
                hovertemplate=(
                    "<b>%{y} — %{x}</b><br>"
                    "比率：%{z:.2f}%<extra></extra>"
                ),
                colorbar=dict(
                    title=dict(text="比率 (%)",
                               font=dict(size=11, color="#1C2833")),
                    tickfont=dict(size=10, color="#2C3E50"),
                    ticksuffix="%",
                    thickness=14, len=0.75,
                ),
                xgap=4, ygap=4,
            ))
            fig_risk1.update_layout(
                height=280,
                paper_bgcolor=PAPER_BG,
                xaxis=dict(
                    title=dict(text="高風險因子", font=AXIS_TITLE_FONT),
                    tickfont=dict(size=12, color="#2C3E50", family="Arial"),
                    side="bottom",
                ),
                yaxis=dict(
                    title=dict(text="科別", font=AXIS_TITLE_FONT),
                    tickfont=dict(size=12, color="#2C3E50", family="Arial"),
                    automargin=True,
                ),
                margin=dict(t=20, b=70, l=80, r=100),
            )
            st.plotly_chart(fig_risk1, use_container_width=True)
        else:
            st.info("各目標科別件數不足，無法產生熱力矩陣。")




# ════════════════════════════════════════════════════════════
#  TAB 3：藥物安全分析
# ════════════════════════════════════════════════════════════
with _tab3:

    # ── 載入藥物工作表（使用與主資料相同的 EXCEL_PATH）──────
    @st.cache_data
    def load_drug_data():
        xl_d = pd.ExcelFile(EXCEL_PATH)
        df_d = pd.read_excel(xl_d, sheet_name="109-113藥物")
        df_d["年月"] = (pd.to_datetime(df_d["發生日期"], errors="coerce")
                        .dt.to_period("M").astype(str))
        # 四個主流程欄（0/1 布林加總）
        for _col, _key in [
            ("_stage_order", "事件發生階段-醫囑開立與輸入-醫囑開立與輸入"),
            ("_stage_disp",  "事件發生階段-藥局調劑-藥局調劑"),
            ("_stage_trans", "事件發生階段-傳送過程-傳送過程"),
            ("_stage_admin", "事件發生階段-給藥階段-給藥階段"),
        ]:
            df_d[_col] = df_d[_key].fillna(0).astype(int) if _key in df_d.columns else 0
        # 高警訊藥物標記
        _ha_kw = (r"insulin|Insulin|胰島素|Novomix|NovoRapid|Lantus|Humulin|"
                  r"Warfarin|warfarin|Heparin|heparin|enoxaparin|"
                  r"KCl|Kcl|potassium|MgSO4|"
                  r"Midazolam|midazolam|Lorazepam|Morphine|morphine")
        df_d["高警訊"] = (df_d["藥物名稱-應給藥名"].fillna("")
                          .str.contains(_ha_kw, case=False, regex=True))
        return df_d

    df_drug = load_drug_data()

    # ── 時間篩選（與側邊欄 date_range 連動）─────────────────
    _ds, _de = st.session_state["date_range"]
    df_drug_f = df_drug[(df_drug["年月"] >= _ds) & (df_drug["年月"] <= _de)].copy()
    _drug_n     = len(df_drug_f)
    _drug_n_all = len(df_drug)

    # ── Page Header ──────────────────────────────────────────
    st.markdown(f"""
<div style='background:linear-gradient(135deg,#2C1654,#6C3483);
            padding:14px 22px;border-radius:10px;margin-bottom:14px'>
  <h2 style='color:#FFFFFF;margin:0;font-size:19px;font-weight:700'>
    💊 藥物安全分析
  </h2>
  <p style='color:#D7BDE2;margin:4px 0 0;font-size:11px'>
    藥物事件深度分析 · 錯誤環節追蹤 · 高警訊藥物監測
    ｜篩選期間：{_ds} ～ {_de}（共 {_drug_n} 件）
  </p>
</div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    #  KPI 四卡（紫色系）
    # ════════════════════════════════════════════════════════
    _ha_n      = int(df_drug_f["高警訊"].sum())
    _admin_n   = int(df_drug_f["_stage_admin"].sum())
    _admin_pct = round(_admin_n / _drug_n * 100, 1) if _drug_n > 0 else 0
    _disp_n    = int(df_drug_f["_stage_disp"].sum())
    _disp_pct  = round(_disp_n / _drug_n * 100, 1) if _drug_n > 0 else 0

    _kc1, _kc2, _kc3, _kc4 = st.columns(4)
    _kpi_s = ("background:#FFFFFF;border-radius:12px;padding:16px 18px;"
              "box-shadow:0 2px 10px rgba(0,0,0,0.09);"
              "border-left:5px solid {color};min-height:100px")
    for _col, _title, _val, _sub, _clr in [
        (_kc1, "💊 藥物事件總件數",  f"{_drug_n} 件",
         f"篩選期 {_drug_n} ／ 全期 {_drug_n_all} 件", "#7D3C98"),
        (_kc2, "🚨 給藥階段佔比",   f"{_admin_pct:.1f}%",
         f"給藥階段 {_admin_n} 件（最前線風險）", "#C0392B"),
        (_kc3, "⚗️ 調劑階段佔比",  f"{_disp_pct:.1f}%",
         f"藥局調劑 {_disp_n} 件（攔截關鍵點）", "#1A5276"),
        (_kc4, "⚠️ 高警訊藥物件數", f"{_ha_n} 件",
         "胰島素·抗凝血劑·電解質·鎮靜劑", "#B7950B"),
    ]:
        _col.markdown(
            f"<div style='{_kpi_s.format(color=_clr)}'>"
            f"<div style='font-size:11px;color:#5D6D7E;font-weight:700;"
            f"letter-spacing:0.5px;margin-bottom:6px'>{_title}</div>"
            f"<div style='font-size:30px;font-weight:900;color:#1C2833;"
            f"line-height:1.1'>{_val}</div>"
            f"<div style='font-size:11px;color:#85929E;margin-top:5px'>{_sub}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    #  漏斗圖（左）+ 劑型分布（右）
    # ════════════════════════════════════════════════════════
    st.markdown("""<div style='background:#F4ECF7;border-radius:8px;
        padding:10px 16px;margin-bottom:12px'>
      <span style='font-size:14px;font-weight:700;color:#4A235A'>
        🔬 給藥流程錯誤分布
      </span>
      <span style='font-size:11px;color:#7D3C98;margin-left:8px'>
        各環節攔截點分析 · 藥物劑型分布
      </span>
    </div>""", unsafe_allow_html=True)

    _fl, _fr = st.columns([1.3, 1])

    with _fl:
        _funnel_stages = ["醫囑開立", "藥局調劑", "傳送過程", "給藥階段"]
        _funnel_cols   = ["_stage_order","_stage_disp","_stage_trans","_stage_admin"]
        _funnel_vals   = [int(df_drug_f[c].sum()) for c in _funnel_cols]
        _funnel_colors = ["#1A5276","#2471A3","#5DADE2","#C0392B"]

        st.markdown('<p class="section-title">🔽 給藥流程錯誤攔截漏斗</p>',
                    unsafe_allow_html=True)
        st.caption("各環節出現的錯誤件數；給藥階段偏高代表前端屏障需強化")

        fig_funnel = go.Figure(go.Funnel(
            y=_funnel_stages, x=_funnel_vals,
            textinfo="value+percent initial",
            textfont=dict(size=13, color="white", family="Arial"),
            marker=dict(color=_funnel_colors, line=dict(width=1, color="white")),
            connector=dict(line=dict(color="#D7BDE2", width=1.5, dash="dot")),
            hovertemplate="<b>%{y}</b><br>件數：%{x}<extra></extra>",
        ))
        fig_funnel.update_layout(
            height=300, paper_bgcolor=PAPER_BG,
            margin=dict(t=10, b=20, l=10, r=10),
            font=dict(family="Arial", color="#1C2833"),
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

    with _fr:
        _dosage_map = {
            "口服藥":   "應給藥物劑型-口服藥",
            "注射劑":   "應給藥物劑型-注射劑",
            "吸入劑":   "應給藥物劑型-吸入劑",
            "外用藥":   "應給藥物劑型-外用藥",
            "化療針劑": "應給藥物劑型-化學治療針劑",
        }
        _dosage_df = pd.DataFrame([
            {"劑型": lbl,
             "件數": int(df_drug_f[col].sum()) if col in df_drug_f.columns else 0}
            for lbl, col in _dosage_map.items()
        ]).query("件數 > 0").sort_values("件數", ascending=True).reset_index(drop=True)

        st.markdown('<p class="section-title">💊 應給藥物劑型分布</p>',
                    unsafe_allow_html=True)
        st.caption("注射劑與口服藥錯誤風險最高，需重點監控雙重核對")

        if not _dosage_df.empty:
            _mx_d = _dosage_df["件數"].max()
            _q6_d = _dosage_df["件數"].quantile(0.6)
            _dose_c = ["#7D3C98" if v == _mx_d else
                       "#A569BD" if v >= _q6_d else "#D7BDE2"
                       for v in _dosage_df["件數"]]
            fig_dosage = go.Figure(go.Bar(
                x=_dosage_df["件數"], y=_dosage_df["劑型"],
                orientation="h",
                marker=dict(color=_dose_c, opacity=0.87,
                            line=dict(width=0)),
                text=[f"{v} 件" for v in _dosage_df["件數"]],
                textposition="outside",
                textfont=dict(size=11, color="#1C2833", family="Arial"),
                hovertemplate="<b>%{y}</b>：%{x} 件<extra></extra>",
            ))
            fig_dosage.update_layout(
                height=260, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                xaxis=dict(title=dict(text="件數", font=AXIS_TITLE_FONT),
                           tickfont=AXIS_TICK_FONT,
                           gridcolor=GRID_COLOR, griddash="dot",
                           range=[0, _mx_d * 1.35]),
                yaxis=dict(tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                           automargin=True),
                margin=dict(t=10, b=40, l=80, r=80),
            )
            st.plotly_chart(fig_dosage, use_container_width=True)
        else:
            st.info("目前篩選期間無劑型資料。")


    # ════════════════════════════════════════════════════════
    #  錯誤子類型橫條圖（Top 20）
    # ════════════════════════════════════════════════════════
    st.markdown('<p class="section-title">🔎 各環節錯誤子類型明細（Top 20）</p>',
                unsafe_allow_html=True)
    st.caption("識別最需系統性介入的具體錯誤類型；顏色代表所屬流程環節")

    _stage_pfx = {
        "給藥階段": "事件發生階段-給藥階段-是-",
        "藥局調劑": "事件發生階段-藥局調劑-是-",
        "醫囑開立": "事件發生階段-醫囑開立與輸入-是-",
        "傳送過程": "事件發生階段-傳送過程-是-",
    }
    _stage_pal = {"給藥階段":"#C0392B","藥局調劑":"#2471A3",
                  "醫囑開立":"#1A5276","傳送過程":"#7D3C98"}

    _sub_rows = []
    for _stg, _pfx in _stage_pfx.items():
        for _c in [c for c in df_drug_f.columns
                   if c.startswith(_pfx) and "文字" not in c]:
            _n = int(df_drug_f[_c].sum())
            if _n > 0:
                _sub_rows.append({
                    "環節": _stg,
                    "錯誤類型": _c.replace(_pfx, ""),
                    "件數": _n,
                })

    if _sub_rows:
        _st_df = (pd.DataFrame(_sub_rows)
                  .sort_values("件數", ascending=False).head(20)
                  .sort_values("件數", ascending=True).reset_index(drop=True))
        _st_c = [_stage_pal.get(s, "#7F8C8D") for s in _st_df["環節"]]

        _lg = "　".join(
            f"<span style='color:{c};font-weight:700'>■ {s}</span>"
            for s, c in _stage_pal.items()
        )
        st.markdown(f"<div style='font-size:11px;margin-bottom:8px'>{_lg}</div>",
                    unsafe_allow_html=True)

        fig_sub = go.Figure(go.Bar(
            x=_st_df["件數"],
            y=_st_df.apply(lambda r: f"[{r['環節']}] {r['錯誤類型']}", axis=1),
            orientation="h",
            marker=dict(color=_st_c, opacity=0.87, line=dict(width=0)),
            text=[f"{v} 件" for v in _st_df["件數"]],
            textposition="outside",
            textfont=dict(size=10, color="#1C2833", family="Arial"),
            hovertemplate="<b>%{y}</b>：%{x} 件<extra></extra>",
        ))
        fig_sub.update_layout(
            height=max(400, len(_st_df) * 28 + 80),
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(title=dict(text="件數", font=AXIS_TITLE_FONT),
                       tickfont=AXIS_TICK_FONT,
                       gridcolor=GRID_COLOR, griddash="dot",
                       range=[0, _st_df["件數"].max() * 1.3]),
            yaxis=dict(tickfont=dict(size=10, color="#2C3E50", family="Arial"),
                       automargin=True),
            margin=dict(t=10, b=40, l=210, r=90),
        )
        st.plotly_chart(fig_sub, use_container_width=True)
    else:
        st.info("目前篩選期間無錯誤子類型資料。")


    # ════════════════════════════════════════════════════════
    #  可能原因分析（Top 20）
    # ════════════════════════════════════════════════════════
    st.markdown('<p class="section-title">🧩 可能原因分析（Top 20）</p>',
                unsafe_allow_html=True)
    st.caption("多選欄位加總；同一事件可歸因多項原因")

    _cause_def = [
        ("人員因素", "#7D3C98",
         [c for c in df_drug_f.columns
          if "可能原因-" in c and "人員" in c and "文字" not in c]),
        ("工作流程", "#C0392B",
         [c for c in df_drug_f.columns
          if "可能原因-" in c and "工作狀態" in c and "文字" not in c]),
        ("溝通因素", "#1A5276",
         [c for c in df_drug_f.columns
          if "可能原因-" in c and "溝通" in c and "文字" not in c]),
        ("器材設備", "#B7950B",
         [c for c in df_drug_f.columns
          if "可能原因-" in c and "器材" in c and "文字" not in c]),
        ("藥物本身", "#1E8449",
         [c for c in df_drug_f.columns
          if "可能原因-" in c
          and any(k in c for k in ["藥名相似","外型","標示","保存","列印"])
          and "文字" not in c]),
        ("病人因素", "#5D6D7E",
         [c for c in df_drug_f.columns
          if "可能原因-" in c and "病人生理" in c and "文字" not in c]),
    ]

    _ca_rows = []
    for _grp, _clr, _cols in _cause_def:
        for _c in _cols:
            _n = int(df_drug_f[_c].sum()) if _c in df_drug_f.columns else 0
            if _n > 0:
                _lbl = _c.replace("可能原因-","")
                _ca_rows.append({"原因大類":_grp,"原因":_lbl,"件數":_n,"顏色":_clr})

    if _ca_rows:
        _ca_df = (pd.DataFrame(_ca_rows)
                  .sort_values("件數", ascending=False).head(20)
                  .sort_values("件數", ascending=True).reset_index(drop=True))

        fig_cause = go.Figure(go.Bar(
            x=_ca_df["件數"],
            y=_ca_df.apply(lambda r: f"[{r['原因大類']}] {r['原因']}", axis=1),
            orientation="h",
            marker=dict(color=_ca_df["顏色"].tolist(), opacity=0.87,
                        line=dict(width=0)),
            text=[f"{v} 件" for v in _ca_df["件數"]],
            textposition="outside",
            textfont=dict(size=10, color="#1C2833", family="Arial"),
            hovertemplate="<b>%{y}</b>：%{x} 件<extra></extra>",
        ))
        fig_cause.update_layout(
            height=max(360, len(_ca_df) * 28 + 80),
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(title=dict(text="歸因件數", font=AXIS_TITLE_FONT),
                       tickfont=AXIS_TICK_FONT,
                       gridcolor=GRID_COLOR, griddash="dot",
                       range=[0, _ca_df["件數"].max() * 1.3]),
            yaxis=dict(tickfont=dict(size=10, color="#2C3E50", family="Arial"),
                       automargin=True),
            margin=dict(t=10, b=40, l=220, r=90),
        )
        st.plotly_chart(fig_cause, use_container_width=True)
    else:
        st.info("目前篩選期間無可能原因資料。")


    # ════════════════════════════════════════════════════════
    #  高警訊藥物監測清單
    # ════════════════════════════════════════════════════════
    st.markdown('<p class="section-title">🚨 高警訊藥物（High-Alert Medications）監測清單</p>',
                unsafe_allow_html=True)
    st.caption("胰島素 · 抗凝血劑 · 濃縮電解質 · 鎮靜麻醉藥；依發生日期降冪排列")

    _ha_df = df_drug_f[df_drug_f["高警訊"] == True].copy()

    if not _ha_df.empty:
        def _detect_stage(row):
            if row.get("_stage_admin", 0): return "給藥階段"
            if row.get("_stage_disp",  0): return "藥局調劑"
            if row.get("_stage_order", 0): return "醫囑開立"
            if row.get("_stage_trans", 0): return "傳送過程"
            return "不明"

        _ha_df = _ha_df.copy()
        _ha_df["錯誤環節"] = _ha_df.apply(_detect_stage, axis=1)
        _ha_show = (_ha_df[["發生日期","藥物名稱-應給藥名","藥物名稱-給錯藥名",
                             "錯誤環節","年月"]]
                    .rename(columns={"藥物名稱-應給藥名":"應給藥名",
                                     "藥物名稱-給錯藥名":"給錯藥名"})
                    .sort_values("發生日期", ascending=False)
                    .head(30).reset_index(drop=True))

        _env_bg = {"給藥階段":"#FADBD8","藥局調劑":"#D6EAF8",
                   "醫囑開立":"#D5F5E3","傳送過程":"#FEF9E7","不明":"#F4F6F6"}

        st.markdown("""
<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;font-size:11px'>
  <span style='background:#FADBD8;padding:2px 8px;border-radius:4px'>■ 給藥階段</span>
  <span style='background:#D6EAF8;padding:2px 8px;border-radius:4px'>■ 藥局調劑</span>
  <span style='background:#D5F5E3;padding:2px 8px;border-radius:4px'>■ 醫囑開立</span>
  <span style='background:#FEF9E7;padding:2px 8px;border-radius:4px'>■ 傳送過程</span>
</div>""", unsafe_allow_html=True)

        _rows_html = ""
        for _, row in _ha_show.iterrows():
            _bg = _env_bg.get(row["錯誤環節"], "#F4F6F6")
            _w  = str(row.get("給錯藥名","")).strip()
            _wd = _w if _w and _w.lower() not in ["nan","","0"] else "—"
            _rows_html += (
                f"<tr style='background:{_bg}'>"
                f"<td style='padding:7px 10px;font-size:12px'>{row['發生日期']}</td>"
                f"<td style='padding:7px 10px;font-size:12px;font-weight:600'>"
                f"{str(row['應給藥名'])[:40]}</td>"
                f"<td style='padding:7px 10px;font-size:12px;color:#C0392B'>"
                f"{_wd[:40]}</td>"
                f"<td style='padding:7px 10px;font-size:11px'>"
                f"<span style='background:{_bg};border:1px solid #D0D3D4;"
                f"border-radius:4px;padding:2px 7px;font-weight:600'>"
                f"{row['錯誤環節']}</span></td>"
                f"<td style='padding:7px 10px;font-size:12px;color:#5D6D7E'>"
                f"{row['年月']}</td>"
                f"</tr>"
            )

        st.markdown(f"""
<table style='width:100%;border-collapse:collapse'>
  <thead>
    <tr style='background:#4A235A;color:white'>
      <th style='padding:8px 10px;text-align:left;font-size:12px'>發生日期</th>
      <th style='padding:8px 10px;text-align:left;font-size:12px'>應給藥名</th>
      <th style='padding:8px 10px;text-align:left;font-size:12px'>給錯藥名</th>
      <th style='padding:8px 10px;text-align:left;font-size:12px'>錯誤環節</th>
      <th style='padding:8px 10px;text-align:left;font-size:12px'>年月</th>
    </tr>
  </thead>
  <tbody>{_rows_html}</tbody>
</table>""", unsafe_allow_html=True)
        st.caption(f"共 {len(_ha_df)} 件高警訊藥物事件（顯示最近 {min(30,len(_ha_df))} 件）")
    else:
        st.info("目前篩選期間無高警訊藥物事件。")




# ════════════════════════════════════════════════════════════
#  TAB 4：傷害行為分析
# ════════════════════════════════════════════════════════════
with _tab4:

    @st.cache_data
    def load_harm_data():
        xl_h = pd.ExcelFile(EXCEL_PATH)
        df_h  = pd.read_excel(xl_h, sheet_name="109-113傷害")
        df_a  = pd.read_excel(xl_h, sheet_name="109-113全部")
        df_a["單位"] = (df_a["通報者資料-通報者服務單位"]
                        .astype(str).str.strip().str.upper())
        df_a["年月"] = (pd.to_datetime(df_a["發生日期"], errors="coerce")
                        .dt.to_period("M").astype(str))
        _mc = [c for c in [
            "通報案號","單位","年月",
            "發生者資料-門診住院日","發生者資料-年齡",
            "發生者資料-性別","發生者資料-診斷",
            "病人/住民-事件發生後對病人健康的影響程度(彙總)","SAC",
        ] if c in df_a.columns]
        df_h = df_h.merge(df_a[_mc].drop_duplicates("通報案號"),
                          on="通報案號", how="left")
        df_h["年月"] = (pd.to_datetime(df_h["發生日期"], errors="coerce")
                        .dt.to_period("M").astype(str))
        df_h["發生日期_dt"] = pd.to_datetime(df_h["發生日期"], errors="coerce")
        df_h["住院日_dt"]   = pd.to_datetime(
            df_h["發生者資料-門診住院日"], errors="coerce")
        df_h["住院後天數"]  = (df_h["發生日期_dt"] - df_h["住院日_dt"]).dt.days
        return df_h

    df_harm_all = load_harm_data()

    _hs, _he = st.session_state["date_range"]
    _harm_base = (df_harm_all if sel_unit == "全院"
                  else df_harm_all[df_harm_all["單位"].isin(["W11","W12"])]
                  if sel_unit == "W11+W12（精神科）"
                  else df_harm_all[df_harm_all["單位"] == sel_unit])
    _hf = _harm_base[
        (_harm_base["年月"] >= _hs) & (_harm_base["年月"] <= _he)
    ].copy()
    _hn = len(_hf)

    # ── Page Header ────────────────────────────────────────
    _h_header = (
        "<div style='background:linear-gradient(135deg,#1C2833,#2E4057);"
        "padding:14px 22px;border-radius:10px;margin-bottom:14px;"
        "border-left:5px solid #E74C3C'>"
        "<h2 style='color:#FFFFFF;margin:0;font-size:19px;font-weight:700'>"
        "&#9888;&#65039; 傷害行為分析</h2>"
        f"<p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>"
        f"身體攻擊 &#183; 自傷 &#183; 自殺企圖 &#183; 可能原因多維分析 &#183; 入院時間風險窗口"
        f" &#65372; 篩選期間：{_hs} ～ {_he}（共 {_hn} 件）</p>"
        "</div>"
    )
    st.markdown(_h_header, unsafe_allow_html=True)

    # ── KPI 四卡 ──────────────────────────────────────────
    _TC = {
        "身體攻擊": "傷害類型-身體攻擊",
        "自傷":     "傷害類型-自傷",
        "自殺企圖": "傷害類型-自殺/企圖自殺",
        "言語衝突": "傷害類型-言語衝突",
    }
    _hkpi = {k: int(_hf[v].fillna(0).sum()) if v in _hf.columns else 0
             for k, v in _TC.items()}
    _hk1, _hk2, _hk3, _hk4 = st.columns(4)
    _hks = ("background:#FFFFFF;border-radius:12px;padding:16px 18px;"
            "box-shadow:0 2px 10px rgba(0,0,0,0.09);"
            "border-left:5px solid {c};min-height:96px")
    def _hkc(col, title, val, sub, c):
        col.markdown(
            f"<div style='{_hks.format(c=c)}'>"
            f"<div style='font-size:11px;color:#5D6D7E;font-weight:700;"
            f"letter-spacing:0.5px;margin-bottom:6px'>{title}</div>"
            f"<div style='font-size:28px;font-weight:900;color:#1C2833;"
            f"line-height:1.1'>{val}</div>"
            f"<div style='font-size:11px;color:#85929E;margin-top:4px'>{sub}</div>"
            f"</div>", unsafe_allow_html=True)
    _hkc(_hk1, "&#9888;&#65039; 傷害事件總件數", f"{_hn} 件",
         f"篩選期 {_hn} / 全期 {len(df_harm_all)} 件", "#E74C3C")
    _hkc(_hk2, "&#128074; 身體攻擊",
         f"{_hkpi['身體攻擊']} 件",
         f"佔比 {round(_hkpi['身體攻擊']/max(_hn,1)*100,1)}%", "#C0392B")
    _hkc(_hk3, "&#129656; 自傷",
         f"{_hkpi['自傷']} 件",
         f"佔比 {round(_hkpi['自傷']/max(_hn,1)*100,1)}%", "#7D3C98")
    _hkc(_hk4, "&#128680; 自殺/企圖自殺",
         f"{_hkpi['自殺企圖']} 件",
         f"佔比 {round(_hkpi['自殺企圖']/max(_hn,1)*100,1)}%", "#922B21")

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    #  第一區：傷害類型結構 + 月別趨勢
    # ════════════════════════════════════════════════════
    st.markdown(
        "<div style='background:#F0F3F4;border-radius:8px;"
        "padding:10px 16px;margin-bottom:12px'>"
        "<span style='font-size:14px;font-weight:700;color:#2C3E50'>"
        "&#128202; 傷害類型結構 &#183; 月別趨勢</span></div>",
        unsafe_allow_html=True)

    _ha1, _ha2 = st.columns([1, 1.4])
    with _ha1:
        _tdf = pd.DataFrame([
            {"類型": k, "件數": _hkpi[k]}
            for k in ["身體攻擊","自傷","言語衝突","自殺企圖"]
        ]).sort_values("件數", ascending=True)
        _tc_map = {"身體攻擊":"#C0392B","自傷":"#7D3C98",
                   "言語衝突":"#E67E22","自殺企圖":"#922B21"}
        fig_type_h = go.Figure(go.Bar(
            x=_tdf["件數"], y=_tdf["類型"], orientation="h",
            marker=dict(color=[_tc_map.get(t,"#AEB6BF") for t in _tdf["類型"]],
                        opacity=0.88, line=dict(width=0)),
            text=[f"{v} 件" for v in _tdf["件數"]], textposition="outside",
            textfont=dict(size=11, color="#1C2833", family="Arial"),
            hovertemplate="<b>%{y}</b>：%{x} 件<extra></extra>",
        ))
        fig_type_h.update_layout(
            height=240, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(title=dict(text="件數", font=AXIS_TITLE_FONT),
                       tickfont=AXIS_TICK_FONT, gridcolor=GRID_COLOR, griddash="dot",
                       range=[0, max(_tdf["件數"].max(),1)*1.35]),
            yaxis=dict(tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                       automargin=True),
            margin=dict(t=10, b=40, l=80, r=80),
        )
        st.markdown('<p class="section-title">各傷害類型件數</p>',
                    unsafe_allow_html=True)
        st.plotly_chart(fig_type_h, use_container_width=True)

    with _ha2:
        _hf["年月顯示"] = _hf["年月"].str.replace("-", "/", regex=False)
        _m_atk = (_hf.groupby("年月顯示")["傷害類型-身體攻擊"]
                  .sum().reset_index(name="攻擊"))
        _m_sih = (_hf.groupby("年月顯示")["傷害類型-自傷"]
                  .sum().reset_index(name="自傷"))
        _m_tot = (_hf.groupby("年月顯示").size().reset_index(name="總件數"))
        _mtr = (_m_atk.merge(_m_sih, on="年月顯示", how="outer")
                      .merge(_m_tot, on="年月顯示", how="outer")
                      .fillna(0))
        fig_trend_h = go.Figure()
        # 總件數（最底層，灰色粗線）
        fig_trend_h.add_trace(go.Scatter(
            x=_mtr["年月顯示"], y=_mtr["總件數"],
            mode="lines+markers", name="傷害總件數",
            line=dict(color="#5D6D7E", width=2.5, dash="dot"),
            marker=dict(size=4, color="#5D6D7E"),
            hovertemplate="<b>%{x}</b><br>總件數：%{y} 件<extra></extra>",
        ))
        fig_trend_h.add_trace(go.Scatter(
            x=_mtr["年月顯示"], y=_mtr["攻擊"],
            mode="lines+markers", name="身體攻擊",
            line=dict(color="#C0392B", width=2), marker=dict(size=5),
            hovertemplate="<b>%{x}</b><br>攻擊：%{y} 件<extra></extra>",
        ))
        fig_trend_h.add_trace(go.Scatter(
            x=_mtr["年月顯示"], y=_mtr["自傷"],
            mode="lines+markers", name="自傷",
            line=dict(color="#7D3C98", width=2), marker=dict(size=5),
            hovertemplate="<b>%{x}</b><br>自傷：%{y} 件<extra></extra>",
        ))
        fig_trend_h.update_layout(
            height=240, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(title=dict(text="年月", font=AXIS_TITLE_FONT),
                       tickfont=dict(size=9, color="#2C3E50", family="Arial"),
                       tickangle=45, showgrid=False),
            yaxis=dict(title=dict(text="件數", font=AXIS_TITLE_FONT),
                       tickfont=AXIS_TICK_FONT, gridcolor=GRID_COLOR,
                       griddash="dot", rangemode="tozero"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                        font=dict(size=11)),
            margin=dict(t=40, b=70, l=50, r=20),
        )
        st.markdown('<p class="section-title">攻擊 vs 自傷月別趨勢</p>',
                    unsafe_allow_html=True)
        st.caption("可觀察是否有季節性規律（文獻：夏末至秋季攻擊事件偏高）")
        st.plotly_chart(fig_trend_h, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    #  第二區：入院後天數分布 + 72h 對比
    # ════════════════════════════════════════════════════
    st.markdown(
        "<div style='background:#F0F3F4;border-radius:8px;"
        "padding:10px 16px;margin-bottom:12px'>"
        "<span style='font-size:14px;font-weight:700;color:#2C3E50'>"
        "&#9201;&#65039; 入院後發生時間分析</span>"
        "<span style='font-size:11px;color:#5D6D7E;margin-left:8px'>"
        "72小時高風險窗口驗證 &#183; 此資料顯示長期住民為主要族群</span>"
        "</div>", unsafe_allow_html=True)

    _hb1, _hb2 = st.columns([1.2, 1])
    with _hb1:
        # 入院後天數隨時間區間連動（_hf已篩選）
        _dv = _hf["住院後天數"].dropna()
        _dv = _dv[_dv >= 0]
        _dlbls = ["0-3天(72h内)","4-7天","8-14天","15-30天","31天以上"]
        _dcnts = [
            int((_dv <= 3).sum()),
            int(((_dv > 3)  & (_dv <= 7)).sum()),
            int(((_dv > 7)  & (_dv <= 14)).sum()),
            int(((_dv > 14) & (_dv <= 30)).sum()),
            int((_dv > 30).sum()),
        ]
        _dbdf = pd.DataFrame({"天數分組":_dlbls,"件數":_dcnts})
        _dbcol = ["#E74C3C","#E67E22","#F39C12","#AED6F1","#85929E"]
        fig_days = go.Figure(go.Bar(
            x=_dbdf["天數分組"], y=_dbdf["件數"],
            marker=dict(color=_dbcol, opacity=0.88, line=dict(width=0)),
            text=_dbdf["件數"], textposition="outside",
            textfont=dict(size=11, color="#1C2833", family="Arial"),
            hovertemplate="<b>%{x}</b>：%{y} 件<extra></extra>",
        ))
        fig_days.update_layout(
            height=280, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(tickfont=dict(size=10, color="#2C3E50", family="Arial"),
                       showgrid=False),
            yaxis=dict(title=dict(text="件數", font=AXIS_TITLE_FONT),
                       tickfont=AXIS_TICK_FONT, gridcolor=GRID_COLOR, griddash="dot",
                       range=[0, max(_dcnts)*1.25]),
            margin=dict(t=20, b=50, l=50, r=20),
        )
        st.markdown('<p class="section-title">入院後天數分布</p>',
                    unsafe_allow_html=True)
        st.caption("紅色=72小時高風險窗口；灰色=長期住民（31天+）為最大族群 ｜ 隨時間區間篩選連動")
        st.plotly_chart(fig_days, use_container_width=True)

    with _hb2:
        _d72   = df_harm_all[df_harm_all["住院後天數"].fillna(99) <= 3]
        _dlate = df_harm_all[df_harm_all["住院後天數"].fillna(-1) > 3]
        _n72, _nlt = max(len(_d72),1), max(len(_dlate),1)
        _tkl = [
            ("身體攻擊","傷害類型-身體攻擊","#C0392B"),
            ("自傷",    "傷害類型-自傷",    "#7D3C98"),
            ("言語衝突","傷害類型-言語衝突","#E67E22"),
            ("自殺企圖","傷害類型-自殺/企圖自殺","#922B21"),
        ]
        fig_72 = go.Figure()
        for lbl, col, color in _tkl:
            _p72  = round(int(_d72[col].fillna(0).sum())/_n72*100,1) if col in _d72.columns else 0
            _plt  = round(int(_dlate[col].fillna(0).sum())/_nlt*100,1) if col in _dlate.columns else 0
            fig_72.add_trace(go.Bar(
                name=lbl, y=["72h 内","72h 後"],
                x=[_p72/100, _plt/100], orientation="h",
                marker=dict(color=color, opacity=0.85, line=dict(width=0)),
                text=[f"{_p72:.0f}%", f"{_plt:.0f}%"],
                textposition="inside",
                textfont=dict(size=10, color="white"),
                hovertemplate=f"<b>{lbl}</b>：%{{text}}<extra></extra>",
            ))
        fig_72.update_layout(
            barmode="stack", height=200,
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(title=dict(text="佔比", font=AXIS_TITLE_FONT),
                       tickformat=".0%", tickfont=AXIS_TICK_FONT,
                       gridcolor=GRID_COLOR, griddash="dot"),
            yaxis=dict(tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                       automargin=True),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                        font=dict(size=10)),
            margin=dict(t=40, b=40, l=70, r=20),
        )
        st.markdown('<p class="section-title">72h 内 vs 72h 後：傷害類型佔比</p>',
                    unsafe_allow_html=True)
        st.caption("自傷在入院早期佔比較高，部分符合文獻急性期高風險描述")
        st.plotly_chart(fig_72, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    #  第三區：可能原因五大群（隨篩選連動）
    # ════════════════════════════════════════════════════
    st.markdown(
        "<div style='background:#F0F3F4;border-radius:8px;"
        "padding:10px 16px;margin-bottom:12px'>"
        "<span style='font-size:14px;font-weight:700;color:#2C3E50'>"
        "&#129513; 可能原因分析（隨篩選連動）</span></div>",
        unsafe_allow_html=True)

    _CGH = [
        ("病人生理行為","#7D3C98",[
            "可能原因-受病情影響","可能原因-情緒不穩",
            "可能原因-病人拒絕服藥或治療","可能原因-物質濫用",
            "可能原因-其他與病人生理及行為因素相關"]),
        ("溝通因素","#2471A3",[
            "可能原因-病友間溝通不良",
            "可能原因-病人或家屬與醫療團隊溝通不足",
            "可能原因-衛教提供不足或衛教方式不當",
            "可能原因-醫療團隊間溝通不足"]),
        ("人員因素","#C0392B",[
            "可能原因-人員疏忽","可能原因-臨床訓練問題",
            "可能原因-未給予適當約束","可能原因-病人評估問題"]),
        ("工作流程","#E67E22",[
            "可能原因-作業流程問題",
            "可能原因-人員工作負荷問題","可能原因-人力問題"]),
        ("環境因素","#1E8449",[
            "可能原因-環境安全防護設計問題",
            "可能原因-環境動線問題","可能原因-照明問題"]),
    ]
    _crh = []
    for grp, color, cols in _CGH:
        for col in cols:
            n = int(_hf[col].fillna(0).sum()) if col in _hf.columns else 0
            if n > 0:
                _crh.append({"原因大類":grp,"原因":col.replace("可能原因-",""),
                              "件數":n,"顏色":color})
    if _crh:
        _cah = (pd.DataFrame(_crh).sort_values("件數",ascending=False)
                .head(20).sort_values("件數",ascending=True).reset_index(drop=True))
        _lgh = "　".join(
            f"<span style='color:{c};font-weight:700'>&#9632; {g}</span>"
            for g, c, _ in _CGH)
        st.markdown(f"<div style='font-size:11px;margin-bottom:8px'>{_lgh}</div>",
                    unsafe_allow_html=True)
        fig_cause_h = go.Figure(go.Bar(
            x=_cah["件數"],
            y=_cah.apply(lambda r: f"[{r['原因大類']}] {r['原因']}", axis=1),
            orientation="h",
            marker=dict(color=_cah["顏色"].tolist(), opacity=0.88, line=dict(width=0)),
            text=[f"{v} 件" for v in _cah["件數"]], textposition="outside",
            textfont=dict(size=10, color="#1C2833", family="Arial"),
            hovertemplate="<b>%{y}</b>：%{x} 件<extra></extra>",
        ))
        fig_cause_h.update_layout(
            height=max(380, len(_cah)*28+80),
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(title=dict(text="件數", font=AXIS_TITLE_FONT),
                       tickfont=AXIS_TICK_FONT, gridcolor=GRID_COLOR, griddash="dot",
                       range=[0, _cah["件數"].max()*1.3]),
            yaxis=dict(tickfont=dict(size=10, color="#2C3E50", family="Arial"),
                       automargin=True),
            margin=dict(t=10, b=40, l=200, r=80),
        )
        st.plotly_chart(fig_cause_h, use_container_width=True)
    else:
        st.info("目前篩選期間無可能原因資料。")

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    #  第四區：攻擊 vs 自傷原因差異（全期全院固定）
    # ════════════════════════════════════════════════════
    st.markdown(
        "<div style='background:#F0F3F4;border-radius:8px;"
        "padding:10px 16px;margin-bottom:12px'>"
        "<span style='font-size:14px;font-weight:700;color:#2C3E50'>"
        "&#9876;&#65039; 身體攻擊 vs 自傷：原因差異對比</span>"
        "<span style='font-size:11px;color:#5D6D7E;margin-left:8px'>"
        "全期全院固定基準</span></div>",
        unsafe_allow_html=True)
    st.caption("紅色=身體攻擊，紫色=自傷；差異越大代表兩類事件需要不同介入策略")

    _ATK = df_harm_all[df_harm_all["傷害類型-身體攻擊"].fillna(0)==1]
    _SIH = df_harm_all[df_harm_all["傷害類型-自傷"].fillna(0)==1]
    _na, _ns = max(len(_ATK),1), max(len(_SIH),1)
    _dpl = [
        ("受病情影響",     "可能原因-受病情影響"),
        ("情緒不穩",       "可能原因-情緒不穩"),
        ("病友溝通不良",   "可能原因-病友間溝通不良"),
        ("人員疏忽",       "可能原因-人員疏忽"),
        ("臨床訓練問題",   "可能原因-臨床訓練問題"),
        ("病人評估問題",   "可能原因-病人評估問題"),
        ("未給予適當約束", "可能原因-未給予適當約束"),
        ("環境安全防護問題","可能原因-環境安全防護設計問題"),
        ("物質濫用",       "可能原因-物質濫用"),
        ("拒絕服藥",       "可能原因-病人拒絕服藥或治療"),
    ]
    _drl = []
    for lbl, col in _dpl:
        _pa = round(int(_ATK[col].fillna(0).sum())/_na*100,1) if col in _ATK.columns else 0
        _ps = round(int(_SIH[col].fillna(0).sum())/_ns*100,1) if col in _SIH.columns else 0
        _drl.append({"原因":lbl,"攻擊%":_pa,"自傷%":_ps,"差異":abs(_pa-_ps)})
    _ddf = (pd.DataFrame(_drl).sort_values("差異",ascending=True)
            .reset_index(drop=True))
    fig_diff = go.Figure()
    fig_diff.add_trace(go.Bar(
        name="身體攻擊", x=_ddf["攻擊%"], y=_ddf["原因"], orientation="h",
        marker=dict(color="#C0392B", opacity=0.85, line=dict(width=0)),
        text=[f"{v:.0f}%" for v in _ddf["攻擊%"]], textposition="outside",
        textfont=dict(size=10, color="#1C2833", family="Arial"),
        hovertemplate="<b>攻擊</b> %{y}：%{x:.1f}%<extra></extra>",
    ))
    fig_diff.add_trace(go.Bar(
        name="自傷", x=_ddf["自傷%"], y=_ddf["原因"], orientation="h",
        marker=dict(color="#7D3C98", opacity=0.60, line=dict(width=0)),
        text=[f"{v:.0f}%" for v in _ddf["自傷%"]], textposition="outside",
        textfont=dict(size=10, color="#1C2833", family="Arial"),
        hovertemplate="<b>自傷</b> %{y}：%{x:.1f}%<extra></extra>",
    ))
    fig_diff.update_layout(
        barmode="group", height=380,
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        xaxis=dict(title=dict(text="佔比（%）", font=AXIS_TITLE_FONT),
                   tickfont=AXIS_TICK_FONT, gridcolor=GRID_COLOR, griddash="dot",
                   range=[0, 110]),
        yaxis=dict(tickfont=dict(size=10, color="#2C3E50", family="Arial"),
                   automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    font=dict(size=11)),
        margin=dict(t=40, b=40, l=140, r=100),
        bargap=0.2, bargroupgap=0.05,
    )
    st.plotly_chart(fig_diff, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    #  第五區：年齡層 × 傷害類型 熱力圖
    # ════════════════════════════════════════════════════
    st.markdown(
        "<div style='background:#F0F3F4;border-radius:8px;"
        "padding:10px 16px;margin-bottom:12px'>"
        "<span style='font-size:14px;font-weight:700;color:#2C3E50'>"
        "&#128101; 年齡層 × 傷害類型 熱力分析</span>"
        "<span style='font-size:11px;color:#5D6D7E;margin-left:8px'>"
        "隨篩選連動 &#183; 顏色越深件數越多</span></div>",
        unsafe_allow_html=True)
    st.caption("0-18歲自傷佔比高；40歲以上身體攻擊比例相對上升；協助識別各年齡層的主要風險類型")

    _AGE_COL = "發生者資料-年齡"
    if _AGE_COL in _hf.columns:
        _hf_age = _hf.copy()
        _hf_age["年齡層"] = pd.cut(
            pd.to_numeric(_hf_age[_AGE_COL], errors="coerce"),
            bins=[0, 18, 40, 60, 200],
            labels=["0-18歲","18-40歲","40-60歲","60歲以上"],
            right=False,
        )
        _age_type_cols = {
            "身體攻擊": "傷害類型-身體攻擊",
            "自傷":     "傷害類型-自傷",
            "言語衝突": "傷害類型-言語衝突",
            "自殺企圖": "傷害類型-自殺/企圖自殺",
        }
        # 建立 年齡層 × 傷害類型 矩陣
        _age_rows = []
        for age_lbl in ["0-18歲","18-40歲","40-60歲","60歲以上"]:
            _sub = _hf_age[_hf_age["年齡層"] == age_lbl]
            for type_lbl, col in _age_type_cols.items():
                _n = int(_sub[col].fillna(0).sum()) if col in _sub.columns else 0
                _age_rows.append({"年齡層": age_lbl, "傷害類型": type_lbl, "件數": _n})
        _age_df = pd.DataFrame(_age_rows)
        _age_piv = _age_df.pivot(index="年齡層", columns="傷害類型", values="件數").fillna(0)
        # 保持年齡順序
        _age_order = ["0-18歲","18-40歲","40-60歲","60歲以上"]
        _col_order  = ["身體攻擊","自傷","言語衝突","自殺企圖"]
        _age_piv = _age_piv.reindex(index=_age_order,
                                     columns=[c for c in _col_order if c in _age_piv.columns])

        _age_text = [[str(int(v)) if v > 0 else "" for v in row]
                     for row in _age_piv.values]

        fig_age_hm = go.Figure(go.Heatmap(
            z=_age_piv.values,
            x=_age_piv.columns.tolist(),
            y=_age_piv.index.tolist(),
            text=_age_text,
            texttemplate="%{text}",
            textfont=dict(size=13, color="white", family="Arial Bold"),
            colorscale=[
                [0.0,  "#F4F6F6"],
                [0.15, "#D7BDE2"],
                [0.5,  "#7D3C98"],
                [1.0,  "#4A235A"],
            ],
            hovertemplate="<b>%{y}</b> × <b>%{x}</b>：%{z} 件<extra></extra>",
            colorbar=dict(
                title=dict(text="件數", font=dict(size=11, color="#1C2833")),
                tickfont=dict(size=10, color="#2C3E50"),
                thickness=14, len=0.7,
            ),
            xgap=4, ygap=3,
        ))
        fig_age_hm.update_layout(
            height=320,
            paper_bgcolor=PAPER_BG, plot_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="傷害類型", font=AXIS_TITLE_FONT),
                tickfont=dict(size=12, color="#2C3E50", family="Arial"),
                side="bottom",
            ),
            yaxis=dict(
                title=dict(text="年齡層", font=AXIS_TITLE_FONT),
                tickfont=dict(size=12, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=20, b=60, l=100, r=80),
        )
        st.plotly_chart(fig_age_hm, use_container_width=True)
    else:
        st.info("年齡欄位不存在，無法產生熱力圖。")

    st.markdown("<br>", unsafe_allow_html=True)


    # ════════════════════════════════════════════════════
    #  第五區：事件說明高頻詞 Top 15
    # ════════════════════════════════════════════════════

# ── 頁底 ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#4D5656;font-size:12px;padding:8px 0'>
    🏥 國軍花蓮總醫院 病人安全事件儀表板 v3.3 ｜
    資料來源：病人安全通報系統 ｜ 本系統資料僅供內部品質管理使用
</div>""", unsafe_allow_html=True)
